"""Два новых паттерна поведения врагов (src/core/map.py):

1. Уклонение от выстрелов (HostileEntity.dodges_projectiles()) — враги с
   лёгкой бронёй (ArmorType.LIGHT) под обстрелом башни покачиваются из
   стороны в сторону вместо движения по прямой.
2. Отступление на лечение — враг с низким HP (ниже WOUNDED_HEALTH_RATIO
   от максимума) отступает к ближайшей точке спавна своей фракции и там
   пассивно лечится. Если ранен кто-то в группе, отступает вся группа
   (ведомые просто следуют за отступающим лидером как обычно)."""
import math

import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import DroneWalker, GiantRoach, HeavyAssaultDrone, ScoutDrone, BioTitan
from src.enums import Faction


# ------------------------------------------------------------------ dodge

def test_only_light_armor_enemies_dodge_projectiles():
    assert DroneWalker(Coordinate(0, 0)).dodges_projectiles() is True
    assert GiantRoach(Coordinate(0, 0)).dodges_projectiles() is False
    assert HeavyAssaultDrone(Coordinate(0, 0)).dodges_projectiles() is False
    assert ScoutDrone(Coordinate(0, 0)).dodges_projectiles() is False
    assert BioTitan(Coordinate(0, 0)).dodges_projectiles() is False


def test_light_enemy_moves_in_a_straight_line_when_not_under_fire():
    game_map = Map(width=4000, height=4000)  # башен нет — нигде не простреливается
    enemy = DroneWalker(Coordinate(500, 500))
    enemy.set_path([Coordinate(2000, 500)])
    game_map.spawn_enemy(enemy)

    for _ in range(20):
        game_map.update(0.1)

    assert enemy.position.y == pytest.approx(500.0), \
        "вне зоны действия башен лёгкий враг не должен вилять в стороны"


def test_light_enemy_wiggles_sideways_when_under_fire():
    from src.entities.turrets import LaserTurret

    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(1250, 500), range_radius=5000)  # накрывает весь путь
    game_map.modules.append(tower)

    enemy = DroneWalker(Coordinate(500, 500))
    enemy.set_path([Coordinate(2000, 500)])
    game_map.spawn_enemy(enemy)

    max_deviation = 0.0
    saw_nonzero = False
    for _ in range(60):
        game_map.update(0.1)
        deviation = abs(enemy.position.y - 500.0)
        max_deviation = max(max_deviation, deviation)
        if deviation > 0.5:
            saw_nonzero = True

    assert saw_nonzero, "под обстрелом лёгкий враг должен отклоняться от прямой линии"
    assert max_deviation <= DroneWalker.DODGE_AMPLITUDE + 5.0, \
        "боковое покачивание должно оставаться в разумных пределах амплитуды"


def test_heavy_enemy_does_not_wiggle_even_when_under_fire():
    from src.entities.turrets import LaserTurret

    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(1250, 500), range_radius=5000)
    game_map.modules.append(tower)

    enemy = GiantRoach(Coordinate(500, 500))
    enemy.set_path([Coordinate(2000, 500)])
    game_map.spawn_enemy(enemy)

    for _ in range(20):
        game_map.update(0.1)

    assert enemy.position.y == pytest.approx(500.0), \
        "тяжёлые враги не уклоняются от выстрелов"


# ---------------------------------------------------------- retreat & heal
#
# Отступление на лечение через точку спавна теперь работает только для
# Fauna - у Corporation вместо этого MedicDrone, лечащий группу напрямую
# (см. Map.FACTIONS_WITHOUT_RETREAT_HEALING и test_medic_drone.py).

def _spawn_fillers(game_map, count=4, faction=Faction.FAUNA, far_away=Coordinate(3999, 3999)):
    """Добавляет здоровых 'фоновых' врагов далеко в стороне — нужно только
    чтобы общее число живых врагов на карте превышало LOW_ENEMY_COUNT_NO_RETREAT
    и не мешало отступлению срабатывать в тестах на само отступление."""
    for i in range(count):
        filler = GiantRoach(Coordinate(far_away.x, far_away.y - i * 10))
        filler.faction = faction
        filler.set_path([Coordinate(far_away.x - 500, far_away.y)])
        game_map.spawn_enemy(filler)


def test_solo_wounded_enemy_retreats_towards_its_spawn_point():
    game_map = Map(width=4000, height=4000)
    game_map.spawn_points_by_faction = {Faction.FAUNA: [Coordinate(200, 200)]}
    _spawn_fillers(game_map)

    enemy = GiantRoach(Coordinate(2000, 2000))
    enemy.health = 50  # меньше 30% от max_health=250
    enemy.set_path([Coordinate(2500, 2000)])
    game_map.spawn_enemy(enemy)

    initial_distance = enemy.position.distance_to(Coordinate(200, 200))

    for _ in range(20):
        game_map.update(0.1)

    assert enemy.is_healing is True
    assert enemy.position.distance_to(Coordinate(200, 200)) < initial_distance


def test_healthy_solo_enemy_does_not_retreat():
    game_map = Map(width=4000, height=4000)
    game_map.spawn_points_by_faction = {Faction.FAUNA: [Coordinate(200, 200)]}

    enemy = GiantRoach(Coordinate(2000, 2000))  # полное здоровье
    enemy.set_path([Coordinate(2500, 2000)])
    game_map.spawn_enemy(enemy)

    game_map.update(0.1)

    assert enemy.is_healing is False


def test_wounded_enemy_heals_near_spawn_and_resumes_path_to_base():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    game_map.spawn_points_by_faction = {Faction.FAUNA: [Coordinate(200, 200)]}
    _spawn_fillers(game_map)

    enemy = GiantRoach(Coordinate(210, 210))  # уже рядом со своей точкой спавна
    enemy.health = 50
    enemy.set_path([Coordinate(2000, 2000)])
    game_map.spawn_enemy(enemy)

    for _ in range(80):
        game_map.update(0.1)

    assert enemy.health == pytest.approx(enemy.max_health)
    assert enemy.is_healing is False
    assert len(enemy.path) > 0, "после лечения враг должен получить новый маршрут к базе"


def test_group_retreats_when_a_follower_is_wounded():
    game_map = Map(width=4000, height=4000)
    game_map.spawn_points_by_faction = {Faction.FAUNA: [Coordinate(200, 200)]}
    _spawn_fillers(game_map)

    leader = GiantRoach(Coordinate(2000, 2000))
    leader.is_group_leader = True
    leader.group_id = 1
    leader.set_path([Coordinate(2500, 2000)])

    follower = GiantRoach(Coordinate(2020, 2000))
    follower.health = 30  # ранен, лидер — нет
    follower.set_path([Coordinate(2500, 2000)])
    follower.join_group(1, leader, Coordinate(20, 0))

    game_map.spawn_enemy(leader)
    game_map.spawn_enemy(follower)

    initial_leader_distance = leader.position.distance_to(Coordinate(200, 200))

    for _ in range(20):
        game_map.update(0.1)

    assert leader.is_healing is True, "лидер должен начать отступать из-за раненого ведомого"
    assert leader.position.distance_to(Coordinate(200, 200)) < initial_leader_distance
    assert follower.group_leader is leader, "ведомый не бросает группу, а просто следует за лидером"


def test_retreating_enemy_ignores_a_nearby_opposing_enemy_instead_of_fighting():
    """Регрессия: раньше отступление проверялось с более низким приоритетом,
    чем бой (in_combat) — если рядом с отступающим оказывался враг другой
    фракции в радиусе обзора, каждый кадр решение "отступать"/"драться"
    могло переключаться туда-сюда, и группа могла бесконечно топтаться на
    месте вместо того, чтобы дойти до точки спавна."""
    game_map = Map(width=4000, height=4000)
    game_map.spawn_points_by_faction = {Faction.FAUNA: [Coordinate(200, 200)]}
    _spawn_fillers(game_map)

    wounded = GiantRoach(Coordinate(2000, 2000))
    wounded.health = 50  # меньше 30% от 250
    wounded.set_path([Coordinate(2500, 2000)])
    game_map.spawn_enemy(wounded)

    pest = DroneWalker(Coordinate(2030, 2000))  # чужая фракция, в радиусе обзора
    game_map.spawn_enemy(pest)

    initial_distance = wounded.position.distance_to(Coordinate(200, 200))

    for _ in range(20):
        game_map.update(0.1)

    assert wounded.is_healing is True
    assert wounded.position.distance_to(Coordinate(200, 200)) < initial_distance, \
        "раненый враг должен непрерывно отступать к спавну, не отвлекаясь на бой"


def test_corporation_enemies_never_use_retreat_to_heal_even_when_wounded():
    """Corporation больше не отступает к точке спавна лечиться вовсе -
    вместо этого их лечит MedicDrone внутри группы (см. test_medic_drone.py)."""
    game_map = Map(width=4000, height=4000)
    game_map.spawn_points_by_faction = {Faction.CORPORATION: [Coordinate(200, 200)]}
    _spawn_fillers(game_map)

    wounded = DroneWalker(Coordinate(2000, 2000))
    wounded.health = 5  # меньше 30% от max_health=60
    wounded.set_path([Coordinate(2500, 2000)])
    game_map.spawn_enemy(wounded)

    initial_distance = wounded.position.distance_to(Coordinate(200, 200))

    for _ in range(20):
        game_map.update(0.1)

    assert wounded.is_healing is False
    assert wounded.position.distance_to(Coordinate(200, 200)) >= initial_distance, \
        "раненый Corporation-юнит должен продолжать двигаться вперёд, а не отступать к спавну"


def test_is_near_own_spawn_heals_passively_over_time():
    game_map = Map(width=4000, height=4000)
    game_map.spawn_points_by_faction = {Faction.FAUNA: [Coordinate(3800, 3800)]}

    enemy = GiantRoach(Coordinate(3800, 3800))
    enemy.health = 50  # max_health=250
    enemy.set_path([Coordinate(2000, 2000)])
    game_map.spawn_enemy(enemy)

    before = enemy.health
    game_map.update(0.1)

    assert enemy.health > before


# ---------------------------------------- last stragglers of a wave: no retreat

def _make_wounded_solo(position, health=50):
    enemy = GiantRoach(position)
    enemy.health = health
    enemy.set_path([Coordinate(position.x + 500, position.y)])
    return enemy


def test_wounded_enemy_does_not_retreat_when_wave_is_down_to_the_last_few():
    game_map = Map(width=4000, height=4000)
    game_map.spawn_points_by_faction = {Faction.FAUNA: [Coordinate(200, 200)]}

    # Всего 3 живых врага на карте — меньше LOW_ENEMY_COUNT_NO_RETREAT (4).
    wounded = _make_wounded_solo(Coordinate(2000, 2000))
    ally_1 = GiantRoach(Coordinate(2100, 2000))
    ally_2 = GiantRoach(Coordinate(2200, 2000))
    for e in (ally_1, ally_2):
        e.set_path([Coordinate(2500, 2000)])
    game_map.spawn_enemy(wounded)
    game_map.spawn_enemy(ally_1)
    game_map.spawn_enemy(ally_2)

    initial_distance = wounded.position.distance_to(Coordinate(200, 200))

    for _ in range(20):
        game_map.update(0.1)

    assert wounded.is_healing is False, \
        "когда врагов в волне мало, раненые больше не должны уходить лечиться"
    assert wounded.position.distance_to(Coordinate(200, 200)) >= initial_distance, \
        "раненый должен продолжать двигаться вперёд, а не отступать к спавну"


def test_wounded_enemy_retreats_when_plenty_of_enemies_remain():
    game_map = Map(width=4000, height=4000)
    game_map.spawn_points_by_faction = {Faction.FAUNA: [Coordinate(200, 200)]}

    wounded = _make_wounded_solo(Coordinate(2000, 2000))
    game_map.spawn_enemy(wounded)
    allies = [GiantRoach(Coordinate(2100 + i * 30, 2000)) for i in range(5)]  # итого 6 > 4
    for a in allies:
        a.set_path([Coordinate(2500, 2000)])
        game_map.spawn_enemy(a)

    for _ in range(5):
        game_map.update(0.1)

    assert wounded.is_healing is True


def test_retreat_stops_once_wave_thins_out_to_the_threshold():
    game_map = Map(width=4000, height=4000)
    game_map.spawn_points_by_faction = {Faction.FAUNA: [Coordinate(200, 200)]}

    wounded = _make_wounded_solo(Coordinate(2000, 2000))
    game_map.spawn_enemy(wounded)
    allies = [GiantRoach(Coordinate(2100 + i * 30, 2000)) for i in range(5)]  # итого 6 > 4
    for a in allies:
        a.set_path([Coordinate(2500, 2000)])
        game_map.spawn_enemy(a)

    game_map.update(0.1)
    assert wounded.is_healing is True, "пока врагов много, раненый отступает"

    # Остальные погибают в бою — волна редеет до 1 (только раненый).
    for a in allies:
        a.health = 0

    game_map.update(0.1)

    assert wounded.is_healing is False, \
        "как только волна поредела до порога, отступление должно прекратиться"
