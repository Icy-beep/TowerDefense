"""Реплан пути врагов при постройке башни, с учётом тумана войны (fog of war)."""
import pytest

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.core.map import Map
from src.entities.turrets import LaserTurret
from src.enums import Faction


@pytest.fixture
def session():
    s = GameSession()
    s.setup_game()
    # Эти тесты про туман войны и реплан пути, а не про секторы прогрессии
    # (см. src/systems/sector.py) - открываем всю карту, чтобы точки блокировки
    # пути вдалеке от базы не упирались в "сектор закрыт".
    for sector in s.map.sectors:
        sector.unlocked = True
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
    assert not session.map.faction_intel[enemy.faction].knows(session.map.modules[0])


def test_replan_reroutes_around_a_tower_already_known_to_the_faction(session):
    """Если фракция уже знает о башне, пересчёт маршрута должен её обходить."""
    enemy = session.enemy_factory.create("drone_walker", Coordinate(2000, 500))
    original_path = session.map.nav_grid.find_path(enemy.position, session.base_position)
    enemy.set_path(original_path)
    session.map.spawn_enemy(enemy)

    block_point = original_path[len(original_path) // 4]
    blocked_node = session.map.nav_grid.get_node(block_point.x, block_point.y)

    success = session.place_turret("laser", block_point)
    assert success is True

    tower = session.map.modules[0]
    session.map.faction_intel[enemy.faction].reveal(tower)

    session.map.replan_enemy_paths()

    new_path_nodes = {
        (session.map.nav_grid.get_node(p.x, p.y).x, session.map.nav_grid.get_node(p.x, p.y).y)
        for p in enemy.path
    }
    assert (blocked_node.x, blocked_node.y) not in new_path_nodes
    assert len(enemy.path) > 0
    assert enemy.path_index == 0, "реплан должен сбрасывать прогресс по индексу нового маршрута"


def test_replan_only_touches_alive_enemies(session):
    """replan_enemy_paths (не place_turret напрямую - см. GameSession.place_turret,
    больше не дёргает реплан сам: свежепостроенная башня физически не может быть
    в чьём-то known_towers ещё до первого _update_vision, так что реплан на каждый
    клик был чистой тратой CPU без единого реального изменения пути, см. фриз при
    постройке через ~5 минут игры) не должен трогать путь мёртвых врагов."""
    dead_enemy = session.enemy_factory.create("drone_walker", Coordinate(2000, 500))
    dead_enemy.health = 0
    dead_enemy.set_path([Coordinate(999, 999)])
    session.map.spawn_enemy(dead_enemy)

    session.place_turret("laser", Coordinate(2000, 900))
    session.map.replan_enemy_paths()

    assert dead_enemy.path == [Coordinate(999, 999)]


def test_replan_keeps_old_path_if_no_new_path_found(session, monkeypatch):
    enemy = session.enemy_factory.create("drone_walker", Coordinate(2000, 500))
    original_path = session.map.nav_grid.find_path(enemy.position, session.base_position)
    enemy.set_path(original_path)
    session.map.spawn_enemy(enemy)

    monkeypatch.setattr(session.map.nav_grid, "find_path", lambda *a, **k: [])

    session.place_turret("laser", Coordinate(2000, 900))
    session.map.replan_enemy_paths()

    assert enemy.path == original_path


def test_place_turret_no_longer_eagerly_replans_all_enemies(session, monkeypatch):
    """Регрессия для фикса фриза при постройке (см. GameSession.place_turret): раньше
    здесь вызывался replan_enemy_paths() безусловно для ВСЕХ живых врагов на каждый
    клик - дорого и бессмысленно, поскольку свежепостроенная башня ещё не могла быть
    known никакой фракции. Проверяем, что place_turret САМ по себе не трогает
    nav_grid.find_path вообще (обнаружение и реальный реплан теперь целиком на
    Map.update -> _update_vision -> replan_enemy_paths(changed_factions))."""
    enemy = session.enemy_factory.create("drone_walker", Coordinate(2000, 500))
    original_path = session.map.nav_grid.find_path(enemy.position, session.base_position)
    enemy.set_path(original_path)
    session.map.spawn_enemy(enemy)

    find_path_calls = []
    original_find_path = session.map.nav_grid.find_path

    def spy_find_path(*args, **kwargs):
        find_path_calls.append((args, kwargs))
        return original_find_path(*args, **kwargs)

    monkeypatch.setattr(session.map.nav_grid, "find_path", spy_find_path)

    success = session.place_turret("laser", Coordinate(2000, 900))

    assert success is True
    assert find_path_calls == [], "place_turret не должен сам запускать поиск пути ни для одного врага"



def test_path_to_base_avoid_danger_never_enters_a_known_towers_range():
    """С avoid_danger=True путь не должен заходить в радиус известной башни вообще."""
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
    """Если строгий запрет оставляет карту без пути, path_to_base не подменяет это компромиссом."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    tower = LaserTurret(Coordinate(2000, 2000), range_radius=6000)
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    path = game_map.path_to_base(Coordinate(500, 500), Faction.CORPORATION, avoid_danger=True)

    assert path == [], "с полной блокировкой честного пути быть не должно - вызывающий код должен отступить"


def test_path_to_base_avoid_danger_finds_a_detour_around_a_single_realistic_tower():
    """Регрессия: с MAX_EXPANSIONS=400 честный объезд даже одной башни с боевым радиусом
    (600, как у миномёта) регулярно не укладывался в лимит A* и path_to_base возвращал
    пустой путь, хотя объезд в обе стороны по карте существовал - из-за этого избегающие
    враги (разведчик) массово уходили в _advance_giving_up и "прилипали" к краю карты."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    tower = LaserTurret(Coordinate(2000, 1200), range_radius=600)
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    path = game_map.path_to_base(Coordinate(2000, 200), Faction.CORPORATION, avoid_danger=True)

    assert path, "честный объезд одной башни должен находиться, а не упираться в лимит поиска"
    assert all(point.distance_to(tower.position) > tower.range_radius for point in path)


def test_path_to_base_default_does_not_hard_block_tower_coverage():
    """Без avoid_danger поведение должно остаться прежним - боевые фракции
    по-прежнему вольны срезать через мягко штрафуемую зону."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    tower = LaserTurret(Coordinate(1000, 500), range_radius=5000)
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.FAUNA].reveal(tower)

    path = game_map.path_to_base(Coordinate(0, 0), Faction.FAUNA, avoid_danger=False)

    assert path, "с мягким избеганием путь должен находиться даже если вся карта под одной башней"
