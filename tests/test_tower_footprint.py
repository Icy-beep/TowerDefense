"""Башни занимают DefenseModule.FOOTPRINT_CELLS (3x3) клеток сетки, а не одну — и не
должны накладываться друг на друга ни при размещении, ни при обходе путей."""
import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.turrets import LaserTurret
from src.enums import Faction


@pytest.fixture
def game_map():
    return Map(width=4000, height=4000)


def _cell_center(game_map, col, row):
    cell = game_map.nav_grid.cell_size
    return Coordinate(col * cell + cell / 2, row * cell + cell / 2)


def test_cannot_place_tower_overlapping_neighboring_footprint(game_map):
    first = _cell_center(game_map, 10, 10)
    game_map.modules.append(LaserTurret(first))

    two_cells_away = _cell_center(game_map, 12, 10)

    assert game_map.can_place_module(two_cells_away) is False


def test_can_place_tower_exactly_three_cells_away(game_map):
    first = _cell_center(game_map, 10, 10)
    game_map.modules.append(LaserTurret(first))

    three_cells_away = _cell_center(game_map, 13, 10)

    assert game_map.can_place_module(three_cells_away) is True


def test_can_place_tower_on_empty_map(game_map):
    assert game_map.can_place_module(_cell_center(game_map, 5, 5)) is True


def test_path_to_base_blocks_full_3x3_footprint_of_known_tower():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(900, 500)
    tower = LaserTurret(Coordinate(450, 500))
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    tower_node = game_map.nav_grid.get_node(tower.position.x, tower.position.y)
    neighbor_cell_center = game_map.nav_grid.get_world_pos(
        game_map.nav_grid.get_node((tower_node.x + 1) * game_map.nav_grid.cell_size,
                                    tower_node.y * game_map.nav_grid.cell_size)
    )

    path = game_map.path_to_base(Coordinate(0, 500), Faction.CORPORATION)
    path_nodes = {(game_map.nav_grid.get_node(p.x, p.y).x, game_map.nav_grid.get_node(p.x, p.y).y)
                  for p in path}

    neighbor_node = game_map.nav_grid.get_node(neighbor_cell_center.x, neighbor_cell_center.y)
    assert (neighbor_node.x, neighbor_node.y) not in path_nodes, \
        "клетка рядом с известной башней тоже входит в её footprint и должна быть заблокирована"
