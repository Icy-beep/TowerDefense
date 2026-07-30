"""Снаряды по типу оружия вместо единого "хоминга": лазер бьёт мгновенно,
пуля летит по прямой и может промазать, мортира летает по параболе и по
приземлении разлетается шрапнелью. Урон — по факту столкновения с любым
живым врагом из списка, а не гарантированно по исходной цели."""
import math
import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import DroneWalker
from src.entities.turrets import LaserTurret, BulletTurret, MortarTurret
from src.entities.projectile import (
    HitscanBeam, BulletProjectile, MortarShell, ShrapnelPellet,
)
from src.enums import DamageType


def _enemy(x, y, health=1000):
    e = DroneWalker(Coordinate(x, y))
    e.health = health
    e.max_health = health
    # Без пути Map.update() сочтёт врага "уже дошедшим до базы"
    # (path_index (0) >= len(path) (0)) и уберёт его до того, как башни
    # успеют выстрелить. Далёкая точка держит врага "в пути" на все
    # тики, которые прогоняют тесты этого модуля.
    e.set_path([Coordinate(x + 100000, y)])
    return e


# ---------------------------------------------------------------- HitscanBeam

def test_hitscan_beam_damages_target_immediately():
    target = _enemy(100, 0)
    beam = HitscanBeam(Coordinate(0, 0), target, damage=25, damage_type=DamageType.ENERGY)

    alive = beam.update(0.016, [target])

    assert target.health == 975
    assert alive is False


def test_hitscan_beam_does_not_damage_already_dead_target():
    target = _enemy(100, 0)
    target.health = 0
    beam = HitscanBeam(Coordinate(0, 0), target, damage=25, damage_type=DamageType.ENERGY)

    beam.update(0.016, [target])

    assert target.health == 0  # не ушёл в минус, take_damage не вызывался повторно


def test_laser_turret_fire_returns_hitscan_beam():
    turret = LaserTurret(Coordinate(0, 0))
    target = _enemy(50, 0)

    projectile = turret.fire(target)

    assert isinstance(projectile, HitscanBeam)


# ------------------------------------------------------------ BulletProjectile

def test_bullet_direction_fixed_at_creation_ignores_later_target_movement():
    target = _enemy(100, 0)
    bullet = BulletProjectile(Coordinate(0, 0), target, damage=10, damage_type=DamageType.KINETIC, speed=50)

    target.position = Coordinate(100, 500)  # цель "увернулась" после выстрела
    bullet.update(1.0, [])

    assert bullet.position.y == pytest.approx(0.0), "пуля не должна доворачивать за целью"
    assert bullet.position.x == pytest.approx(50.0)


def test_bullet_hits_any_enemy_in_path_not_only_original_target():
    original_target = _enemy(1000, 0)
    decoy = _enemy(50, 0)  # оказался на линии полёта раньше исходной цели
    bullet = BulletProjectile(Coordinate(0, 0), original_target, damage=40,
                               damage_type=DamageType.KINETIC, speed=100)

    alive = bullet.update(1.0, [decoy, original_target])

    assert decoy.health < decoy.max_health
    assert original_target.health == original_target.max_health
    assert alive is False


def test_bullet_misses_if_nothing_in_path_and_expires_past_max_distance():
    target = _enemy(100, 0)
    bullet = BulletProjectile(Coordinate(0, 0), target, damage=10, damage_type=DamageType.KINETIC,
                               speed=1000, max_distance=50)

    alive = bullet.update(1.0, [])  # улетел на 1000, но max_distance=50

    assert alive is False


def test_bullet_keeps_flying_while_under_max_distance_and_nothing_hit():
    target = _enemy(1000, 0)
    bullet = BulletProjectile(Coordinate(0, 0), target, damage=10, damage_type=DamageType.KINETIC,
                               speed=100, max_distance=5000)

    alive = bullet.update(1.0, [])

    assert alive is True
    assert bullet.position.x == pytest.approx(100.0)


def test_bullet_turret_fire_returns_bullet_projectile():
    turret = BulletTurret(Coordinate(0, 0))
    target = _enemy(50, 0)

    assert isinstance(turret.fire(target), BulletProjectile)


# ---------------------------------------------------------------- MortarShell

def test_mortar_shell_interpolates_position_toward_target():
    target = _enemy(1000, 0)
    shell = MortarShell(Coordinate(0, 0), target, damage=80, damage_type=DamageType.EXPLOSIVE)

    shell.update(shell.flight_time / 2, [])

    assert shell.position.x == pytest.approx(500.0, abs=1.0)


def test_mortar_shell_height_peaks_at_midflight_and_zero_at_ends():
    target = _enemy(1000, 0)
    shell = MortarShell(Coordinate(0, 0), target, damage=80, damage_type=DamageType.EXPLOSIVE)

    shell.update(0.001, [])
    height_start = shell.height
    shell.update(shell.flight_time / 2 - 0.001, [])
    height_mid = shell.height

    assert height_mid > height_start
    assert height_mid == pytest.approx(shell.PEAK_HEIGHT, rel=0.05)


def test_mortar_shell_lands_and_stops_after_flight_time():
    target = _enemy(300, 0)
    shell = MortarShell(Coordinate(0, 0), target, damage=80, damage_type=DamageType.EXPLOSIVE)

    alive = shell.update(shell.flight_time + 1.0, [])

    assert alive is False
    assert shell.height == 0.0
    assert shell.position == Coordinate(300, 0)


def test_mortar_shell_spawns_shrapnel_on_landing():
    target = _enemy(300, 0)
    shell = MortarShell(Coordinate(0, 0), target, damage=80, damage_type=DamageType.EXPLOSIVE)

    shell.update(shell.flight_time + 1.0, [])
    spawned = shell.collect_spawned()

    assert len(spawned) == MortarShell.SHRAPNEL_COUNT
    assert all(isinstance(p, ShrapnelPellet) for p in spawned)
    total_damage = sum(p.damage for p in spawned)
    assert total_damage == pytest.approx(80.0)


def test_mortar_shrapnel_spread_evenly_in_a_circle():
    target = _enemy(300, 0)
    shell = MortarShell(Coordinate(0, 0), target, damage=80, damage_type=DamageType.EXPLOSIVE)
    shell.update(shell.flight_time + 1.0, [])
    spawned = shell.collect_spawned()

    angles = sorted(math.atan2(p.direction[1], p.direction[0]) for p in spawned)
    gaps = [(angles[i + 1] - angles[i]) for i in range(len(angles) - 1)]
    gaps.append((angles[0] + 2 * math.pi) - angles[-1])
    expected_gap = 2 * math.pi / MortarShell.SHRAPNEL_COUNT
    assert all(gap == pytest.approx(expected_gap, abs=0.01) for gap in gaps)


def test_collect_spawned_drains_only_once():
    target = _enemy(300, 0)
    shell = MortarShell(Coordinate(0, 0), target, damage=80, damage_type=DamageType.EXPLOSIVE)
    shell.update(shell.flight_time + 1.0, [])

    first = shell.collect_spawned()
    second = shell.collect_spawned()

    assert len(first) == MortarShell.SHRAPNEL_COUNT
    assert second == []


def test_mortar_turret_fire_returns_mortar_shell():
    turret = MortarTurret(Coordinate(0, 0))
    target = _enemy(50, 0)

    assert isinstance(turret.fire(target), MortarShell)


def test_shrapnel_pellet_damages_enemy_in_path_and_expires():
    victim = _enemy(50, 0)
    pellet = ShrapnelPellet(Coordinate(0, 0), direction=(1, 0), damage=10,
                             damage_type=DamageType.EXPLOSIVE, speed=200, max_distance=90)

    alive = pellet.update(1.0, [victim])

    assert victim.health < victim.max_health
    assert alive is False


# --------------------------------------------------------- Map.update() wiring

def test_map_update_passes_enemies_and_bullet_can_hit_nontarget():
    game_map = Map(width=4000, height=4000)
    turret = BulletTurret(Coordinate(0, 0))
    turret.cooldown_timer = 0
    game_map.modules.append(turret)

    decoy = _enemy(60, 0)
    far_target = _enemy(140, 0)  # ровно на границе range_radius=150
    game_map.enemies.extend([decoy, far_target])

    game_map.update(0.1)  # башня стреляет, снаряд появляется в map.projectiles
    assert len(game_map.projectiles) == 1

    for _ in range(20):
        game_map.update(0.1)

    assert decoy.health < decoy.max_health or far_target.health < far_target.max_health


def test_map_update_collects_mortar_shrapnel_into_projectile_list():
    game_map = Map(width=4000, height=4000)
    turret = MortarTurret(Coordinate(0, 0))
    turret.cooldown_timer = 0
    game_map.modules.append(turret)

    target = _enemy(150, 0)
    game_map.enemies.append(target)

    game_map.update(0.1)
    shells = [p for p in game_map.projectiles if isinstance(p, MortarShell)]
    assert len(shells) == 1
    shell = shells[0]

    for _ in range(200):
        if shell not in game_map.projectiles:
            break
        game_map.update(0.05)

    pellets = [p for p in game_map.projectiles if isinstance(p, ShrapnelPellet)]
    assert len(pellets) == MortarShell.SHRAPNEL_COUNT
