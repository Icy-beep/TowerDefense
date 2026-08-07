"""Экран дерева технологий: выбор башни сверху, клики по веткам-заглушкам, "Назад"."""
import pygame

from src.ui.tech_tree_screen import TechTreeScreen

TOWER_OPTIONS = [
    {"type": "laser", "name": "Laser (50)"},
    {"type": "bullet", "name": "Bullet (100)"},
    {"type": "mortar", "name": "Mortar (200)"},
]


def test_click_tower_button_selects_it_and_returns_action():
    screen = TechTreeScreen()
    width, height = 900, 600
    screen._layout(width, height, TOWER_OPTIONS)
    x, y, w, h = screen._tower_rects["bullet"]
    center = (x + w // 2, y + h // 2)

    action = screen.handle_click(center, width, height, TOWER_OPTIONS)

    assert action == ("select_tower", "bullet")
    assert screen.selected_type == "bullet"


def test_click_branch_returns_select_branch_action():
    screen = TechTreeScreen()
    width, height = 900, 600
    screen._layout(width, height, TOWER_OPTIONS)
    x, y, w, h = screen._branch_rects["damage"]
    center = (x + w // 2, y + h // 2)

    action = screen.handle_click(center, width, height, TOWER_OPTIONS)

    assert action == ("select_branch", "damage")


def test_selected_branch_is_tracked_per_tower_type():
    """Ветка, выбранная у одной башни, не должна подсвечиваться у другой."""
    screen = TechTreeScreen()
    width, height = 900, 600
    screen._layout(width, height, TOWER_OPTIONS)
    x, y, w, h = screen._branch_rects["radius"]
    screen.handle_click((x + w // 2, y + h // 2), width, height, TOWER_OPTIONS)

    assert screen._selected_branch.get("laser") == "radius"
    assert screen._selected_branch.get("bullet") is None


def test_click_back_button_returns_back_action():
    screen = TechTreeScreen()
    width, height = 900, 600
    screen._layout(width, height, TOWER_OPTIONS)
    x, y, w, h = screen._back_rect
    center = (x + w // 2, y + h // 2)

    action = screen.handle_click(center, width, height, TOWER_OPTIONS)

    assert action == ("back", None)


def test_click_outside_everything_returns_none():
    screen = TechTreeScreen()
    assert screen.handle_click((0, 0), 900, 600, TOWER_OPTIONS) is None


def test_tower_buttons_do_not_overlap():
    screen = TechTreeScreen()
    screen._layout(900, 600, TOWER_OPTIONS)
    laser_x, _, laser_w, _ = screen._tower_rects["laser"]
    bullet_x, _, _, _ = screen._tower_rects["bullet"]

    assert laser_x + laser_w <= bullet_x


def test_branch_boxes_do_not_overlap():
    screen = TechTreeScreen()
    screen._layout(900, 600, TOWER_OPTIONS)
    radius_x, _, radius_w, _ = screen._branch_rects["radius"]
    damage_x, _, damage_w, _ = screen._branch_rects["damage"]
    speed_x, _, _, _ = screen._branch_rects["attack_speed"]

    assert radius_x + radius_w <= damage_x
    assert damage_x + damage_w <= speed_x


def test_render_does_not_crash():
    screen = TechTreeScreen()
    pygame.init()
    surface = pygame.Surface((900, 600))
    font = pygame.font.SysFont("Arial", 18)
    small_font = pygame.font.SysFont("Arial", 14)
    title_font = pygame.font.SysFont("Arial", 40, bold=True)

    screen.render(surface, 900, 600, font, small_font, title_font, TOWER_OPTIONS)
