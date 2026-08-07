"""Снаряды по типу оружия: лазер мгновенный, пуля летит по прямой, мортира по параболе."""
import math

import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import DroneWalker
from src.entities.projectile import (
    BulletProjectile,
    HitscanBeam,
    MortarShell,
    ShrapnelPellet,
)
from src.entities.turrets import BulletTurret, LaserTurret, MortarTurret
from src.enums import DamageType


def _enemy(x, y, health=1000):
    e = DroneWalker(Coordinate(x, y))
    e.health = health
    e.max_health = health
    e.set_path([Coordinate(x + 100000, y)])
    return e



def test_hitscan_beam_damages_target_immediately_on_creation():
    target = _enemy(100, 0)
    HitscanBeam(Coordinate(0, 0), target, damage=25, damage_type=DamageType.ENERGY)

    assert target.health == 975, "лазер наносит урон сразу при создании, не дожидаясь update()"


def test_hitscan_beam_stays_visible_for_a_short_time_then_disappears():
    """Луч не должен пропадать в тот же кадр, в котором был создан - иначе
    выстрел лазерной башни никогда не успевает попасть в рендер."""
    target = _enemy(100, 0)
    beam = HitscanBeam(Coordinate(0, 0), target, damage=25, damage_type=DamageType.ENERGY)

    assert beam.update(0.01, [target]) is True, "луч должен оставаться на экране хотя бы пару кадров"
    assert target.health == 975, "повторные update() не должны наносить урон ещё раз"

    alive = beam.update(HitscanBeam.BEAM_LIFETIME, [target])
    assert alive is False


def test_hitscan_beam_does_not_damage_already_dead_target():
    target = _enemy(100, 0)
    target.health = 0
    beam = HitscanBeam(Coordinate(0, 0), target, damage=25, damage_type=DamageType.ENERGY)

    beam.update(0.016, [target])

    assert target.health == 0


def test_hitscan_beam_landed_event_name_is_laser_hit_when_target_was_alive():
    target = _enemy(100, 0)
    beam = HitscanBeam(Coordinate(0, 0), target, damage=25, damage_type=DamageType.ENERGY)

    assert beam.landed_event_name() == "laser_hit"


def test_hitscan_beam_landed_event_name_is_none_when_target_already_dead():
    target = _enemy(100, 0)
    target.health = 0
    beam = HitscanBeam(Coordinate(0, 0), target, damage=25, damage_type=DamageType.ENERGY)

    assert beam.landed_event_name() is None


def test_laser_turret_fire_returns_hitscan_beam():
    turret = LaserTurret(Coordinate(0, 0))
    target = _enemy(50, 0)

    projectile = turret.fire(target)

    assert isinstance(projectile, HitscanBeam)



def test_bullet_direction_fixed_at_creation_ignores_later_target_movement():
    target = _enemy(100, 0)
    bullet = BulletProjectile(Coordinate(0, 0), target, damage=10, damage_type=DamageType.KINETIC, speed=50)

    target.position = Coordinate(100, 500)
    bullet.update(1.0, [])

    assert bullet.position.y == pytest.approx(0.0), "пуля не должна доворачивать за целью"
    assert bullet.position.x == pytest.approx(50.0)


def test_bullet_hits_any_enemy_in_path_not_only_original_target():
    original_target = _enemy(1000, 0)
    decoy = _enemy(50, 0)
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

    alive = bullet.update(1.0, [])

    assert alive is False


def test_bullet_landed_event_name_is_bullet_hit_after_hitting_someone():
    original_target = _enemy(1000, 0)
    decoy = _enemy(50, 0)
    bullet = BulletProjectile(Coordinate(0, 0), original_target, damage=40,
                               damage_type=DamageType.KINETIC, speed=100)

    bullet.update(1.0, [decoy, original_target])

    assert bullet.landed_event_name() == "bullet_hit"


def test_bullet_landed_event_name_is_none_when_it_just_misses():
    target = _enemy(100, 0)
    bullet = BulletProjectile(Coordinate(0, 0), target, damage=10, damage_type=DamageType.KINETIC,
                               speed=1000, max_distance=50)

    bullet.update(1.0, [])

    assert bullet.landed_event_name() is None


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


def test_bullet_projectile_zero_spread_keeps_exact_direction():
    target = _enemy(100, 0)
    bullet = BulletProjectile(Coordinate(0, 0), target, damage=10, damage_type=DamageType.KINETIC,
                               speed=50, spread_degrees=0.0)

    assert bullet.direction == pytest.approx((1.0, 0.0))


def test_bullet_projectile_applies_random_spread_within_bounds():
    import random
    target = _enemy(1000, 0)
    rng = random.Random(42)
    bullet = BulletProjectile(Coordinate(0, 0), target, damage=10, damage_type=DamageType.KINETIC,
                               speed=1000, spread_degrees=20.0, rng=rng)

    angle = math.atan2(bullet.direction[1], bullet.direction[0])
    assert 0 < abs(angle) <= math.radians(20.0 / 2) + 1e-6


def test_bullet_turret_fire_applies_spread_degrees_constant():
    """Повторные выстрелы дают разброс направления, но не выходят за ±SPREAD_DEGREES/2."""
    turret = BulletTurret(Coordinate(0, 0))
    target = _enemy(1000, 0)

    angles = set()
    for _ in range(30):
        bullet = turret.fire(target)
        angle = math.atan2(bullet.direction[1], bullet.direction[0])
        assert abs(angle) <= math.radians(BulletTurret.SPREAD_DEGREES / 2) + 1e-6
        angles.add(round(angle, 6))

    assert len(angles) > 1, "повторные выстрелы должны давать разные направления из-за разброса"



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


def test_landed_event_name_is_none_before_any_collision():
    target = _enemy(100, 0)
    bullet = BulletProjectile(Coordinate(0, 0), target, damage=10, damage_type=DamageType.KINETIC, speed=50)
    pellet = ShrapnelPellet(Coordinate(0, 0), direction=(1, 0), damage=10,
                             damage_type=DamageType.EXPLOSIVE, speed=200, max_distance=90)

    assert bullet.landed_event_name() is None
    assert pellet.landed_event_name() is None


def test_shrapnel_pellet_never_has_its_own_landed_event_even_after_a_hit():
    victim = _enemy(50, 0)
    pellet = ShrapnelPellet(Coordinate(0, 0), direction=(1, 0), damage=10,
                             damage_type=DamageType.EXPLOSIVE, speed=200, max_distance=90)

    pellet.update(1.0, [victim])

    assert pellet.landed_event_name() is None, "звук взрыва мортиры уже проигран, шрапнель не дублирует его"


def test_mortar_shell_landed_event_name_is_mortar_explosion():
    target = _enemy(300, 0)
    shell = MortarShell(Coordinate(0, 0), target, damage=80, damage_type=DamageType.EXPLOSIVE)

    assert shell.landed_event_name() == "mortar_explosion"


def test_shrapnel_pellet_damages_enemy_in_path_and_expires():
    victim = _enemy(50, 0)
    pellet = ShrapnelPellet(Coordinate(0, 0), direction=(1, 0), damage=10,
                             damage_type=DamageType.EXPLOSIVE, speed=200, max_distance=90)

    alive = pellet.update(1.0, [victim])

    assert victim.health < victim.max_health
    assert alive is False



def test_map_update_passes_enemies_and_bullet_can_hit_nontarget():
    game_map = Map(width=4000, height=4000)
    turret = BulletTurret(Coordinate(0, 0))
    turret.cooldown_timer = 0
    game_map.modules.append(turret)

    decoy = _enemy(60, 0)
    far_target = _enemy(140, 0)
    game_map.enemies.extend([decoy, far_target])

    game_map.update(0.1)
    assert len(game_map.projectiles) == 1

    for _ in range(20):
        game_map.update(0.1)

    assert decoy.health < decoy.max_health or far_target.health < far_target.max_health


def test_map_update_keeps_laser_beam_visible_for_a_couple_of_frames():
    """Луч должен пережить хотя бы один полный Map.update(), а не исчезать тем же кадром."""
    game_map = Map(width=4000, height=4000)
    turret = LaserTurret(Coordinate(0, 0))
    turret.cooldown_timer = 0
    game_map.modules.append(turret)

    target = _enemy(50, 0)
    game_map.enemies.append(target)

    game_map.update(0.01)

    beams = [p for p in game_map.projectiles if isinstance(p, HitscanBeam)]
    assert beams, "луч должен оставаться в map.projectiles хотя бы один кадр после выстрела"


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


def test_map_emits_mortar_explosion_separately_from_tower_fired_on_landing():
    events = []
    game_map = Map(width=4000, height=4000, on_event=lambda name, **data: events.append((name, data)))
    turret = MortarTurret(Coordinate(0, 0))
    turret.type_name = "mortar"
    turret.cooldown_timer = 0
    game_map.modules.append(turret)

    target = _enemy(150, 0)
    game_map.enemies.append(target)

    game_map.update(0.1)
    fired = [e for e in events if e[0] == "tower_fired"]
    assert len(fired) == 1, "выстрел должен породить ровно одно событие tower_fired"
    assert not any(e[0] == "mortar_explosion" for e in events), "снаряд ещё в полёте, взрыва быть не должно"

    shell = next(p for p in game_map.projectiles if isinstance(p, MortarShell))
    for _ in range(200):
        if shell not in game_map.projectiles:
            break
        game_map.update(0.05)

    exploded = [e for e in events if e[0] == "mortar_explosion"]
    assert len(exploded) == 1
    assert exploded[0][1]["position"] == shell.position


def test_map_emits_laser_hit_event_after_the_beam_expires():
    events = []
    game_map = Map(width=4000, height=4000, on_event=lambda name, **data: events.append((name, data)))
    turret = LaserTurret(Coordinate(0, 0))
    turret.type_name = "laser"
    turret.cooldown_timer = 0
    game_map.modules.append(turret)

    target = _enemy(50, 0)
    game_map.enemies.append(target)

    game_map.update(0.01)
    assert not any(e[0] == "laser_hit" for e in events), "луч ещё виден на экране, событие ещё не должно случиться"

    game_map.update(HitscanBeam.BEAM_LIFETIME)

    hits = [e for e in events if e[0] == "laser_hit"]
    assert len(hits) == 1
    assert hits[0][1]["position"] == Coordinate(0, 0)


def test_map_emits_bullet_hit_event_only_when_the_bullet_actually_connects():
    events = []
    game_map = Map(width=4000, height=4000, on_event=lambda name, **data: events.append((name, data)))
    turret = BulletTurret(Coordinate(0, 0), range_radius=5000)
    turret.type_name = "bullet"
    turret.cooldown_timer = 0
    game_map.modules.append(turret)

    target = _enemy(60, 0)
    game_map.enemies.append(target)

    for _ in range(20):
        game_map.update(0.1)

    hits = [e for e in events if e[0] == "bullet_hit"]
    assert hits, "хотя бы одна из пуль должна была попасть по единственному врагу в радиусе"
