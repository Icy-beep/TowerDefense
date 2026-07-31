"""Фракции врагов (Faction) + поведение ScoutDrone через
HostileEntity.avoids_danger(): разведчик больше не замирает на месте —
его единственная задача - разведка, и как только он попадает в радиус
действия башни, он убегает от неё вместо боя или движения к базе."""
import pytest
from src.entities.enemies import DroneWalker, GiantRoach, ScoutDrone
from src.entities.hostile_entity import HostileEntity
from src.entities.turrets import LaserTurret
from src.core.coordinate import Coordinate
from src.core.map import Map
from src.enums import Faction, ArmorType, DamageType
from src.factories.enemy_factory import EnemyFactory


def test_drone_walker_default_faction_is_corporation():
    assert DroneWalker(Coordinate(0, 0)).faction == Faction.CORPORATION


def test_giant_roach_default_faction_is_fauna():
    assert GiantRoach(Coordinate(0, 0)).faction == Faction.FAUNA


def test_scout_drone_default_faction_is_corporation():
    assert ScoutDrone(Coordinate(0, 0)).faction == Faction.CORPORATION


def test_enemy_factory_reads_faction_from_config_for_all_registered_types():
    factory = EnemyFactory()
    expected = {
        "drone_walker": Faction.CORPORATION,
        "giant_roach": Faction.FAUNA,
        "scout_drone": Faction.CORPORATION,
    }
    for type_name, faction in expected.items():
        enemy = factory.create(type_name, Coordinate(0, 0))
        assert enemy.faction == faction


def test_scout_avoids_danger_returns_true():
    scout = ScoutDrone(Coordinate(0, 0))
    assert scout.avoids_danger() is True


def test_default_enemy_avoids_danger_returns_false():
    assert DroneWalker(Coordinate(0, 0)).avoids_danger() is False
    assert GiantRoach(Coordinate(0, 0)).avoids_danger() is False


def test_scout_act_is_a_no_op():
    scout = ScoutDrone(Coordinate(500, 500))
    scout.act(1.0, in_danger=True)
    assert scout.position == Coordinate(500, 500)
    assert scout.is_moving() is True


def test_map_is_position_covered_true_within_tower_range():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(1000, 1000))  # range_radius=120 по умолчанию
    game_map.modules.append(tower)

    assert game_map.is_position_covered(Coordinate(1050, 1000)) is True
    assert game_map.is_position_covered(Coordinate(5000, 5000)) is False


def test_map_update_moves_scout_away_from_covering_tower():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(1000, 1000))  # range_radius=120 по умолчанию
    game_map.modules.append(tower)

    scout = ScoutDrone(Coordinate(1050, 1000))
    scout.set_path([Coordinate(1500, 1000)])
    game_map.spawn_enemy(scout)

    game_map.update(1.0)

    before_distance = Coordinate(1050, 1000).distance_to(tower.position)
    after_distance = scout.position.distance_to(tower.position)
    assert after_distance > before_distance, "разведчик должен убегать от накрывающей его башни"


def test_map_update_moves_scout_towards_base_when_no_tower_covers_it():
    game_map = Map(width=4000, height=4000)
    scout = ScoutDrone(Coordinate(500, 500))
    scout.set_path([Coordinate(1500, 500)])
    game_map.spawn_enemy(scout)

    game_map.update(1.0)

    assert scout.position.x > 500, "вне зоны действия башен разведчик должен двигаться по маршруту"


def test_hud_selection_panel_shows_enemy_faction():
    from src.ui.hud_renderer import HudRenderer
    import types

    enemy = GiantRoach(Coordinate(0, 0))
    enemy.type_name = "giant_roach"
    controller = types.SimpleNamespace(selected_module=None, selected_enemy=enemy)

    lines = HudRenderer()._build_selection_info({"selected_tower": None, "credits": 0}, controller, [])

    assert any("Фауна планеты" in line for line in lines)


class _AlwaysMovingDummyEnemy(HostileEntity):
    """Минимальная конкретная реализация HostileEntity для проверки, что
    Map.update() по-прежнему вызывает move_along_path для врагов, не
    переопределяющих is_moving() (регрессия для DroneWalker/GiantRoach)."""
    def __init__(self, position):
        super().__init__(position, max_health=10, speed=100, armor=ArmorType.LIGHT, reward=1)
        self.act_calls = []

    def act(self, delta_time, in_danger=False):
        self.act_calls.append(in_danger)

    def take_damage(self, amount, damage_type: DamageType):
        self.health -= amount


def test_map_update_calls_act_with_danger_flag_and_moves_default_enemy():
    game_map = Map(width=4000, height=4000)
    enemy = _AlwaysMovingDummyEnemy(Coordinate(0, 0))
    enemy.set_path([Coordinate(1000, 0)])
    game_map.spawn_enemy(enemy)

    game_map.update(1.0)

    assert enemy.act_calls == [False]
    assert enemy.position.x == pytest.approx(100.0)  # speed=100, dt=1.0


# ----------------------------------------------- гистерезис бегства (граница радиуса)

def test_nearest_covering_tower_respects_optional_margin():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(1000, 1000))  # range_radius=120

    just_outside = Coordinate(1000 + 130, 1000)
    assert game_map._nearest_covering_tower(just_outside) is None, \
        "без запаса точка за пределами обычного радиуса не считается накрытой"

    game_map.modules.append(tower)
    assert game_map._nearest_covering_tower(just_outside) is None
    assert game_map._nearest_covering_tower(just_outside, margin=Map.FLEE_EXIT_MARGIN) is tower


def test_in_flee_danger_only_uses_hysteresis_margin_while_already_fleeing():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(1000, 1000))
    game_map.modules.append(tower)
    scout = ScoutDrone(Coordinate(1000 + 130, 1000))  # за обычным радиусом, но в пределах запаса

    assert game_map._in_flee_danger(scout, in_danger=False, was_fleeing=False) is False, \
        "если враг не убегал и формально не накрыт - в опасности не считается"
    assert game_map._in_flee_danger(scout, in_danger=False, was_fleeing=True) is True, \
        "если враг уже убегал - опасность отступает только за пределами запаса"
    assert game_map._in_flee_danger(scout, in_danger=True, was_fleeing=False) is True, \
        "прямое накрытие всегда считается опасностью, независимо от гистерезиса"


def test_scout_does_not_oscillate_at_the_edge_of_tower_range():
    """Разведчик на самой границе радиуса башни не должен метаться туда-обратно
    между бегством и патрулированием: раз начав убегать, он должен монотонно
    удаляться от башни, а не топтаться ровно на границе."""
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(1000, 1000))  # range_radius=120
    game_map.modules.append(tower)

    scout = ScoutDrone(Coordinate(1000 + 119, 1000))  # чуть внутри радиуса
    scout.set_path([Coordinate(2000, 1000)])
    game_map.spawn_enemy(scout)

    distances = []
    for _ in range(20):
        game_map.update(0.1)
        distances.append(scout.position.distance_to(tower.position))

    assert all(b >= a - 1e-6 for a, b in zip(distances, distances[1:])), \
        "разведчик не должен метаться туда-обратно у границы обстрела"
    assert distances[-1] > tower.range_radius + Map.FLEE_EXIT_MARGIN


def test_scout_flees_a_cluster_of_towers_instead_of_ping_ponging_between_them():
    """Раньше бегство считалось только от ближайшей башни по прямой - в
    кластере из нескольких башен это могло увести разведчика напрямую в
    радиус соседней, и он мог кружить между ними, пока не погибнет. Теперь
    направление бегства учитывает сразу все угрожающие башни и должно
    в итоге вывести разведчика за пределы радиуса (+ запас) обеих."""
    game_map = Map(width=4000, height=4000)
    tower_a = LaserTurret(Coordinate(950, 1000))  # range_radius=120
    tower_b = LaserTurret(Coordinate(1050, 1000))  # соседняя башня рядом
    game_map.modules.append(tower_a)
    game_map.modules.append(tower_b)

    scout = ScoutDrone(Coordinate(1000, 1000))  # ровно между башнями, внутри обеих
    # Путь в ту же сторону, куда логично убегать (перпендикулярно линии
    # башен) - иначе без base_position "движение к базе" после бегства
    # наивно потащит разведчика обратно по прямой прямо в кластер башен,
    # что проверяло бы уже другой сценарий, а не механику самого бегства.
    scout.set_path([Coordinate(1000, 3000)])
    game_map.spawn_enemy(scout)

    for _ in range(200):
        game_map.update(0.05)

    assert scout.position.distance_to(tower_a.position) > tower_a.range_radius + Map.FLEE_EXIT_MARGIN
    assert scout.position.distance_to(tower_b.position) > tower_b.range_radius + Map.FLEE_EXIT_MARGIN


def test_flee_target_pushes_away_from_all_covering_towers_combined():
    game_map = Map(width=4000, height=4000)
    tower_a = LaserTurret(Coordinate(900, 1000))
    tower_b = LaserTurret(Coordinate(1100, 1000))  # башни по разные стороны от врага

    target = game_map._flee_target_from_towers(Coordinate(1000, 1000), [tower_a, tower_b])

    # силы от симметрично расположенных башен вдоль X должны погаситься по X
    # и вытолкнуть врага перпендикулярно (по Y), а не оставить на месте
    assert target.y != pytest.approx(1000.0)


def test_scout_does_not_repeatedly_walk_back_into_the_same_tower_on_its_way_to_base():
    """Раньше после бегства разведчик возобновлял старый маршрут, который
    мог по-прежнему срезать через радиус той же башни (мягкое избегание при
    построении пути это допускает, если так короче) - он заходил в радиус,
    получал выстрел, убегал, и снова возвращался тем же путём. Теперь путь
    строится заново от безопасной точки сразу после бегства, с жёстким
    запретом простреливаемых клеток для разведчика."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 200)
    tower = LaserTurret(Coordinate(2000, 1000))  # range_radius=120, прямо на линии до базы
    game_map.modules.append(tower)

    scout = ScoutDrone(Coordinate(2000, 1800))
    scout.set_path([Coordinate(2000, 200)])  # "наивный" путь напрямик - башня ещё не видна
    game_map.spawn_enemy(scout)

    flee_transitions = 0
    was_fleeing = False
    for _ in range(600):
        game_map.update(0.05)
        if scout.is_fleeing and not was_fleeing:
            flee_transitions += 1
        was_fleeing = scout.is_fleeing

    # Полностью нулевого касания не гарантировать - клетки навигационной
    # сетки квадратные, а радиус башни круглый, так что путь у самой
    # границы иногда может на мгновение задеть окружность между двумя
    # соседними, формально безопасными узлами. Важно, что это единичные
    # касания при обходе, а не бесконечное хождение туда-обратно.
    assert flee_transitions <= 4, \
        f"разведчик не должен заходить в радиус одной и той же башни снова и снова (было {flee_transitions} раз)"


def test_scout_is_fleeing_flag_tracks_flee_state():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(1000, 1000))
    game_map.modules.append(tower)

    scout = ScoutDrone(Coordinate(1000 + 50, 1000))  # глубоко внутри радиуса
    scout.set_path([Coordinate(2000, 1000)])
    game_map.spawn_enemy(scout)

    assert scout.is_fleeing is False
    game_map.update(0.1)
    assert scout.is_fleeing is True

    scout.position = Coordinate(5000, 5000)  # телепортируем далеко от всех башен
    game_map.update(0.1)
    assert scout.is_fleeing is False
