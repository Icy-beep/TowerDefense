"""Экран дерева технологий: выбор башни сверху, покупка веток по центру, "Назад".
Апгрейд ветки общий на весь тип башни (см. GameSession.upgrade_tech_branch)."""
import pygame
import pytest

from src.core.game_session import GameSession
from src.ui.tech_tree_screen import TechTreeScreen

TOWER_OPTIONS = [
    {"type": "laser", "name": "Laser (50)"},
    {"type": "bullet", "name": "Bullet (100)"},
    {"type": "mortar", "name": "Mortar (200)"},
]


@pytest.fixture
def session():
    s = GameSession()
    s.setup_game()
    return s


def test_click_tower_button_selects_it(session):
    screen = TechTreeScreen()
    width, height = 900, 600
    screen._layout(width, height, TOWER_OPTIONS)
    x, y, w, h = screen._tower_rects["bullet"]
    center = (x + w // 2, y + h // 2)

    action = screen.handle_click(center, width, height, TOWER_OPTIONS, session)

    assert action is None
    assert screen.selected_type == "bullet"


def test_click_branch_purchases_upgrade_via_session(session):
    screen = TechTreeScreen()
    width, height = 900, 600
    screen._layout(width, height, TOWER_OPTIONS)
    session.resources.scrap = 1000
    x, y, w, h = screen._branch_rects["damage"]
    scrap_before = session.resources.scrap

    screen.handle_click((x + w // 2, y + h // 2), width, height, TOWER_OPTIONS, session)

    assert session.tech_tree.level_for("laser", "damage") == 1
    assert session.resources.scrap < scrap_before


def test_click_branch_without_enough_scrap_does_not_upgrade(session):
    screen = TechTreeScreen()
    width, height = 900, 600
    screen._layout(width, height, TOWER_OPTIONS)
    session.resources.scrap = 0
    x, y, w, h = screen._branch_rects["damage"]

    screen.handle_click((x + w // 2, y + h // 2), width, height, TOWER_OPTIONS, session)

    assert session.tech_tree.level_for("laser", "damage") == 0


def test_click_back_button_returns_back(session):
    screen = TechTreeScreen()
    width, height = 900, 600
    screen._layout(width, height, TOWER_OPTIONS)
    x, y, w, h = screen._back_rect
    center = (x + w // 2, y + h // 2)

    action = screen.handle_click(center, width, height, TOWER_OPTIONS, session)

    assert action == "back"


def test_click_outside_everything_returns_none(session):
    screen = TechTreeScreen()
    assert screen.handle_click((0, 0), 900, 600, TOWER_OPTIONS, session) is None


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


def test_render_does_not_crash(session):
    screen = TechTreeScreen()
    pygame.init()
    surface = pygame.Surface((900, 600))
    font = pygame.font.SysFont("Arial", 18)
    small_font = pygame.font.SysFont("Arial", 14)
    title_font = pygame.font.SysFont("Arial", 40, bold=True)

    screen.render(surface, 900, 600, font, small_font, title_font, TOWER_OPTIONS, session)


def test_render_does_not_crash_when_branch_is_maxed(session):
    """Регрессия: когда ветка достигает максимума, upgrade_cost возвращает None -
    отрисовка не должна на этом падать."""
    session.resources.scrap = 10_000
    max_level = len(session.tower_factory.get_upgrade_costs("laser"))
    for _ in range(max_level):
        session.upgrade_tech_branch("laser", "damage")

    screen = TechTreeScreen()
    pygame.init()
    surface = pygame.Surface((900, 600))
    font = pygame.font.SysFont("Arial", 18)
    small_font = pygame.font.SysFont("Arial", 14)
    title_font = pygame.font.SysFont("Arial", 40, bold=True)

    screen.render(surface, 900, 600, font, small_font, title_font, TOWER_OPTIONS, session)
