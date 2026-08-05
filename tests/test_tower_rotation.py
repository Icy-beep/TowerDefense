"""Поворот башни к цели (DefenseModule.facing_angle) для направленных спрайтов."""
import pytest

from src.core.coordinate import Coordinate
from src.entities.enemies import DroneWalker
from src.entities.turrets import LaserTurret


def test_tower_faces_up_towards_target_directly_above():
    tower = LaserTurret(Coordinate(100, 100))
    enemy = DroneWalker(Coordinate(100, 0))

    tower.update(0.1, [enemy])

    assert tower.facing_angle == pytest.approx(0.0)


def test_tower_faces_right_towards_target_to_the_east():
    tower = LaserTurret(Coordinate(100, 100))
    enemy = DroneWalker(Coordinate(200, 100))

    tower.update(0.1, [enemy])

    assert tower.facing_angle == pytest.approx(90.0)


def test_tower_faces_down_towards_target_below():
    tower = LaserTurret(Coordinate(100, 100))
    enemy = DroneWalker(Coordinate(100, 200))

    tower.update(0.1, [enemy])

    assert tower.facing_angle == pytest.approx(180.0)


def test_tower_faces_left_towards_target_to_the_west():
    tower = LaserTurret(Coordinate(100, 100))
    enemy = DroneWalker(Coordinate(0, 100))

    tower.update(0.1, [enemy])

    assert tower.facing_angle == pytest.approx(270.0)


def test_tower_keeps_last_facing_when_no_target_in_range():
    tower = LaserTurret(Coordinate(100, 100))
    enemy_in_range = DroneWalker(Coordinate(200, 100))
    tower.update(0.1, [enemy_in_range])
    assert tower.facing_angle == pytest.approx(90.0)

    enemy_far = DroneWalker(Coordinate(5000, 5000))
    tower.update(0.1, [enemy_far])

    assert tower.facing_angle == pytest.approx(90.0), \
        "без цели в радиусе башня должна сохранять последнее направление, а не сбрасываться"


def test_tower_keeps_tracking_target_while_on_cooldown():
    tower = LaserTurret(Coordinate(100, 100))
    enemy = DroneWalker(Coordinate(200, 100))

    tower.update(0.1, [enemy])
    assert tower.cooldown_timer > 0, "первый выстрел должен поставить башню на кулдаун"

    enemy.position = Coordinate(100, 200)
    tower.update(0.05, [enemy])

    assert tower.facing_angle == pytest.approx(180.0), \
        "наведение должно обновляться каждый кадр, даже пока башня перезаряжается"
