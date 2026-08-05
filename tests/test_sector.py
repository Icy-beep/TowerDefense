"""Sector/build_sector_grid: разбиение карты на сетку, открытие стартового сектора."""
from src.core.coordinate import Coordinate
from src.systems.sector import Sector, build_sector_grid


def test_build_sector_grid_creates_grid_size_squared_sectors():
    sectors = build_sector_grid(900, 900, grid_size=3)

    assert len(sectors) == 9


def test_sectors_cover_the_map_without_gaps_or_overlaps():
    sectors = build_sector_grid(900, 900, grid_size=3)

    for x in range(0, 900, 37):
        for y in range(0, 900, 41):
            owners = [s for s in sectors if s.contains(Coordinate(x, y))]
            assert len(owners) == 1, f"точка ({x},{y}) должна принадлежать ровно одному сектору"


def test_last_row_and_column_stretch_to_the_exact_map_edge():
    sectors = build_sector_grid(1000, 700, grid_size=3)

    max_x = max(s.bounds[2] for s in sectors)
    max_y = max(s.bounds[3] for s in sectors)
    assert max_x == 1000
    assert max_y == 700
    # точка почти у самого края всё ещё должна принадлежать какому-то сектору
    edge_owners = [s for s in sectors if s.contains(Coordinate(999.9, 699.9))]
    assert len(edge_owners) == 1


def test_sector_containing_base_starts_unlocked():
    sectors = build_sector_grid(900, 900, grid_size=3, base_position=Coordinate(450, 450))

    unlocked = [s for s in sectors if s.unlocked]
    assert len(unlocked) == 1
    assert unlocked[0].contains(Coordinate(450, 450))


def test_all_other_sectors_start_locked():
    sectors = build_sector_grid(900, 900, grid_size=3, base_position=Coordinate(450, 450))

    locked = [s for s in sectors if not s.unlocked]
    assert len(locked) == 8


def test_without_base_position_everything_starts_locked():
    sectors = build_sector_grid(900, 900, grid_size=3)

    assert all(not s.unlocked for s in sectors)


def test_sector_contains_respects_half_open_bounds():
    sector = Sector(row=0, col=0, bounds=(0.0, 0.0, 300.0, 300.0))

    assert sector.contains(Coordinate(0.0, 0.0)) is True
    assert sector.contains(Coordinate(299.9, 299.9)) is True
    assert sector.contains(Coordinate(300.0, 0.0)) is False, "правая граница принадлежит следующему сектору"
    assert sector.contains(Coordinate(0.0, 300.0)) is False, "нижняя граница принадлежит следующему сектору"
