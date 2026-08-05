"""Главное меню: клики по кнопкам "Продолжить"/"Начать игру"/"Настройки"/"Выйти"."""
import pygame

from src.ui.menu_screen import MenuScreen


def test_click_inside_start_button_returns_start():
    menu = MenuScreen()
    width, height = 900, 600
    menu._layout(width, height)
    x, y, w, h = menu._start_rect
    center = (x + w // 2, y + h // 2)

    assert menu.handle_click(center, width, height) == "start"


def test_click_inside_settings_button_returns_settings():
    menu = MenuScreen()
    width, height = 900, 600
    menu._layout(width, height)
    x, y, w, h = menu._settings_rect
    center = (x + w // 2, y + h // 2)

    assert menu.handle_click(center, width, height) == "settings"


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
    _, settings_y, _, settings_h = menu._settings_rect
    _, exit_y, _, _ = menu._exit_rect

    assert start_y + start_h <= settings_y, "кнопки не должны перекрываться"
    assert settings_y + settings_h <= exit_y, "кнопки не должны перекрываться"


def test_layout_adapts_to_window_size():
    menu = MenuScreen()
    menu._layout(1200, 800)
    x, _, w, _ = menu._start_rect

    assert 0 <= x <= 1200 - w


def test_continue_button_hidden_without_has_continue():
    menu = MenuScreen()
    menu._layout(900, 600)

    assert menu._continue_rect == (0, 0, 0, 0)
    assert menu.handle_click((0, 0), 900, 600) is None


def test_continue_button_click_returns_continue_when_enabled():
    menu = MenuScreen()
    width, height = 900, 600
    menu._layout(width, height, has_continue=True)
    x, y, w, h = menu._continue_rect
    center = (x + w // 2, y + h // 2)

    assert menu.handle_click(center, width, height, has_continue=True) == "continue"


def test_continue_button_sits_above_start_button_when_enabled():
    menu = MenuScreen()
    menu._layout(900, 600, has_continue=True)
    _, continue_y, _, continue_h = menu._continue_rect
    _, start_y, _, _ = menu._start_rect

    assert continue_y + continue_h <= start_y


def test_ignoring_has_continue_click_does_not_match_start_button_by_accident():
    """Без has_continue раскладка сдвигается вверх - клик по бывшей позиции кнопки
    "Продолжить" не должен случайно совпасть с какой-то другой кнопкой."""
    menu = MenuScreen()
    menu._layout(900, 600, has_continue=True)
    continue_center = (menu._continue_rect[0] + menu._continue_rect[2] // 2,
                        menu._continue_rect[1] + menu._continue_rect[3] // 2)

    assert menu.handle_click(continue_center, 900, 600, has_continue=False) is None


def test_render_with_continue_does_not_crash():
    menu = MenuScreen()
    pygame.init()
    surface = pygame.Surface((900, 600))
    font = pygame.font.SysFont("Arial", 18)
    title_font = pygame.font.SysFont("Arial", 40, bold=True)

    menu.render(surface, 900, 600, font, title_font, has_continue=True)
