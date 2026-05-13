import pytest
from src.entities.coordinate import Coordinate
from src.entities.turrets import LaserTurret, BulletTurret
from src.entities.enemies import DroneWalker, GiantRoach
from src.enums.enums import DamageType, ArmorType


class TestDamageSystem:
    """Тесты системы урона"""

    def test_tower_deals_damage(self, laser_turret, drone_enemy):
        """Тест 5: Корректность нанесения урона противнику"""
        initial_health = drone_enemy.health
        drone_enemy.take_damage(laser_turret.damage, laser_turret.damage_type)

        assert drone_enemy.health < initial_health

    def test_armor_reduction(self):
        """Проверка уменьшения урона броней"""
        heavy_enemy = GiantRoach(Coordinate(100, 100))
        initial_health = heavy_enemy.health

        heavy_enemy.take_damage(100, DamageType.KINETIC)

        damage_taken = initial_health - heavy_enemy.health
        assert damage_taken <= 100

    def test_different_tower_damage(self):
        """Проверка разного урона у разных башен"""
        laser = LaserTurret(Coordinate(100, 100))
        bullet = BulletTurret(Coordinate(100, 100))

        enemy1 = DroneWalker(Coordinate(150, 100))
        enemy2 = DroneWalker(Coordinate(150, 100))

        h1_before = enemy1.health
        h2_before = enemy2.health
        
        enemy1.take_damage(laser.damage, laser.damage_type)
        enemy2.take_damage(bullet.damage, bullet.damage_type)

        dmg_laser = h1_before - enemy1.health
        dmg_bullet = h2_before - enemy2.health

        assert dmg_laser != dmg_bullet