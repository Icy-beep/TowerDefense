"""Сериализация GameSession: session_to_dict/apply_dict_to_session должны давать
практичный (см. docstring serializer.py), но полный по составу round-trip."""
import pytest

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.enums import Faction
from src.save_load.serializer import SAVE_FORMAT_VERSION, apply_dict_to_session, session_to_dict


@pytest.fixture
def session():
    s = GameSession()
    s.setup_game(endless=True)
    return s


def _place_tower(session, tower_type="bullet", offset=(300, 0)):
    """Создаёт и добавляет на карту башню заданного типа рядом с базой, применяя
    текущие уровни дерева технологий (см. TechTree.apply_to)."""
    base = session.base_position
    position = session.map.snap_to_grid(Coordinate(base.x + offset[0], base.y + offset[1]))
    tower = session.tower_factory.create(tower_type, position)
    session.tech_tree.apply_to(tower)
    session.map.add_module(tower)
    return tower


def _spawn_enemy(session, enemy_type="drone_walker", offset=(1000, 0)):
    """Создаёт и добавляет на карту врага заданного типа рядом с базой."""
    base = session.base_position
    position = Coordinate(base.x + offset[0], base.y + offset[1])
    enemy = session.enemy_factory.create(enemy_type, position)
    enemy.path = session.map.path_to_base(position, enemy.faction)
    session.map.spawn_enemy(enemy)
    return enemy


def test_session_to_dict_includes_format_version(session):
    data = session_to_dict(session)

    assert data["version"] == SAVE_FORMAT_VERSION
    assert data["endless"] is True


def test_round_trip_restores_resources_and_progress(session):
    session.resources.credits = 1234
    session.resources.scrap = 5
    session.elapsed_time = 42.5
    session.base_health = 77
    session.map.towers_lost_count = 3

    data = session_to_dict(session)
    restored = GameSession()
    apply_dict_to_session(restored, data)

    assert restored.resources.credits == 1234
    assert restored.resources.scrap == 5
    assert restored.elapsed_time == 42.5
    assert restored.base_health == 77
    assert restored.endless is True
    assert restored.map.towers_lost_count == 3


def test_round_trip_restores_tower_type_and_health(session):
    tower = _place_tower(session, "laser")
    tower.health = 40.0

    data = session_to_dict(session)
    restored = GameSession()
    apply_dict_to_session(restored, data)

    assert len(restored.map.modules) == 1
    restored_tower = restored.map.modules[0]
    assert restored_tower.type_name == "laser"
    assert restored_tower.health == 40.0


def test_round_trip_restores_tech_tree_levels_and_reapplies_them_to_towers(session):
    """Апгрейды дерева технологий общие на тип (см. TechTree) - после загрузки
    сохранённого уровня характеристики восстановленной башни должны совпадать с
    тем, что дал бы тот же апгрейд заново, а не сбрасываться в базовые значения."""
    session.resources.credits = 10_000
    session.upgrade_tech_branch("laser", "damage")
    tower = _place_tower(session, "laser")

    data = session_to_dict(session)
    restored = GameSession()
    apply_dict_to_session(restored, data)

    assert restored.tech_tree.level_for("laser", "damage") == 1
    restored_tower = restored.map.modules[0]
    assert restored_tower.damage == pytest.approx(tower.damage)
    assert restored_tower.damage == pytest.approx(restored_tower.base_damage * 1.4)


def test_round_trip_restores_enemy_type_health_and_recomputes_path(session):
    enemy = _spawn_enemy(session, "giant_roach")
    enemy.health = 3.0

    data = session_to_dict(session)
    restored = GameSession()
    apply_dict_to_session(restored, data)

    assert len(restored.map.enemies) == 1
    restored_enemy = restored.map.enemies[0]
    assert restored_enemy.type_name == "giant_roach"
    assert restored_enemy.health == 3.0
    # Путь не сериализуется - он должен быть проложен заново при восстановлении.
    assert restored_enemy.path == restored.map.path_to_base(restored_enemy.position, restored_enemy.faction)


def test_dead_enemies_and_nests_are_not_serialized(session):
    enemy = _spawn_enemy(session)
    enemy.health = 0.0

    data = session_to_dict(session)

    assert data["map"]["enemies"] == []


def test_round_trip_restores_fauna_nests_and_spawn_points(session):
    original_nests = session.map.fauna_nests
    assert original_nests, "setup_game должен создавать хотя бы одно гнездо фауны"
    original_nests[0].health = 10.0

    data = session_to_dict(session)
    restored = GameSession()
    apply_dict_to_session(restored, data)

    assert len(restored.map.fauna_nests) == len(original_nests)
    assert restored.map.fauna_nests[0].health == 10.0
    restored_spawn_positions = restored.map.spawn_points_by_faction[Faction.FAUNA]
    assert restored_spawn_positions == [nest.position for nest in restored.map.fauna_nests]


def test_round_trip_restores_threat_strategy_elapsed(session):
    session.threat_strategies[Faction.CORPORATION].elapsed = 99.0
    session.threat_strategies[Faction.FAUNA].elapsed = 12.0

    data = session_to_dict(session)
    restored = GameSession()
    apply_dict_to_session(restored, data)

    assert restored.threat_strategies[Faction.CORPORATION].elapsed == 99.0
    assert restored.threat_strategies[Faction.FAUNA].elapsed == 12.0


def test_round_trip_restores_unlocked_sectors(session):
    locked = next(s for s in session.map.sectors if not s.unlocked)
    session.resources.credits = 100000
    ok = session.unlock_sector_at(Coordinate(locked.bounds[0] + 1, locked.bounds[1] + 1))
    assert ok is True

    data = session_to_dict(session)
    restored = GameSession()
    apply_dict_to_session(restored, data)

    restored_sector = next(s for s in restored.map.sectors if s.row == locked.row and s.col == locked.col)
    assert restored_sector.unlocked is True
    # Остальные (не открытые вручную) секторы, кроме стартового, должны остаться закрытыми.
    still_locked = [s for s in restored.map.sectors
                     if (s.row, s.col) not in {(locked.row, locked.col)} and not s.contains(restored.base_position)]
    assert all(not s.unlocked for s in still_locked)


def test_apply_dict_to_session_defaults_missing_fields_gracefully():
    """Минимальный словарь (как будто из более старой/урезанной версии формата) не
    должен приводить к падению - только к разумным значениям по умолчанию."""
    restored = GameSession()
    apply_dict_to_session(restored, {"version": SAVE_FORMAT_VERSION, "endless": False})

    assert restored.map.modules == []
    assert restored.map.enemies == []
    assert restored.elapsed_time == 0.0
