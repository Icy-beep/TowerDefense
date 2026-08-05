"""SaveLoadScreen: раскладка и клики по кнопке "Новое сохранение", слотам и "Назад"."""
import pygame
import pytest

from src.ui.save_load_screen import SaveLoadScreen

WIDTH, HEIGHT = 900, 600


def _center(rect):
    x, y, w, h = rect
    return (x + w // 2, y + h // 2)


@pytest.fixture
def screen():
    return SaveLoadScreen()


def _slot(slot_id, is_quicksave=False, elapsed_time=10.0):
    return {
        "slot_id": slot_id,
        "saved_at": "2024-01-01T12:00:00",
        "endless": True,
        "elapsed_time": elapsed_time,
        "is_quicksave": is_quicksave,
    }


def test_click_on_back_button_returns_back(screen):
    screen._layout(WIDTH, HEIGHT, "save", [])

    assert screen.handle_click(_center(screen._back_rect), WIDTH, HEIGHT, "save", []) == ("back", None)


def test_click_outside_controls_returns_none(screen):
    assert screen.handle_click((0, 0), WIDTH, HEIGHT, "save", []) is None


def test_save_mode_new_save_button_returns_new_save(screen):
    screen._layout(WIDTH, HEIGHT, "save", [])

    action = screen.handle_click(_center(screen._new_save_rect), WIDTH, HEIGHT, "save", [])

    assert action == ("new_save", None)


def test_load_mode_has_no_new_save_button(screen):
    slots = [_slot("save_1")]
    screen._layout(WIDTH, HEIGHT, "load", slots)

    assert screen._new_save_rect == (0, 0, 0, 0)


def test_click_on_slot_in_save_mode_returns_save_slot(screen):
    slots = [_slot("save_1")]
    screen._layout(WIDTH, HEIGHT, "save", slots)
    rect, slot_id = screen._slot_rects[0]

    action = screen.handle_click(_center(rect), WIDTH, HEIGHT, "save", slots)

    assert action == ("save_slot", "save_1")


def test_click_on_slot_in_load_mode_returns_load_slot(screen):
    slots = [_slot("save_1")]
    screen._layout(WIDTH, HEIGHT, "load", slots)
    rect, slot_id = screen._slot_rects[0]

    action = screen.handle_click(_center(rect), WIDTH, HEIGHT, "load", slots)

    assert action == ("load_slot", "save_1")


def test_quicksave_slot_first_in_load_mode_ordering_is_preserved_from_input(screen):
    """Экран сам не сортирует и не переупорядочивает - порядок (быстрое сохранение
    первым в режиме загрузки) обеспечивает вызывающая сторона (GameView._current_save_slots).
    Здесь только проверяем, что первый переданный слот получает первую строку."""
    slots = [_slot("_quicksave", is_quicksave=True), _slot("save_1")]
    screen._layout(WIDTH, HEIGHT, "load", slots)

    assert screen._slot_rects[0][1] == "_quicksave"
    assert screen._slot_rects[1][1] == "save_1"


def test_slot_rows_do_not_overlap_with_new_save_button(screen):
    slots = [_slot("save_1"), _slot("save_2")]
    screen._layout(WIDTH, HEIGHT, "save", slots)

    new_save_y = screen._new_save_rect[1]
    new_save_h = screen._new_save_rect[3]
    first_slot_y = screen._slot_rects[0][0][1]

    assert new_save_y + new_save_h <= first_slot_y


def test_slot_rows_do_not_overlap_each_other(screen):
    slots = [_slot("save_1"), _slot("save_2"), _slot("save_3")]
    screen._layout(WIDTH, HEIGHT, "load", slots)

    for (rect_a, _), (rect_b, _) in zip(screen._slot_rects, screen._slot_rects[1:]):
        assert rect_a[1] + rect_a[3] <= rect_b[1]


def test_back_button_is_below_all_slots(screen):
    slots = [_slot("save_1"), _slot("save_2")]
    screen._layout(WIDTH, HEIGHT, "load", slots)

    last_rect, _ = screen._slot_rects[-1]
    assert last_rect[1] + last_rect[3] <= screen._back_rect[1]


def test_only_max_visible_slots_get_a_row():
    screen = SaveLoadScreen()
    slots = [_slot(f"save_{i}") for i in range(10)]
    screen._layout(WIDTH, HEIGHT, "load", slots)

    from src.ui.save_load_screen import MAX_VISIBLE_SLOTS
    assert len(screen._slot_rects) == MAX_VISIBLE_SLOTS


def test_layout_adapts_to_window_size(screen):
    screen._layout(1200, 800, "save", [])
    x, _, w, _ = screen._back_rect

    assert 0 <= x <= 1200 - w


def test_render_does_not_crash_empty_and_with_slots(screen):
    pygame.init()
    surface = pygame.Surface((WIDTH, HEIGHT))
    font = pygame.font.SysFont("Arial", 18)
    small_font = pygame.font.SysFont("Arial", 14)
    title_font = pygame.font.SysFont("Arial", 40, bold=True)

    screen.render(surface, WIDTH, HEIGHT, font, small_font, title_font, "save", [])
    screen.render(surface, WIDTH, HEIGHT, font, small_font, title_font, "load",
                   [_slot("_quicksave", is_quicksave=True), _slot("save_1")])
