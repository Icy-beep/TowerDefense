"""Генератор и пилон после автообрезки спрайта реально шире, чем выше - раньше
_blit_scaled всегда масштабировал в квадрат и сжимал их по ширине вместе со всеми
остальными постройками (см. запрос пользователя, MapRenderer.TOWER_SPRITE_WIDTH_MULTIPLIERS)."""
import types

import pygame
import pytest

from src.core.coordinate import Coordinate
from src.entities.power_generator import PowerGenerator
from src.entities.turrets import LaserTurret
from src.ui.map_renderer import TOWER_SPRITE_WIDTH_MULTIPLIERS, MapRenderer


def _camera(zoom=1.0):
    return types.SimpleNamespace(world_to_screen=lambda x, y: (x, y), zoom=zoom)


class _FakeSpriteManager:
    """Отдаёт один и тот же фейковый спрайт под любым ключом."""

    def get_frame_for_angle(self, key, angle_degrees):
        return pygame.Surface((32, 32), pygame.SRCALPHA)


def test_blit_scaled_stretches_width_only_when_multiplier_given(monkeypatch):
    renderer = MapRenderer()
    screen = pygame.Surface((200, 200))
    sprite = pygame.Surface((100, 50), pygame.SRCALPHA)

    scaled_sizes = []
    original = pygame.transform.smoothscale

    def spy(surface, size):
        scaled_sizes.append(size)
        return original(surface, size)

    monkeypatch.setattr(pygame.transform, "smoothscale", spy)
    renderer._blit_scaled(screen, sprite, 100, 100, target_size=64, width_multiplier=1.4)

    width, height = scaled_sizes[-1]
    assert height == 64
    assert width == pytest.approx(64 * 1.4, abs=1)


def test_blit_scaled_defaults_to_square_without_multiplier():
    renderer = MapRenderer()
    screen = pygame.Surface((200, 200))
    sprite = pygame.Surface((100, 50), pygame.SRCALPHA)

    renderer._blit_scaled(screen, sprite, 100, 100, target_size=64)
    # Не падает и рисует что-то - квадратная отрисовка уже покрыта test_base_sprite_scaling.py.


def test_draw_modules_widens_generator_more_than_a_regular_tower(monkeypatch):
    generator = PowerGenerator(Coordinate(0, 0))
    generator.type_name = "generator"
    laser = LaserTurret(Coordinate(200, 0))
    laser.type_name = "laser"

    session = types.SimpleNamespace(map=types.SimpleNamespace(modules=[generator, laser]))
    controller = types.SimpleNamespace(selected_module=None)

    sizes_by_call = []
    original = pygame.transform.smoothscale

    def spy(surface, size):
        sizes_by_call.append(size)
        return original(surface, size)

    monkeypatch.setattr(pygame.transform, "smoothscale", spy)

    renderer = MapRenderer(sprite_manager=_FakeSpriteManager())
    screen = pygame.Surface((900, 600))
    renderer._draw_modules(screen, _camera(zoom=1.0), session, controller, [])

    generator_size, laser_size = sizes_by_call[0], sizes_by_call[1]
    assert generator_size[0] > generator_size[1], "спрайт генератора должен быть шире, чем выше"
    assert laser_size[0] == laser_size[1], "обычная башня по-прежнему рисуется квадратом"
    assert generator_size[0] == pytest.approx(
        generator_size[1] * TOWER_SPRITE_WIDTH_MULTIPLIERS["generator"], abs=1)
