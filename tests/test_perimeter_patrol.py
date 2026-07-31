"""Настоящее патрулирование по периметру базы (src/core/map.py).

Раньше враг, которому известная башня перекрывала прямой путь к базе,
просто прокладывал маршрут в обход (мягкое избегание в path_to_base).
Теперь, если известная башня перекрывает текущее направление на базу,
враг вместо этого начинает кружить по периметру вокруг базы, ища угол,
не перекрытый ни одной известной башней — и только найдя такой разрыв,
возобновляет обычное движение к базе."""
import math

import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import DroneWalker, ScoutDrone
from src.entities.turrets import LaserTurret
from src.enums import Faction


def _map_with_base_and_known_tower(tower_position, enemy_position):
    """Карта с базой в (2000, 2000) и одной башней, уже известной Corporation."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    tower = LaserTurret(tower_position)  # range_radius=120 по умолчанию
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    enemy = DroneWalker(enemy_position)
    enemy.faction = Faction.CORPORATION
    return game_map, tower, enemy


def test_bearing_from_base_matches_expected_angle():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    assert game_map._bearing_from_base(Coordinate(2500, 2000)) == pytest.approx(0.0)
    assert game_map._bearing_from_base(Coordinate(2000, 2500)) == pytest.approx(math.pi / 2)
    assert game_map._bearing_from_base(Coordinate(1500, 2000)) == pytest.approx(math.pi)


def test_advance_towards_base_starts_patrolling_when_known_tower_blocks_bearing():
    game_map, tower, enemy = _map_with_base_and_known_tower(
        tower_position=Coordinate(2200, 2000),  # bearing 0 от базы
        enemy_position=Coordinate(2500, 2000),  # тот же bearing 0 — перекрыт
    )

    game_map._advance_towards_base(enemy, 0.1)

    assert enemy.is_patrolling is True


def test_advance_towards_base_goes_direct_when_gap_at_current_bearing():
    game_map, tower, enemy = _map_with_base_and_known_tower(
        tower_position=Coordinate(2200, 2000),  # башня перекрывает bearing 0
        enemy_position=Coordinate(1500, 2000),  # враг на bearing pi — разрыв тут есть
    )
    enemy.set_path([Coordinate(1600, 2000)])

    game_map._advance_towards_base(enemy, 0.1)

    assert enemy.is_patrolling is False, "на этом направлении башня не перекрывает обзор — патруль не нужен"


def test_patrol_movement_curves_around_base_instead_of_beelining():
    game_map, tower, enemy = _map_with_base_and_known_tower(
        tower_position=Coordinate(2200, 2000),
        enemy_position=Coordinate(2500, 2000),
    )

    game_map._advance_towards_base(enemy, 1.0)

    assert enemy.is_patrolling is True
    assert enemy.position.y != pytest.approx(2000.0), \
        "движение по патрулю должно уводить врага по дуге, а не по прямой к базе"


def test_patrol_eventually_finds_gap_and_resumes_normal_pathing():
    game_map, tower, enemy = _map_with_base_and_known_tower(
        tower_position=Coordinate(2200, 2000),
        enemy_position=Coordinate(2500, 2000),
    )

    found_gap = False
    for _ in range(400):  # угловая скорость 0.5 рад/с * dt суммарно покрывает весь круг
        game_map._advance_towards_base(enemy, 0.1)
        if not enemy.is_patrolling:
            found_gap = True
            break

    assert found_gap is True, "враг должен был найти разрыв в обороне и прекратить патрулирование"


def test_patrol_keeps_enemy_outside_tower_range_while_circling():
    # Башня далеко от базы (500 юнитов) — орбита патруля (150 + range_radius)
    # проходит значительно ближе к базе, чем сама башня.
    game_map, tower, enemy = _map_with_base_and_known_tower(
        tower_position=Coordinate(2500, 2000),
        enemy_position=Coordinate(2450, 2000),  # изначально в радиусе действия башни
    )

    for _ in range(40):
        game_map._advance_towards_base(enemy, 0.1)

    assert enemy.position.distance_to(tower.position) > tower.range_radius, \
        "патрулируя по периметру, враг должен был выйти из радиуса действия этой башни"


def test_map_update_patrols_enemy_around_defended_base():
    """Интеграционный тест через полный Map.update(): враг с назначенным
    маршрутом, при известной перекрывающей башне, кружит вокруг базы вместо
    того, чтобы либо стоять, либо переть напролом через простреливаемую зону."""
    game_map, tower, enemy = _map_with_base_and_known_tower(
        tower_position=Coordinate(2200, 2000),
        enemy_position=Coordinate(2500, 2000),
    )
    enemy.set_path([Coordinate(2000, 2000)])
    game_map.spawn_enemy(enemy)

    for _ in range(10):
        game_map.update(0.1)

    assert enemy.is_patrolling is True
    assert enemy in game_map.enemies
    assert enemy.position.y != pytest.approx(2000.0)


# --------------------------- avoids_danger()=True враги: без кругового патруля

def test_avoiding_enemy_never_patrols_even_when_known_tower_blocks_bearing():
    """Круговой патруль на одном радиусе плохо справляется с кластером из
    нескольких перекрывающихся башен - враг мог застревать на стыке двух
    зон. Разведчик (и любой другой avoids_danger()=True враг) вместо этого
    идёт строго по честному A*-маршруту в обход, без патруля вовсе."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    tower = LaserTurret(Coordinate(2200, 2000))  # bearing 0 от базы - перекрыт
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    scout = ScoutDrone(Coordinate(2500, 2000))  # тот же bearing 0
    scout.set_path([Coordinate(2000, 2000)])

    game_map._advance_towards_base(scout, 0.1)

    assert scout.is_patrolling is False, "разведчик не должен переключаться в круговой патруль"


def test_avoiding_enemy_follows_honest_route_around_known_tower():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 3500)
    tower = LaserTurret(Coordinate(2000, 2000), range_radius=300)
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    scout = ScoutDrone(Coordinate(2000, 500))
    scout.set_path([Coordinate(2000, 3500)])  # "наивный" путь напрямик, будто башня не видна
    game_map.spawn_enemy(scout)

    for _ in range(700):
        game_map.update(0.1)
        if scout.position.distance_to(game_map.base_position) < 50:
            break

    assert scout.position.distance_to(game_map.base_position) < 50, \
        "разведчик должен был обойти башню по честному маршруту и дойти до базы"


def test_avoiding_enemy_gives_up_and_retreats_when_no_safe_route_exists():
    """Если известная башня накрывает вообще всё пространство между врагом
    и базой, разведчик не должен биться о границу её радиуса - он должен
    отступить, а не пытаться прорваться."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    tower = LaserTurret(Coordinate(2000, 2000), range_radius=6000)  # накрывает всё
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    scout = ScoutDrone(Coordinate(500, 500))
    scout.set_path([Coordinate(2000, 2000)])
    game_map.spawn_enemy(scout)

    initial_distance = scout.position.distance_to(game_map.base_position)
    for _ in range(20):
        game_map.update(0.1)

    # Corporation после высадки не имеет фиксированных точек спавна -
    # отступление идёт по прямой прочь от базы, а не к точке спавна.
    assert scout.position.distance_to(game_map.base_position) > initial_distance, \
        "без честного маршрута враг должен отступать прочь от базы, а не топтаться на месте"
