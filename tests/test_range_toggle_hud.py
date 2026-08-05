"""Постоянный показ радиусов через HUD-кнопки/хоткеи G (энергосеть) и T (атака
башен) - отдельно от временного ALT (см. tests/test_tower_range_visibility.py),
который по-прежнему показывает радиусы всех построек разом."""
import types

import pygame

from src.core.coordinate import Coordinate
from src.core.game_controller import GameController
from src.core.game_session import GameSession
from src.core.orbital_mode_controller import OrbitalModeController
from src.entities.power_pylon import PowerPylon
from src.entities.turrets import LaserTurret
from src.ui.hud_renderer import HudRenderer
from src.ui.map_renderer import MapRenderer

WIDTH, HEIGHT = 900, 600


def _camera(zoom=1.0):
    return types.SimpleNamespace(world_to_screen=lambda x, y: (x, y), zoom=zoom)


def _spy_on_circle(monkeypatch):
    calls = []

    def spy_circle(screen, color, pos, radius, width=0):
        calls.append(radius)

    monkeypatch.setattr(pygame.draw, "circle", spy_circle)
    return calls


# ---------------------------------------------------------------------------
# OrbitalModeController: состояние переключателей
# ---------------------------------------------------------------------------

def _controller():
    session = GameSession()
    session.setup_game()
    return OrbitalModeController(session)


def test_toggle_power_radii_flips_state_and_returns_new_value():
    controller = _controller()

    assert controller.toggle_power_radii() is True
    assert controller.show_power_radii is True
    assert controller.toggle_power_radii() is False
    assert controller.show_power_radii is False


def test_toggle_tower_ranges_flips_state_and_returns_new_value():
    controller = _controller()

    assert controller.toggle_tower_ranges() is True
    assert controller.show_tower_ranges is True
    assert controller.toggle_tower_ranges() is False
    assert controller.show_tower_ranges is False


def test_toggles_are_independent_of_each_other():
    controller = _controller()

    controller.toggle_power_radii()

    assert controller.show_power_radii is True
    assert controller.show_tower_ranges is False


def test_get_game_state_reports_toggle_state():
    controller = _controller()
    controller.toggle_tower_ranges()

    state = controller.get_game_state()

    assert state["show_tower_ranges"] is True
    assert state["show_power_radii"] is False


def test_g_key_toggles_power_radii():
    controller = _controller()

    controller.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_g))

    assert controller.show_power_radii is True


def test_t_key_toggles_tower_ranges():
    controller = _controller()

    controller.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t))

    assert controller.show_tower_ranges is True


# ---------------------------------------------------------------------------
# GameController: проксирование в активный режим (нужно HUD-кнопке)
# ---------------------------------------------------------------------------

def test_game_controller_proxies_toggle_power_radii():
    session = GameSession()
    session.setup_game()
    game_controller = GameController(session)

    result = game_controller.toggle_power_radii()

    assert result is True
    assert game_controller.active_mode.show_power_radii is True


def test_game_controller_proxies_toggle_tower_ranges():
    session = GameSession()
    session.setup_game()
    game_controller = GameController(session)

    result = game_controller.toggle_tower_ranges()

    assert result is True
    assert game_controller.active_mode.show_tower_ranges is True


def test_game_controller_toggle_is_safe_without_support():
    """Если у активного режима нет метода переключения (например, урезанный
    тестовый двойник), GameController не должен падать - просто вернуть False."""
    fake_controller = GameController.__new__(GameController)
    fake_controller.active_mode = types.SimpleNamespace()

    assert fake_controller.toggle_power_radii() is False
    assert fake_controller.toggle_tower_ranges() is False


# ---------------------------------------------------------------------------
# HudRenderer: раскладка и попадание клика по кнопкам
# ---------------------------------------------------------------------------

def test_toggle_buttons_do_not_overlap_and_are_centered():
    renderer = HudRenderer()
    slots = renderer._layout_toggle_buttons(WIDTH)

    assert len(slots) == 2
    (rect_a, _, _), (rect_b, _, _) = slots
    assert rect_a.right <= rect_b.left, "кнопки-переключатели не должны перекрываться"

    center = (rect_a.left + rect_b.right) / 2
    assert abs(center - WIDTH / 2) < 2, "пара кнопок должна быть отцентрирована по ширине"


def test_handle_toggle_click_returns_key_for_each_button():
    renderer = HudRenderer()
    slots = renderer._layout_toggle_buttons(WIDTH)

    for rect, key, _hotkey in slots:
        assert renderer.handle_toggle_click(rect.center, WIDTH) == key


def test_handle_toggle_click_returns_none_outside_buttons():
    renderer = HudRenderer()

    assert renderer.handle_toggle_click((5, 5), WIDTH) is None


def test_draw_toggle_buttons_does_not_crash_on_or_off():
    renderer = HudRenderer()
    pygame.init()
    screen = pygame.Surface((WIDTH, HEIGHT))
    small_font = pygame.font.SysFont("Arial", 14)

    renderer._draw_toggle_buttons(screen, {"show_power_radii": True, "show_tower_ranges": False},
                                   WIDTH, small_font)
    renderer._draw_toggle_buttons(screen, {"show_power_radii": False, "show_tower_ranges": False},
                                   WIDTH, small_font)


# ---------------------------------------------------------------------------
# MapRenderer: постоянный показ радиуса раздельно по категории постройки
# ---------------------------------------------------------------------------

def test_show_tower_ranges_reveals_combat_tower_radius_but_not_power_infra(monkeypatch):
    calls = _spy_on_circle(monkeypatch)
    tower = LaserTurret(Coordinate(500, 500))
    pylon = PowerPylon(Coordinate(900, 900))
    camera = _camera()
    session = types.SimpleNamespace(map=types.SimpleNamespace(modules=[tower, pylon]))
    controller = types.SimpleNamespace(selected_module=None)
    tower_radius = int(tower.range_radius * camera.zoom)
    pylon_radius = int(pylon.range_radius * camera.zoom)

    MapRenderer()._draw_modules(pygame.Surface((10, 10)), camera, session, controller, [],
                                 alt_held=False, show_tower_ranges=True, show_power_radii=False)

    assert tower_radius in calls
    assert pylon_radius not in calls


def test_show_power_radii_reveals_power_infra_radius_but_not_combat_tower(monkeypatch):
    calls = _spy_on_circle(monkeypatch)
    tower = LaserTurret(Coordinate(500, 500))
    pylon = PowerPylon(Coordinate(900, 900))
    camera = _camera()
    session = types.SimpleNamespace(map=types.SimpleNamespace(modules=[tower, pylon]))
    controller = types.SimpleNamespace(selected_module=None)
    tower_radius = int(tower.range_radius * camera.zoom)
    pylon_radius = int(pylon.range_radius * camera.zoom)

    MapRenderer()._draw_modules(pygame.Surface((10, 10)), camera, session, controller, [],
                                 alt_held=False, show_tower_ranges=False, show_power_radii=True)

    assert pylon_radius in calls
    assert tower_radius not in calls


def test_alt_held_still_shows_both_categories_regardless_of_toggles():
    """Регрессия: ALT должен по-прежнему временно показывать радиусы всех построек
    разом, независимо от состояния новых постоянных переключателей (см. запрос
    пользователя - 'alt можно оставить')."""
    tower = LaserTurret(Coordinate(500, 500))
    pylon = PowerPylon(Coordinate(900, 900))
    camera = _camera()
    session = types.SimpleNamespace(map=types.SimpleNamespace(modules=[tower, pylon]))
    controller = types.SimpleNamespace(selected_module=None)

    # Не должно падать и должно применяться единообразно ко всем модулям.
    MapRenderer()._draw_modules(pygame.Surface((10, 10)), camera, session, controller, [],
                                 alt_held=True, show_tower_ranges=False, show_power_radii=False)


def test_render_passes_controller_toggle_state_into_draw_modules(monkeypatch):
    """Смоук-тест полного render(): флаги show_power_radii/show_tower_ranges
    контроллера должны доходить до _draw_modules без падений."""
    session = GameSession()
    session.setup_game()
    session.map.modules.append(LaserTurret(Coordinate(500, 500)))

    controller = types.SimpleNamespace(
        selected_module=None, selected_tower_type=None, selected_enemy=None,
        show_power_radii=True, show_tower_ranges=True,
        _is_valid_position=lambda pos: True,
    )
    camera = types.SimpleNamespace(
        world_to_screen=lambda x, y: (x, y), screen_to_world=lambda x, y: (x, y),
        x=0, y=0, zoom=1.0,
    )
    screen = pygame.Surface((WIDTH, HEIGHT))

    MapRenderer().render(screen, camera, session, controller, [], WIDTH, HEIGHT)
