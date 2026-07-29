"""Заготовка главного меню: клики по кнопкам "Начать игру"/"Выйти".
Раскладка кнопок пересчитывается под переданный размер окна, поэтому
тест не завязан на конкретное окно pygame."""
from src.ui.menu_screen import MenuScreen


def test_click_inside_start_button_returns_start():
    menu = MenuScreen()
    width, height = 900, 600
    menu._layout(width, height)
    x, y, w, h = menu._start_rect
    center = (x + w // 2, y + h // 2)

    assert menu.handle_click(center, width, height) == "start"


def test_click_inside_exit_button_returns_exit():
    menu = MenuScreen()
    width, height = 900, 600
    menu._layout(width, height)
    x, y, w, h = menu._exit_rect
    center = (x + w // 2, y + h // 2)

    assert menu.handle_click(center, width, height) == "exit"


def test_click_outside_buttons_returns_none():
    menu = MenuScreen()
    assert menu.handle_click((0, 0), 900, 600) is None


def test_buttons_do_not_overlap():
    menu = MenuScreen()
    menu._layout(900, 600)
    _, start_y, _, start_h = menu._start_rect
    _, exit_y, _, _ = menu._exit_rect

    assert start_y + start_h <= exit_y, "кнопки не должны перекрываться"


def test_layout_adapts_to_window_size():
    menu = MenuScreen()
    menu._layout(1200, 800)
    x, _, w, _ = menu._start_rect

    assert 0 <= x <= 1200 - w
