"""Кликабельная HUD-панель построек (нижняя командная панель): раскладка иконок и
попадание клика (см. HudRenderer._layout_build_panel/_draw_build_icons/handle_build_click)."""
import types

import pygame

from src.ui.hud_renderer import HudRenderer

TOWER_OPTIONS = [
    {"key": pygame.K_1, "type": "laser", "name": "Laser (50)", "color": (0, 255, 255)},
    {"key": pygame.K_2, "type": "bullet", "name": "Bullet (100)", "color": (255, 255, 0)},
    {"key": pygame.K_3, "type": "mortar", "name": "Mortar (200)", "color": (255, 100, 0)},
    {"key": pygame.K_4, "type": "generator", "name": "Generator (220)", "color": (255, 215, 0)},
    {"key": pygame.K_5, "type": "pylon", "name": "Pylon (60)", "color": (0, 200, 120)},
]

WIDTH, HEIGHT = 900, 600


def test_build_panel_slots_do_not_overlap_and_are_centered():
    renderer = HudRenderer()
    slots = renderer._layout_build_panel(TOWER_OPTIONS, WIDTH, HEIGHT)

    assert len(slots) == len(TOWER_OPTIONS)
    for (rect_a, _), (rect_b, _) in zip(slots, slots[1:]):
        assert rect_a.right <= rect_b.left, "иконки построек не должны перекрываться"

    group_left = slots[0][0].left
    group_right = slots[-1][0].right
    center = (group_left + group_right) / 2
    assert abs(center - WIDTH / 2) < 2, "ряд иконок должен быть отцентрирован по ширине"


def test_handle_build_click_returns_type_for_each_icon():
    renderer = HudRenderer()
    slots = renderer._layout_build_panel(TOWER_OPTIONS, WIDTH, HEIGHT)

    for rect, opt in slots:
        result = renderer.handle_build_click(rect.center, TOWER_OPTIONS, WIDTH, HEIGHT)
        assert result == opt["type"]


def test_handle_build_click_returns_none_outside_panel():
    renderer = HudRenderer()

    assert renderer.handle_build_click((5, 5), TOWER_OPTIONS, WIDTH, HEIGHT) is None


def test_handle_build_click_returns_none_for_empty_options():
    renderer = HudRenderer()

    assert renderer.handle_build_click((WIDTH // 2, HEIGHT - 60), [], WIDTH, HEIGHT) is None


def _fake_controller(credits=1000, selected_tower=None):
    session = types.SimpleNamespace(
        tower_factory=types.SimpleNamespace(
            get_cost=lambda t: {"laser": 50, "bullet": 100, "mortar": 200,
                                 "generator": 220, "pylon": 60}.get(t)
        )
    )
    return types.SimpleNamespace(session=session), {
        "credits": credits, "selected_tower": selected_tower,
    }


def test_draw_build_icons_does_not_crash_when_affordable_and_selected():
    renderer = HudRenderer()
    pygame.init()
    screen = pygame.Surface((WIDTH, HEIGHT))
    small_font = pygame.font.SysFont("Arial", 14)
    controller, state = _fake_controller(credits=1000, selected_tower="laser")
    slots = renderer._layout_build_panel(TOWER_OPTIONS, WIDTH, HEIGHT)

    renderer._draw_build_icons(screen, state, controller, slots, small_font)


def test_draw_build_icons_does_not_crash_when_unaffordable_and_no_sprite_manager():
    renderer = HudRenderer(sprite_manager=None)
    pygame.init()
    screen = pygame.Surface((WIDTH, HEIGHT))
    small_font = pygame.font.SysFont("Arial", 14)
    controller, state = _fake_controller(credits=0, selected_tower=None)
    slots = renderer._layout_build_panel(TOWER_OPTIONS, WIDTH, HEIGHT)

    renderer._draw_build_icons(screen, state, controller, slots, small_font)


def test_draw_build_icons_does_not_crash_without_tower_factory():
    """Регрессия: если у переданного controller.session вообще нет tower_factory
    (например, урезанный тестовый двойник), панель не должна падать - просто не
    покажет цену."""
    renderer = HudRenderer()
    pygame.init()
    screen = pygame.Surface((WIDTH, HEIGHT))
    small_font = pygame.font.SysFont("Arial", 14)
    controller = types.SimpleNamespace(session=types.SimpleNamespace())
    state = {"credits": 100, "selected_tower": None}
    slots = renderer._layout_build_panel(TOWER_OPTIONS, WIDTH, HEIGHT)

    renderer._draw_build_icons(screen, state, controller, slots, small_font)
