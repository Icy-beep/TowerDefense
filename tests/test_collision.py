"""Корректность определения противников, находящихся
в зоне действия башни (DefenseModule.find_target)"""
from src.core.coordinate import Coordinate
from src.entities.turrets import BulletTurret
from src.entities.enemies import DroneWalker


def test_enemy_inside_radius_is_detected():
    turret = BulletTurret(Coordinate(0, 0))
    enemy = DroneWalker(Coordinate(100, 0))

    target = turret.find_target([enemy])

    assert target is enemy


def test_enemy_outside_radius_is_not_detected():
    turret = BulletTurret(Coordinate(0, 0))
    enemy = DroneWalker(Coordinate(300, 0))

    target = turret.find_target([enemy])

    assert target is None


def test_enemy_exactly_on_radius_edge_is_detected():
    turret = BulletTurret(Coordinate(0, 0))
    enemy = DroneWalker(Coordinate(150, 0))

    target = turret.find_target([enemy])

    assert target is enemy, "граница радиуса должна включаться (<=), а не исключаться"


def test_finds_closest_of_multiple_enemies_in_range():
    turret = BulletTurret(Coordinate(0, 0))
    far_enemy = DroneWalker(Coordinate(140, 0))
    near_enemy = DroneWalker(Coordinate(50, 0))

    target = turret.find_target([far_enemy, near_enemy])

    assert target is near_enemy


def test_no_target_when_enemy_list_is_empty():
    turret = BulletTurret(Coordinate(0, 0))

    assert turret.find_target([]) is None


def test_no_target_when_all_enemies_out_of_range():
    turret = BulletTurret(Coordinate(0, 0))
    enemies = [DroneWalker(Coordinate(200, 0)), DroneWalker(Coordinate(500, 500))]

    assert turret.find_target(enemies) is None
