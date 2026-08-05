"""OrbitalModeController.pause_game() ('P') и upgrade_selected() ('U')."""
import pytest
from src.core.game_session import GameSession
from src.core.orbital_mode_controller import OrbitalModeController
from src.core.coordinate import Coordinate
from src.enums import GameState


@pytest.fixture
def controller():
    session = GameSession()
    session.setup_game()
    return OrbitalModeController(session)


def test_pause_game_switches_playing_to_paused(controller):
    controller.session.state = GameState.PLAYING
    controller.pause_game()
    assert controller.session.state == GameState.PAUSED


def test_pause_game_switches_paused_back_to_playing(controller):
    controller.session.state = GameState.PAUSED
    controller.pause_game()
    assert controller.session.state == GameState.PLAYING


def test_pause_game_is_noop_outside_playing_or_paused(controller):
    for state in (GameState.MENU, GameState.GAME_OVER, GameState.VICTORY):
        controller.session.state = state
        controller.pause_game()
        assert controller.session.state == state


def test_pause_game_toggle_is_idempotent_over_two_calls(controller):
    controller.session.state = GameState.PLAYING
    controller.pause_game()
    controller.pause_game()
    assert controller.session.state == GameState.PLAYING


def _place_and_select(controller, tower_type="laser", pos=Coordinate(2300, 2000)):
    controller.select_tower(tower_type)
    controller.place_tower(pos)
    controller.selected_module = controller.session.map.modules[-1]
    return controller.selected_module


def test_upgrade_selected_spends_credits_and_upgrades_module(controller):
    module = _place_and_select(controller)
    credits_before = controller.session.resources.credits
    cost = module.get_upgrade_cost()

    result = controller.upgrade_selected()

    assert result is True
    assert module.level == 2
    assert controller.session.resources.credits == credits_before - cost


def test_upgrade_selected_fails_without_enough_credits(controller):
    module = _place_and_select(controller)
    controller.session.resources.credits = 0

    result = controller.upgrade_selected()

    assert result is False
    assert module.level == 1


def test_upgrade_selected_fails_at_max_level(controller):
    module = _place_and_select(controller)
    controller.session.resources.credits = 10_000
    while module.can_upgrade():
        controller.upgrade_selected()

    result = controller.upgrade_selected()

    assert result is False
    assert module.level == module.max_level


def test_upgrade_selected_fails_when_nothing_selected(controller):
    controller.selected_module = None
    assert controller.upgrade_selected() is False
