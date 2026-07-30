"""Групповое поведение врагов (src/systems/group_formation.py).

Раньше волна из одной фракции всегда шла к базе поодиночке. Теперь
GroupFormationSystem время от времени случайно собирает эскорт вокруг
врага-лидера определённого типа (по умолчанию ScoutDrone) из ближайших
врагов ТОЙ ЖЕ фракции; пока лидер жив и не дошёл до базы, эскорт движется
не по своему маршруту, а рядом с лидером (см. Map.update())."""
import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import DroneWalker, GiantRoach, ScoutDrone
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


def test_scout_recruits_nearby_enemy_of_same_faction():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    scout = _tagged(ScoutDrone(Coordinate(0, 0)), "scout_drone")
    ally = _tagged(DroneWalker(Coordinate(50, 0)), "drone_walker")  # тоже Corporation

    system.update(1.0, [scout, ally])

    assert scout.is_group_leader is True
    assert ally.group_leader is scout
    assert ally.group_id == scout.group_id


def test_scout_does_not_recruit_enemy_of_different_faction():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    scout = _tagged(ScoutDrone(Coordinate(0, 0)), "scout_drone")  # Corporation
    roach = _tagged(GiantRoach(Coordinate(50, 0)), "giant_roach")  # Fauna

    system.update(1.0, [scout, roach])

    assert roach.group_leader is None, "фракции разные — вербовки быть не должно"


def test_scout_does_not_recruit_enemy_outside_group_radius():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    scout = _tagged(ScoutDrone(Coordinate(0, 0)), "scout_drone")
    far_ally = _tagged(DroneWalker(Coordinate(GroupFormationSystem.GROUP_RADIUS + 50, 0)), "drone_walker")

    system.update(1.0, [scout, far_ally])

    assert far_ally.group_leader is None


def test_form_chance_gates_recruitment():
    system = GroupFormationSystem(rng=_NeverFormRng())
    scout = _tagged(ScoutDrone(Coordinate(0, 0)), "scout_drone")
    ally = _tagged(DroneWalker(Coordinate(10, 0)), "drone_walker")

    system.update(1.0, [scout, ally])

    assert ally.group_leader is None


def test_escort_size_is_capped():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    scout = _tagged(ScoutDrone(Coordinate(0, 0)), "scout_drone")
    allies = [_tagged(DroneWalker(Coordinate(10 * i, 0)), "drone_walker") for i in range(1, 6)]

    for _ in range(10):
        system.update(1.0, [scout] + allies)

    escorted = sum(1 for a in allies if a.group_leader is scout)
    assert escorted == GroupFormationSystem.MAX_ESCORT_SIZE


def test_already_grouped_enemy_is_not_recruited_by_another_leader():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    scout_a = _tagged(ScoutDrone(Coordinate(0, 0)), "scout_drone")
    scout_b = _tagged(ScoutDrone(Coordinate(1000, 0)), "scout_drone")
    ally = _tagged(DroneWalker(Coordinate(10, 0)), "drone_walker")

    system.update(1.0, [scout_a, ally])
    assert ally.group_leader is scout_a

    ally.position = Coordinate(1010, 0)  # физически рядом со вторым лидером
    system.update(1.0, [scout_b, ally])

    assert ally.group_leader is scout_a, "уже состоящий в группе враг не должен переманиваться"


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
