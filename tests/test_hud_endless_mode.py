"""HUD в бесконечном режиме не должен показывать прогресс/остаток времени -
там нет ограничения по времени (см. GameSession.setup_game(endless=True))."""
import pygame

from src.localization.loc import loc
from src.ui.hud_renderer import HudRenderer


def _state(endless):
    return {
        'credits': 1000,
        'base_health': 100,
        'max_base_health': 100,
        'elapsed_time': 42.0,
        'survive_duration_target': 180.0,
        'endless': endless,
    }


def _requested_keys(endless):
    renderer = HudRenderer()
    pygame.init()
    font = pygame.font.SysFont("Arial", 18)
    screen = pygame.Surface((900, 600))

    requested = []
    original_get = loc.get

    def spy_get(key, **kwargs):
        requested.append(key)
        return original_get(key, **kwargs)

    loc.get = spy_get
    try:
        renderer._draw_top_bar(screen, _state(endless), font, width=900)
    finally:
        loc.get = original_get
    return requested


def test_endless_mode_does_not_render_survive_timer_lines():
    keys = _requested_keys(endless=True)

    assert "hud.money" in keys
    assert "hud.base_health" in keys
    assert "hud.survive_progress" not in keys
    assert "hud.survive_remaining" not in keys


def test_normal_mode_still_renders_survive_timer_lines():
    keys = _requested_keys(endless=False)

    assert "hud.survive_progress" in keys
    assert "hud.survive_remaining" in keys


def test_status_panel_does_not_crash_without_endless_key():
    """Регрессия: старый код вызова без ключа 'endless' в state (если где-то
    остался) должен вести себя как обычный режим, а не падать."""
    renderer = HudRenderer()
    pygame.init()
    font = pygame.font.SysFont("Arial", 18)
    screen = pygame.Surface((900, 600))
    state = _state(endless=False)
    del state['endless']

    renderer._draw_top_bar(screen, state, font, width=900)
