"""Радиус атаки виден только у выбранной башни или у всех сразу, пока зажат ALT."""
import types

import pygame

from src.core.coordinate import Coordinate
from src.entities.turrets import LaserTurret
from src.ui.map_renderer import MapRenderer


def _spy_on_circle(monkeypatch):
    calls = []

    def spy_circle(screen, color, pos, radius, width=0):
        calls.append(radius)

    monkeypatch.setattr(pygame.draw, "circle", spy_circle)
    return calls


def _camera(zoom=1.0):
    return types.SimpleNamespace(world_to_screen=lambda x, y: (x, y), zoom=zoom)


def test_range_circle_hidden_by_default(monkeypatch):
    calls = _spy_on_circle(monkeypatch)
    tower = LaserTurret(Coordinate(500, 500))
    camera = _camera()
    session = types.SimpleNamespace(map=types.SimpleNamespace(modules=[tower]))
    controller = types.SimpleNamespace(selected_module=None)
    expected_radius = int(tower.range_radius * camera.zoom)

    MapRenderer()._draw_modules(pygame.Surface((10, 10)), camera, session, controller, [], alt_held=False)

    assert expected_radius not in calls, "без выбора и без ALT радиус атаки не должен рисоваться"


def test_range_circle_shown_for_selected_tower_without_alt(monkeypatch):
    calls = _spy_on_circle(monkeypatch)
    tower = LaserTurret(Coordinate(500, 500))
    camera = _camera()
    session = types.SimpleNamespace(map=types.SimpleNamespace(modules=[tower]))
    controller = types.SimpleNamespace(selected_module=tower)
    expected_radius = int(tower.range_radius * camera.zoom)

    MapRenderer()._draw_modules(pygame.Surface((10, 10)), camera, session, controller, [], alt_held=False)

    assert expected_radius in calls


def test_range_circle_shown_for_all_towers_when_alt_held(monkeypatch):
    calls = _spy_on_circle(monkeypatch)
    tower_a = LaserTurret(Coordinate(500, 500))
    tower_b = LaserTurret(Coordinate(900, 900))
    camera = _camera()
    session = types.SimpleNamespace(map=types.SimpleNamespace(modules=[tower_a, tower_b]))
    controller = types.SimpleNamespace(selected_module=None)
    expected_radius = int(tower_a.range_radius * camera.zoom)

    MapRenderer()._draw_modules(pygame.Surface((10, 10)), camera, session, controller, [], alt_held=True)

    assert calls.count(expected_radius) == 2, "ALT должен раскрыть радиус у обеих башен разом"


def test_render_computes_alt_held_from_either_alt_key(monkeypatch):
    """Смоук-тест полного render(): ALT читается через pygame.key.get_pressed()
    один раз в начале и не должен ронять остальной рендер."""
    import collections
    from src.core.game_session import GameSession

    session = GameSession()
    session.setup_game()
    session.map.modules.append(LaserTurret(Coordinate(500, 500)))

    controller = types.SimpleNamespace(selected_module=None, selected_tower_type=None, selected_enemy=None,
                                        _is_valid_position=lambda pos: True)
    camera = types.SimpleNamespace(
        world_to_screen=lambda x, y: (x, y), screen_to_world=lambda x, y: (x, y),
        x=0, y=0, zoom=1.0,
    )
    screen = pygame.Surface((900, 600))

    pressed = collections.defaultdict(bool)
    pressed[pygame.K_LALT] = True
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: pressed)

    MapRenderer().render(screen, camera, session, controller, [], 900, 600)
