"""Спрайт базы должен расти/уменьшаться вместе с зумом камеры, как башни и враги, а не
оставаться зафиксированным в пикселях экрана (иначе на приближении визуально "тонет" на
фоне выросшей остальной карты) - см. MapRenderer._base_screen_size."""
import types

import pygame

from src.core.game_session import GameSession
from src.ui.map_renderer import MapRenderer


def _camera(zoom=1.0):
    return types.SimpleNamespace(world_to_screen=lambda x, y: (x, y), zoom=zoom)


def test_base_screen_size_grows_when_zooming_in():
    renderer = MapRenderer()
    size_at_default_zoom = renderer._base_screen_size(_camera(zoom=1.0))
    size_zoomed_in = renderer._base_screen_size(_camera(zoom=2.0))

    assert size_zoomed_in > size_at_default_zoom, \
        "при приближении камеры спрайт базы должен становиться крупнее на экране"


def test_base_screen_size_has_a_floor_when_zooming_out():
    renderer = MapRenderer()
    size = renderer._base_screen_size(_camera(zoom=0.01))

    assert size >= MapRenderer.BASE_SPRITE_MIN_SCREEN_SIZE, \
        "при сильном отдалении спрайт базы не должен становиться меньше минимального размера"


class _FakeSpriteManager:
    """Отдаёт один и тот же фейковый спрайт под любым ключом."""

    def get_frame(self, key, elapsed_time):
        return pygame.Surface((32, 32))

    def get_frame_for_angle(self, key, angle_degrees):
        return pygame.Surface((32, 32))


def test_draw_base_scales_sprite_with_camera_zoom(monkeypatch):
    session = GameSession()
    session.setup_game()

    scaled_sizes = []
    original = pygame.transform.smoothscale

    def spy_smoothscale(surface, size):
        scaled_sizes.append(size)
        return original(surface, size)

    monkeypatch.setattr(pygame.transform, "smoothscale", spy_smoothscale)

    renderer = MapRenderer(sprite_manager=_FakeSpriteManager())
    screen = pygame.Surface((900, 600))

    renderer._draw_base(screen, _camera(zoom=1.0), session)
    size_at_zoom_1 = scaled_sizes[-1]

    scaled_sizes.clear()
    renderer._draw_base(screen, _camera(zoom=2.0), session)
    size_at_zoom_2 = scaled_sizes[-1]

    assert size_at_zoom_2[0] > size_at_zoom_1[0], \
        "отрисовка базы должна масштабировать спрайт под текущий зум, а не рисовать фиксированный размер"
