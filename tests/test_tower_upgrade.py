"""DefenseModule.upgrade()/can_upgrade()/get_upgrade_cost() — рабочий
функционал (апгрейд башен по 'U'), но до сих пор не было ни одного
теста на него."""
import pytest
from src.entities.turrets import LaserTurret
from src.core.coordinate import Coordinate


@pytest.fixture
def turret():
    return LaserTurret(Coordinate(0, 0))


def test_new_turret_starts_at_level_1_and_can_upgrade(turret):
    assert turret.level == 1
    assert turret.can_upgrade() is True


def test_get_upgrade_cost_matches_registered_costs_per_level(turret):
    assert turret.get_upgrade_cost() == turret.upgrade_costs[0]
    turret.upgrade()
    assert turret.get_upgrade_cost() == turret.upgrade_costs[1]


def test_get_upgrade_cost_is_none_at_max_level(turret):
    while turret.can_upgrade():
        turret.upgrade()

    assert turret.level == turret.max_level
    assert turret.can_upgrade() is False
    assert turret.get_upgrade_cost() is None


def test_upgrade_increases_level_and_returns_true(turret):
    assert turret.upgrade() is True
    assert turret.level == 2


def test_upgrade_fails_and_returns_false_at_max_level(turret):
    while turret.can_upgrade():
        turret.upgrade()

    stats_before = (turret.damage, turret.range_radius, turret.attack_speed)
    assert turret.upgrade() is False
    assert turret.level == turret.max_level
    assert (turret.damage, turret.range_radius, turret.attack_speed) == stats_before


def test_upgrade_scales_damage_range_and_attack_speed(turret):
    base_damage = turret.base_damage
    base_range = turret.base_range
    base_speed = turret.base_attack_speed

    turret.upgrade()  # level 2

    assert turret.damage == pytest.approx(base_damage * 1.4)
    assert turret.range_radius == pytest.approx(base_range * 1.2)
    assert turret.attack_speed == pytest.approx(base_speed * 1.25)


def test_upgrade_stats_are_cumulative_not_additive_per_call(turret):
    """Мультипликаторы считаются от level, а не накапливаются поверх уже
    применённого апгрейда — level 3 должен пересчитываться от base_*,
    а не от значений после level 2."""
    turret.upgrade()  # level 2
    turret.upgrade()  # level 3

    assert turret.damage == pytest.approx(turret.base_damage * (1.0 + 2 * 0.4))
    assert turret.range_radius == pytest.approx(turret.base_range * (1.0 + 2 * 0.2))
    assert turret.attack_speed == pytest.approx(turret.base_attack_speed * (1.0 + 2 * 0.25))
