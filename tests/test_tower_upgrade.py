"""TechTree - апгрейды веток дерева технологий, общие на весь тип башни (см.
src/systems/tech_tree.py). Замена старой прокачки по 'U', привязанной к одной
конкретной поставленной башне."""
import pytest

from src.systems.tech_tree import TechTree

UPGRADE_COSTS = [80, 120]


@pytest.fixture
def tree():
    return TechTree()


def test_new_tree_starts_at_level_zero_for_any_type_and_branch(tree):
    assert tree.level_for("laser", "damage") == 0
    assert tree.multiplier_for("laser", "damage") == 1.0


def test_upgrade_cost_matches_registered_costs_per_level(tree):
    assert tree.upgrade_cost("laser", "damage", UPGRADE_COSTS) == UPGRADE_COSTS[0]
    tree.upgrade("laser", "damage")
    assert tree.upgrade_cost("laser", "damage", UPGRADE_COSTS) == UPGRADE_COSTS[1]


def test_upgrade_cost_is_none_at_max_level(tree):
    tree.upgrade("laser", "damage")
    tree.upgrade("laser", "damage")

    assert tree.level_for("laser", "damage") == len(UPGRADE_COSTS)
    assert tree.upgrade_cost("laser", "damage", UPGRADE_COSTS) is None


def test_upgrade_increases_level(tree):
    tree.upgrade("laser", "damage")
    assert tree.level_for("laser", "damage") == 1


def test_branches_and_types_are_independent(tree):
    """Апгрейд одной ветки/типа не должен затрагивать другие ветки или другие типы."""
    tree.upgrade("laser", "damage")

    assert tree.level_for("laser", "radius") == 0
    assert tree.level_for("laser", "attack_speed") == 0
    assert tree.level_for("bullet", "damage") == 0


def test_multiplier_scales_with_level_per_branch(tree):
    tree.upgrade("laser", "radius")
    tree.upgrade("laser", "damage")
    tree.upgrade("laser", "damage")

    assert tree.multiplier_for("laser", "radius") == pytest.approx(1.0 + 1 * 0.2)
    assert tree.multiplier_for("laser", "damage") == pytest.approx(1.0 + 2 * 0.4)
    assert tree.multiplier_for("laser", "attack_speed") == pytest.approx(1.0)


def test_apply_to_recomputes_stats_from_base_values():
    from src.core.coordinate import Coordinate
    from src.entities.turrets import LaserTurret

    tree = TechTree()
    turret = LaserTurret(Coordinate(0, 0))
    turret.type_name = "laser"
    tree.upgrade("laser", "damage")

    tree.apply_to(turret)

    assert turret.damage == pytest.approx(turret.base_damage * 1.4)
    assert turret.range_radius == pytest.approx(turret.base_range)
    assert turret.attack_speed == pytest.approx(turret.base_attack_speed)
