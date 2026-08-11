"""OrbitalModeController.pause_game() ('P'), GameSession.upgrade_tech_branch() (за
scrap, общий на весь тип башни - см. TechTreeScreen) и install_ai_module() (из
инвентаря дропа, см. GameSession.ai_module_stock)."""
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


def test_upgrade_tech_branch_spends_scrap_and_boosts_the_tower(controller):
    module = _place_and_select(controller)
    controller.session.resources.scrap = 1000
    scrap_before = controller.session.resources.scrap
    cost = controller.session.tower_factory.get_upgrade_costs("laser")[0]

    result = controller.session.upgrade_tech_branch("laser", "damage")

    assert result is True
    assert module.damage == pytest.approx(module.base_damage * 1.4)
    assert controller.session.resources.scrap == scrap_before - cost


def test_upgrade_tech_branch_fails_without_enough_scrap(controller):
    module = _place_and_select(controller)
    controller.session.resources.scrap = 0

    result = controller.session.upgrade_tech_branch("laser", "damage")

    assert result is False
    assert module.damage == module.base_damage


def test_upgrade_tech_branch_fails_at_max_level(controller):
    _place_and_select(controller)
    controller.session.resources.scrap = 10_000
    max_level = len(controller.session.tower_factory.get_upgrade_costs("laser"))
    for _ in range(max_level):
        controller.session.upgrade_tech_branch("laser", "damage")

    result = controller.session.upgrade_tech_branch("laser", "damage")

    assert result is False


def test_upgrade_tech_branch_applies_to_every_tower_of_that_type(controller):
    """Апгрейд общий на тип - должен затронуть все уже стоящие башни этого типа,
    а не только ту, что была выбрана при покупке."""
    controller.session.resources.scrap = 10_000
    controller.select_tower("laser")
    controller.place_tower(Coordinate(2300, 2000))
    controller.select_tower("laser")
    controller.place_tower(Coordinate(2400, 2000))
    laser_1, laser_2 = controller.session.map.modules[-2:]

    controller.session.upgrade_tech_branch("laser", "attack_speed")

    assert laser_1.attack_speed == pytest.approx(laser_1.base_attack_speed * 1.25)
    assert laser_2.attack_speed == pytest.approx(laser_2.base_attack_speed * 1.25)


def test_newly_placed_tower_inherits_already_purchased_upgrades(controller):
    controller.session.resources.scrap = 10_000
    controller.session.upgrade_tech_branch("laser", "radius")

    module = _place_and_select(controller)

    assert module.range_radius == pytest.approx(module.base_range * 1.2)


def test_install_ai_module_consumes_one_from_stock_and_sets_module(controller):
    module = _place_and_select(controller)
    controller.session.ai_module_stock["finish_wounded"] = 2

    result = controller.install_ai_module("finish_wounded")

    assert result is True
    assert module.ai_module == "finish_wounded"
    assert controller.session.ai_module_stock["finish_wounded"] == 1


def test_install_ai_module_fails_without_any_in_stock(controller):
    module = _place_and_select(controller)

    result = controller.install_ai_module("finish_wounded")

    assert result is False
    assert module.ai_module is None


def test_install_ai_module_fails_when_already_installed(controller):
    module = _place_and_select(controller)
    controller.session.ai_module_stock["finish_wounded"] = 1
    controller.session.ai_module_stock["hunt_leaders"] = 1
    controller.install_ai_module("finish_wounded")

    result = controller.install_ai_module("hunt_leaders")

    assert result is False
    assert module.ai_module == "finish_wounded", \
        "повторная установка не должна заменять уже стоящий модуль"


def test_install_ai_module_fails_for_unknown_module_key(controller):
    module = _place_and_select(controller)
    controller.session.ai_module_stock["does_not_exist"] = 5

    result = controller.install_ai_module("does_not_exist")

    assert result is False
    assert module.ai_module is None


def test_install_ai_module_fails_when_nothing_selected(controller):
    controller.selected_module = None
    controller.session.ai_module_stock["finish_wounded"] = 1
    assert controller.install_ai_module("finish_wounded") is False
