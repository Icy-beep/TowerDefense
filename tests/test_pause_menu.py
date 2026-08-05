"""Внутриигровое меню паузы (ESC): открытие/закрытие, save/load-заглушки, выход в меню/из игры."""
import types

import pygame
import pytest

from src.core.game_session import GameSession
from src.core.settings import Settings
from src.enums import GameState
from src.ui.game_window import GameView


@pytest.fixture
def view(monkeypatch):
    game_view = GameView(GameSession(), settings=Settings())
    monkeypatch.setattr(game_view.settings, "save", lambda *a, **kw: None)
    game_view._start_game()
    return game_view


def _click_event(pos):
    """Минимальное событие клика левой кнопкой мыши для _handle_pause_menu_input."""
    return types.SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def test_escape_during_play_opens_pause_menu_and_pauses(view):
    assert view.session.state == GameState.PLAYING

    view._handle_escape()

    assert view.session.state == GameState.PAUSED
    assert view.pause_menu_open is True
    assert view.pause_view == "menu"


def test_escape_again_closes_pause_menu_and_resumes(view):
    view._handle_escape()

    view._handle_escape()

    assert view.session.state == GameState.PLAYING
    assert view.pause_menu_open is False


def test_escape_in_pause_settings_returns_to_pause_menu_without_resuming(view):
    view._handle_escape()
    view.pause_view = "settings"

    view._handle_escape()

    assert view.pause_view == "menu"
    assert view.session.state == GameState.PAUSED


def test_escape_while_raw_paused_by_p_key_opens_menu(view):
    """Пауза через P (без открытого меню) — ESC должен открыть меню, а не сразу возобновить игру."""
    view.session.state = GameState.PAUSED
    view.pause_menu_open = False

    view._handle_escape()

    assert view.pause_menu_open is True
    assert view.session.state == GameState.PAUSED


def test_resume_button_resumes_game(view):
    view._handle_escape()

    view._apply_pause_action("resume")

    assert view.session.state == GameState.PLAYING
    assert view.pause_menu_open is False


def test_save_button_opens_save_load_screen_in_save_mode(view):
    view._handle_escape()

    view._apply_pause_action("save")

    assert view.pause_view == "save_load"
    assert view._save_load_mode == "save"
    assert view.session.state == GameState.PAUSED


def test_load_button_opens_save_load_screen_in_load_mode(view):
    view._handle_escape()

    view._apply_pause_action("load")

    assert view.pause_view == "save_load"
    assert view._save_load_mode == "load"


def test_settings_button_switches_pause_view(view):
    view._handle_escape()

    view._apply_pause_action("settings")

    assert view.pause_view == "settings"


def test_main_menu_button_returns_to_main_menu_and_clears_controller(view):
    view._handle_escape()

    view._apply_pause_action("main_menu")

    assert view.session.state == GameState.MENU
    assert view.controller is None
    assert view.pause_menu_open is False
    assert view.menu_view == "main"


def test_exit_button_stops_running(view):
    view._handle_escape()

    view._apply_pause_action("exit")

    assert view.running is False


def test_click_routes_through_handle_pause_menu_input(view):
    view._handle_escape()
    view.pause_menu_screen._layout(view.width, view.height)
    x, y, w, h = view.pause_menu_screen._rects["resume"]

    view._handle_pause_menu_input(_click_event((x + w // 2, y + h // 2)))

    assert view.session.state == GameState.PLAYING


def test_pause_menu_click_does_not_leak_to_controller(view):
    """Пока открыто меню паузы, клики не должны доходить до контроллера (ставить башни и т.п.)."""
    view._handle_escape()
    towers_before = len(view.session.map.modules)
    view.pause_menu_screen._layout(view.width, view.height)
    x, y, w, h = view.pause_menu_screen._rects["save"]

    view._handle_pause_menu_input(_click_event((x + w // 2, y + h // 2)))

    assert len(view.session.map.modules) == towers_before
