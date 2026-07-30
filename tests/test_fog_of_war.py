"""Туман войны: раньше враги были всеведущими — путь до базы считался
A* по глобальной сетке, где физически построенная башня сразу и
навсегда блокировала клетку для абсолютно всех врагов. Теперь позиция
базы известна фракции всегда (это цель вторжения), а про конкретные
башни фракция узнаёт только когда её юнит физически окажется в радиусе
обзора (HostileEntity.vision_radius) — см. src/systems/faction_intel.py
и Map._update_vision()/path_to_base().

MVP-версия: обнаружение сразу становится известно всей фракции целиком
("мгновенный аплоад"), без цепочки ретрансляции юнит-юнит-точка спавна —
это сознательное упрощение с заделом на будущее расширение (см.
docstring FactionIntel)."""
import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.core.navigation import NavigationGrid
from src.entities.enemies import DroneWalker, GiantRoach, ScoutDrone
from src.entities.turrets import LaserTurret
from src.enums import Faction
from src.systems.faction_intel import FactionIntel


# --------------------------------------------------------------- FactionIntel

def test_reveal_returns_true_only_the_first_time():
    intel = FactionIntel()
    tower = LaserTurret(Coordinate(0, 0))

    assert intel.reveal(tower) is True
    assert intel.reveal(tower) is False, "повторное обнаружение уже известной башни не событие"
    assert intel.knows(tower) is True


def test_unknown_tower_is_not_known():
    intel = FactionIntel()
    tower = LaserTurret(Coordinate(0, 0))

    assert intel.knows(tower) is False
    assert intel.known_towers() == []


def test_two_distinct_towers_tracked_independently():
    intel = FactionIntel()
    tower_a = LaserTurret(Coordinate(0, 0))
    tower_b = LaserTurret(Coordinate(100, 0))

    intel.reveal(tower_a)

    assert intel.knows(tower_a) is True
    assert intel.knows(tower_b) is False
    assert intel.known_towers() == [tower_a]


# ------------------------------------------------------------- vision_radius

def test_scout_drone_has_larger_vision_radius_than_default_enemy():
    assert ScoutDrone(Coordinate(0, 0)).vision_radius > DroneWalker(Coordinate(0, 0)).vision_radius


def test_vision_radius_can_be_overridden_explicitly():
    enemy = DroneWalker(Coordinate(0, 0), vision_radius=999)
    assert enemy.vision_radius == 999


# --------------------------------------------------------- NavigationGrid

def test_navigation_grid_extra_blocked_forces_detour_without_mutating_grid():
    grid = NavigationGrid(width=1000, height=1000, cell_size=32)
    start, end = Coordinate(0, 500), Coordinate(900, 500)

    direct_path = grid.find_path(start, end)
    blocked_node = grid.get_node(450, 500)
    detour_path = grid.find_path(start, end, extra_blocked={(blocked_node.x, blocked_node.y)})

    direct_nodes = {(grid.get_node(p.x, p.y).x, grid.get_node(p.x, p.y).y) for p in direct_path}
    detour_nodes = {(grid.get_node(p.x, p.y).x, grid.get_node(p.x, p.y).y) for p in detour_path}

    assert (blocked_node.x, blocked_node.y) in direct_nodes, "прямой путь по прямой идёт через центр"
    assert (blocked_node.x, blocked_node.y) not in detour_nodes

    # extra_blocked не должен быть постоянным состоянием сетки
    unblocked_again = grid.find_path(start, end)
    assert unblocked_again == direct_path


def test_navigation_grid_extra_cost_prefers_detour_when_one_exists():
    grid = NavigationGrid(width=1000, height=1000, cell_size=32)
    start, end = Coordinate(0, 500), Coordinate(900, 500)

    direct_path = grid.find_path(start, end)
    costly_node = grid.get_node(450, 500)
    high_cost = {(costly_node.x, costly_node.y): 10_000.0}

    detour_path = grid.find_path(start, end, extra_cost=high_cost)
    detour_nodes = {(grid.get_node(p.x, p.y).x, grid.get_node(p.x, p.y).y) for p in detour_path}

    assert len(detour_path) > 0, "штраф стоимости не должен блокировать путь полностью"
    assert (costly_node.x, costly_node.y) not in detour_nodes, \
        "при наличии альтернативы дорогая клетка должна быть объезжена"
    assert len(detour_path) != len(direct_path) or detour_path != direct_path


def test_navigation_grid_extra_cost_does_not_block_the_only_route():
    """В отличие от extra_blocked, extra_cost — это штраф, а не запрет:
    даже если ВСЕ клетки на пути дорогие, путь всё равно должен
    находиться (иначе "мягкий" обход был бы неотличим от жёсткой
    блокировки и мог бы намертво запечатать базу)."""
    grid = NavigationGrid(width=200, height=200, cell_size=32)
    start, end = Coordinate(0, 0), Coordinate(190, 190)

    all_nodes_cost = {(col, row): 1_000_000.0 for col in range(grid.cols) for row in range(grid.rows)}
    path = grid.find_path(start, end, extra_cost=all_nodes_cost)

    assert len(path) > 0


# ------------------------------------------------------------- Map.path_to_base

def test_path_to_base_ignores_towers_unknown_to_the_faction():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(900, 500)
    tower = LaserTurret(Coordinate(450, 500))
    game_map.modules.append(tower)

    path = game_map.path_to_base(Coordinate(0, 500), Faction.CORPORATION)
    nodes = {(game_map.nav_grid.get_node(p.x, p.y).x, game_map.nav_grid.get_node(p.x, p.y).y) for p in path}
    tower_node = game_map.nav_grid.get_node(tower.position.x, tower.position.y)

    assert (tower_node.x, tower_node.y) in nodes, "никто ещё не видел башню — путь должен идти прямо через неё"


def test_path_to_base_avoids_towers_known_to_the_faction():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(900, 500)
    tower = LaserTurret(Coordinate(450, 500))
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    path = game_map.path_to_base(Coordinate(0, 500), Faction.CORPORATION)
    nodes = {(game_map.nav_grid.get_node(p.x, p.y).x, game_map.nav_grid.get_node(p.x, p.y).y) for p in path}
    tower_node = game_map.nav_grid.get_node(tower.position.x, tower.position.y)

    assert (tower_node.x, tower_node.y) not in nodes


def test_path_to_base_avoids_the_range_around_a_known_tower_not_just_its_own_cell():
    """"Обходить стороной" должно означать держаться подальше от радиуса
    поражения известной башни, а не просто не наступать ровно на её
    клетку — иначе враг всё равно шёл бы прямо через центр зоны обстрела."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(900, 500)
    tower = LaserTurret(Coordinate(450, 500))  # range_radius по умолчанию 400 (после ребаланса)
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    path = game_map.path_to_base(Coordinate(0, 500), Faction.CORPORATION)

    assert all(p.distance_to(tower.position) > tower.range_radius * 0.5 for p in path), \
        "путь должен держаться на почтительном расстоянии от известной башни, а не впритык к ней"


def test_path_to_base_still_reaches_base_when_surrounded_by_known_towers():
    """Штраф за радиус поражения — не жёсткая блокировка: даже если
    известные башни окружают базу со всех сторон, путь обязан
    найтись (иначе игрок мог бы навсегда запечатать базу кольцом
    построек, и волны застряли бы неразрешимо)."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    towers = [
        LaserTurret(Coordinate(2000 + dx, 2000 + dy))
        for dx, dy in [(-300, 0), (300, 0), (0, -300), (0, 300)]
    ]
    for tower in towers:
        game_map.modules.append(tower)
        game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    path = game_map.path_to_base(Coordinate(0, 0), Faction.CORPORATION)

    assert len(path) > 0
    assert path[-1] == game_map.nav_grid.get_world_pos(game_map.nav_grid.get_node(2000, 2000))


def test_base_position_is_always_known_without_any_discovery():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(900, 500)

    path = game_map.path_to_base(Coordinate(0, 500), Faction.FAUNA)

    assert len(path) > 0
    assert path[-1] == game_map.nav_grid.get_world_pos(game_map.nav_grid.get_node(900, 500))


def test_path_to_base_returns_empty_list_without_a_base_position():
    game_map = Map(width=4000, height=4000)  # base_position не выставлен

    assert game_map.path_to_base(Coordinate(0, 500), Faction.CORPORATION) == []


# --------------------------------------------------------------- Map.update()

def test_map_update_discovers_tower_within_vision_and_reroutes_same_frame():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(900, 500)
    tower = LaserTurret(Coordinate(450, 500))
    game_map.modules.append(tower)

    # В радиусе обзора (140 по умолчанию), но не на самой клетке башни —
    # иначе первой же точкой пересчитанного маршрута неизбежно была бы
    # клетка, где враг физически стоит.
    enemy = DroneWalker(Coordinate(350, 500))
    enemy.set_path(game_map.nav_grid.find_path(enemy.position, game_map.base_position))
    game_map.spawn_enemy(enemy)
    assert not game_map.faction_intel[enemy.faction].knows(tower)

    game_map.update(0.016)

    assert game_map.faction_intel[enemy.faction].knows(tower) is True
    tower_node = game_map.nav_grid.get_node(tower.position.x, tower.position.y)
    path_nodes = {(game_map.nav_grid.get_node(p.x, p.y).x, game_map.nav_grid.get_node(p.x, p.y).y)
                  for p in enemy.path}
    assert (tower_node.x, tower_node.y) not in path_nodes


def test_map_update_does_not_discover_tower_outside_vision_radius():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(3000, 500)
    tower = LaserTurret(Coordinate(1500, 500))
    game_map.modules.append(tower)

    far_enemy = DroneWalker(Coordinate(0, 500))  # 1500 >> vision_radius по умолчанию (140)
    far_enemy.set_path([Coordinate(50, 500)])
    game_map.spawn_enemy(far_enemy)

    game_map.update(0.016)

    assert not game_map.faction_intel[far_enemy.faction].knows(tower)


def test_different_faction_does_not_benefit_from_anothers_discovery():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(900, 500)
    tower = LaserTurret(Coordinate(450, 500))
    game_map.modules.append(tower)

    corp_enemy = DroneWalker(Coordinate(450, 500))  # Corporation, вплотную к башне
    corp_enemy.set_path([Coordinate(900, 500)])
    roach = GiantRoach(Coordinate(2000, 2000))  # Fauna, далеко от башни
    roach.set_path([Coordinate(2100, 2000)])
    game_map.spawn_enemy(corp_enemy)
    game_map.spawn_enemy(roach)

    game_map.update(0.016)

    assert game_map.faction_intel[Faction.CORPORATION].knows(tower) is True
    assert game_map.faction_intel[Faction.FAUNA].knows(tower) is False


def test_scout_drone_wider_vision_discovers_tower_that_regular_drone_would_miss():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(3000, 500)
    tower = LaserTurret(Coordinate(1200, 500))
    game_map.modules.append(tower)

    # 200 юнитов до башни: дальше стандартного vision_radius (140), но
    # ближе, чем у ScoutDrone (260) — разница должна быть заметна.
    scout = ScoutDrone(Coordinate(1000, 500))
    scout.set_path([Coordinate(1050, 500)])
    game_map.spawn_enemy(scout)

    game_map.update(0.016)

    assert game_map.faction_intel[scout.faction].knows(tower) is True
