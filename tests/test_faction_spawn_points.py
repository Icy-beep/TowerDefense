"""Раньше все враги спавнились из общего пула точек (Map.spawn_points),
случайно выбираемого в WaveProtocol.update() — Corporation и Fauna могли
появиться из одной и той же точки на карте. Теперь у каждой фракции
может быть свой набор точек спавна (Map.spawn_points_by_faction), а
позицию для конкретного врага выбирает GameSession._spawn_enemy_factory
через Map.spawn_points_for(faction) — WaveProtocol больше не выбирает
позицию сам, только вызывает spawn_factory(enemy_type) и передаёт
получившегося врага (или None, если точки спавна нет) дальше."""
import random

import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.core.game_session import GameSession
from src.enums import Faction
from src.factories.enemy_factory import EnemyFactory


# --------------------------------------------------------- EnemyFactory.faction_for

def test_faction_for_matches_configured_faction_for_every_registered_type():
    factory = EnemyFactory()
    expected = {
        "drone_walker": Faction.CORPORATION,
        "giant_roach": Faction.FAUNA,
        "scout_drone": Faction.CORPORATION,
        "heavy_assault_drone": Faction.CORPORATION,
        "bio_titan": Faction.FAUNA,
    }
    for type_name, faction in expected.items():
        assert factory.faction_for(type_name) == faction


def test_faction_for_unknown_type_defaults_to_fauna():
    factory = EnemyFactory()
    assert factory.faction_for("totally_unregistered_type") == Faction.FAUNA


# ------------------------------------------------------------- Map.spawn_points_for

def test_spawn_points_for_returns_faction_specific_points_when_configured():
    game_map = Map(width=4000, height=4000)
    corp_points = [Coordinate(0, 0)]
    fauna_points = [Coordinate(4000, 4000)]
    game_map.spawn_points_by_faction = {
        Faction.CORPORATION: corp_points,
        Faction.FAUNA: fauna_points,
    }

    assert game_map.spawn_points_for(Faction.CORPORATION) == corp_points
    assert game_map.spawn_points_for(Faction.FAUNA) == fauna_points


def test_spawn_points_for_falls_back_to_shared_list_when_faction_not_configured():
    game_map = Map(width=4000, height=4000)
    game_map.spawn_points = [Coordinate(100, 100)]

    assert game_map.spawn_points_for(Faction.CORPORATION) == [Coordinate(100, 100)]


def test_faction_spawn_points_are_actually_different_after_setup():
    """Corporation высаживается кораблями и больше не держит фиксированных
    точек спавна вовсе (см. ShipLandingStrategy/MedicDrone) - только Fauna
    по-прежнему появляется из своих двух точек."""
    session = GameSession()
    session.setup_game()

    corp_points = session.map.spawn_points_for(Faction.CORPORATION)
    fauna_points = session.map.spawn_points_for(Faction.FAUNA)

    assert corp_points == [], "у Corporation больше не должно быть фиксированных точек спавна"
    assert fauna_points, "у Fauna по-прежнему должны быть свои точки спавна"


# --------------------------------------------------------- GameSession._spawn_enemy_factory

def test_spawned_fauna_enemy_appears_at_a_point_belonging_to_its_faction():
    session = GameSession()
    session.setup_game()

    fauna_points = {(p.x, p.y) for p in session.map.spawn_points_for(Faction.FAUNA)}

    for _ in range(20):
        fauna_enemy = session._spawn_enemy_factory("giant_roach")
        assert (fauna_enemy.position.x, fauna_enemy.position.y) in fauna_points


def test_spawning_corporation_enemy_without_explicit_position_fails():
    """У Corporation больше нет фиксированных точек спавна - без явной
    позиции (её передаёт ShipLandingStrategy) спавн невозможен."""
    session = GameSession()
    session.setup_game()

    assert session._spawn_enemy_factory("drone_walker") is None


def test_spawned_enemy_does_not_alias_the_spawn_point_coordinate():
    """Регрессия: враг раньше получал ту же самую ссылку на Coordinate,
    что лежит в spawn_points_by_faction. Движение врага (self.position.x
    += ...) мутирует объект на месте, поэтому без копии сама точка спавна
    незаметно "уезжала" вслед за врагом (и маркер на карте, и будущие
    точки спавна для всей фракции)."""
    session = GameSession()
    session.setup_game()

    enemy = session._spawn_enemy_factory("giant_roach")
    spawn_points = session.map.spawn_points_for(enemy.faction)

    assert not any(enemy.position is p for p in spawn_points), \
        "враг не должен владеть тем же объектом Coordinate, что и точка спавна"

    original = [Coordinate(p.x, p.y) for p in spawn_points]

    for _ in range(50):
        enemy.move_towards_point(Coordinate(2000, 2000), 1.0)

    assert spawn_points == original, "точки спавна фракции не должны сдвигаться при движении врага"


def test_spawn_factory_returns_none_when_faction_has_no_spawn_points_at_all():
    session = GameSession()
    session.setup_game()
    session.map.spawn_points = []
    session.map.spawn_points_by_faction = {}

    assert session._spawn_enemy_factory("drone_walker") is None


def test_map_renderer_does_not_draw_stale_corporation_spawn_markers():
    """Corporation больше не появляется из фиксированных точек спавна
    (высаживается кораблями через ShipLandingStrategy) - старые точки
    остаются в spawn_points_by_faction только для отступления на лечение
    и не должны рисоваться на карте как места появления врагов."""
    from src.ui.map_renderer import MapRenderer, FACTION_SPAWN_COLORS
    import types
    import pygame

    session = GameSession()
    session.setup_game()

    drawn_colors = []
    original_polygon = pygame.draw.polygon

    def spy_polygon(surface, color, points, *args, **kwargs):
        drawn_colors.append(tuple(color))
        return original_polygon(surface, color, points, *args, **kwargs)

    pygame.draw.polygon = spy_polygon
    try:
        camera = types.SimpleNamespace(world_to_screen=lambda x, y: (x, y), x=0, y=0, zoom=1.0)
        screen = pygame.Surface((900, 600))
        MapRenderer()._draw_spawn_points(screen, camera, session)
    finally:
        pygame.draw.polygon = original_polygon

    corp_color = FACTION_SPAWN_COLORS[Faction.CORPORATION]
    fauna_color = FACTION_SPAWN_COLORS[Faction.FAUNA]
    assert corp_color not in drawn_colors, "маркеры точек высадки корпоратов не должны рисоваться"
    assert fauna_color in drawn_colors, "точки спавна фауны всё ещё актуальны и должны рисоваться"


def test_spawn_factory_uses_explicit_position_when_given():
    """ShipLandingStrategy передаёт конкретную точку высадки вместо того,
    чтобы полагаться на случайный выбор из точек спавна фракции."""
    session = GameSession()
    session.setup_game()

    landing_point = Coordinate(3999, 1)
    enemy = session._spawn_enemy_factory("drone_walker", landing_point)

    assert (enemy.position.x, enemy.position.y) == (landing_point.x, landing_point.y)
    assert enemy.position is not landing_point
