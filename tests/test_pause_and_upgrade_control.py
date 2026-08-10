"""OrbitalModeController.pause_game() ('P') и GameSession.upgrade_tech_branch()
(см. TechTreeScreen - апгрейд теперь общий на весь тип башни, не на одну
конкретную постройку, как раньше был upgrade_selected() по 'U')."""
import pytest

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.core.orbital_mode_controller import OrbitalModeController
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


def test_upgrade_tech_branch_spends_credits_and_boosts_the_tower(controller):
    module = _place_and_select(controller)
    credits_before = controller.session.resources.credits
    cost = controller.session.tower_factory.get_upgrade_costs("laser")[0]

    result = controller.session.upgrade_tech_branch("laser", "damage")

    assert result is True
    assert module.damage == pytest.approx(module.base_damage * 1.4)
    assert controller.session.resources.credits == credits_before - cost


def test_upgrade_tech_branch_fails_without_enough_credits(controller):
    module = _place_and_select(controller)
    controller.session.resources.credits = 0

    result = controller.session.upgrade_tech_branch("laser", "damage")

    assert result is False
    assert module.damage == module.base_damage


def test_upgrade_tech_branch_fails_at_max_level(controller):
    _place_and_select(controller)
    controller.session.resources.credits = 10_000
    max_level = len(controller.session.tower_factory.get_upgrade_costs("laser"))
    for _ in range(max_level):
        controller.session.upgrade_tech_branch("laser", "damage")

    result = controller.session.upgrade_tech_branch("laser", "damage")

    assert result is False


def test_upgrade_tech_branch_applies_to_every_tower_of_that_type(controller):
    """Апгрейд общий на тип - должен затронуть все уже стоящие башни этого типа,
    а не только ту, что была выбрана при покупке."""
    controller.session.resources.credits = 10_000
    controller.select_tower("laser")
    controller.place_tower(Coordinate(2300, 2000))
    controller.select_tower("laser")
    controller.place_tower(Coordinate(2400, 2000))
    laser_1, laser_2 = controller.session.map.modules[-2:]

    controller.session.upgrade_tech_branch("laser", "attack_speed")

    assert laser_1.attack_speed == pytest.approx(laser_1.base_attack_speed * 1.25)
    assert laser_2.attack_speed == pytest.approx(laser_2.base_attack_speed * 1.25)


def test_newly_placed_tower_inherits_already_purchased_upgrades(controller):
    controller.session.resources.credits = 10_000
    controller.session.upgrade_tech_branch("laser", "radius")

    module = _place_and_select(controller)

    assert module.range_radius == pytest.approx(module.base_range * 1.2)


def test_install_ai_module_spends_scrap_and_sets_module(controller):
    module = _place_and_select(controller)
    controller.session.resources.scrap = 1000
    cost = module.AI_MODULE_COSTS["finish_wounded"]

    result = controller.install_ai_module("finish_wounded")

    assert result is True
    assert module.ai_module == "finish_wounded"
    assert controller.session.resources.scrap == 1000 - cost


def test_install_ai_module_fails_without_enough_scrap(controller):
    module = _place_and_select(controller)
    controller.session.resources.scrap = 0

    result = controller.install_ai_module("finish_wounded")

    assert result is False
    assert module.ai_module is None


def test_install_ai_module_fails_when_already_installed(controller):
    module = _place_and_select(controller)
    controller.session.resources.scrap = 1000
    controller.install_ai_module("finish_wounded")

    result = controller.install_ai_module("hunt_leaders")

    assert result is False
    assert module.ai_module == "finish_wounded", \
        "повторная установка не должна заменять уже стоящий модуль"


def test_install_ai_module_fails_for_unknown_module_key(controller):
    module = _place_and_select(controller)
    controller.session.resources.scrap = 1000

    result = controller.install_ai_module("does_not_exist")

    assert result is False
    assert module.ai_module is None


def test_install_ai_module_fails_when_nothing_selected(controller):
    controller.selected_module = None
    controller.session.resources.scrap = 1000
    assert controller.install_ai_module("finish_wounded") is False
