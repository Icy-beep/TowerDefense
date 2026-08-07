"""Привязка построек к сетке (Map.snap_to_grid) вместо произвольной точки."""
import pytest

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.core.map import Map


@pytest.fixture
def session():
    s = GameSession()
    s.setup_game()
    return s


def test_snap_to_grid_snaps_to_cell_center():
    game_map = Map(width=4000, height=4000)
    cell = game_map.nav_grid.cell_size

    snapped = game_map.snap_to_grid(Coordinate(cell * 3 + 5, cell * 7 + 5))

    assert snapped.x == pytest.approx(cell * 3 + cell / 2)
    assert snapped.y == pytest.approx(cell * 7 + cell / 2)


def test_snap_to_grid_is_idempotent():
    game_map = Map(width=4000, height=4000)
    once = game_map.snap_to_grid(Coordinate(777, 1234))
    twice = game_map.snap_to_grid(once)

    assert once == twice


def test_two_nearby_clicks_in_same_cell_snap_to_identical_position():
    game_map = Map(width=4000, height=4000)
    cell = game_map.nav_grid.cell_size
    cell_start = cell * 3

    a = game_map.snap_to_grid(Coordinate(cell_start, cell_start))
    b = game_map.snap_to_grid(Coordinate(cell_start + cell - 1, cell_start + cell - 1))

    assert a == b


def test_place_turret_snaps_position_to_grid(session):
    cell = session.map.nav_grid.cell_size
    off_grid_pos = Coordinate(2300 + 3, 2000 + 3)

    success = session.place_turret("laser", off_grid_pos)

    assert success is True
    placed = session.map.modules[0].position
    expected = session.map.snap_to_grid(off_grid_pos)
    assert placed == expected
    assert placed != off_grid_pos
