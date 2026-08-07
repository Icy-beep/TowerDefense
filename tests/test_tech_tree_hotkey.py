"""Открытие дерева технологий (K) хоткеем и кнопкой в HUD, закрытие ESC/K/кнопкой."""
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


def _key_event(key):
    return types.SimpleNamespace(type=pygame.KEYDOWN, key=key)


def _click_event(pos):
    return types.SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def test_hotkey_opens_tech_tree(view):
    assert view.tech_tree_open is False
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=view.TECH_TREE_KEY))

    view.handle_events()

    assert view.tech_tree_open is True


def test_escape_closes_tech_tree_without_opening_pause_menu(view):
    view.tech_tree_open = True

    view._handle_escape()

    assert view.tech_tree_open is False
    assert view.pause_menu_open is False
    assert view.session.state == GameState.PLAYING


def test_tech_tree_input_key_closes_open_tree(view):
    view.tech_tree_open = True

    view._handle_tech_tree_input(_key_event(view.TECH_TREE_KEY))

    assert view.tech_tree_open is False


def test_hud_button_click_opens_and_closes_tech_tree(view):
    rect = view.hud_renderer._layout_tech_tree_button(view.width)
    center = (rect.x + rect.w // 2, rect.y + rect.h // 2)

    consumed = view._handle_tech_tree_button_click(_click_event(center))
    assert consumed is True
    assert view.tech_tree_open is True

    view._handle_tech_tree_input(_click_event(center))
    assert view.tech_tree_open is False


def test_tech_tree_back_button_closes_tree(view):
    view.tech_tree_open = True
    view.tech_tree_screen._layout(view.width, view.height, view.combat_tower_options)
    x, y, w, h = view.tech_tree_screen._back_rect

    view._handle_tech_tree_input(_click_event((x + w // 2, y + h // 2)))

    assert view.tech_tree_open is False


def test_build_panel_click_does_not_leak_while_tech_tree_open(view):
    """Пока открыто дерево технологий, клики не должны доходить до постройки башен."""
    view.tech_tree_open = True
    towers_before = len(view.session.map.modules)

    view._handle_tech_tree_input(_click_event((10, 10)))

    assert len(view.session.map.modules) == towers_before


def test_combat_tower_options_excludes_infrastructure(view):
    types_ = {opt["type"] for opt in view.combat_tower_options}
    assert types_ == {"laser", "bullet", "mortar"}
