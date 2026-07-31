"""Раньше путь врага до базы считался один раз при спавне
(GameSession._spawn_enemy_factory -> nav_grid.find_path) и больше не
пересчитывался, а сам find_path учитывал ВСЕ физически построенные башни
сразу — враги были всеведущими.

С введением тумана войны (fog of war, см. src/systems/faction_intel.py и
Map.path_to_base/_update_vision) путь строится только с учётом башен,
уже ИЗВЕСТНЫХ фракции врага — поэтому свежепостроенная и ещё никем не
замеченная башня саму по себе путь не меняет: враги "не знают" о ней,
пока не окажутся в радиусе обзора (это отдельно проверяется в
test_fog_of_war.py). GameSession.place_turret() всё равно вызывает
Map.replan_enemy_paths() на постройку — эта подстраховка нужна на
случай, если башня строится в уже разведанной фракцией зоне."""
import pytest

from src.core.game_session import GameSession
from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.turrets import LaserTurret
from src.enums import Faction


@pytest.fixture
def session():
    s = GameSession()
    s.setup_game()
    return s


def test_newly_built_undiscovered_tower_does_not_reroute_the_path(session):
    """Башня, которую фракция ещё не видела, не должна ничего менять в
    уже проложенном маршруте — в этом весь смысл тумана войны."""
    enemy = session.enemy_factory.create("drone_walker", Coordinate(2000, 500))
    original_path = session.map.nav_grid.find_path(enemy.position, session.base_position)
    enemy.set_path(original_path)
    session.map.spawn_enemy(enemy)

    block_point = original_path[len(original_path) // 4]

    success = session.place_turret("laser", block_point)
    assert success is True

    new_path = session.map.path_to_base(Coordinate(2000, 500), enemy.faction)
    assert len(new_path) > 0
    # Путь пересчитан (реплан вызывается всегда), но он идёт так же
    # напролом, как и раньше — башня ещё не обнаружена этой фракцией.
    assert not session.map.faction_intel[enemy.faction].knows(session.map.modules[0])


def test_replan_reroutes_around_a_tower_already_known_to_the_faction(session):
    """Если фракция уже знает о башне (например, её увидел другой юнит),
    пересчёт маршрута должен её обходить — ровно так же, как раньше
    работало для всех башен без исключения."""
    enemy = session.enemy_factory.create("drone_walker", Coordinate(2000, 500))
    original_path = session.map.nav_grid.find_path(enemy.position, session.base_position)
    enemy.set_path(original_path)
    session.map.spawn_enemy(enemy)

    block_point = original_path[len(original_path) // 4]
    blocked_node = session.map.nav_grid.get_node(block_point.x, block_point.y)

    success = session.place_turret("laser", block_point)
    assert success is True

    tower = session.map.modules[0]
    session.map.faction_intel[enemy.faction].reveal(tower)  # фракция уже знает о башне

    session.map.replan_enemy_paths()

    new_path_nodes = {
        (session.map.nav_grid.get_node(p.x, p.y).x, session.map.nav_grid.get_node(p.x, p.y).y)
        for p in enemy.path
    }
    assert (blocked_node.x, blocked_node.y) not in new_path_nodes
    assert len(enemy.path) > 0
    assert enemy.path_index == 0, "реплан должен сбрасывать прогресс по индексу нового маршрута"


def test_replan_only_touches_alive_enemies(session):
    dead_enemy = session.enemy_factory.create("drone_walker", Coordinate(2000, 500))
    dead_enemy.health = 0
    dead_enemy.set_path([Coordinate(999, 999)])
    session.map.spawn_enemy(dead_enemy)

    session.place_turret("laser", Coordinate(2000, 900))

    # Путь мёртвого врага не должен трогаться репланом.
    assert dead_enemy.path == [Coordinate(999, 999)]


def test_replan_keeps_old_path_if_no_new_path_found(session, monkeypatch):
    enemy = session.enemy_factory.create("drone_walker", Coordinate(2000, 500))
    original_path = session.map.nav_grid.find_path(enemy.position, session.base_position)
    enemy.set_path(original_path)
    session.map.spawn_enemy(enemy)

    monkeypatch.setattr(session.map.nav_grid, "find_path", lambda *a, **k: [])

    session.place_turret("laser", Coordinate(2000, 900))

    assert enemy.path == original_path


# --------------------------------------------------- avoid_danger (жёсткий обход)

def test_path_to_base_avoid_danger_never_enters_a_known_towers_range():
    """Мягкое избегание (без avoid_danger) может срезать через радиус
    известной башни, если так дешевле по сумме расстояния и штрафа - это
    нормально для боевых фракций. Но для врагов, которые вообще избегают
    простреливаемых зон (ScoutDrone), путь не должен заходить в радиус
    башни ни при каких раскладах, иначе они снова и снова возвращаются
    под обстрел по тому же самому маршруту."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 3500)
    tower = LaserTurret(Coordinate(2000, 2000), range_radius=300)
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    path = game_map.path_to_base(Coordinate(2000, 500), Faction.CORPORATION, avoid_danger=True)

    assert path, "путь должен существовать - карта достаточно большая для обхода"
    assert all(point.distance_to(tower.position) > tower.range_radius for point in path), \
        "с avoid_danger=True маршрут не должен заходить в радиус известной башни вообще"


def test_path_to_base_avoid_danger_returns_empty_when_fully_boxed_in():
    """Если строгий запрет оставляет карту без пути вовсе (враг полностью
    окружён простреливаемой территорией), path_to_base не подменяет это
    компромиссным маршрутом через опасную зону - решение, что делать
    дальше (отступать), принимает вызывающий код
    (Map._advance_honestly_or_give_up), а не сам путь тайком срезает
    через огонь."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    # Огромная башня накрывает вообще всё - строгий запрет неизбежно
    # оставит карту без пути.
    tower = LaserTurret(Coordinate(2000, 2000), range_radius=6000)
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    path = game_map.path_to_base(Coordinate(500, 500), Faction.CORPORATION, avoid_danger=True)

    assert path == [], "с полной блокировкой честного пути быть не должно - вызывающий код должен отступить"


def test_path_to_base_default_does_not_hard_block_tower_coverage():
    """Без avoid_danger поведение должно остаться прежним - боевые фракции
    по-прежнему вольны срезать через мягко штрафуемую зону."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    tower = LaserTurret(Coordinate(1000, 500), range_radius=5000)  # накрывает всю карту
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.FAUNA].reveal(tower)

    path = game_map.path_to_base(Coordinate(0, 0), Faction.FAUNA, avoid_danger=False)

    assert path, "с мягким избеганием путь должен находиться даже если вся карта под одной башней"
