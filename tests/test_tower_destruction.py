"""Разрушаемые башни: DefenseModule.health/take_damage/is_destroyed давно
существовали, но не были задействованы (ни один враг не атаковал башни).
Теперь ТОЛЬКО сформированные эскорты (лидер + хотя бы один ведомый, см.
src/systems/group_formation.py) могут целенаправленно переключиться с
похода к базе на снос известной им башни в радиусе Map.TOWER_HUNT_RADIUS
(см. Map._update_group_targets/HostileEntity.group_target_tower). Одиночки
башни по-прежнему не трогают. После уничтожения башни группа как ни в чём
не бывало продолжает путь к базе."""
import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import DroneWalker, ScoutDrone
from src.entities.turrets import LaserTurret
from src.enums import Faction
from src.systems.group_formation import GroupFormationSystem


def _tagged(enemy, type_name):
    enemy.type_name = type_name
    return enemy


class _NeverFormRng:
    """Формирование новых групп внутри теста не нужно — состав группы
    выставляется руками через join_group, чтобы сценарий был предсказуем."""
    def random(self):
        return 1.0

    def choice(self, seq):
        return seq[0]


# --------------------------------------------------- _update_group_targets

def test_solo_enemy_never_gets_a_tower_target():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(0, 0))
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    solo = _tagged(ScoutDrone(Coordinate(10, 0)), "scout_drone")  # рядом, но без группы
    game_map._update_group_targets([solo])

    assert solo.group_target_tower() is None


def test_group_leader_targets_nearest_known_tower_within_hunt_radius():
    game_map = Map(width=4000, height=4000)
    near_tower = LaserTurret(Coordinate(100, 0))
    far_tower = LaserTurret(Coordinate(3000, 3000))
    game_map.modules.extend([near_tower, far_tower])
    game_map.faction_intel[Faction.CORPORATION].reveal(near_tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(far_tower)

    leader = _tagged(ScoutDrone(Coordinate(0, 0)), "scout_drone")
    leader.is_group_leader = True
    follower = _tagged(DroneWalker(Coordinate(0, 10)), "drone_walker")
    follower.join_group(1, leader, Coordinate(0, 10))

    game_map._update_group_targets([leader, follower])

    assert leader.target_tower is near_tower
    assert follower.group_target_tower() is near_tower, "ведомый разделяет цель лидера"


def test_group_leader_ignores_towers_outside_hunt_radius():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(Map.TOWER_HUNT_RADIUS + 50, 0))
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    leader = _tagged(ScoutDrone(Coordinate(0, 0)), "scout_drone")
    leader.is_group_leader = True

    game_map._update_group_targets([leader])

    assert leader.target_tower is None


def test_group_leader_ignores_towers_unknown_to_its_faction():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(50, 0))  # не разведана
    game_map.modules.append(tower)

    leader = _tagged(ScoutDrone(Coordinate(0, 0)), "scout_drone")
    leader.is_group_leader = True

    game_map._update_group_targets([leader])

    assert leader.target_tower is None


def test_leader_keeps_current_target_instead_of_switching_to_a_closer_one():
    game_map = Map(width=4000, height=4000)
    original_target = LaserTurret(Coordinate(100, 0))
    closer_tower = LaserTurret(Coordinate(20, 0))
    game_map.modules.extend([original_target, closer_tower])
    game_map.faction_intel[Faction.CORPORATION].reveal(original_target)
    game_map.faction_intel[Faction.CORPORATION].reveal(closer_tower)

    leader = _tagged(ScoutDrone(Coordinate(0, 0)), "scout_drone")
    leader.is_group_leader = True
    leader.target_tower = original_target

    game_map._update_group_targets([leader])

    assert leader.target_tower is original_target, "не должен бросать текущую цель ради более близкой"


def test_target_is_dropped_once_destroyed_and_replaced_only_if_new_candidate_exists():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(50, 0))
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    leader = _tagged(DroneWalker(Coordinate(0, 0)), "scout_drone")
    leader.is_group_leader = True
    leader.target_tower = tower
    tower.health = 0  # уничтожена

    game_map._update_group_targets([leader])

    assert leader.target_tower is None


# ------------------------------------------------------------------- Map.update()

def test_grouped_enemy_attacks_tower_in_range_instead_of_moving_to_base():
    game_map = Map(width=4000, height=4000, group_formation=GroupFormationSystem(rng=_NeverFormRng()))
    game_map.base_position = Coordinate(4000, 4000)
    tower = LaserTurret(Coordinate(20, 0))
    tower.cooldown_timer = 999  # башня в этом тесте не должна отстреливаться
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    # DroneWalker, а не ScoutDrone: act() у DroneWalker ничего не делает,
    # тогда как у ScoutDrone есть случайный шанс уйти в "разведку" и
    # застыть — это сделало бы движение непредсказуемым в этом тесте.
    leader = _tagged(DroneWalker(Coordinate(0, 0)), "scout_drone")
    leader.is_group_leader = True
    leader.target_tower = tower
    leader.set_path([Coordinate(4000, 4000)])
    game_map.spawn_enemy(leader)

    game_map.update(1.0)

    assert tower.health < tower.max_health, "враг в радиусе атаки должен наносить урон башне"
    assert leader.position == Coordinate(0, 0), "во время атаки враг не должен продолжать движение"


def test_grouped_enemy_moves_towards_tower_when_out_of_attack_range():
    game_map = Map(width=4000, height=4000, group_formation=GroupFormationSystem(rng=_NeverFormRng()))
    game_map.base_position = Coordinate(4000, 4000)
    tower = LaserTurret(Coordinate(1000, 0))
    tower.cooldown_timer = 999
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    leader = _tagged(DroneWalker(Coordinate(0, 0)), "scout_drone")
    leader.is_group_leader = True
    leader.target_tower = tower
    leader.set_path([Coordinate(4000, 4000)])
    game_map.spawn_enemy(leader)

    game_map.update(1.0)

    assert tower.health == tower.max_health, "далеко от башни — урона быть не должно"
    assert leader.position.x > 0, "должен идти в сторону башни, а не к базе"


def test_tower_is_removed_from_map_once_destroyed():
    game_map = Map(width=4000, height=4000, group_formation=GroupFormationSystem(rng=_NeverFormRng()))
    game_map.base_position = Coordinate(4000, 4000)
    tower = LaserTurret(Coordinate(20, 0))
    tower.health = 1  # умрёт от одной атаки
    tower.cooldown_timer = 999
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    leader = _tagged(DroneWalker(Coordinate(0, 0)), "scout_drone")
    leader.is_group_leader = True
    leader.target_tower = tower
    leader.set_path([Coordinate(4000, 4000)])
    game_map.spawn_enemy(leader)

    game_map.update(1.0)
    assert tower.is_destroyed()

    game_map.update(1.0)  # уничтоженные башни убираются в начале следующего update()
    assert tower not in game_map.modules


def test_group_resumes_path_to_base_after_destroying_its_target():
    game_map = Map(width=4000, height=4000, group_formation=GroupFormationSystem(rng=_NeverFormRng()))
    game_map.base_position = Coordinate(1000, 0)
    tower = LaserTurret(Coordinate(20, 0))
    tower.health = 1
    tower.cooldown_timer = 999
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    leader = _tagged(DroneWalker(Coordinate(0, 0)), "scout_drone")
    leader.is_group_leader = True
    leader.target_tower = tower
    leader.set_path([Coordinate(1000, 0)])
    game_map.spawn_enemy(leader)

    game_map.update(1.0)  # уничтожает башню
    assert tower.is_destroyed()
    position_after_kill = Coordinate(leader.position.x, leader.position.y)

    game_map.update(1.0)  # цель протухла, должен продолжить путь

    assert leader.target_tower is None
    assert leader.position.x > position_after_kill.x, "должен снова двигаться по маршруту к базе"


def test_follower_resumes_following_leader_after_target_destroyed():
    game_map = Map(width=4000, height=4000, group_formation=GroupFormationSystem(rng=_NeverFormRng()))
    game_map.base_position = Coordinate(1000, 0)
    tower = LaserTurret(Coordinate(20, 0))
    tower.health = 1
    tower.cooldown_timer = 999
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    leader = _tagged(DroneWalker(Coordinate(0, 0)), "scout_drone")
    leader.is_group_leader = True
    leader.target_tower = tower
    leader.set_path([Coordinate(1000, 0)])

    follower = _tagged(DroneWalker(Coordinate(0, 30)), "drone_walker")
    follower.set_path([Coordinate(1000, 0)])
    follower.join_group(1, leader, Coordinate(0, 30))

    game_map.spawn_enemy(leader)
    game_map.spawn_enemy(follower)

    game_map.update(1.0)  # эскорт сносит башню
    assert tower.is_destroyed()

    for _ in range(5):
        game_map.update(1.0)

    assert follower.group_leader is leader, "остаётся в группе, просто снова следует за лидером"
    assert follower.position.x > 0, "должен снова двигаться в сторону базы вместе с лидером"
