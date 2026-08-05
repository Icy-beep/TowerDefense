"""GameSession + секторы: сетка строится при setup_game, стартовый сектор с базой уже
открыт, unlock_sector_at тратит кредиты и растёт в цене."""
from src.core.coordinate import Coordinate
from src.core.game_session import GameSession


def _session():
    s = GameSession()
    s.setup_game(endless=True)
    return s


def test_setup_game_builds_sector_grid():
    session = _session()

    assert len(session.map.sectors) == session.SECTOR_GRID_SIZE ** 2


def test_setup_game_unlocks_only_the_sector_containing_the_base():
    session = _session()

    unlocked = [s for s in session.map.sectors if s.unlocked]
    assert len(unlocked) == 1
    assert unlocked[0].contains(session.base_position)


def test_sector_unlock_cost_starts_at_base_cost():
    session = _session()

    assert session.sector_unlock_cost() == session.SECTOR_UNLOCK_BASE_COST


def test_sector_unlock_cost_grows_with_each_purchased_sector():
    session = _session()
    locked = next(s for s in session.map.sectors if not s.unlocked)

    session.resources.credits = 100000
    session.unlock_sector_at(Coordinate(locked.bounds[0] + 1, locked.bounds[1] + 1))

    assert session.sector_unlock_cost() == session.SECTOR_UNLOCK_BASE_COST + session.SECTOR_UNLOCK_COST_STEP


def test_unlock_sector_at_spends_credits_and_unlocks():
    session = _session()
    locked = next(s for s in session.map.sectors if not s.unlocked)
    session.resources.credits = 100000
    point = Coordinate(locked.bounds[0] + 1, locked.bounds[1] + 1)
    credits_before = session.resources.credits

    ok = session.unlock_sector_at(point)

    assert ok is True
    assert locked.unlocked is True
    assert session.resources.credits == credits_before - session.SECTOR_UNLOCK_BASE_COST


def test_unlock_sector_at_fails_without_enough_credits():
    session = _session()
    locked = next(s for s in session.map.sectors if not s.unlocked)
    session.resources.credits = 0
    point = Coordinate(locked.bounds[0] + 1, locked.bounds[1] + 1)

    ok = session.unlock_sector_at(point)

    assert ok is False
    assert locked.unlocked is False
    assert session.resources.credits == 0


def test_unlock_sector_at_fails_for_already_unlocked_sector():
    session = _session()
    session.resources.credits = 100000
    credits_before = session.resources.credits

    ok = session.unlock_sector_at(session.base_position)

    assert ok is False
    assert session.resources.credits == credits_before


def test_unlock_sector_at_fails_outside_any_sector():
    session = _session()
    session.resources.credits = 100000

    ok = session.unlock_sector_at(Coordinate(-500, -500))

    assert ok is False
