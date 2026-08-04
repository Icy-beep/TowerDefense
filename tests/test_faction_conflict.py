"""Бой между Corporation и Fauna при встрече в радиусе обзора, приоритет над охотой на башню."""
import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import DroneWalker, GiantRoach, ScoutDrone
from src.entities.turrets import LaserTurret
from src.enums import Faction
from src.systems.group_formation import GroupFormationSystem


def _tagged(enemy, type_name):
    enemy.type_name = type_name
    return enemy


class _NeverFormRng:
    """Формирование новых групп в этих тестах не нужно — состав задаётся вручную."""
    def random(self):
        return 1.0

    def choice(self, seq):
        return seq[0]



def test_finds_nearest_opposing_enemy_in_vision_range():
    game_map = Map(width=4000, height=4000)
    corp = _tagged(DroneWalker(Coordinate(0, 0)), "drone_walker")
    fauna = _tagged(GiantRoach(Coordinate(30, 0)), "giant_roach")
    game_map.enemies = [corp, fauna]

    assert game_map._find_enemy_combat_target(corp) is fauna
    assert game_map._find_enemy_combat_target(fauna) is corp


def test_ignores_same_faction_enemies():
    game_map = Map(width=4000, height=4000)
    corp_a = _tagged(DroneWalker(Coordinate(0, 0)), "drone_walker")
    corp_b = _tagged(DroneWalker(Coordinate(10, 0)), "drone_walker")
    game_map.enemies = [corp_a, corp_b]

    assert game_map._find_enemy_combat_target(corp_a) is None


def test_ignores_opposing_enemy_outside_combat_detection_range():
    game_map = Map(width=4000, height=4000)
    corp = _tagged(DroneWalker(Coordinate(0, 0)), "drone_walker")
    fauna = _tagged(GiantRoach(Coordinate(Map.ENEMY_COMBAT_DETECTION_RADIUS + 50, 0)), "giant_roach")
    game_map.enemies = [corp, fauna]

    assert game_map._find_enemy_combat_target(corp) is None


def test_ignores_dead_opposing_enemy():
    game_map = Map(width=4000, height=4000)
    corp = _tagged(DroneWalker(Coordinate(0, 0)), "drone_walker")
    fauna = _tagged(GiantRoach(Coordinate(20, 0)), "giant_roach")
    fauna.health = 0
    game_map.enemies = [corp, fauna]

    assert game_map._find_enemy_combat_target(corp) is None


def test_picks_the_closest_of_several_opposing_enemies():
    game_map = Map(width=4000, height=4000)
    corp = _tagged(DroneWalker(Coordinate(0, 0)), "drone_walker")
    far_fauna = _tagged(GiantRoach(Coordinate(100, 0)), "giant_roach")
    near_fauna = _tagged(GiantRoach(Coordinate(30, 0)), "giant_roach")

    game_map.enemies = [corp, far_fauna, near_fauna]
    assert game_map._find_enemy_combat_target(corp) is near_fauna



def test_opposing_enemies_in_attack_range_damage_each_other():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(4000, 4000)
    corp = _tagged(DroneWalker(Coordinate(0, 0)), "drone_walker")
    corp.set_path([Coordinate(4000, 4000)])
    fauna = _tagged(GiantRoach(Coordinate(20, 0)), "giant_roach")
    fauna.set_path([Coordinate(4000, 4000)])
    game_map.spawn_enemy(corp)
    game_map.spawn_enemy(fauna)

    game_map.update(1.0)

    assert corp.health < corp.max_health, "враг Fauna должен наносить урон врагу Corporation"
    assert fauna.health < fauna.max_health, "враг Corporation должен наносить урон врагу Fauna"


def test_enemies_fighting_do_not_advance_towards_base():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(4000, 4000)
    corp = _tagged(DroneWalker(Coordinate(0, 0)), "drone_walker")
    corp.set_path([Coordinate(4000, 4000)])
    fauna = _tagged(GiantRoach(Coordinate(20, 0)), "giant_roach")
    fauna.set_path([Coordinate(4000, 4000)])
    game_map.spawn_enemy(corp)
    game_map.spawn_enemy(fauna)

    game_map.update(1.0)

    assert corp.position == Coordinate(0, 0), "во время боя враг не должен продолжать путь к базе"


def test_same_faction_enemies_ignore_each_other_and_walk_to_base():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(1000, 0)
    corp_a = _tagged(DroneWalker(Coordinate(0, 0)), "drone_walker")
    corp_a.set_path([Coordinate(1000, 0)])
    corp_b = _tagged(DroneWalker(Coordinate(20, 0)), "drone_walker")
    corp_b.set_path([Coordinate(1000, 0)])
    game_map.spawn_enemy(corp_a)
    game_map.spawn_enemy(corp_b)

    game_map.update(1.0)

    assert corp_a.health == corp_a.max_health
    assert corp_b.health == corp_b.max_health
    assert corp_a.position.x > 0, "своих не трогаем, продолжаем идти к базе"


def test_enemy_moves_towards_distant_opposing_enemy_within_vision():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(-4000, 0)
    corp = _tagged(DroneWalker(Coordinate(0, 0)), "drone_walker")
    corp.set_path([Coordinate(-4000, 0)])
    fauna = _tagged(GiantRoach(Coordinate(100, 0)), "giant_roach")
    fauna.set_path([Coordinate(-4000, 0)])
    game_map.spawn_enemy(corp)
    game_map.spawn_enemy(fauna)

    game_map.update(1.0)

    assert corp.health == corp.max_health, "далеко от цели — урона ещё быть не должно"
    assert corp.position.x > 0, "должен идти навстречу врагу, а не по своему пути к базе"


def test_combat_takes_priority_over_tower_hunting():
    game_map = Map(width=4000, height=4000, group_formation=GroupFormationSystem(rng=_NeverFormRng()))
    game_map.base_position = Coordinate(4000, 4000)
    tower = LaserTurret(Coordinate(500, 0))
    tower.cooldown_timer = 999
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.FAUNA].reveal(tower)

    leader = _tagged(GiantRoach(Coordinate(0, 0)), "giant_roach")
    leader.is_group_leader = True
    leader.target_tower = tower
    leader.set_path([Coordinate(4000, 4000)])
    game_map.spawn_enemy(leader)

    corp = _tagged(DroneWalker(Coordinate(20, 0)), "drone_walker")
    corp.set_path([Coordinate(4000, 4000)])
    game_map.spawn_enemy(corp)

    game_map.update(1.0)

    assert tower.health == tower.max_health, "бой с врагом важнее охоты на башню"
    assert corp.health < corp.max_health, "должен драться с ближайшим врагом вместо похода к башне"


def test_enemy_killed_in_combat_is_removed_from_map():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(4000, 4000)
    corp = _tagged(DroneWalker(Coordinate(0, 0)), "drone_walker")
    corp.set_path([Coordinate(4000, 4000)])
    fauna = _tagged(GiantRoach(Coordinate(20, 0)), "giant_roach")
    fauna.health = 1
    fauna.set_path([Coordinate(4000, 4000)])
    game_map.spawn_enemy(corp)
    game_map.spawn_enemy(fauna)

    _, killed = game_map.update(1.0)

    assert fauna in killed
    assert fauna not in game_map.enemies


def test_fighting_does_not_falsely_count_as_reached_base():
    """У атакующего path_index уже указывает за конец маршрута (например,
    после долгого боя), но пока бой не завершён — это не "дошёл до базы"."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(0, 0)
    corp = _tagged(DroneWalker(Coordinate(0, 0)), "drone_walker")
    corp.set_path([Coordinate(0, 0)])
    corp.path_index = 1
    fauna = _tagged(GiantRoach(Coordinate(20, 0)), "giant_roach")
    fauna.set_path([Coordinate(4000, 4000)])
    game_map.spawn_enemy(corp)
    game_map.spawn_enemy(fauna)

    reached_base, _ = game_map.update(1.0)

    assert corp not in reached_base, "враг дерётся, а не дошёл до базы"
