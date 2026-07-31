"""Групповое поведение врагов (src/systems/group_formation.py).

Раньше волна из одной фракции всегда шла к базе поодиночке. Теперь
GroupFormationSystem время от времени случайно собирает эскорт вокруг
врага-лидера определённого типа (по умолчанию HeavyAssaultDrone) из
ближайших врагов ТОЙ ЖЕ фракции; пока лидер жив и не дошёл до базы,
эскорт движется не по своему маршруту, а рядом с лидером (см.
Map.update()). ScoutDrone теперь входит в SOLO_TYPES и никогда не
участвует в группах — ни как лидер, ни как ведомый: его единственная
задача — разведка и бегство от башен."""
import math

import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import DroneWalker, GiantRoach, HeavyAssaultDrone, MedicDrone, ScoutDrone
from src.entities.turrets import LaserTurret
from src.systems.group_formation import GroupFormationSystem


def _tagged(enemy, type_name):
    """EnemyFactory обычно сама проставляет type_name — тут враги создаются
    напрямую, поэтому тег нужно выставить руками."""
    enemy.type_name = type_name
    return enemy


class _AlwaysFormRng:
    """random() всегда 0.0 (< любой положительный шанс — формирование
    гарантированно происходит), choice всегда берёт первого кандидата."""
    def random(self):
        return 0.0

    def choice(self, seq):
        return seq[0]


class _NeverFormRng:
    def random(self):
        return 1.0

    def choice(self, seq):
        return seq[0]


# --------------------------------------------------------- GroupFormationSystem

def test_only_configured_leader_type_can_start_a_group():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    non_leader = _tagged(DroneWalker(Coordinate(0, 0)), "drone_walker")
    nearby = _tagged(DroneWalker(Coordinate(10, 0)), "drone_walker")

    system.update(1.0, [non_leader, nearby])

    assert non_leader.group_id is None
    assert nearby.group_id is None


def test_heavy_assault_drone_recruits_nearby_enemy_of_same_faction():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    leader = _tagged(HeavyAssaultDrone(Coordinate(0, 0)), "heavy_assault_drone")
    ally = _tagged(DroneWalker(Coordinate(50, 0)), "drone_walker")  # тоже Corporation

    system.update(1.0, [leader, ally])

    assert leader.is_group_leader is True
    assert ally.group_leader is leader
    assert ally.group_id == leader.group_id


def test_heavy_assault_drone_does_not_recruit_enemy_of_different_faction():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    leader = _tagged(HeavyAssaultDrone(Coordinate(0, 0)), "heavy_assault_drone")  # Corporation
    roach = _tagged(GiantRoach(Coordinate(50, 0)), "giant_roach")  # Fauna

    system.update(1.0, [leader, roach])

    assert roach.group_leader is None, "фракции разные — вербовки быть не должно"


def test_heavy_assault_drone_does_not_recruit_enemy_outside_group_radius():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    leader = _tagged(HeavyAssaultDrone(Coordinate(0, 0)), "heavy_assault_drone")
    far_ally = _tagged(DroneWalker(Coordinate(GroupFormationSystem.GROUP_RADIUS + 50, 0)), "drone_walker")

    system.update(1.0, [leader, far_ally])

    assert far_ally.group_leader is None


def test_form_chance_gates_recruitment():
    system = GroupFormationSystem(rng=_NeverFormRng())
    leader = _tagged(HeavyAssaultDrone(Coordinate(0, 0)), "heavy_assault_drone")
    ally = _tagged(DroneWalker(Coordinate(10, 0)), "drone_walker")

    system.update(1.0, [leader, ally])

    assert ally.group_leader is None


def test_escort_size_is_capped():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    leader = _tagged(HeavyAssaultDrone(Coordinate(0, 0)), "heavy_assault_drone")
    allies = [_tagged(DroneWalker(Coordinate(10 * i, 0)), "drone_walker") for i in range(1, 6)]

    for _ in range(10):
        system.update(1.0, [leader] + allies)

    escorted = sum(1 for a in allies if a.group_leader is leader)
    assert escorted == GroupFormationSystem.MAX_ESCORT_SIZE


def test_already_grouped_enemy_is_not_recruited_by_another_leader():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    leader_a = _tagged(HeavyAssaultDrone(Coordinate(0, 0)), "heavy_assault_drone")
    leader_b = _tagged(HeavyAssaultDrone(Coordinate(1000, 0)), "heavy_assault_drone")
    ally = _tagged(DroneWalker(Coordinate(10, 0)), "drone_walker")

    system.update(1.0, [leader_a, ally])
    assert ally.group_leader is leader_a

    ally.position = Coordinate(1010, 0)  # физически рядом со вторым лидером
    system.update(1.0, [leader_b, ally])

    assert ally.group_leader is leader_a, "уже состоящий в группе враг не должен переманиваться"


def test_scout_drone_never_becomes_a_leader():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    scout = _tagged(ScoutDrone(Coordinate(0, 0)), "scout_drone")
    ally = _tagged(DroneWalker(Coordinate(10, 0)), "drone_walker")

    system.update(1.0, [scout, ally])

    assert scout.is_group_leader is False
    assert ally.group_leader is None


def test_scout_drone_is_never_recruited_as_a_follower():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    leader = _tagged(HeavyAssaultDrone(Coordinate(0, 0)), "heavy_assault_drone")
    scout = _tagged(ScoutDrone(Coordinate(10, 0)), "scout_drone")

    system.update(1.0, [leader, scout])

    assert scout.group_leader is None, "разведчик — SOLO_TYPES, не должен входить в группы"


# --------------------------------------------------------------- Map.update()

def test_map_moves_follower_towards_leader_instead_of_own_path():
    game_map = Map(width=4000, height=4000, group_formation=GroupFormationSystem(rng=_NeverFormRng()))
    leader = DroneWalker(Coordinate(500, 500))
    leader.speed = 0  # позиция лидера должна остаться предсказуемой в тесте
    leader.set_path([Coordinate(9999, 9999)])

    follower = DroneWalker(Coordinate(0, 0))
    follower.set_path([Coordinate(-9999, -9999)])  # маршрут в противоположную сторону
    follower.join_group(1, leader, Coordinate(20, 0))

    game_map.spawn_enemy(leader)
    game_map.spawn_enemy(follower)

    game_map.update(1.0)

    assert leader.position == Coordinate(500, 500)
    # Двигался к лидеру (вправо-вниз), а не по своему пути (влево-вверх)
    assert follower.position.x > 0
    assert follower.position.y > 0


def test_group_disbands_when_leader_dies():
    game_map = Map(width=4000, height=4000, group_formation=GroupFormationSystem(rng=_NeverFormRng()))
    leader = DroneWalker(Coordinate(500, 500))
    leader.health = 0
    leader.set_path([Coordinate(9999, 9999)])

    follower = DroneWalker(Coordinate(0, 0))
    follower.set_path([Coordinate(1000, 0)])
    follower.join_group(1, leader, Coordinate(20, 0))

    game_map.spawn_enemy(leader)
    game_map.spawn_enemy(follower)

    game_map.update(1.0)

    assert follower.group_leader is None
    assert follower.position.x == pytest.approx(50.0)  # снова по своему маршруту, speed=50


# --------------------------------------------- группа прикрывает лидера от обстрела

def test_shield_offset_biases_towards_tower_direction():
    game_map = Map(width=4000, height=4000)
    leader_pos = Coordinate(500, 500)
    tower_pos = Coordinate(500, 400)  # прямо "над" лидером
    offset = Coordinate(50, 0)  # исходный слот - справа от лидера

    shielded = game_map._shield_offset(offset, tower_pos, leader_pos)

    def _angle_diff(a, b):
        return abs((a - b + math.pi) % (2 * math.pi) - math.pi)

    original_angle = math.atan2(offset.y, offset.x)
    tower_angle = math.atan2(tower_pos.y - leader_pos.y, tower_pos.x - leader_pos.x)
    shielded_angle = math.atan2(shielded.y, shielded.x)

    assert _angle_diff(shielded_angle, tower_angle) < _angle_diff(original_angle, tower_angle), \
        "смещённый угол слота должен быть заметно ближе к направлению на башню"
    assert math.hypot(shielded.x, shielded.y) == pytest.approx(math.hypot(offset.x, offset.y)), \
        "расстояние до лидера должно сохраняться - меняется только угол"


def test_combatant_follower_shields_leader_from_threatening_tower():
    game_map = Map(width=4000, height=4000, group_formation=GroupFormationSystem(rng=_NeverFormRng()))
    tower = LaserTurret(Coordinate(500, 300))  # range_radius=120 по умолчанию
    game_map.modules.append(tower)

    leader = HeavyAssaultDrone(Coordinate(500, 380))  # в 80 юнитах от башни - накрыт
    leader.speed = 0
    leader.is_group_leader = True
    leader.group_id = 7
    leader.set_path([Coordinate(9999, 9999)])

    follower = DroneWalker(Coordinate(550, 380))
    follower.join_group(7, leader, Coordinate(50, 0))
    follower.set_path([Coordinate(-9999, -9999)])

    game_map.spawn_enemy(leader)
    game_map.spawn_enemy(follower)

    plain_slot_distance_to_tower = Coordinate(550, 380).distance_to(tower.position)
    game_map.update(1.0)

    assert follower.position.distance_to(tower.position) < plain_slot_distance_to_tower, \
        "боевой эскорт должен смещаться в сторону угрожающей лидеру башни, прикрывая его собой"


def test_noncombatant_follower_ignores_shielding_and_keeps_normal_slot():
    """Медик не должен подставляться под огонь вместе с боевым эскортом -
    is_combatant()=False полностью отключает смещение слота построения."""
    game_map = Map(width=4000, height=4000, group_formation=GroupFormationSystem(rng=_NeverFormRng()))
    tower = LaserTurret(Coordinate(500, 300))
    game_map.modules.append(tower)

    leader = HeavyAssaultDrone(Coordinate(500, 380))
    leader.speed = 0
    leader.is_group_leader = True
    leader.group_id = 7
    leader.set_path([Coordinate(9999, 9999)])

    medic = MedicDrone(Coordinate(550, 380))
    medic.join_group(7, leader, Coordinate(50, 0))
    medic.set_path([Coordinate(-9999, -9999)])

    game_map.spawn_enemy(leader)
    game_map.spawn_enemy(medic)

    game_map.update(1.0)

    assert medic.position == Coordinate(550, 380), \
        "не боевой юнит сохраняет обычный слот построения, даже когда лидер под обстрелом"


def test_group_disbands_when_leader_has_reached_end_of_path():
    game_map = Map(width=4000, height=4000, group_formation=GroupFormationSystem(rng=_NeverFormRng()))
    leader = DroneWalker(Coordinate(500, 500))
    leader.set_path([Coordinate(500, 500)])
    leader.path_index = 1  # уже дошёл до конца маршрута (убран бы из карты)

    follower = DroneWalker(Coordinate(0, 0))
    follower.set_path([Coordinate(1000, 0)])
    follower.join_group(1, leader, Coordinate(20, 0))

    game_map.spawn_enemy(leader)
    game_map.spawn_enemy(follower)

    game_map.update(1.0)

    assert follower.group_leader is None
    assert follower.position.x == pytest.approx(50.0)
