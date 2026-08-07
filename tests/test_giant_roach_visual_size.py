"""GiantRoach крупнее остальных врагов на экране (см. задачу пользователя:
замедлить и компенсировать здоровьем/бронёй, плюс увеличить спрайт)."""
import types

import pygame
import pytest

from src.core.coordinate import Coordinate
from src.entities.enemies import DroneWalker, GiantRoach
from src.factories.enemy_factory import EnemyFactory
from src.ui.map_renderer import ENEMY_SPRITE_SIZE_MULTIPLIERS, MapRenderer


def _camera(zoom=1.0):
    return types.SimpleNamespace(world_to_screen=lambda x, y: (x, y), zoom=zoom)


def test_giant_roach_screen_size_is_larger_than_default():
    renderer = MapRenderer()
    camera = _camera(zoom=1.0)

    roach_size = renderer._enemy_screen_size(camera, "giant_roach")
    default_size = renderer._enemy_screen_size(camera, "drone_walker")

    assert roach_size > default_size
    assert roach_size == pytest.approx(default_size * ENEMY_SPRITE_SIZE_MULTIPLIERS["giant_roach"])


def test_unknown_type_uses_default_size():
    renderer = MapRenderer()
    camera = _camera(zoom=1.0)

    assert renderer._enemy_screen_size(camera, None) == renderer._enemy_screen_size(camera, "some_new_type")


class _FakeSpriteManager:
    """Отдаёт один и тот же фейковый спрайт под любым ключом."""

    def get_frame(self, key, elapsed_time):
        return pygame.Surface((32, 32))


def test_draw_enemies_scales_roach_sprite_bigger_than_walker(monkeypatch):
    factory = EnemyFactory()
    roach = factory.create("giant_roach", Coordinate(0, 0))
    walker = factory.create("drone_walker", Coordinate(100, 0))

    session = types.SimpleNamespace(map=types.SimpleNamespace(enemies=[roach, walker]), elapsed_time=0.0)
    controller = types.SimpleNamespace(selected_enemy=None)
    camera = _camera(zoom=1.0)

    scaled_sizes = {}
    original = pygame.transform.smoothscale

    def spy_smoothscale(surface, size):
        scaled_sizes[len(scaled_sizes)] = size
        return original(surface, size)

    monkeypatch.setattr(pygame.transform, "smoothscale", spy_smoothscale)

    renderer = MapRenderer(sprite_manager=_FakeSpriteManager())
    screen = pygame.Surface((900, 600))
    renderer._draw_enemies(screen, camera, session, controller, 900, 600)

    roach_size, walker_size = scaled_sizes[0], scaled_sizes[1]
    assert roach_size[0] > walker_size[0]


def test_giant_roach_default_speed_is_slower_than_drone_walker():
    assert GiantRoach(Coordinate(0, 0)).speed < DroneWalker(Coordinate(0, 0)).speed


def test_giant_roach_speed_decrease_is_compensated_by_equivalent_health_increase():
    """Регрессия/фиксация баланса: скорость снижена с 25 до 20 (-20%), здоровье
    поднято с 250 до 300 (+20%) - та же пропорция, чтобы понижение скорости не
    делало таракана слабее в целом, а сдвигало его архетип в сторону
    "медленный и живучий" (см. задачу пользователя)."""
    roach = GiantRoach(Coordinate(0, 0))
    old_speed, old_health = 25, 250

    assert roach.speed == pytest.approx(old_speed * 0.8)
    assert roach.max_health == pytest.approx(old_health * 1.2)
