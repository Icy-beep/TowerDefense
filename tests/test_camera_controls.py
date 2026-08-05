"""Ускорение камеры на Shift и перетаскивание камеры ЛКМ (когда клик не
попал по башне и постройка не выбрана)."""
import collections
import types
import pygame
import pytest

from src.core.camera import Camera
from src.core.game_session import GameSession
from src.core.orbital_mode_controller import OrbitalModeController
from src.core.coordinate import Coordinate


def _keys(pressed: dict):
    d = collections.defaultdict(bool)
    d.update(pressed)
    return d


def test_shift_boosts_camera_speed():
    normal = Camera(screen_w=900, screen_h=600)
    boosted = Camera(screen_w=900, screen_h=600)

    normal.update(1.0, _keys({pygame.K_d: True}))
    boosted.update(1.0, _keys({pygame.K_d: True, pygame.K_LSHIFT: True}))

    assert boosted.x > normal.x
    assert boosted.x == pytest.approx(normal.x * normal.boost_multiplier)


def _event(type_, **kwargs):
    return types.SimpleNamespace(type=type_, **kwargs)


@pytest.fixture
def controller():
    session = GameSession()
    session.setup_game()
    return OrbitalModeController(session)


def test_empty_click_starts_camera_drag(controller):
    down = _event(pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 300))
    controller.handle_input(down)

    assert controller.dragging_camera is True


def test_drag_pans_camera_opposite_to_mouse_movement(controller):
    controller.handle_input(_event(pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 300)))
    x_before, y_before = controller.camera.x, controller.camera.y

    controller.handle_input(_event(pygame.MOUSEMOTION, pos=(450, 320)))

    assert controller.camera.x < x_before
    assert controller.camera.y < y_before


def test_mouse_up_stops_drag(controller):
    controller.handle_input(_event(pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 300)))
    controller.handle_input(_event(pygame.MOUSEBUTTONUP, button=1))

    assert controller.dragging_camera is False

    x_before = controller.camera.x
    controller.handle_input(_event(pygame.MOUSEMOTION, pos=(500, 300)))
    assert controller.camera.x == x_before, "после отпускания ЛКМ движение мыши не должно двигать камеру"


def test_click_on_existing_module_does_not_start_drag(controller):
    controller.select_tower("laser")
    controller.place_tower(Coordinate(2300, 2000))
    controller.deselect()

    module_pos = controller.session.map.modules[0].position
    down = _event(pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 300))
    controller.camera.x, controller.camera.y = module_pos.x - 400, module_pos.y - 300

    controller.handle_input(down)

    assert controller.dragging_camera is False
    assert controller.selected_module is not None


def test_click_while_placing_tower_does_not_start_drag(controller):
    controller.select_tower("laser")
    down = _event(pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 300))
    controller.camera.x, controller.camera.y = 2300 - 400, 2000 - 300

    controller.handle_input(down)

    assert controller.dragging_camera is False
