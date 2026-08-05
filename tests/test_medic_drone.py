"""Дрон-медик Corporation: не атакует, лечит союзников в группе, избегает башен вне группы."""
import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import MedicDrone, HeavyAssaultDrone, GiantRoach
from src.enums import ArmorType, Faction
from src.factories.enemy_factory import EnemyFactory
from src.core.game_session import GameSession



def test_medic_drone_cannot_attack_and_heals_allies():
    medic = MedicDrone(Coordinate(0, 0))

    assert medic.is_combatant() is False
    assert medic.heals_allies() is True
    assert medic.armor == ArmorType.ENERGY_SHIELDED
    assert medic.faction == Faction.CORPORATION


def test_medic_drone_avoids_danger_only_while_solo():
    medic = MedicDrone(Coordinate(0, 0))
    assert medic.avoids_danger() is True, "пока не в группе - избегает простреливаемых зон"

    leader = HeavyAssaultDrone(Coordinate(100, 100))
    leader.is_group_leader = True
    leader.group_id = 1
    medic.join_group(1, leader, Coordinate(0, 0))

    assert medic.avoids_danger() is False, "в группе - не должен пытаться убежать"


def test_medic_drone_registered_with_energy_shield_and_corporation_faction():
    factory = EnemyFactory()
    medic = factory.create("medic_drone", Coordinate(0, 0))

    assert medic is not None
    assert medic.armor == ArmorType.ENERGY_SHIELDED
    assert medic.faction == Faction.CORPORATION
    assert medic.type_name == "medic_drone"


def test_medic_drone_is_part_of_corporation_landing_roster():
    session = GameSession()
    session.setup_game()

    strategy = session.threat_strategies[Faction.CORPORATION]
    assert "medic_drone" in strategy.enemy_types



def test_solo_medic_moves_towards_nearest_ally_group_leader():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    leader = HeavyAssaultDrone(Coordinate(2500, 2000))
    leader.is_group_leader = True
    leader.group_id = 7
    leader.set_path([Coordinate(2500, 100)])
    game_map.spawn_enemy(leader)

    medic = MedicDrone(Coordinate(2000, 2000))
    medic.set_path([Coordinate(9999, 9999)])
    game_map.spawn_enemy(medic)

    initial_distance = medic.position.distance_to(leader.position)
    game_map.update(0.5)

    assert medic.position.distance_to(leader.position) < initial_distance


def test_solo_medic_joins_group_once_close_enough():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    leader = HeavyAssaultDrone(Coordinate(2020, 2000))
    leader.is_group_leader = True
    leader.group_id = 7
    leader.set_path([Coordinate(2500, 100)])
    game_map.spawn_enemy(leader)

    medic = MedicDrone(Coordinate(2000, 2000))
    medic.set_path([Coordinate(9999, 9999)])
    game_map.spawn_enemy(medic)

    game_map.update(0.1)

    assert medic.group_leader is leader
    assert medic.group_id == 7


def test_medic_ignores_groups_of_the_opposing_faction():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    fauna_leader = GiantRoach(Coordinate(2010, 2000))
    fauna_leader.is_group_leader = True
    fauna_leader.group_id = 3
    fauna_leader.set_path([Coordinate(2500, 100)])
    game_map.spawn_enemy(fauna_leader)

    medic = MedicDrone(Coordinate(2000, 2000))
    medic.set_path([Coordinate(9999, 9999)])
    game_map.spawn_enemy(medic)

    game_map.update(0.1)

    assert medic.group_leader is None, "медик не должен присоединяться к группе чужой фракции"


def test_solo_medic_falls_back_to_advancing_to_base_when_no_group_exists():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    medic = MedicDrone(Coordinate(500, 500))
    medic.set_path([Coordinate(600, 500)])
    game_map.spawn_enemy(medic)

    game_map.update(0.1)

    assert medic.position.x > 500, "без союзной группы медик должен идти к базе как обычно"



def test_grouped_medic_heals_wounded_group_members():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    leader = HeavyAssaultDrone(Coordinate(2000, 2000))
    leader.is_group_leader = True
    leader.group_id = 7
    leader.health = 90
    leader.set_path([Coordinate(2500, 100)])
    game_map.spawn_enemy(leader)

    medic = MedicDrone(Coordinate(2010, 2000))
    medic.join_group(7, leader, Coordinate(10, 0))
    medic.set_path([Coordinate(9999, 9999)])
    game_map.spawn_enemy(medic)

    before = leader.health
    game_map.update(1.0)

    assert leader.health > before


def test_medic_does_not_heal_members_outside_its_radius():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    leader = HeavyAssaultDrone(Coordinate(2000, 2000))
    leader.is_group_leader = True
    leader.group_id = 7
    leader.health = 90
    leader.set_path([Coordinate(2500, 100)])
    game_map.spawn_enemy(leader)

    far_medic = MedicDrone(Coordinate(2000, 2000 + Map.HEALER_HEAL_RADIUS + 50))
    far_medic.join_group(7, leader, Coordinate(0, Map.HEALER_HEAL_RADIUS + 50))
    far_medic.set_path([Coordinate(9999, 9999)])
    game_map.spawn_enemy(far_medic)

    before = leader.health
    game_map.update(1.0)

    assert leader.health == before


def test_medic_heals_itself_too():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    leader = HeavyAssaultDrone(Coordinate(2000, 2000))
    leader.is_group_leader = True
    leader.group_id = 7
    leader.set_path([Coordinate(2500, 100)])
    game_map.spawn_enemy(leader)

    medic = MedicDrone(Coordinate(2010, 2000))
    medic.health = 40
    medic.join_group(7, leader, Coordinate(10, 0))
    medic.set_path([Coordinate(9999, 9999)])
    game_map.spawn_enemy(medic)

    before = medic.health
    game_map.update(1.0)

    assert medic.health > before



def test_medic_never_attacks_even_with_enemy_in_range():
    game_map = Map(width=4000, height=4000)

    medic = MedicDrone(Coordinate(2000, 2000))
    medic.set_path([Coordinate(9999, 9999)])
    game_map.spawn_enemy(medic)

    target = GiantRoach(Coordinate(2010, 2000))
    target.set_path([Coordinate(9999, 9999)])
    game_map.spawn_enemy(target)

    before = target.health
    for _ in range(10):
        game_map.update(0.1)

    assert target.health == before, "медик не должен наносить урон, даже если враг рядом"


def test_medic_never_hunts_towers_even_as_part_of_a_group():
    """is_combatant()=False должен блокировать охоту на башню лидера именно для медика."""
    from src.entities.turrets import LaserTurret

    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(2010, 2000))
    game_map.modules.append(tower)

    leader = HeavyAssaultDrone(Coordinate(0, 0))
    leader.is_group_leader = True
    leader.group_id = 7
    leader.target_tower = tower
    leader.set_path([Coordinate(0, 0)])
    game_map.spawn_enemy(leader)

    medic = MedicDrone(Coordinate(2000, 2000))
    medic.join_group(7, leader, Coordinate(0, 0))
    medic.set_path([Coordinate(9999, 9999)])
    game_map.spawn_enemy(medic)

    before = tower.health
    game_map.update(0.1)

    assert tower.health == before, "медик не должен атаковать башню, даже если её преследует его лидер"
