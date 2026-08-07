"""Списание ресурсов при размещении башни и запрет при недостатке средств."""
import pytest

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.entities.turrets import BulletTurret, LaserTurret


@pytest.fixture
def session():
    s = GameSession()
    s.setup_game()
    return s


def test_place_turret_deducts_resources(session):
    credits_before = session.resources.credits
    cost = LaserTurret(Coordinate(0, 0)).cost
    pos = Coordinate(2300, 2000)

    success = session.place_turret("laser", pos)

    assert success is True
    assert session.resources.credits == credits_before - cost
    assert len(session.map.modules) == 1
    assert session.map.modules[0].position == session.map.snap_to_grid(pos)


def test_place_turret_rejected_when_not_enough_resources(session):
    session.resources.credits = 10
    modules_before = len(session.map.modules)

    success = session.place_turret("laser", Coordinate(2300, 2000))

    assert success is False
    assert session.resources.credits == 10, "ресурсы не должны списываться при отказе в размещении"
    assert len(session.map.modules) == modules_before, "башня не должна попасть на карту при отказе"


def test_place_multiple_towers_deducts_cumulatively(session):
    credits_before = session.resources.credits
    laser_cost = LaserTurret(Coordinate(0, 0)).cost
    bullet_cost = BulletTurret(Coordinate(0, 0)).cost

    assert session.place_turret("laser", Coordinate(2300, 2000)) is True
    assert session.place_turret("bullet", Coordinate(2400, 2000)) is True

    assert session.resources.credits == credits_before - laser_cost - bullet_cost
    assert len(session.map.modules) == 2


def test_place_turret_fails_exactly_at_boundary_of_available_credits():
    session = GameSession()
    session.setup_game()
    cost = LaserTurret(Coordinate(0, 0)).cost
    session.resources.credits = cost - 1

    success = session.place_turret("laser", Coordinate(2300, 2000))

    assert success is False
    assert session.resources.credits == cost - 1
