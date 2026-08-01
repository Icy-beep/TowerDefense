"""Выбор врага кликом: приоритет клика и очистка выбора при исчезновении врага."""
import pytest
from src.core.game_session import GameSession
from src.core.orbital_mode_controller import OrbitalModeController
from src.entities.enemies import DroneWalker
from src.core.coordinate import Coordinate


@pytest.fixture
def controller():
    session = GameSession()
    session.setup_game()
    return OrbitalModeController(session)


def _spawn_enemy(controller, pos: Coordinate) -> DroneWalker:
    enemy = controller.session.enemy_factory.create("drone_walker", pos)
    controller.session.map.enemies.append(enemy)
    return enemy


def test_click_near_enemy_selects_it(controller):
    enemy = _spawn_enemy(controller, Coordinate(1000, 1000))

    result = controller.handle_click(Coordinate(1005, 1000))

    assert result == "selected_enemy"
    assert controller.selected_enemy is enemy
    assert controller.selected_module is None


def test_click_far_from_enemy_does_not_select_it(controller):
    _spawn_enemy(controller, Coordinate(1000, 1000))

    result = controller.handle_click(Coordinate(1000, 1500))

    assert result == "none"
    assert controller.selected_enemy is None


def test_click_on_module_takes_priority_over_nearby_enemy(controller):
    controller.select_tower("laser")
    controller.place_tower(Coordinate(2300, 2000))
    controller.deselect()
    module_pos = controller.session.map.modules[0].position
    enemy = _spawn_enemy(controller, Coordinate(module_pos.x + 2, module_pos.y))

    result = controller.handle_click(module_pos)

    assert result == "selected"
    assert controller.selected_module is not None
    assert controller.selected_enemy is None


def test_selecting_tower_type_takes_priority_over_enemy_click():
    """Пока игрок строит башню, клик по врагу не должен переключать
    выбор на него — сначала обрабатывается попытка постройки."""
    session = GameSession()
    session.setup_game()
    controller = OrbitalModeController(session)
    enemy = _spawn_enemy(controller, Coordinate(2300, 2000))
    controller.select_tower("laser")

    controller.handle_click(Coordinate(2300, 2000))

    assert controller.selected_enemy is None


def test_selected_enemy_cleared_when_enemy_dies(controller):
    enemy = _spawn_enemy(controller, Coordinate(1000, 1000))
    controller.handle_click(Coordinate(1000, 1000))
    assert controller.selected_enemy is enemy

    controller.session.map.enemies.remove(enemy)
    controller.update(0.016)

    assert controller.selected_enemy is None


def test_deselect_clears_selected_enemy(controller):
    _spawn_enemy(controller, Coordinate(1000, 1000))
    controller.handle_click(Coordinate(1000, 1000))
    assert controller.selected_enemy is not None

    controller.deselect()

    assert controller.selected_enemy is None


def test_enemy_factory_stamps_type_name(controller):
    enemy = controller.session.enemy_factory.create("giant_roach", Coordinate(0, 0))
    assert enemy.type_name == "giant_roach"
