"""Интеграционные тесты save/load через GameView: сохранение/загрузка из паузы,
кнопка "Продолжить" в главном меню и таймер автосохранения."""
import types

import pygame
import pytest

from src.core.game_session import GameSession
from src.core.settings import Settings
from src.enums import GameState
from src.localization.loc import loc
from src.save_load.save_manager import QUICKSAVE_SLOT_ID, SaveManager
from src.ui.game_window import GameView


@pytest.fixture
def view(monkeypatch, tmp_path):
    game_view = GameView(GameSession(), settings=Settings())
    monkeypatch.setattr(game_view.settings, "save", lambda *a, **kw: None)
    game_view.save_manager = SaveManager(saves_dir=tmp_path)
    game_view._start_game()
    return game_view


def _click_event(pos):
    """Минимальное событие клика левой кнопкой мыши."""
    return types.SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def test_new_save_from_pause_menu_writes_a_slot_file(view, tmp_path):
    view._handle_escape()
    view._apply_pause_action("save")
    view.save_load_screen._layout(view.width, view.height, "save", [])

    view._apply_save_load_action(("new_save", None))

    saved_files = list(tmp_path.glob("*.json"))
    assert len(saved_files) == 1


def test_new_save_shows_success_notice(view):
    view._handle_escape()

    view._apply_save_load_action(("new_save", None))

    assert view._pause_notice == loc.get("pause.saved")


def test_save_then_load_round_trip_restores_credits(view):
    view.session.resources.credits = 4242
    view._handle_escape()
    view._apply_save_load_action(("new_save", None))
    slot_id = view.save_manager.list_slots()[0]["slot_id"]

    view.session.resources.credits = 0
    view._apply_save_load_action(("load_slot", slot_id))

    assert view.session.resources.credits == 4242


def test_load_slot_resumes_game_and_returns_to_pause_menu_view(view):
    view._handle_escape()
    view._apply_save_load_action(("new_save", None))
    slot_id = view.save_manager.list_slots()[0]["slot_id"]

    view._apply_save_load_action(("load_slot", slot_id))

    assert view.session.state == GameState.PLAYING
    assert view.pause_menu_open is False
    assert view.pause_view == "menu"


def test_load_missing_slot_shows_failure_notice_and_stays_paused(view):
    view._handle_escape()

    view._apply_save_load_action(("load_slot", "no_such_slot"))

    assert view._pause_notice == loc.get("pause.load_failed")
    assert view.session.state == GameState.PAUSED


def test_continue_button_hidden_on_fresh_main_menu(view):
    view._apply_pause_action("main_menu")

    has_continue = view.save_manager.has_any_save()

    assert has_continue is False


def test_continue_game_loads_most_recent_save_and_creates_controller(view):
    view.session.resources.credits = 777
    view.save_manager.save_to_slot(view.session, "slot_a")
    view._apply_pause_action("main_menu")
    assert view.controller is None

    view._continue_game()

    assert view.controller is not None
    assert view.session.resources.credits == 777
    assert view.session.state == GameState.PLAYING


def test_continue_button_click_in_main_menu_starts_the_game(view):
    view.save_manager.save_to_slot(view.session, "slot_a")
    view._apply_pause_action("main_menu")
    has_continue = view.save_manager.has_any_save()
    view.menu_screen._layout(view.width, view.height, has_continue)
    x, y, w, h = view.menu_screen._continue_rect

    view._handle_menu_input(_click_event((x + w // 2, y + h // 2)))

    assert view.session.state == GameState.PLAYING
    assert view.controller is not None


def test_continue_game_does_nothing_when_no_saves_exist(view):
    view._apply_pause_action("main_menu")

    view._continue_game()

    assert view.controller is None
    assert view.session.state == GameState.MENU


def test_autosave_ticks_and_writes_quicksave_after_interval(view, tmp_path):
    view.settings.autosave_interval_seconds = 30.0
    view._autosave_timer = 0.0

    view._tick_autosave(29.0)
    assert not (tmp_path / f"{QUICKSAVE_SLOT_ID}.json").exists()

    view._tick_autosave(1.5)
    assert (tmp_path / f"{QUICKSAVE_SLOT_ID}.json").exists()


def test_autosave_disabled_when_interval_is_zero(view, tmp_path):
    view.settings.autosave_interval_seconds = 0.0
    view._autosave_timer = 0.0

    view._tick_autosave(1000.0)

    assert not (tmp_path / f"{QUICKSAVE_SLOT_ID}.json").exists()
