"""корректность движения противника по маршруту"""
import pytest
from src.core.coordinate import Coordinate
from src.entities.enemies import DroneWalker  # speed=50


def test_enemy_moves_towards_first_waypoint_proportionally_to_speed_and_time():
    enemy = DroneWalker(Coordinate(0, 0))
    enemy.set_path([Coordinate(100, 0)])

    reached_end = enemy.move_along_path(delta_time=1.0)  # speed=50 -> 50 юнитов за 1с

    assert enemy.position.x == pytest.approx(50.0)
    assert enemy.position.y == pytest.approx(0.0)
    assert reached_end is False
    assert enemy.path_index == 0, "точка ещё не достигнута — индекс не должен сдвигаться"


def test_enemy_reaches_close_waypoints_and_advances_index():
    enemy = DroneWalker(Coordinate(0, 0))
    enemy.set_path([Coordinate(10, 0), Coordinate(20, 0)])

    enemy.move_along_path(delta_time=1.0)  # 50 юнитов доступного хода — с запасом на обе точки

    assert enemy.path_index == 2, "обе точки ближе одного шага — должен пройти обе за один тик"
    assert enemy.position == Coordinate(20, 0)


def test_enemy_reaches_end_of_path_returns_true():
    enemy = DroneWalker(Coordinate(0, 0))
    enemy.set_path([Coordinate(10, 0)])

    reached_end = enemy.move_along_path(delta_time=10.0)  # с большим запасом

    assert reached_end is True
    assert enemy.path_index >= len(enemy.path)


def test_enemy_without_path_is_considered_arrived():
    enemy = DroneWalker(Coordinate(0, 0))

    assert enemy.move_along_path(delta_time=1.0) is True


def test_enemy_moves_diagonally_towards_waypoint():
    enemy = DroneWalker(Coordinate(0, 0))
    enemy.set_path([Coordinate(300, 400)])  # расстояние = 500

    enemy.move_along_path(delta_time=5.0)  # 50 * 5 = 250 юнитов пути, половина расстояния

    # направление должно сохраняться (соотношение x:y как 3:4)
    assert enemy.position.x == pytest.approx(150.0, abs=0.5)
    assert enemy.position.y == pytest.approx(200.0, abs=0.5)


def test_move_along_path_accumulates_across_multiple_ticks():
    enemy = DroneWalker(Coordinate(0, 0))
    enemy.set_path([Coordinate(100, 0)])

    for _ in range(4):
        enemy.move_along_path(delta_time=0.5)  # 25 юнитов за тик, 4 тика = 100

    assert enemy.position == Coordinate(100, 0)
    assert enemy.path_index == 1
