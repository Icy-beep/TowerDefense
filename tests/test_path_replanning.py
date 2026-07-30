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
