"""Высадка башни с орбиты: падение, неуязвимость, урон при приземлении."""
from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import DroneWalker
from src.entities.power_generator import PowerGenerator
from src.entities.power_pylon import PowerPylon
from src.entities.turrets import LaserTurret, MortarTurret
from src.enums import DamageType


def _enemy(x, y, health=1000):
    e = DroneWalker(Coordinate(x, y))
    e.health = health
    e.max_health = health
    e.set_path([Coordinate(x + 100000, y)])
    return e


def test_start_landing_sets_initial_falling_state():
    turret = LaserTurret(Coordinate(0, 0))

    turret.start_landing()

    assert turret.is_landing is True
    assert turret.landing_elapsed == 0.0
    assert turret.landing_height == turret.LANDING_START_HEIGHT


def test_turret_does_not_fire_while_landing_even_with_target_in_range():
    turret = LaserTurret(Coordinate(0, 0))
    turret.cooldown_timer = 0
    turret.start_landing()
    target = _enemy(50, 0)

    projectile = turret.update(0.1, [target])

    assert projectile is None


def test_turret_is_invulnerable_while_landing():
    turret = LaserTurret(Coordinate(0, 0))
    turret.start_landing()

    turret.take_damage(1000, DamageType.KINETIC)

    assert turret.health == turret.max_health


def test_turret_takes_damage_normally_after_landing_completes():
    turret = LaserTurret(Coordinate(0, 0))
    turret.start_landing()
    turret.update(turret.LANDING_DURATION + 0.1, [])

    turret.take_damage(30, DamageType.KINETIC)

    assert turret.health == turret.max_health - 30


def test_landing_height_decreases_to_zero_over_landing_duration():
    turret = LaserTurret(Coordinate(0, 0))
    turret.start_landing()

    turret.update(turret.LANDING_DURATION / 2, [])
    mid_height = turret.landing_height
    assert 0.0 < mid_height < turret.LANDING_START_HEIGHT

    turret.update(turret.LANDING_DURATION, [])
    assert turret.is_landing is False
    assert turret.landing_height == 0.0


def test_landing_completion_is_reported_exactly_once():
    turret = LaserTurret(Coordinate(0, 0))
    turret.start_landing()
    turret.update(turret.LANDING_DURATION + 0.1, [])

    assert turret.take_landing_event() is True
    assert turret.take_landing_event() is False


def test_turret_can_fire_normally_once_landing_completes():
    turret = LaserTurret(Coordinate(0, 0))
    turret.cooldown_timer = 0
    turret.start_landing()
    turret.update(turret.LANDING_DURATION + 0.1, [])

    target = _enemy(50, 0)
    projectile = turret.update(0.0, [target])

    assert projectile is not None


def test_landing_impact_damages_enemies_within_radius():
    turret = MortarTurret(Coordinate(0, 0))
    turret.start_landing()
    close_enemy = _enemy(20, 0)
    far_enemy = _enemy(turret.LANDING_IMPACT_RADIUS + 50, 0)

    turret.update(turret.LANDING_DURATION + 0.1, [close_enemy, far_enemy])

    assert close_enemy.health == 1000 - turret.damage * 2
    assert far_enemy.health == 1000


def test_landing_impact_ignores_already_dead_enemies():
    turret = LaserTurret(Coordinate(0, 0))
    turret.start_landing()
    dead_enemy = _enemy(10, 0)
    dead_enemy.health = 0

    turret.update(turret.LANDING_DURATION + 0.1, [dead_enemy])

    assert dead_enemy.health == 0


def test_power_infrastructure_landing_does_not_crash_or_damage_nearby_enemies():
    """Регрессия: PowerPylon/PowerGenerator никогда не задают self.damage_type (см.
    PowerInfrastructure - damage=0.0, они не умеют атаковать), а _deal_landing_impact
    раньше безусловно к нему обращался - приземление рядом с врагом роняло игру
    с AttributeError."""
    for tower in (PowerPylon(Coordinate(0, 0)), PowerGenerator(Coordinate(0, 0))):
        tower.start_landing()
        nearby_enemy = _enemy(10, 0)

        tower.update(tower.LANDING_DURATION + 0.1, [nearby_enemy])

        assert nearby_enemy.health == 1000


def test_map_emits_tower_placed_only_after_the_module_lands():
    events = []
    game_map = Map(width=4000, height=4000, on_event=lambda name, **data: events.append((name, data)))
    turret = LaserTurret(Coordinate(0, 0))
    turret.type_name = "laser"
    turret.start_landing()
    game_map.modules.append(turret)

    game_map.update(0.1)
    assert not any(e[0] == "tower_placed" for e in events), "звук установки не должен играть, пока башня ещё падает"

    for _ in range(50):
        game_map.update(0.1)

    placed = [e for e in events if e[0] == "tower_placed"]
    assert len(placed) == 1
    assert placed[0][1] == {"tower_type": "laser", "position": turret.position}
