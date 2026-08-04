"""Экран настроек: клики по режиму экрана, разрешению, громкости, языку и кнопке "Назад"."""
import pygame
import pytest

from src.core.settings import DISPLAY_MODE_BORDERLESS, DISPLAY_MODE_WINDOWED, Settings
from src.ui.settings_screen import SettingsScreen

WIDTH, HEIGHT = 900, 600


def _center(rect):
    x, y, w, h = rect
    return (x + w // 2, y + h // 2)


@pytest.fixture
def screen():
    return SettingsScreen()


def test_click_on_display_mode_segment_returns_display_mode_action(screen):
    settings = Settings()
    screen._layout(WIDTH, HEIGHT)

    action = screen.handle_click(_center(screen._display_mode_rects[DISPLAY_MODE_BORDERLESS]),
                                  WIDTH, HEIGHT, settings)

    assert action == ("display_mode", DISPLAY_MODE_BORDERLESS)


def test_click_on_back_button_returns_back(screen):
    settings = Settings()
    screen._layout(WIDTH, HEIGHT)

    assert screen.handle_click(_center(screen._back_rect), WIDTH, HEIGHT, settings) == ("back", None)


def test_click_outside_controls_returns_none(screen):
    settings = Settings()
    assert screen.handle_click((0, 0), WIDTH, HEIGHT, settings) is None


def test_resolution_stepper_returns_action_when_windowed(screen):
    settings = Settings(display_mode=DISPLAY_MODE_WINDOWED)
    screen._layout(WIDTH, HEIGHT)

    action = screen.handle_click(_center(screen._resolution_next_rect), WIDTH, HEIGHT, settings)

    assert action == ("resolution", 1)


def test_resolution_stepper_disabled_when_borderless(screen):
    settings = Settings(display_mode=DISPLAY_MODE_BORDERLESS)
    screen._layout(WIDTH, HEIGHT)

    action = screen.handle_click(_center(screen._resolution_next_rect), WIDTH, HEIGHT, settings)

    assert action is None


def test_music_volume_stepper_returns_action(screen):
    settings = Settings()
    screen._layout(WIDTH, HEIGHT)

    assert screen.handle_click(_center(screen._music_up_rect), WIDTH, HEIGHT, settings) == ("music_volume", 1)
    assert screen.handle_click(_center(screen._music_down_rect), WIDTH, HEIGHT, settings) == ("music_volume", -1)


def test_sfx_volume_stepper_returns_action(screen):
    settings = Settings()
    screen._layout(WIDTH, HEIGHT)

    assert screen.handle_click(_center(screen._sfx_up_rect), WIDTH, HEIGHT, settings) == ("sfx_volume", 1)


def test_language_stepper_returns_action(screen):
    settings = Settings()
    screen._layout(WIDTH, HEIGHT)

    assert screen.handle_click(_center(screen._language_next_rect), WIDTH, HEIGHT, settings) == ("language", 1)


def test_layout_adapts_to_window_size(screen):
    screen._layout(1200, 800)
    x, _, w, _ = screen._back_rect

    assert 0 <= x <= 1200 - w


def test_rows_do_not_overlap(screen):
    screen._layout(WIDTH, HEIGHT)
    windowed_y = screen._display_mode_rects[DISPLAY_MODE_WINDOWED][1]
    windowed_h = screen._display_mode_rects[DISPLAY_MODE_WINDOWED][3]
    resolution_y = screen._resolution_prev_rect[1]

    assert windowed_y + windowed_h <= resolution_y


def test_render_does_not_crash(screen):
    pygame.init()
    surface = pygame.Surface((WIDTH, HEIGHT))
    font = pygame.font.SysFont("Arial", 18)
    small_font = pygame.font.SysFont("Arial", 14)
    title_font = pygame.font.SysFont("Arial", 40, bold=True)
    settings = Settings()

    screen.render(surface, WIDTH, HEIGHT, font, small_font, title_font, settings)
