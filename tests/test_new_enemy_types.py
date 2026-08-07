"""HeavyAssaultDrone и BioTitan: каждый контрит один конкретный тип урона башен."""
from src.core.coordinate import Coordinate
from src.entities.enemies import BioTitan, HeavyAssaultDrone
from src.enums import ArmorType, Faction
from src.factories.enemy_factory import EnemyFactory


def test_heavy_assault_drone_defaults():
    enemy = HeavyAssaultDrone(Coordinate(0, 0))

    assert enemy.armor == ArmorType.HEAVY
    assert enemy.faction == Faction.CORPORATION
    assert enemy.max_health > 0
    assert enemy.health == enemy.max_health


def test_bio_titan_defaults():
    enemy = BioTitan(Coordinate(0, 0))

    assert enemy.armor == ArmorType.ORGANIC
    assert enemy.faction == Faction.FAUNA
    assert enemy.max_health > 0


def test_bio_titan_is_the_tankiest_enemy_by_max_health():
    from src.entities.enemies import DroneWalker, GiantRoach, ScoutDrone

    all_health = [
        DroneWalker(Coordinate(0, 0)).max_health,
        GiantRoach(Coordinate(0, 0)).max_health,
        ScoutDrone(Coordinate(0, 0)).max_health,
        HeavyAssaultDrone(Coordinate(0, 0)).max_health,
    ]
    assert BioTitan(Coordinate(0, 0)).max_health > max(all_health)


def test_enemy_factory_creates_new_types_with_config_values():
    factory = EnemyFactory()

    heavy = factory.create("heavy_assault_drone", Coordinate(0, 0))
    titan = factory.create("bio_titan", Coordinate(0, 0))

    assert heavy is not None and heavy.armor == ArmorType.HEAVY and heavy.faction == Faction.CORPORATION
    assert titan is not None and titan.armor == ArmorType.ORGANIC and titan.faction == Faction.FAUNA
    assert heavy.type_name == "heavy_assault_drone"
    assert titan.type_name == "bio_titan"


def test_new_types_are_included_in_available_types_for_wave_generation():
    factory = EnemyFactory()
    available = factory.available_types()

    assert "heavy_assault_drone" in available
    assert "bio_titan" in available
