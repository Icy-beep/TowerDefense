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
