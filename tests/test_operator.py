import pygame
import pytest

from src.core.coordinate import Coordinate
from src.core.game_controller import GameController
from src.core.game_session import GameSession
from src.core.settings import Settings
from src.entities.enemies import DroneWalker
from src.entities.operator import Operator
from src.entities.turrets import LaserTurret
from src.entities.power_pylon import PowerPylon
from src.enums import GameState
from src.save_load.serializer import apply_dict_to_session, session_to_dict
from src.ui.game_window import GameView


@pytest.fixture
def session():
    session = GameSession()
    session.setup_game(endless=True)
    session.threat_strategies = {}
    session.map.fauna_nests = []
    return session


def test_switch_keeps_same_soldier_health_and_position(session):
    controller = GameController(session)
    assert controller.enter_operator("assault")
    soldier = session.operator
    soldier.health = 75
    position = Coordinate(soldier.position.x, soldier.position.y)
    controller.return_to_orbit()
    assert not soldier.manual
    assert controller.enter_operator()
    assert session.operator is soldier
    assert soldier.health == 75
    assert soldier.position == position
    assert controller.operator_mode


def test_manual_boost_expires_in_orbit_without_automatic_reactivation(session):
    controller = GameController(session)
    controller.enter_operator("assault")
    soldier = session.operator
    controller.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    assert soldier.boost_time == 5
    controller.return_to_orbit()
    # Постоянная цель рядом: наличие противника не должно запускать новый эффект.
    enemy = DroneWalker(Coordinate(soldier.position.x + 150, soldier.position.y))
    enemy.speed = 0
    enemy.health = enemy.max_health = 100000
    session.map.enemies.append(enemy)
    for _ in range(51):
        session.update(0.1)
    assert soldier.boost_time == 0
    assert soldier.ability_cooldown == pytest.approx(9.9)
    for _ in range(150):
        session.update(0.1)
    assert soldier.boost_time == 0
    assert soldier.ability_cooldown == 0
    assert controller.enter_operator()
    controller.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    assert soldier.boost_time == 5


def test_engineer_does_not_repeat_repair_automatically_in_orbit(session):
    controller = GameController(session)
    controller.enter_operator("engineer")
    soldier = session.operator
    soldier.health = 30
    soldier.use_ability(session.map)
    assert soldier.health == 50
    controller.return_to_orbit()
    for _ in range(100):
        session.update(0.1)
    assert soldier.ability_cooldown == 0
    assert soldier.health == 50


def test_guard_ignores_pylons_and_retreats_towards_base(session):
    assert session.deploy_operator("assault")
    soldier = session.operator
    soldier.position = Coordinate(4200, 3000)
    front = LaserTurret(Coordinate(4200, 3100))
    rear = LaserTurret(Coordinate(3500, 3000))
    farther = LaserTurret(Coordinate(4400, 3100))
    session.map.modules = [front, rear, farther, PowerPylon(Coordinate(4200, 3000))]
    soldier.leave_manual(session.map)
    assert soldier.guard is front
    front.health = 0
    soldier.update(0.05, session.map)
    assert soldier.guard is rear
    rear.health = 0
    soldier.update(0.05, session.map)
    assert soldier.guard is None
    assert soldier.retreat_limit == 500


def test_autonomous_operator_walks_around_obstacles_to_guard(session):
    soldier = Operator("assault", Coordinate(3500, 3000))
    guard = LaserTurret(Coordinate(4100, 3000))
    obstacle = PowerPylon(Coordinate(3800, 3000))
    session.map.modules = [guard, obstacle]
    soldier.leave_manual(session.map)
    for _ in range(400):
        soldier.update(0.05, session.map)
    assert soldier.position.distance_to(guard.position) <= 125
    assert soldier.can_stand(soldier.position, session.map, soldier.blocked_cells(session.map))


def test_operator_without_towers_returns_to_base(session):
    soldier = Operator("engineer", Coordinate(3800, 3000))
    for _ in range(300):
        soldier.update(0.05, session.map)
    assert soldier.position.distance_to(session.base_position) <= 125


def test_building_cannot_trap_operator(session):
    session.deploy_operator("assault")
    assert not session.place_turret("laser", session.operator.position)


def test_saving_after_guard_removed_preserves_retreat_direction(session):
    session.deploy_operator("assault")
    soldier = session.operator
    soldier.position = Coordinate(3500, 3000)
    front = LaserTurret(Coordinate(3500, 3100))
    outer = LaserTurret(Coordinate(4200, 3000))
    session.map.modules = [front, outer]
    soldier.leave_manual(session.map)
    assert soldier.guard is front
    session.map.modules.remove(front)
    restored = Operator.from_dict(soldier.to_dict(), session.map)
    restored.update(0.1, session.map)
    assert restored.guard is None
    assert restored.retreat_limit == front.position.distance_to(session.base_position)


def test_operator_shoots_and_base_simulation_keeps_running(session):
    assert session.deploy_operator("assault")
    soldier = session.operator
    soldier.manual = True
    enemy = DroneWalker(Coordinate(soldier.position.x + 100, soldier.position.y))
    enemy.speed = 0
    session.map.enemies.append(enemy)
    soldier.aim = enemy.position
    soldier.trigger = True
    initial = enemy.health
    for _ in range(10):
        session.update(0.02)
    assert enemy.health < initial
    assert session.elapsed_time > 0


def test_enemy_attacks_operator_and_death_is_recoverable(session):
    controller = GameController(session)
    controller.enter_operator("assault")
    soldier = session.operator
    soldier.health = 1
    enemy = DroneWalker(Coordinate(soldier.position.x + 10, soldier.position.y))
    session.map.enemies.append(enemy)
    session.update(0.1)
    controller.update(0)
    assert not soldier.is_alive()
    assert not controller.operator_mode
    assert session.state == GameState.PLAYING
    assert not session.deploy_operator("engineer")
    session.elapsed_time = session.operator_respawn_at
    credits = session.resources.credits
    assert session.deploy_operator("engineer")
    assert session.resources.credits == credits - 200


def test_pause_freezes_operator_and_abilities(session):
    controller = GameController(session)
    controller.enter_operator("assault")
    soldier = session.operator
    soldier.move_input = (1, 0)
    position = Coordinate(soldier.position.x, soldier.position.y)
    session.state = GameState.PAUSED
    controller.handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    session.update(1)
    assert soldier.position == position
    assert soldier.ability_cooldown == 0


def test_engineer_repairs_but_does_not_resurrect_destroyed_towers(session):
    session.deploy_operator("engineer")
    soldier = session.operator
    tower = LaserTurret(Coordinate(soldier.position.x + 80, soldier.position.y))
    tower.health = 20
    dead = LaserTurret(Coordinate(soldier.position.x - 80, soldier.position.y))
    dead.health = 0
    session.map.modules = [tower, dead]
    assert soldier.use_ability(session.map)
    assert tower.health == 65
    assert dead.health == 0
    assert not soldier.use_ability(session.map)


def test_movement_cannot_cross_a_tower_or_map_edge(session):
    soldier = Operator("assault", Coordinate(100, 100))
    tower = LaserTurret(Coordinate(200, 100))
    session.map.modules = [tower]
    blocked = soldier.blocked_cells(session.map)
    soldier.move(1, 0, 2, session.map, blocked)
    assert soldier.position.x < 200
    soldier.move(-1, 0, 10, session.map, blocked)
    assert soldier.position.x >= soldier.RADIUS


@pytest.mark.parametrize("manual", [True, False])
def test_save_restores_operator_and_mode(session, manual):
    controller = GameController(session)
    controller.enter_operator("engineer")
    if not manual:
        controller.return_to_orbit()
    session.operator.health = 63
    session.operator.ability_cooldown = 4
    restored = GameSession()
    apply_dict_to_session(restored, session_to_dict(session))
    controller = GameController(restored)
    assert restored.operator.health == 63
    assert restored.operator.ability_cooldown == 4
    assert controller.operator_mode == manual
    assert restored.map.operator is restored.operator


def test_menu_selection_blocks_building_and_renders_both_modes(session):
    view = GameView(session, Settings())
    view._start_game(endless=True)
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_o))
    view.handle_events()
    assert view.operator_menu_open
    view.render()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2))
    view.handle_events()
    assert view.controller.operator_mode
    assert view.session.operator.kind == "engineer"
    assert view.controller.selected_tower_type is None
    view.render()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_o))
    view.handle_events()
    assert not view.controller.operator_mode
    view.render()
