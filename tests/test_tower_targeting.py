import pytest
from src.entities.coordinate import Coordinate
from src.entities.turrets import LaserTurret
from src.entities.enemies import DroneWalker


class TestTowerTargeting:
    """Тесты наведения башен на цели"""

    def test_find_target_in_range(self):
        """Тест 4: Корректность определения противников в зоне действия башни"""
        tower = LaserTurret(Coordinate(100, 100))
        enemy_in_range = DroneWalker(Coordinate(150, 100))
        enemy_out_of_range = DroneWalker(Coordinate(300, 100))

        enemies = [enemy_out_of_range, enemy_in_range]
        target = tower.find_target(enemies)

        assert target == enemy_in_range
        assert target is not None

    def test_no_target_in_range(self):
        """Проверка, когда врагов в радиусе нет"""
        tower = LaserTurret(Coordinate(100, 100))
        enemy_far = DroneWalker(Coordinate(500, 500))

        target = tower.find_target([enemy_far])

        assert target is None

    def test_find_nearest_target(self):
        """Проверка выбора ближайшей цели"""
        tower = LaserTurret(Coordinate(100, 100))
        enemy_near = DroneWalker(Coordinate(120, 100))
        enemy_far = DroneWalker(Coordinate(180, 100))

        target = tower.find_target([enemy_far, enemy_near])

        assert target == enemy_near