"""Режим экрана и переход между главным меню и настройками (GameView)."""
import types

import pygame
import pytest

from src.core.game_session import GameSession
from src.core.settings import DISPLAY_MODE_BORDERLESS, DISPLAY_MODE_FULLSCREEN, DISPLAY_MODE_WINDOWED, Settings
from src.ui.game_window import GameView


@pytest.fixture
def view(monkeypatch):
    game_view = GameView(GameSession(), settings=Settings())
    monkeypatch.setattr(game_view.settings, "save", lambda *a, **kw: None)
    return game_view


def _click_event(pos):
    """Минимальное событие клика левой кнопкой мыши для _handle_menu_input."""
    return types.SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def test_default_display_mode_is_windowed(view):
    assert view.settings.display_mode == DISPLAY_MODE_WINDOWED


def test_apply_settings_action_display_mode_switches_to_fullscreen(view):
    view._apply_settings_action(("display_mode", DISPLAY_MODE_FULLSCREEN))

    assert view.settings.display_mode == DISPLAY_MODE_FULLSCREEN


def test_escape_in_settings_returns_to_main_menu_without_quitting(view):
    view.menu_view = "settings"

    view._handle_escape()

    assert view.menu_view == "main"
    assert view.running is True


def test_escape_in_main_menu_quits(view):
    view.menu_view = "main"

    view._handle_escape()

    assert view.running is False


def test_menu_click_on_settings_switches_menu_view(view):
    view.menu_screen._layout(view.width, view.height)
    x, y, w, h = view.menu_screen._settings_rect

    view._handle_menu_input(_click_event((x + w // 2, y + h // 2)))

    assert view.menu_view == "settings"


def test_settings_click_on_display_mode_switches_mode(view):
    view.menu_view = "settings"
    view.settings_screen._layout(view.width, view.height)
    x, y, w, h = view.settings_screen._display_mode_rects[DISPLAY_MODE_BORDERLESS]

    view._handle_menu_input(_click_event((x + w // 2, y + h // 2)))

    assert view.settings.display_mode == DISPLAY_MODE_BORDERLESS


def test_settings_click_on_music_volume_up_increases_it(view):
    view.menu_view = "settings"
    original_volume = view.settings.music_volume
    view.settings_screen._layout(view.width, view.height)
    x, y, w, h = view.settings_screen._music_up_rect

    view._handle_menu_input(_click_event((x + w // 2, y + h // 2)))

    assert view.settings.music_volume > original_volume


def test_settings_click_on_back_returns_to_main_menu(view):
    view.menu_view = "settings"
    view.settings_screen._layout(view.width, view.height)
    x, y, w, h = view.settings_screen._back_rect

    view._handle_menu_input(_click_event((x + w // 2, y + h // 2)))

    assert view.menu_view == "main"


def test_resize_in_windowed_mode_updates_resolution(view):
    view._handle_resize(1024, 768)

    assert view.settings.resolution == (1024, 768)


def test_start_button_opens_mode_select_instead_of_starting_immediately(view):
    view.menu_screen._layout(view.width, view.height)
    x, y, w, h = view.menu_screen._start_rect

    view._handle_menu_input(_click_event((x + w // 2, y + h // 2)))

    assert view.menu_view == "mode_select"
    assert view.controller is None, "игра не должна стартовать раньше выбора режима"


def test_mode_select_endless_click_starts_an_endless_game(view):
    view.menu_view = "mode_select"
    view.mode_select_screen._layout(view.width, view.height)
    x, y, w, h = view.mode_select_screen._endless_rect

    view._handle_menu_input(_click_event((x + w // 2, y + h // 2)))

    assert view.controller is not None
    assert view.session.endless is True


def test_mode_select_story_click_does_nothing(view):
    """Кнопка "Сюжет" пока заглушка - клик по ней не должен запускать игру."""
    view.menu_view = "mode_select"
    view.mode_select_screen._layout(view.width, view.height)
    x, y, w, h = view.mode_select_screen._story_rect

    view._handle_menu_input(_click_event((x + w // 2, y + h // 2)))

    assert view.menu_view == "mode_select"
    assert view.controller is None


def test_mode_select_back_click_returns_to_main_menu(view):
    view.menu_view = "mode_select"
    view.mode_select_screen._layout(view.width, view.height)
    x, y, w, h = view.mode_select_screen._back_rect

    view._handle_menu_input(_click_event((x + w // 2, y + h // 2)))

    assert view.menu_view == "main"


def test_escape_in_mode_select_returns_to_main_menu_without_quitting(view):
    view.menu_view = "mode_select"

    view._handle_escape()

    assert view.menu_view == "main"
    assert view.running is True
