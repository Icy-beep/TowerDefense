"""SniperDrone: дрон Corporation с увеличенным ATTACK_RANGE, бьющий башню, не заходя в её
собственный радиус - контрится прокачкой башни или миномётом (см. src/entities/enemies.py)."""
from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import SniperDrone
from src.enums import ArmorType, Faction
from src.factories.enemy_factory import EnemyFactory
from src.factories.tower_factory import TowerFactory


def test_sniper_drone_defaults():
    enemy = SniperDrone(Coordinate(0, 0))

    assert enemy.armor == ArmorType.LIGHT
    assert enemy.faction == Faction.CORPORATION
    assert enemy.max_health > 0
    assert enemy.health == enemy.max_health


def test_enemy_factory_creates_sniper_drone_with_config_values():
    factory = EnemyFactory()
    sniper = factory.create("sniper_drone", Coordinate(0, 0))

    assert sniper is not None
    assert sniper.type_name == "sniper_drone"
    assert sniper.armor == ArmorType.LIGHT
    assert sniper.faction == Faction.CORPORATION


def test_sniper_drone_is_included_in_available_types():
    factory = EnemyFactory()
    assert "sniper_drone" in factory.available_types()


def test_sniper_range_exceeds_base_level_laser_and_bullet_towers():
    """Основная фишка: должен доставать турели первого уровня (реальные радиусы из
    data/config/towers.json - через TowerFactory, а не "голые" дефолты классов), оставаясь
    вне их досягаемости."""
    factory = TowerFactory()
    sniper = SniperDrone(Coordinate(0, 0))
    laser = factory.create("laser", Coordinate(0, 0))
    bullet = factory.create("bullet", Coordinate(0, 0))

    assert sniper.ATTACK_RANGE > laser.range_radius
    assert sniper.ATTACK_RANGE > bullet.range_radius


def test_sniper_range_loses_to_mortar_and_to_upgraded_towers():
    """Контрится: миномёт сразу вне досягаемости снайпера, а лазер/пулемётная после
    апгрейда тоже дотягиваются дальше него - у игрока должен быть реальный ответ."""
    factory = TowerFactory()
    sniper = SniperDrone(Coordinate(0, 0))
    mortar = factory.create("mortar", Coordinate(0, 0))
    assert sniper.ATTACK_RANGE < mortar.range_radius

    laser = factory.create("laser", Coordinate(0, 0))
    laser.upgrade()
    assert sniper.ATTACK_RANGE < laser.range_radius, "апгрейженный лазер должен доставать дальше снайпера"


def test_sniper_drone_dodges_projectiles():
    """Лёгкая броня - должен уклоняться от снарядов, как и другие лёгкие дроны."""
    assert SniperDrone(Coordinate(0, 0)).dodges_projectiles() is True


def test_sniper_drone_stages_before_attacking_like_other_combat_types():
    assert SniperDrone(Coordinate(0, 0)).stages_before_attacking() is True


def test_corporation_hunt_radius_leaves_room_for_the_sniper_to_engage_from_safety():
    """Регрессия: TOWER_HUNT_RADIUS раньше был меньше боевого радиуса турелей первого
    уровня, так что отряд узнавал башню целью, уже стоя внутри её обстрела - снайпер
    почти никогда не успевал открыть огонь снаружи. Радиус охоты должен быть достаточно
    большим, чтобы у него был реальный шанс начать стрелять ещё вне радиуса башни."""
    game_map = Map(width=4000, height=4000)
    laser = TowerFactory().create("laser", Coordinate(0, 0))

    assert game_map._hunt_radius_for(Faction.CORPORATION) > laser.range_radius
    assert game_map._hunt_radius_for(Faction.CORPORATION) < SniperDrone(Coordinate(0, 0)).ATTACK_RANGE + 50


def test_sniper_drone_damages_tower_from_outside_its_range_without_taking_return_fire():
    """Интеграционная проверка всей боевой цепочки: снайпер стоит вне радиуса башни,
    но в своём ATTACK_RANGE - должен наносить урон, оставаясь невредимым."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    tower = TowerFactory().create("laser", Coordinate(2000, 1000))  # range_radius 400
    game_map.modules.append(tower)

    sniper = SniperDrone(Coordinate(2000, 1000 + tower.range_radius + 20))  # 420 от башни: вне её 400, внутри своих 430
    sniper.type_name = "sniper_drone"
    sniper.is_group_leader = True
    sniper.target_tower = tower
    sniper.set_path([Coordinate(2000, 2000)])
    game_map.spawn_enemy(sniper)

    for _ in range(20):
        game_map.update(0.1)

    assert tower.health < tower.max_health, "снайпер должен наносить урон башне издалека"
    assert sniper.health == sniper.max_health, "башня не должна доставать снайпера - он вне её радиуса"


def test_sniper_drone_walks_into_range_of_an_upgraded_tower_and_takes_fire_back():
    """Контрольный случай: если башню прокачали так, что её радиус превысил ATTACK_RANGE
    снайпера, он всё равно идёт добивать дистанцию и получает сдачи по пути."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    tower = TowerFactory().create("laser", Coordinate(2000, 1000))
    tower.upgrade()  # range_radius 480 > sniper ATTACK_RANGE 430
    game_map.modules.append(tower)

    sniper = SniperDrone(Coordinate(2000, 1000 + tower.range_radius + 20))
    sniper.type_name = "sniper_drone"
    sniper.is_group_leader = True
    sniper.target_tower = tower
    sniper.set_path([Coordinate(2000, 2000)])
    game_map.spawn_enemy(sniper)

    for _ in range(30):
        game_map.update(0.1)

    assert sniper.health < sniper.max_health, "в зоне апгрейженной башни снайпер должен получать урон"
