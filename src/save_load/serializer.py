"""Сериализация GameSession в/из простого JSON-совместимого словаря.

Практичный набор состояния (см. обсуждение с пользователем при добавлении save/load):
башни (тип/уровень/HP/позиция), враги (тип/HP/позиция/прогресс по пути), гнёзда
фауны, ресурсы, пройденное время, здоровье базы. Снаряды в полёте и мелкие
переходные таймеры ИИ (уклонение, разведка, формации групп, точный кулдаун
следующего спавна) не сохраняются - они длятся секунды и просто начинаются
заново после загрузки, разницы не заметно. Исключение - ThreatStrategy.elapsed
(прогресс эскалации спавна): без него после загрузки долгой партии враги вдруг
начали бы спавниться заметно медленнее, чем должны на этом этапе - это уже
заметная разница, поэтому его сохраняем.

apply_dict_to_session переиспользует GameSession.setup_game() для правильной
инициализации карты, источников угроз, точек спавна и заданий, а затем подменяет
содержимое сохранёнными значениями - так восстановление всегда остаётся в
синхроне с логикой обычного старта игры, даже если она поменяется в будущем."""
from src.core.coordinate import Coordinate
from src.entities.fauna_nest import FaunaNest
from src.enums import Faction

SAVE_FORMAT_VERSION = 1


def session_to_dict(session) -> dict:
    """Собирает снимок состояния игры в словарь, пригодный для json.dump."""
    game_map = session.map
    return {
        "version": SAVE_FORMAT_VERSION,
        "endless": session.endless,
        "elapsed_time": session.elapsed_time,
        "survive_duration_target": session.survive_duration_target,
        "base_health": session.base_health,
        "max_base_health": session.max_base_health,
        "credits": session.resources.credits,
        "scrap": session.resources.scrap,
        "tech_tree": session.tech_tree.levels,
        "ai_module_stock": session.ai_module_stock,
        "map": {
            "width": game_map.width,
            "height": game_map.height,
            "towers_lost_count": game_map.towers_lost_count,
            "modules": [_module_to_dict(module) for module in game_map.modules],
            "enemies": [_enemy_to_dict(enemy) for enemy in game_map.enemies
                        if enemy.is_alive() and getattr(enemy, "type_name", None)],
            "fauna_nests": [_nest_to_dict(nest) for nest in game_map.fauna_nests if nest.is_alive()],
            "unlocked_sectors": [[sector.row, sector.col] for sector in game_map.sectors if sector.unlocked],
            "threat_strategy_elapsed": {
                faction.value: getattr(strategy, "elapsed", 0.0)
                for faction, strategy in session.threat_strategies.items()
            },
        },
    }


def _module_to_dict(module) -> dict:
    """Сериализует одну башню: тип, позиция, HP и установленный ИИ-модуль (см.
    DefenseModule.ai_module - привязан к конкретной башне, в отличие от дерева
    технологий). Урон/радиус/скорострельность не сохраняются - их пересчитает
    apply_dict_to_session из session["tech_tree"] (см. TechTree.apply_to)."""
    return {
        "type": module.type_name,
        "x": module.position.x,
        "y": module.position.y,
        "health": module.health,
        "ai_module": module.ai_module,
    }


def _enemy_to_dict(enemy) -> dict:
    """Сериализует одного врага: тип, позиция, HP и прогресс по индексу пути (сам
    путь при загрузке прокладывается заново - см. apply_dict_to_session)."""
    return {
        "type": enemy.type_name,
        "x": enemy.position.x,
        "y": enemy.position.y,
        "health": enemy.health,
        "path_index": enemy.path_index,
    }


def _nest_to_dict(nest) -> dict:
    """Сериализует одно гнездо фауны: позиция, текущее и макс. здоровье, награда."""
    return {
        "x": nest.position.x,
        "y": nest.position.y,
        "health": nest.health,
        "max_health": nest.max_health,
        "reward": nest.reward,
    }


def apply_dict_to_session(session, data: dict) -> None:
    """Восстанавливает игровую сессию из словаря, полученного session_to_dict."""
    endless = bool(data.get("endless", False))
    session.setup_game(endless=endless)

    session.elapsed_time = data.get("elapsed_time", 0.0)
    session.max_base_health = data.get("max_base_health", session.max_base_health)
    session.base_health = data.get("base_health", session.max_base_health)
    session.resources.credits = data.get("credits", session.resources.credits)
    session.resources.scrap = data.get("scrap", 0)
    # До восстановления башен ниже - _restore_module применяет текущие уровни
    # дерева технологий к каждой пересозданной башне (см. TechTree.apply_to).
    session.tech_tree.levels = {
        tower_type: dict(branches) for tower_type, branches in data.get("tech_tree", {}).items()
    }
    session.ai_module_stock = dict(data.get("ai_module_stock", {}))

    map_data = data.get("map", {})
    game_map = session.map
    game_map.towers_lost_count = map_data.get("towers_lost_count", 0)

    game_map.modules = []
    for entry in map_data.get("modules", []):
        _restore_module(session, game_map, entry)

    game_map.enemies = []
    for entry in map_data.get("enemies", []):
        _restore_enemy(session, game_map, entry)

    game_map.fauna_nests = []
    for entry in map_data.get("fauna_nests", []):
        _restore_nest(game_map, entry)
    game_map.spawn_points_by_faction[Faction.FAUNA] = [nest.position for nest in game_map.fauna_nests]

    # setup_game() уже построил свежую сетку секторов (только стартовый открыт) -
    # без этого прогресс открытия карты (см. src/systems/sector.py) молча терялся бы
    # при каждой загрузке.
    unlocked_sectors = {tuple(pair) for pair in map_data.get("unlocked_sectors", [])}
    for sector in game_map.sectors:
        if (sector.row, sector.col) in unlocked_sectors:
            sector.unlocked = True

    strategy_elapsed = map_data.get("threat_strategy_elapsed", {})
    for faction, strategy in session.threat_strategies.items():
        if hasattr(strategy, "elapsed") and faction.value in strategy_elapsed:
            strategy.elapsed = strategy_elapsed[faction.value]


def _restore_module(session, game_map, entry: dict) -> None:
    """Пересоздаёт башню через TowerFactory (правильные базовые характеристики из
    конфига) и применяет к ней уже восстановленные уровни дерева технологий (см.
    apply_dict_to_session, TechTree.apply_to)."""
    module = session.tower_factory.create(entry["type"], Coordinate(entry["x"], entry["y"]))
    if module is None:
        return
    session.tech_tree.apply_to(module)
    module.health = entry.get("health", module.max_health)
    module.ai_module = entry.get("ai_module")
    game_map.add_module(module)


def _restore_enemy(session, game_map, entry: dict) -> None:
    """Пересоздаёт врага через EnemyFactory и прокладывает ему путь к базе заново
    (см. модульный докстринг - путь не сериализуется)."""
    enemy = session.enemy_factory.create(entry["type"], Coordinate(entry["x"], entry["y"]))
    if enemy is None:
        return
    enemy.health = entry.get("health", enemy.max_health)
    enemy.path_index = entry.get("path_index", 0)
    enemy.path = game_map.path_to_base(enemy.position, enemy.faction)
    game_map.spawn_enemy(enemy)


def _restore_nest(game_map, entry: dict) -> None:
    """Пересоздаёт гнездо фауны с сохранённым здоровьем."""
    nest = FaunaNest(Coordinate(entry["x"], entry["y"]),
                      max_health=entry.get("max_health", 150.0),
                      reward=entry.get("reward", 200))
    nest.health = entry.get("health", nest.max_health)
    game_map.add_fauna_nest(nest)
