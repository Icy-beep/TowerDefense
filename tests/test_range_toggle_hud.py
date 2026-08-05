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


def test_game_controller_exposes_show_power_radii_from_active_mode():
    """Регрессия: MapRenderer.render читает show_power_radii/show_tower_ranges прямо
    с controller (getattr(controller, ...)), а не через get_game_state() - GameController
    проксировал только toggle-методы, но не сами свойства, так что радиусы включались
    в HUD (рамка кнопки золотела - она читает через get_game_state()), но никогда не
    рисовались на карте, потому что render() всегда видел GameController.show_power_radii
    как отсутствующий атрибут (default False)."""
    session = GameSession()
    session.setup_game()
    game_controller = GameController(session)

    game_controller.toggle_power_radii()

    assert game_controller.show_power_radii is True


def test_game_controller_exposes_show_tower_ranges_from_active_mode():
    session = GameSession()
    session.setup_game()
    game_controller = GameController(session)

    game_controller.toggle_tower_ranges()

    assert game_controller.show_tower_ranges is True


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


def test_end_to_end_game_controller_toggle_actually_renders_ring(monkeypatch):
    """Полный путь как в игре: GameController.toggle_tower_ranges() -> MapRenderer.render(screen,
    ..., controller=game_controller, ...) должен реально нарисовать кольцо радиуса, а не
    только подсветить рамку кнопки в HUD (см. предыдущий тест на суть регрессии)."""
    session = GameSession()
    session.setup_game()
    session.map.modules.append(LaserTurret(Coordinate(session.base_position.x + 300,
                                                        session.base_position.y)))
    game_controller = GameController(session)
    game_controller.toggle_tower_ranges()

    blitted = []
    screen = pygame.Surface((WIDTH, HEIGHT))
    original_blit = screen.blit

    def spy_blit(source, dest, *a, **k):
        blitted.append(source)
        return original_blit(source, dest, *a, **k)

    monkeypatch.setattr(screen, "blit", spy_blit)
    camera = types.SimpleNamespace(
        world_to_screen=lambda x, y: (x, y), screen_to_world=lambda x, y: (x, y),
        x=0, y=0, zoom=1.0,
    )

    MapRenderer().render(screen, camera, session, game_controller, [], WIDTH, HEIGHT)

    assert any(getattr(s, "get_flags", lambda: 0)() & pygame.SRCALPHA for s in blitted), \
        "включённый через реальный GameController show_tower_ranges должен приводить к блиту кольца"


def test_range_ring_is_blitted_to_screen_via_alpha_overlay(monkeypatch):
    """Регрессия: pygame.draw.circle с альфа-цветом молча игнорирует альфу при
    рисовании прямо на screen (у него нет per-pixel alpha) - раньше кольцо радиуса
    рисовалось так напрямую и потому не показывалось на экране, хотя код "выполнялся
    без ошибок". Теперь кольцо копится на отдельной SRCALPHA-поверхности и
    блитится на screen - проверяем, что блит действительно происходит."""
    tower = LaserTurret(Coordinate(500, 500))
    camera = _camera()
    session = types.SimpleNamespace(map=types.SimpleNamespace(modules=[tower]))
    controller = types.SimpleNamespace(selected_module=None)

    blitted = []
    screen = pygame.Surface((100, 100))
    original_blit = screen.blit

    def spy_blit(source, dest, *a, **k):
        blitted.append(source)
        return original_blit(source, dest, *a, **k)

    monkeypatch.setattr(screen, "blit", spy_blit)

    MapRenderer()._draw_modules(screen, camera, session, controller, [],
                                 alt_held=False, show_tower_ranges=True, show_power_radii=False)

    assert any(getattr(s, "get_flags", lambda: 0)() & pygame.SRCALPHA for s in blitted), \
        "полупрозрачное кольцо должно попадать на экран через блит SRCALPHA-поверхности"


def test_range_overlay_not_blitted_when_nothing_to_show(monkeypatch):
    """Если ни одно кольцо не должно рисоваться, лишнего блита на весь экран быть не
    должно (см. any_ring_drawn в _draw_modules) - не тратим кадр впустую."""
    tower = LaserTurret(Coordinate(500, 500))
    camera = _camera()
    session = types.SimpleNamespace(map=types.SimpleNamespace(modules=[tower]))
    controller = types.SimpleNamespace(selected_module=None)

    blitted = []
    screen = pygame.Surface((100, 100))
    original_blit = screen.blit

    def spy_blit(source, dest, *a, **k):
        blitted.append(source)
        return original_blit(source, dest, *a, **k)

    monkeypatch.setattr(screen, "blit", spy_blit)

    MapRenderer()._draw_modules(screen, camera, session, controller, [],
                                 alt_held=False, show_tower_ranges=False, show_power_radii=False)

    assert not any(getattr(s, "get_flags", lambda: 0)() & pygame.SRCALPHA for s in blitted)


# ---------------------------------------------------------------------------
# Кнопка "?" (подсказка по управлению) - см. запрос пользователя: список
# подсказок раньше вылезал за пределы экрана, теперь это всплывающая панель.
# ---------------------------------------------------------------------------

def test_help_button_starts_closed():
    renderer = HudRenderer()
    assert renderer.show_help is False


def test_handle_help_click_on_button_opens_and_closes_popup():
    renderer = HudRenderer()
    rect = renderer._layout_help_button(WIDTH, HEIGHT)

    handled = renderer.handle_help_click(rect.center, WIDTH, HEIGHT)
    assert handled is True
    assert renderer.show_help is True

    handled = renderer.handle_help_click(rect.center, WIDTH, HEIGHT)
    assert handled is True
    assert renderer.show_help is False


def test_handle_help_click_outside_button_does_not_toggle():
    renderer = HudRenderer()

    handled = renderer.handle_help_click((5, 5), WIDTH, HEIGHT)

    assert handled is False
    assert renderer.show_help is False


def test_help_button_stays_within_screen_bounds():
    renderer = HudRenderer()
    rect = renderer._layout_help_button(WIDTH, HEIGHT)

    assert 0 <= rect.left and rect.right <= WIDTH
    assert 0 <= rect.top and rect.bottom <= HEIGHT


def test_help_popup_stays_within_screen_bounds_even_with_all_hint_lines():
    """Регрессия: раньше список подсказок был статичным текстом внизу справа и с
    добавлением новой строки съезжал за пределы окна. Всплывающая панель растёт
    вверх от кнопки, поэтому должна помещаться в экран по вертикали и горизонтали
    независимо от числа строк подсказок."""
    renderer = HudRenderer()
    button_rect = renderer._layout_help_button(WIDTH, HEIGHT)
    lines = renderer._help_lines()
    popup_h = len(lines) * renderer.HELP_POPUP_LINE_HEIGHT + renderer.HELP_POPUP_PADDING * 2
    popup_x = WIDTH - 16 - renderer.HELP_POPUP_WIDTH
    popup_y = button_rect.top - 8 - popup_h

    assert popup_x >= 0, "подсказка не должна вылезать за левый край"
    assert popup_x + renderer.HELP_POPUP_WIDTH <= WIDTH, "подсказка не должна вылезать за правый край"
    assert popup_y >= 0, "подсказка не должна вылезать за верхний край при таком количестве строк"


def test_draw_help_button_and_popup_do_not_crash():
    renderer = HudRenderer()
    renderer.show_help = True
    pygame.init()
    screen = pygame.Surface((WIDTH, HEIGHT))
    small_font = pygame.font.SysFont("Arial", 14)

    renderer._draw_help_button(screen, WIDTH, HEIGHT, small_font)
    renderer._draw_help_popup(screen, WIDTH, HEIGHT, small_font)


def test_controls_zone_only_draws_help_button_when_closed(monkeypatch):
    """Регрессия для самой жалобы пользователя: без открытой подсказки в правой зоне
    нижней панели должна рисоваться только одна строка (позиция камеры) и кнопка -
    никакого длинного статичного списка, который может вылезти за экран."""
    renderer = HudRenderer()
    pygame.init()
    screen = pygame.Surface((WIDTH, HEIGHT))
    small_font = pygame.font.SysFont("Arial", 14)
    camera = types.SimpleNamespace(x=0, y=0, zoom=1.0)

    blit_calls = []
    original_blit = screen.blit

    def spy_blit(source, dest, *a, **k):
        blit_calls.append(dest)
        return original_blit(source, dest, *a, **k)

    monkeypatch.setattr(screen, "blit", spy_blit)

    renderer._draw_controls_zone(screen, camera, small_font, 0, 500, WIDTH - 16, 100, WIDTH, HEIGHT)

    # Камера (1 блит) + кнопка "?" (значок "?", 1 блит) - без открытой панели
    # никаких дополнительных строк подсказок рисоваться не должно.
    assert len(blit_calls) == 2


# ---------------------------------------------------------------------------
# Радиус бесплатного питания от базы (Map.BASE_POWER_RADIUS) - раньше кнопка/хоткей
# G показывала радиусы только у пилонов/генераторов, но не у самой базы (см. запрос
# пользователя).
# ---------------------------------------------------------------------------

def _session_with_power_grid(base_power_radius=550.0):
    session = GameSession()
    session.setup_game()
    session.map.BASE_POWER_RADIUS = base_power_radius
    return session


def test_base_power_radius_not_drawn_when_toggle_is_off(monkeypatch):
    session = _session_with_power_grid()
    camera = _camera()
    screen = pygame.Surface((WIDTH, HEIGHT))
    blitted = []
    original_blit = screen.blit

    def spy_blit(source, dest, *a, **k):
        blitted.append(source)
        return original_blit(source, dest, *a, **k)

    monkeypatch.setattr(screen, "blit", spy_blit)

    MapRenderer()._draw_base(screen, camera, session, show_power_radii=False)

    assert not any(getattr(s, "get_flags", lambda: 0)() & pygame.SRCALPHA for s in blitted)


def test_base_power_radius_drawn_when_toggle_is_on(monkeypatch):
    session = _session_with_power_grid()
    camera = _camera()
    screen = pygame.Surface((WIDTH, HEIGHT))
    blitted = []
    original_blit = screen.blit

    def spy_blit(source, dest, *a, **k):
        blitted.append(source)
        return original_blit(source, dest, *a, **k)

    monkeypatch.setattr(screen, "blit", spy_blit)

    MapRenderer()._draw_base(screen, camera, session, show_power_radii=True)

    assert any(getattr(s, "get_flags", lambda: 0)() & pygame.SRCALPHA for s in blitted), \
        "радиус питания базы должен рисоваться через SRCALPHA-поверхность при включённом G"


def test_base_power_radius_uses_maps_actual_constant(monkeypatch):
    """Радиус должен читаться прямо с session.map.BASE_POWER_RADIUS, а не быть
    захардкожен в рендерере - иначе отрисовка могла бы разойтись с реальной
    механикой (см. Map._update_power_grid)."""
    session = _session_with_power_grid(base_power_radius=777.0)
    camera = _camera(zoom=1.0)
    screen = pygame.Surface((WIDTH, HEIGHT))
    circle_calls = []
    original_circle = pygame.draw.circle

    def spy_circle(surf, color, pos, radius, width=0):
        circle_calls.append(radius)
        return original_circle(surf, color, pos, radius, width)

    monkeypatch.setattr(pygame.draw, "circle", spy_circle)

    MapRenderer()._draw_base(screen, camera, session, show_power_radii=True)

    assert int(777.0 * camera.zoom) in circle_calls


def test_base_power_radius_skipped_when_power_grid_disabled(monkeypatch):
    """На картах/сессиях без включённой энергосети (power_grid_enabled=False) башни
    и так всегда запитаны - показывать радиус базы там нечего и вводило бы в
    заблуждение."""
    session = _session_with_power_grid()
    session.map.power_grid_enabled = False
    camera = _camera()
    screen = pygame.Surface((WIDTH, HEIGHT))
    blitted = []
    original_blit = screen.blit

    def spy_blit(source, dest, *a, **k):
        blitted.append(source)
        return original_blit(source, dest, *a, **k)

    monkeypatch.setattr(screen, "blit", spy_blit)

    MapRenderer()._draw_base(screen, camera, session, show_power_radii=True)

    assert not any(getattr(s, "get_flags", lambda: 0)() & pygame.SRCALPHA for s in blitted)


def test_end_to_end_toggle_power_radii_also_reveals_base_ring(monkeypatch):
    """Полный путь: GameController.toggle_power_radii() -> MapRenderer.render должен
    нарисовать и кольцо у базы, не только у пилонов/генераторов."""
    session = _session_with_power_grid()
    game_controller = GameController(session)
    game_controller.toggle_power_radii()

    blitted = []
    screen = pygame.Surface((WIDTH, HEIGHT))
    original_blit = screen.blit

    def spy_blit(source, dest, *a, **k):
        blitted.append(source)
        return original_blit(source, dest, *a, **k)

    monkeypatch.setattr(screen, "blit", spy_blit)
    camera = types.SimpleNamespace(
        world_to_screen=lambda x, y: (x, y), screen_to_world=lambda x, y: (x, y),
        x=0, y=0, zoom=1.0,
    )

    MapRenderer().render(screen, camera, session, game_controller, [], WIDTH, HEIGHT)

    assert any(getattr(s, "get_flags", lambda: 0)() & pygame.SRCALPHA for s in blitted)
