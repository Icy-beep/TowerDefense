"""Экран выбора режима: клики по кнопкам "Бесконечный режим"/"Сюжет"/"Назад"."""
from src.ui.mode_select_screen import ModeSelectScreen


def test_click_inside_endless_button_returns_endless():
    screen = ModeSelectScreen()
    width, height = 900, 600
    screen._layout(width, height)
    x, y, w, h = screen._endless_rect
    center = (x + w // 2, y + h // 2)

    assert screen.handle_click(center, width, height) == "endless"


def test_click_inside_story_button_returns_none():
    """Кнопка "Сюжет" неактивна - клик по ней не должен ничего запускать."""
    screen = ModeSelectScreen()
    width, height = 900, 600
    screen._layout(width, height)
    x, y, w, h = screen._story_rect
    center = (x + w // 2, y + h // 2)

    assert screen.handle_click(center, width, height) is None


def test_click_inside_back_button_returns_back():
    screen = ModeSelectScreen()
    width, height = 900, 600
    screen._layout(width, height)
    x, y, w, h = screen._back_rect
    center = (x + w // 2, y + h // 2)

    assert screen.handle_click(center, width, height) == "back"


def test_click_outside_buttons_returns_none():
    screen = ModeSelectScreen()
    assert screen.handle_click((0, 0), 900, 600) is None


def test_buttons_do_not_overlap():
    screen = ModeSelectScreen()
    screen._layout(900, 600)
    _, endless_y, _, endless_h = screen._endless_rect
    _, story_y, _, story_h = screen._story_rect
    _, back_y, _, _ = screen._back_rect

    assert endless_y + endless_h <= story_y, "кнопки не должны перекрываться"
    assert story_y + story_h <= back_y, "кнопки не должны перекрываться"


def test_layout_adapts_to_window_size():
    screen = ModeSelectScreen()
    screen._layout(1200, 800)
    x, _, w, _ = screen._endless_rect

    assert 0 <= x <= 1200 - w
