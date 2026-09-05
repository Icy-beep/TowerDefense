"""Установка ИИ-модуля через HUD-панель выбора: кнопки под статами выбранной
башни, доступные только когда есть модуль в запасе (см. GameSession.ai_module_stock,
запрос пользователя - интерфейс должен быть частью панели выбора башни)."""
import types

import pygame
import pytest

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.core.settings import Settings
from src.entities.defense_module import DefenseModule
from src.entities.power_pylon import PowerPylon
from src.entities.turrets import LaserTurret
from src.localization.loc import loc
from src.ui.game_window import GameView
from src.ui.hud_renderer import HudRenderer

WIDTH, HEIGHT = 900, 600
TOWER_OPTIONS = [
    {"type": "laser", "name": "Laser (50)"},
    {"type": "bullet", "name": "Bullet (100)"},
    {"type": "mortar", "name": "Mortar (200)"},
    {"type": "generator", "name": "Generator (220)"},
    {"type": "pylon", "name": "Pylon (60)"},
]


def _selection_zone_bounds(hud, tower_options=TOWER_OPTIONS, width=WIDTH, height=HEIGHT):
    slots = hud._layout_build_panel(tower_options, width, height)
    build_left = slots[0][0].left
    bar_y = height - hud.BOTTOM_BAR_HEIGHT
    return 16, bar_y + 10, build_left - 26, hud.BOTTOM_BAR_HEIGHT - 20


def test_no_buttons_when_nothing_selected():
    hud = HudRenderer()
    controller = types.SimpleNamespace(selected_module=None)

    assert hud._layout_ai_module_buttons(controller, *_selection_zone_bounds(hud)) == []


def test_no_buttons_for_infrastructure():
    hud = HudRenderer()
    controller = types.SimpleNamespace(selected_module=PowerPylon(Coordinate(0, 0)))

    assert hud._layout_ai_module_buttons(controller, *_selection_zone_bounds(hud)) == []


def test_build_selection_hides_ai_buttons_and_disables_their_hitboxes():
    from src.core.game_controller import GameController

    session = GameSession()
    session.setup_game()
    controller = GameController(session)
    tower = LaserTurret(Coordinate(0, 0))
    session.map.modules.append(tower)
    controller.active_mode.selected_module = tower
    hud = HudRenderer()
    bounds = _selection_zone_bounds(hud)
    buttons = hud._layout_ai_module_buttons(controller, *bounds)
    assert len(buttons) == 3

    controller.select_tower("mortar")

    assert hud._layout_ai_module_buttons(controller, *bounds) == []
    for rect, _key in buttons:
        assert hud.handle_ai_module_click(
            rect.center, controller, TOWER_OPTIONS, WIDTH, HEIGHT
        ) is None


def test_no_buttons_when_module_already_installed():
    hud = HudRenderer()
    tower = LaserTurret(Coordinate(0, 0))
    tower.ai_module = "hunt_leaders"
    controller = types.SimpleNamespace(selected_module=tower)

    assert hud._layout_ai_module_buttons(controller, *_selection_zone_bounds(hud)) == []


def test_three_buttons_for_a_combat_tower_without_a_module():
    hud = HudRenderer()
    controller = types.SimpleNamespace(selected_module=LaserTurret(Coordinate(0, 0)))

    buttons = hud._layout_ai_module_buttons(controller, *_selection_zone_bounds(hud))

    assert [key for _rect, key in buttons] == list(DefenseModule.AI_MODULE_KEYS)


def test_buttons_do_not_overlap():
    hud = HudRenderer()
    controller = types.SimpleNamespace(selected_module=LaserTurret(Coordinate(0, 0)))

    buttons = hud._layout_ai_module_buttons(controller, *_selection_zone_bounds(hud))

    for (rect_a, _), (rect_b, _) in zip(buttons, buttons[1:]):
        assert rect_a.right <= rect_b.left


def test_handle_click_returns_key_for_a_button_and_none_outside():
    hud = HudRenderer()
    controller = types.SimpleNamespace(selected_module=LaserTurret(Coordinate(0, 0)))
    x, y, right, h = _selection_zone_bounds(hud)
    buttons = hud._layout_ai_module_buttons(controller, x, y, right, h)
    rect, key = buttons[0]

    hit = hud.handle_ai_module_click(rect.center, controller, TOWER_OPTIONS, WIDTH, HEIGHT)
    miss = hud.handle_ai_module_click((0, 0), controller, TOWER_OPTIONS, WIDTH, HEIGHT)

    assert hit == key
    assert miss is None


def test_render_ai_module_buttons_does_not_crash_with_and_without_stock():
    hud = HudRenderer()
    controller = types.SimpleNamespace(selected_module=LaserTurret(Coordinate(0, 0)))
    x, y, right, h = _selection_zone_bounds(hud)
    small_font = pygame.font.SysFont("Arial", 14)
    screen = pygame.Surface((WIDTH, HEIGHT))

    hud._draw_ai_module_buttons(screen, {"ai_module_stock": {}}, controller, small_font, x, y, right, h)
    hud._draw_ai_module_buttons(screen, {"ai_module_stock": {"hunt_leaders": 2}}, controller,
                                 small_font, x, y, right, h)


def test_selection_info_shows_installed_module_name():
    hud = HudRenderer()
    tower = LaserTurret(Coordinate(0, 0))
    tower.type_name = "laser"
    tower.ai_module = "hunt_leaders"
    controller = types.SimpleNamespace(selected_module=tower, selected_enemy=None)
    state = {"selected_tower": None, "credits": 0}

    lines = hud._build_selection_info(state, controller, TOWER_OPTIONS)

    expected = loc.get("hud.ai_module_installed", name=loc.get("hud.ai_module_full_hunt_leaders"))
    assert expected in lines


def test_selection_info_prompts_for_module_when_none_installed():
    hud = HudRenderer()
    tower = LaserTurret(Coordinate(0, 0))
    tower.type_name = "laser"
    controller = types.SimpleNamespace(selected_module=tower, selected_enemy=None)
    state = {"selected_tower": None, "credits": 0}

    lines = hud._build_selection_info(state, controller, TOWER_OPTIONS)

    assert any("модул" in line.lower() for line in lines)


@pytest.fixture
def view(monkeypatch):
    game_view = GameView(GameSession(), settings=Settings())
    monkeypatch.setattr(game_view.settings, "save", lambda *a, **kw: None)
    game_view._start_game()
    return game_view


def _click_event(pos):
    return types.SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


def test_game_view_click_installs_module_and_does_not_leak_to_map(view):
    """Идёт через GameController-фасад так же, как в реальной игре (не напрямую
    через OrbitalModeController) - раньше install_ai_module не был проброшен через
    фасад, и клик падал бы с AttributeError (см. GameController.install_ai_module)."""
    view.controller.select_tower("laser")
    view.controller.active_mode.place_tower(view.session.base_position)
    tower = view.session.map.modules[-1]
    view.controller.active_mode.selected_module = tower
    view.session.ai_module_stock["hunt_leaders"] = 1
    towers_before = len(view.session.map.modules)

    x, y, right, h = _selection_zone_bounds(view.hud_renderer, view.tower_options, view.width, view.height)
    rect, _key = view.hud_renderer._layout_ai_module_buttons(view.controller, x, y, right, h)[2]

    consumed = view._handle_ai_module_click(_click_event(rect.center))

    assert consumed is True
    assert tower.ai_module == "hunt_leaders"
    assert view.session.ai_module_stock["hunt_leaders"] == 0
    assert len(view.session.map.modules) == towers_before, \
        "клик по кнопке не должен долетать до карты и ставить новую башню"
