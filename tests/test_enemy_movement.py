import pytest

from src.enums import DamageType
from src.entities.coordinate import Coordinate
from src.entities.enemies import DroneWalker


class TestEnemyMovement:
    """Тесты движения врагов"""

    def test_initial_position(self, drone_enemy, coord):
        """Проверка начальной позиции врага"""
        assert drone_enemy.position == coord

    def test_move_along_path_single_segment(self):
        """Тест 3: Корректность движения противника по маршруту (один сегмент)"""
        enemy = DroneWalker(Coordinate(0, 100))
        path = [Coordinate(200, 100)]

        enemy.move_along_path(path, delta_time=2.0)

        assert enemy.position.x == 100
        assert enemy.path_index == 0

    def test_move_reach_waypoint(self):
        """Проверка достижения точки пути"""
        enemy = DroneWalker(Coordinate(0, 100))
        path = [Coordinate(100, 100), Coordinate(200, 100)]

        enemy.move_along_path(path, delta_time=2.0)

        assert enemy.path_index == 1
        assert enemy.position.x == 100

    def test_move_complete_path(self):
        """Проверка прохождения всего пути"""
        enemy = DroneWalker(Coordinate(0, 100))
        path = [Coordinate(50, 100), Coordinate(100, 100)]

        completed = enemy.move_along_path(path, delta_time=3.0)

        assert completed is True
        assert enemy.path_index == 2

    def test_health_after_damage(self, drone_enemy):
        """Проверка здоровья после получения урона"""
        initial_health = drone_enemy.health
        drone_enemy.take_damage(20, DamageType.KINETIC)
        assert drone_enemy.health == initial_health - 20

    def test_enemy_death(self, drone_enemy):
        """Тест 6: Корректность удаления уничтоженного противника"""
        drone_enemy.take_damage(1000, DamageType.KINETIC)

        assert drone_enemy.is_alive() is False