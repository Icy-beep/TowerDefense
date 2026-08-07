"""Отрисовка предупреждающего маркера высадки Corporation (MapRenderer._draw_pending_landings)."""
import types

import pygame

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.enums import Faction
from src.systems.threat_strategy import PendingLanding
from src.ui.map_renderer import FACTION_SPAWN_COLORS, MapRenderer


def _camera():
    return types.SimpleNamespace(world_to_screen=lambda x, y: (x, y), x=0, y=0, zoom=1.0)


def _spy_circle_colors():
    drawn = []
    original = pygame.draw.circle

    def spy(surface, color, center, radius, *args, **kwargs):
        drawn.append(tuple(color))
        return original(surface, color, center, radius, *args, **kwargs)

    return drawn, spy


def test_pending_corporation_landing_gets_a_visible_marker():
    session = GameSession()
    session.setup_game()
    strategy = session.threat_strategies[Faction.CORPORATION]
    strategy.pending_landings.append(PendingLanding(Coordinate(3999, 500), warning_time=3.0))

    drawn, spy = _spy_circle_colors()
    original = pygame.draw.circle
    pygame.draw.circle = spy
    try:
        screen = pygame.Surface((900, 600))
        MapRenderer()._draw_pending_landings(screen, _camera(), session)
    finally:
        pygame.draw.circle = original

    corp_color = FACTION_SPAWN_COLORS[Faction.CORPORATION]
    assert corp_color in drawn, "маркер высадки Corporation должен рисоваться на карте"


def test_no_pending_landings_draws_nothing():
    session = GameSession()
    session.setup_game()

    drawn, spy = _spy_circle_colors()
    original = pygame.draw.circle
    pygame.draw.circle = spy
    try:
        screen = pygame.Surface((900, 600))
        MapRenderer()._draw_pending_landings(screen, _camera(), session)
    finally:
        pygame.draw.circle = original

    assert drawn == []


def test_fauna_never_gets_a_landing_marker_since_it_uses_nest_spawn():
    """Fauna спавнится через NestSpawnStrategy без предупреждающих маркеров вовсе."""
    session = GameSession()
    session.setup_game()
    session.threat_strategies[Faction.CORPORATION].pending_landings.append(
        PendingLanding(Coordinate(3999, 500), warning_time=3.0))

    drawn, spy = _spy_circle_colors()
    original = pygame.draw.circle
    pygame.draw.circle = spy
    try:
        screen = pygame.Surface((900, 600))
        MapRenderer()._draw_pending_landings(screen, _camera(), session)
    finally:
        pygame.draw.circle = original

    fauna_color = FACTION_SPAWN_COLORS[Faction.FAUNA]
    assert fauna_color not in drawn


def test_marker_countdown_ring_shrinks_as_time_runs_out():
    """Внутреннее кольцо стягивается к центру по мере приближения отряда - радиус
    должен уменьшаться, когда time_remaining становится меньше."""
    session = GameSession()
    session.setup_game()

    radii = []
    original = pygame.draw.circle

    def spy(surface, color, center, radius, *args, **kwargs):
        radii.append(radius)
        return original(surface, color, center, radius, *args, **kwargs)

    pygame.draw.circle = spy
    try:
        screen = pygame.Surface((900, 600))
        renderer = MapRenderer()
        early = PendingLanding(Coordinate(3999, 500), warning_time=3.0)
        early.time_remaining = 2.9
        renderer._draw_pending_landing_marker(screen, _camera(), early, warning_time=3.0, color=(1, 1, 1))
        radius_early = radii[-1]

        radii.clear()
        late = PendingLanding(Coordinate(3999, 500), warning_time=3.0)
        late.time_remaining = 0.1
        renderer._draw_pending_landing_marker(screen, _camera(), late, warning_time=3.0, color=(1, 1, 1))
        radius_late = radii[-1]
    finally:
        pygame.draw.circle = original

    assert radius_late < radius_early, "чем меньше времени осталось, тем сильнее должно стянуться кольцо"
