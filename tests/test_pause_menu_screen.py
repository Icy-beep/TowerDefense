"""PauseMenuScreen: раскладка кнопок и определение кликов."""
import pygame
import pytest

from src.ui.pause_menu_screen import PauseMenuScreen

WIDTH, HEIGHT = 900, 600


def _center(rect):
    x, y, w, h = rect
    return (x + w // 2, y + h // 2)


@pytest.fixture
def screen():
    return PauseMenuScreen()


@pytest.mark.parametrize("key", ["resume", "save", "load", "settings", "main_menu", "exit"])
def test_click_on_each_button_returns_its_key(screen, key):
    screen._layout(WIDTH, HEIGHT)

    assert screen.handle_click(_center(screen._rects[key]), WIDTH, HEIGHT) == key


def test_click_outside_buttons_returns_none(screen):
    assert screen.handle_click((0, 0), WIDTH, HEIGHT) is None


def test_buttons_do_not_overlap(screen):
    screen._layout(WIDTH, HEIGHT)
    rects = [screen._rects[k] for k in ("resume", "save", "load", "settings", "main_menu", "exit")]
    for (_, y1, _, h1), (_, y2, _, _) in zip(rects, rects[1:]):
        assert y1 + h1 <= y2, "кнопки меню паузы не должны перекрываться"


def test_layout_adapts_to_window_size(screen):
    screen._layout(1200, 800)
    x, _, w, _ = screen._rects["resume"]

    assert 0 <= x <= 1200 - w


def test_render_does_not_crash_with_and_without_notice(screen):
    pygame.init()
    surface = pygame.Surface((WIDTH, HEIGHT))
    font = pygame.font.SysFont("Arial", 18)
    small_font = pygame.font.SysFont("Arial", 14)
    title_font = pygame.font.SysFont("Arial", 40, bold=True)

    screen.render(surface, WIDTH, HEIGHT, font, small_font, title_font)
    screen.render(surface, WIDTH, HEIGHT, font, small_font, title_font, notice="Пока не реализовано")
