"""Открытие секторов через OrbitalModeController: Ctrl+ЛКМ, отдельно от обычного
клика (который используется для перетаскивания камеры - см. handle_click)."""
import pygame
import pytest

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.core.orbital_mode_controller import OrbitalModeController


@pytest.fixture
def controller():
    session = GameSession()
    session.setup_game()
    return OrbitalModeController(session)


def _locked_sector(controller):
    return next(s for s in controller.session.map.sectors if not s.unlocked)


def _mousedown_event(controller, world_pos):
    screen_pos = controller.camera.world_to_screen(world_pos.x, world_pos.y)
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=screen_pos)


def test_try_unlock_sector_spends_credits_and_unlocks(controller):
    locked = _locked_sector(controller)
    controller.session.resources.credits = 100000
    point = Coordinate(locked.bounds[0] + 1, locked.bounds[1] + 1)

    ok = controller.try_unlock_sector(point)

    assert ok is True
    assert locked.unlocked is True


def test_plain_click_in_locked_sector_does_not_spend_credits(controller):
    """Обычный клик по пустому месту в закрытом секторе не должен тратить кредиты -
    это тот же клик, что запускает перетаскивание камеры (handle_input)."""
    locked = _locked_sector(controller)
    point = Coordinate(locked.bounds[0] + 1, locked.bounds[1] + 1)
    credits_before = controller.session.resources.credits

    result = controller.handle_click(point)

    assert result == "none"
    assert not locked.unlocked
    assert controller.session.resources.credits == credits_before


def test_ctrl_click_unlocks_sector_and_does_not_start_camera_drag(controller, monkeypatch):
    locked = _locked_sector(controller)
    controller.session.resources.credits = 100000
    monkeypatch.setattr(pygame.key, "get_mods", lambda: pygame.KMOD_CTRL)

    handled = controller.handle_input(_mousedown_event(controller, Coordinate(locked.bounds[0] + 1, locked.bounds[1] + 1)))

    assert handled is True
    assert locked.unlocked is True
    assert controller.dragging_camera is False


def test_plain_click_without_ctrl_still_starts_camera_drag_on_empty_space(controller, monkeypatch):
    locked = _locked_sector(controller)
    monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)

    handled = controller.handle_input(_mousedown_event(controller, Coordinate(locked.bounds[0] + 1, locked.bounds[1] + 1)))

    assert handled is True
    assert not locked.unlocked
    assert controller.dragging_camera is True


def test_ctrl_click_without_enough_credits_does_not_crash_or_unlock(controller, monkeypatch):
    locked = _locked_sector(controller)
    controller.session.resources.credits = 0
    monkeypatch.setattr(pygame.key, "get_mods", lambda: pygame.KMOD_CTRL)

    handled = controller.handle_input(_mousedown_event(controller, Coordinate(locked.bounds[0] + 1, locked.bounds[1] + 1)))

    assert handled is True
    assert not locked.unlocked
