"""Фракции врагов (Faction) + поведение ScoutDrone через
HostileEntity.act()/is_moving(): вместо одноразовой паузы у спавна,
разведчик может в любой точке маршрута случайно остановиться на
разведку — но только пока НЕ в радиусе действия ни одной башни. Если
башня "накрывает" его позицию — разведка прерывается."""
import random
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


class _AlwaysScoutRng:
    """Фейковый rng: random() всегда 0.0 (< любой положительный шанс —
    разведка гарантированно начинается), uniform всегда возвращает max."""
    def random(self):
        return 0.0

    def uniform(self, a, b):
        return b


class _NeverScoutRng:
    """random() всегда 1.0 — разведка никогда не начинается."""
    def random(self):
        return 1.0

    def uniform(self, a, b):
        return a


def test_scout_starts_scouting_when_roll_succeeds_and_not_in_danger():
    scout = ScoutDrone(Coordinate(0, 0), rng=_AlwaysScoutRng())

    scout.act(1.0, in_danger=False)

    assert scout.is_scouting is True
    assert scout.is_moving() is False


def test_scout_does_not_start_scouting_when_roll_fails():
    scout = ScoutDrone(Coordinate(0, 0), rng=_NeverScoutRng())

    scout.act(1.0, in_danger=False)

    assert scout.is_scouting is False
    assert scout.is_moving() is True


def test_scout_never_starts_scouting_while_in_danger():
    scout = ScoutDrone(Coordinate(0, 0), rng=_AlwaysScoutRng())

    scout.act(1.0, in_danger=True)

    assert scout.is_scouting is False, "не должен начинать разведку в радиусе башни"


def test_scout_scouting_interrupted_when_tower_starts_covering_it():
    scout = ScoutDrone(Coordinate(0, 0), rng=_AlwaysScoutRng())
    scout.act(1.0, in_danger=False)
    assert scout.is_scouting is True

    scout.act(0.1, in_danger=True)  # башню только что построили рядом

    assert scout.is_scouting is False
    assert scout.is_moving() is True


def test_scout_scouting_expires_naturally_over_time():
    scout = ScoutDrone(Coordinate(0, 0), rng=_AlwaysScoutRng())
    scout.act(1.0, in_danger=False)
    duration = scout.scout_timer
    assert duration > 0

    scout.act(duration + 0.1, in_danger=False)

    assert scout.is_scouting is False
    assert scout.is_moving() is True


def test_scout_recon_duration_is_within_configured_bounds():
    scout = ScoutDrone(Coordinate(0, 0), rng=_AlwaysScoutRng())
    scout.act(1.0, in_danger=False)

    assert ScoutDrone.MIN_SCOUT_TIME <= scout.scout_timer <= ScoutDrone.MAX_SCOUT_TIME


def test_map_is_position_covered_true_within_tower_range():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(1000, 1000))  # range_radius=120 по умолчанию
    game_map.modules.append(tower)

    assert game_map.is_position_covered(Coordinate(1050, 1000)) is True
    assert game_map.is_position_covered(Coordinate(5000, 5000)) is False


def test_map_update_does_not_move_scouting_enemy():
    game_map = Map(width=4000, height=4000)
    scout = ScoutDrone(Coordinate(500, 500), rng=_AlwaysScoutRng())
    scout.set_path([Coordinate(1500, 500)])
    game_map.spawn_enemy(scout)

    game_map.update(1.0)

    assert scout.position == Coordinate(500, 500), "во время разведки враг не должен двигаться"
    assert scout in game_map.enemies


def test_map_update_moves_non_scouting_enemy():
    game_map = Map(width=4000, height=4000)
    scout = ScoutDrone(Coordinate(500, 500), rng=_NeverScoutRng())
    scout.set_path([Coordinate(1500, 500)])
    game_map.spawn_enemy(scout)

    game_map.update(1.0)

    assert scout.position.x > 500


def test_map_update_interrupts_scouting_near_newly_built_tower():
    game_map = Map(width=4000, height=4000)
    scout = ScoutDrone(Coordinate(500, 500), rng=_AlwaysScoutRng())
    scout.set_path([Coordinate(1500, 500)])
    game_map.spawn_enemy(scout)
    game_map.update(1.0)  # начал разведку
    assert scout.is_scouting is True

    game_map.modules.append(LaserTurret(Coordinate(510, 500)))  # башня рядом
    game_map.update(0.1)

    assert scout.is_scouting is False


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
