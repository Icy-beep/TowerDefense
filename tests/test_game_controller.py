"""GameController: делегирование в активный режим (OrbitalModeController по
умолчанию) - в частности select_tower, нужный HUD-панели построек, чтобы клик по
иконке работал так же, как хоткей 1-5 (см. src/ui/hud_renderer.py)."""
from src.core.game_session import GameSession
from src.core.game_controller import GameController


def _controller():
    session = GameSession()
    session.setup_game()
    return GameController(session)


def test_select_tower_delegates_to_active_mode():
    controller = _controller()

    assert controller.select_tower("laser") is True
    assert controller.selected_tower_type == "laser"


def test_select_tower_returns_false_for_unknown_type():
    controller = _controller()

    assert controller.select_tower("no_such_tower") is False


def test_select_tower_returns_false_if_active_mode_does_not_support_it():
    """Регрессия: раньше GameController не делегировал select_tower вовсе, и вызов
    падал бы с AttributeError, если бы активный режим не поддерживал его."""
    controller = _controller()
    controller.active_mode = object()

    assert controller.select_tower("laser") is False
