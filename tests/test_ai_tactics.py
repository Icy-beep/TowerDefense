"""Улучшения AI: приоритет боевых башен над инфраструктурой при выборе цели
группой, ярость GiantRoach на низком здоровье, пробивное поведение BioTitan
(breaks_through - не патрулирует и не отступает лечиться)."""
from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import BioTitan, GiantRoach
from src.entities.power_pylon import PowerPylon
from src.entities.turrets import LaserTurret
from src.enums import Faction


def _tagged(enemy, type_name):
    enemy.type_name = type_name
    return enemy


def test_group_leader_prefers_combat_tower_over_closer_infrastructure():
    game_map = Map(width=4000, height=4000)
    pylon = PowerPylon(Coordinate(15, 0))
    laser = LaserTurret(Coordinate(25, 0))
    game_map.modules += [pylon, laser]
    game_map.faction_intel[Faction.FAUNA].reveal(pylon)
    game_map.faction_intel[Faction.FAUNA].reveal(laser)

    leader = _tagged(GiantRoach(Coordinate(0, 0)), "giant_roach")
    leader.is_group_leader = True

    game_map._update_group_targets([leader])

    assert leader.target_tower is laser, "пилон безобиден и не должен отвлекать группу от реальной угрозы"


def test_group_leader_still_targets_infrastructure_if_it_is_the_only_option():
    game_map = Map(width=4000, height=4000)
    pylon = PowerPylon(Coordinate(15, 0))
    game_map.modules.append(pylon)
    game_map.faction_intel[Faction.FAUNA].reveal(pylon)

    leader = _tagged(GiantRoach(Coordinate(0, 0)), "giant_roach")
    leader.is_group_leader = True

    game_map._update_group_targets([leader])

    assert leader.target_tower is pylon


def test_giant_roach_does_not_enrage_above_health_threshold():
    roach = GiantRoach(Coordinate(0, 0))
    base_speed = roach.speed

    roach.act(0.1)

    assert roach.is_enraged is False
    assert roach.speed == base_speed


def test_giant_roach_enrages_below_health_threshold():
    roach = GiantRoach(Coordinate(0, 0))
    base_speed = roach.speed
    base_damage = roach.ATTACK_DAMAGE_PER_SECOND
    roach.health = roach.max_health * (GiantRoach.ENRAGE_HEALTH_RATIO - 0.05)

    roach.act(0.1)

    assert roach.is_enraged is True
    assert roach.speed == base_speed * GiantRoach.ENRAGE_SPEED_MULTIPLIER
    assert roach.ATTACK_DAMAGE_PER_SECOND == base_damage * GiantRoach.ENRAGE_DAMAGE_MULTIPLIER


def test_giant_roach_enrage_does_not_revert_after_healing():
    roach = GiantRoach(Coordinate(0, 0))
    base_speed = roach.speed
    roach.health = roach.max_health * 0.1
    roach.act(0.1)

    roach.health = roach.max_health
    roach.act(0.1)

    assert roach.speed == base_speed * GiantRoach.ENRAGE_SPEED_MULTIPLIER, "ярость - разовый переход, не снимается"


def test_giant_roach_dead_does_not_enrage():
    roach = GiantRoach(Coordinate(0, 0))
    roach.health = 0

    roach.act(0.1)

    assert roach.is_enraged is False


def test_bio_titan_breaks_through_is_true_by_default():
    assert BioTitan(Coordinate(0, 0)).breaks_through() is True


def test_regular_enemy_does_not_break_through_by_default():
    assert GiantRoach(Coordinate(0, 0)).breaks_through() is False


def test_bio_titan_ignores_patrol_around_a_blocking_known_tower():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    blocking_tower = LaserTurret(Coordinate(1000, 2000))
    game_map.modules.append(blocking_tower)
    game_map.faction_intel[Faction.FAUNA].reveal(blocking_tower)

    titan = BioTitan(Coordinate(500, 2000))
    titan.set_path([Coordinate(2000, 2000)])
    start_x = titan.position.x

    game_map._advance_towards_base(titan, 1.0)

    assert titan.is_patrolling is False
    assert titan.position.x > start_x, "титан должен продолжить движение по маршруту, а не встать в патруль"


def test_regular_enemy_still_patrols_around_the_same_blocking_tower():
    """Контрольный случай: без breaks_through то же самое известное перекрытие
    переводит юнита в патруль, как и раньше - фикс не сломал обычное поведение."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    blocking_tower = LaserTurret(Coordinate(1000, 2000))
    game_map.modules.append(blocking_tower)
    game_map.faction_intel[Faction.FAUNA].reveal(blocking_tower)

    roach = GiantRoach(Coordinate(500, 2000))
    roach.set_path([Coordinate(2000, 2000)])

    game_map._advance_towards_base(roach, 1.0)

    assert roach.is_patrolling is True


def test_wounded_bio_titan_never_enters_retreat_heal_state():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    game_map.spawn_points_by_faction = {Faction.FAUNA: [Coordinate(0, 0)]}

    titan = BioTitan(Coordinate(1000, 1000))
    titan.health = titan.max_health * 0.1
    titan.is_group_leader = True
    titan.group_id = 1
    titan.set_path([Coordinate(2000, 2000)])
    game_map.spawn_enemy(titan)

    escort = GiantRoach(Coordinate(1010, 1000))
    escort.group_id = 1
    escort.group_leader = titan
    game_map.spawn_enemy(escort)

    for _ in range(5):
        game_map.update(0.5)

    assert titan.is_healing is False
