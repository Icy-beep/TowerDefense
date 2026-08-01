"""Агрессивный групповой профиль Fauna: любой юнит может быть лидером, больший радиус охоты на башни."""
from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import BioTitan, DroneWalker, GiantRoach, ScoutDrone
from src.entities.turrets import LaserTurret
from src.enums import Faction
from src.systems.group_formation import GroupFormationSystem


def _tagged(enemy, type_name):
    enemy.type_name = type_name
    return enemy


class _AlwaysFormRng:
    def random(self):
        return 0.0

    def choice(self, seq):
        return seq[0]


class _NeverFormRng:
    def random(self):
        return 1.0

    def choice(self, seq):
        return seq[0]



def test_giant_roach_can_lead_a_fauna_group():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    roach = _tagged(GiantRoach(Coordinate(0, 0)), "giant_roach")
    ally = _tagged(GiantRoach(Coordinate(50, 0)), "giant_roach")

    system.update(1.0, [roach, ally])

    assert roach.is_group_leader is True
    assert ally.group_leader is roach


def test_bio_titan_can_lead_a_fauna_group():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    titan = _tagged(BioTitan(Coordinate(0, 0)), "bio_titan")
    ally = _tagged(GiantRoach(Coordinate(50, 0)), "giant_roach")

    system.update(1.0, [titan, ally])

    assert titan.is_group_leader is True
    assert ally.group_leader is titan


def test_giant_roach_cannot_lead_a_corporation_group():
    """leader_types по фракциям не смешивается — таракан не входит в
    профиль Corporation, даже если бы вдруг оказался в их рядах."""
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    roach = _tagged(GiantRoach(Coordinate(0, 0)), "giant_roach")
    roach.faction = Faction.CORPORATION
    ally = _tagged(DroneWalker(Coordinate(50, 0)), "drone_walker")
    ally.faction = Faction.CORPORATION

    system.update(1.0, [roach, ally])

    assert roach.is_group_leader is False
    assert ally.group_leader is None


def test_scout_drone_cannot_lead_a_fauna_group():
    """Обратная проверка: если разведчик корпорации почему-то оказался
    во фракции Fauna, он всё равно не входит в её leader_types."""
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    scout = _tagged(ScoutDrone(Coordinate(0, 0)), "scout_drone")
    scout.faction = Faction.FAUNA
    ally = _tagged(GiantRoach(Coordinate(50, 0)), "giant_roach")

    system.update(1.0, [scout, ally])

    assert scout.is_group_leader is False
    assert ally.group_leader is None



def test_fauna_recruits_from_a_wider_radius_than_corporation_default():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    distance = GroupFormationSystem.GROUP_RADIUS + 50
    assert distance <= system._profile_for(Faction.FAUNA)["group_radius"]

    roach = _tagged(GiantRoach(Coordinate(0, 0)), "giant_roach")
    far_ally = _tagged(GiantRoach(Coordinate(distance, 0)), "giant_roach")

    system.update(1.0, [roach, far_ally])

    assert far_ally.group_leader is roach, "у Fauna шире радиус сбора, чем дефолт Corporation"


def test_fauna_escort_cap_is_larger_than_corporation_default():
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    roach = _tagged(GiantRoach(Coordinate(0, 0)), "giant_roach")
    allies = [_tagged(GiantRoach(Coordinate(10 * i, 0)), "fauna_grunt") for i in range(1, 8)]

    for _ in range(10):
        system.update(1.0, [roach] + allies)

    escorted = sum(1 for a in allies if a.group_leader is roach)
    assert escorted == GroupFormationSystem.FACTION_OVERRIDES[Faction.FAUNA]["max_escort_size"]
    assert escorted > GroupFormationSystem.MAX_ESCORT_SIZE, "мобы Fauna крупнее эскортов Corporation"


def test_fauna_form_chance_is_higher_than_corporation_default():
    fauna_chance = GroupFormationSystem.FACTION_OVERRIDES[Faction.FAUNA]["form_chance_per_second"]
    assert fauna_chance > GroupFormationSystem.FORM_CHANCE_PER_SECOND


def test_corporation_profile_is_unaffected_by_fauna_overrides():
    """Существующее поведение Corporation (см. test_group_formation.py)
    не должно измениться от добавления профиля Fauna."""
    system = GroupFormationSystem(rng=_AlwaysFormRng())
    profile = system._profile_for(Faction.CORPORATION)

    assert profile["leader_types"] == GroupFormationSystem.LEADER_TYPES
    assert profile["form_chance_per_second"] == GroupFormationSystem.FORM_CHANCE_PER_SECOND
    assert profile["group_radius"] == GroupFormationSystem.GROUP_RADIUS
    assert profile["max_escort_size"] == GroupFormationSystem.MAX_ESCORT_SIZE
    assert profile["formation_radius"] == GroupFormationSystem.FORMATION_RADIUS



def test_fauna_hunt_radius_is_larger_than_corporation():
    game_map = Map(width=4000, height=4000)
    assert game_map._hunt_radius_for(Faction.FAUNA) > game_map._hunt_radius_for(Faction.CORPORATION)
    assert game_map._hunt_radius_for(Faction.CORPORATION) == Map.TOWER_HUNT_RADIUS


def test_fauna_group_leader_targets_tower_beyond_corporation_hunt_radius():
    """Башня вне TOWER_HUNT_RADIUS, но в пределах расширенного радиуса охоты Fauna."""
    distance = Map.TOWER_HUNT_RADIUS + 50
    assert distance <= Map.TOWER_HUNT_RADIUS_OVERRIDES[Faction.FAUNA]

    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(distance, 0))
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.FAUNA].reveal(tower)

    leader = _tagged(GiantRoach(Coordinate(0, 0)), "giant_roach")
    leader.is_group_leader = True

    game_map._update_group_targets([leader])

    assert leader.target_tower is tower, "Fauna агрессивнее — должна замечать башни дальше Corporation"


def test_corporation_group_leader_ignores_tower_beyond_its_own_hunt_radius():
    """Контрольный случай: то же расстояние, но фракция Corporation — её
    радиус охоты меньше, цель не назначается."""
    distance = Map.TOWER_HUNT_RADIUS + 50

    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(distance, 0))
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    leader = _tagged(ScoutDrone(Coordinate(0, 0)), "scout_drone")
    leader.is_group_leader = True

    game_map._update_group_targets([leader])

    assert leader.target_tower is None



def test_fauna_mob_ignores_path_to_base_and_attacks_nearest_tower():
    """Моб фауны сносит башню на пути к базе вместо того, чтобы идти дальше."""
    game_map = Map(width=4000, height=4000, group_formation=GroupFormationSystem(rng=_NeverFormRng()))
    game_map.base_position = Coordinate(4000, 4000)
    tower = LaserTurret(Coordinate(20, 0))
    tower.cooldown_timer = 999
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.FAUNA].reveal(tower)

    leader = _tagged(GiantRoach(Coordinate(0, 0)), "giant_roach")
    leader.is_group_leader = True
    leader.target_tower = tower
    leader.set_path([Coordinate(4000, 4000)])
    game_map.spawn_enemy(leader)

    game_map.update(1.0)

    assert tower.health < tower.max_health, "моб фауны должен атаковать башню, а не игнорировать её"
    assert leader.position == Coordinate(0, 0), "во время атаки не продолжает путь к базе"
