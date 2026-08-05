"""Интеграция Sector в Map: поиск сектора по точке, разблокировка, гейтинг постройки
и точек спавна фауны."""
from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.fauna_nest import FaunaNest
from src.systems.sector import Sector, build_sector_grid


def test_map_without_sectors_treats_everything_as_unlocked():
    """Обратная совместимость: Map(), созданная напрямую без setup_game (как в
    большинстве существующих тестов), не должна внезапно всё запрещать."""
    game_map = Map(width=4000, height=4000)

    assert game_map.sectors == []
    assert game_map.sector_at(Coordinate(100, 100)) is None
    assert game_map.is_position_unlocked(Coordinate(100, 100)) is True


def test_sector_at_finds_the_right_sector():
    game_map = Map(width=900, height=900)
    game_map.sectors = build_sector_grid(900, 900, grid_size=3)

    found = game_map.sector_at(Coordinate(450, 450))

    assert found is not None
    assert found.row == 1 and found.col == 1


def test_is_position_unlocked_reflects_sector_state():
    game_map = Map(width=900, height=900)
    game_map.sectors = build_sector_grid(900, 900, grid_size=3, base_position=Coordinate(450, 450))

    assert game_map.is_position_unlocked(Coordinate(450, 450)) is True  # стартовый сектор
    assert game_map.is_position_unlocked(Coordinate(50, 50)) is False  # угловой сектор


def test_can_place_module_rejects_locked_sector():
    game_map = Map(width=900, height=900)
    game_map.sectors = build_sector_grid(900, 900, grid_size=3, base_position=Coordinate(450, 450))

    assert game_map.can_place_module(Coordinate(50, 50)) is False


def test_can_place_module_allows_unlocked_sector():
    game_map = Map(width=900, height=900)
    game_map.sectors = build_sector_grid(900, 900, grid_size=3, base_position=Coordinate(450, 450))

    assert game_map.can_place_module(Coordinate(450, 450)) is True


def test_can_place_module_allows_locked_sector_once_it_is_unlocked():
    game_map = Map(width=900, height=900)
    game_map.sectors = build_sector_grid(900, 900, grid_size=3, base_position=Coordinate(450, 450))
    sector = game_map.sector_at(Coordinate(50, 50))
    sector.unlocked = True

    assert game_map.can_place_module(Coordinate(50, 50)) is True


def test_unlocked_fauna_spawn_points_excludes_nests_in_locked_sectors():
    game_map = Map(width=900, height=900)
    game_map.sectors = build_sector_grid(900, 900, grid_size=3, base_position=Coordinate(450, 450))

    nest_in_start_sector = FaunaNest(Coordinate(450, 450))
    nest_in_locked_sector = FaunaNest(Coordinate(50, 50))
    game_map.fauna_nests = [nest_in_start_sector, nest_in_locked_sector]

    points = game_map.unlocked_fauna_spawn_points()

    assert points == [nest_in_start_sector.position]


def test_unlocked_fauna_spawn_points_excludes_dead_nests():
    game_map = Map(width=900, height=900)
    game_map.sectors = build_sector_grid(900, 900, grid_size=3, base_position=Coordinate(450, 450))

    dead_nest = FaunaNest(Coordinate(450, 450))
    dead_nest.health = 0
    game_map.fauna_nests = [dead_nest]

    assert game_map.unlocked_fauna_spawn_points() == []


def test_unlocked_fauna_spawn_points_ignores_sectors_when_none_configured():
    game_map = Map(width=900, height=900)
    nest = FaunaNest(Coordinate(50, 50))
    game_map.fauna_nests = [nest]

    assert game_map.unlocked_fauna_spawn_points() == [nest.position]
