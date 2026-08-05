"""Отложенная атака: враги ждут сбора группы у точки появления и наваливаются на базу
массой, набрав Map.STAGING_GROUP_SIZE живых участников (см. Map._update_staging_groups)."""
import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.core.game_session import GameSession
from src.entities.enemies import DroneWalker, GiantRoach, HeavyAssaultDrone, BioTitan, ScoutDrone, MedicDrone
from src.systems.group_formation import GroupFormationSystem
from src.enums import Faction


def test_combat_enemies_stage_before_attacking():
    assert DroneWalker(Coordinate(0, 0)).stages_before_attacking() is True
    assert GiantRoach(Coordinate(0, 0)).stages_before_attacking() is True
    assert HeavyAssaultDrone(Coordinate(0, 0)).stages_before_attacking() is True
    assert BioTitan(Coordinate(0, 0)).stages_before_attacking() is True


def test_scout_drone_does_not_stage():
    """Разведчик всегда убегает от башен и никогда не участвует в общей группе."""
    assert ScoutDrone(Coordinate(0, 0)).stages_before_attacking() is False


def test_medic_drone_does_not_stage():
    """Медик сам ищет уже сформированную боевую группу, а не собирает свою."""
    assert MedicDrone(Coordinate(0, 0)).stages_before_attacking() is False


def _staged_enemy(position, faction=Faction.FAUNA):
    enemy = GiantRoach(position)
    enemy.faction = faction
    enemy.is_staging = True
    return enemy


def test_staging_enemy_circles_near_spawn_instead_of_marching_to_base():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    enemies = [_staged_enemy(Coordinate(100, 100)) for _ in range(2)]
    for e in enemies:
        game_map.spawn_enemy(e)

    for _ in range(50):
        game_map.update(0.1)

    for e in enemies:
        assert e.is_staging is True, "группа ещё не набрала STAGING_GROUP_SIZE - атака не должна начинаться"
        assert e.position.distance_to(Coordinate(2000, 2000)) > 1500, \
            "пока группа не собралась, враг должен кружить у точки появления, а не идти к базе"


def test_group_stays_staging_below_the_size_threshold():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    enemies = [_staged_enemy(Coordinate(100 + i * 5, 100)) for i in range(Map.STAGING_GROUP_SIZE - 1)]
    for e in enemies:
        game_map.spawn_enemy(e)

    for _ in range(10):
        game_map.update(0.1)

    assert all(e.is_staging for e in enemies), \
        "группе не хватает одного участника до STAGING_GROUP_SIZE - атака не должна начинаться"
    assert all(e.group_id is None for e in enemies)


def test_group_commits_and_rushes_the_base_once_threshold_is_reached():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    enemies = [_staged_enemy(Coordinate(100 + i * 5, 100)) for i in range(Map.STAGING_GROUP_SIZE)]
    for e in enemies:
        game_map.spawn_enemy(e)

    game_map.update(0.1)

    assert all(e.is_staging is False for e in enemies), \
        "как только набралось STAGING_GROUP_SIZE участников, вся группа должна выступить разом"

    leaders = [e for e in enemies if e.is_group_leader]
    assert len(leaders) == 1, "у выступившей группы должен быть ровно один лидер"
    leader = leaders[0]
    assert len(leader.path) > 0, "лидер группы должен получить маршрут до базы"

    followers = [e for e in enemies if e is not leader]
    assert all(f.group_leader is leader for f in followers)
    assert all(f.group_id == leader.group_id for f in followers)


def test_distant_same_faction_groups_stay_local_instead_of_merging_across_the_map():
    """Регрессия: враги одной фракции, появившиеся в разных концах карты (например,
    у разных точек спавна Fauna), не должны тянуться к одному общему месту сбора -
    у каждой локальной кучки должен быть свой якорь рядом с тем, где она появилась."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    near_corner = [_staged_enemy(Coordinate(100 + i * 10, 100)) for i in range(3)]
    far_corner = [_staged_enemy(Coordinate(3900 - i * 10, 3900)) for i in range(3)]
    for e in near_corner + far_corner:
        game_map.spawn_enemy(e)

    for _ in range(20):
        game_map.update(0.1)

    for e in near_corner:
        assert e.position.distance_to(Coordinate(100, 100)) < 500, \
            "враг у ближнего угла не должен уходить к дальней группе своей же фракции"
    for e in far_corner:
        assert e.position.distance_to(Coordinate(3900, 3900)) < 500, \
            "враг у дальнего угла не должен уходить к ближней группе своей же фракции"

    near_anchors = {id(e.stage_anchor) for e in near_corner}
    far_anchors = {id(e.stage_anchor) for e in far_corner}
    assert len(near_anchors) == 1 and len(far_anchors) == 1, "враги рядом друг с другом должны делить один якорь"
    assert near_anchors != far_anchors, "у далёких друг от друга кучек должны быть разные якоря"


def test_isolated_group_still_commits_after_max_wait_even_below_threshold():
    """Изолированная кучка (например, отряд Corporation, высадившийся далеко ото всех)
    может никогда не набрать STAGING_GROUP_SIZE сама по себе - она не должна кружить
    вечно, а обязана выступить по истечении STAGING_MAX_WAIT."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    enemies = [_staged_enemy(Coordinate(100 + i * 10, 100)) for i in range(3)]
    for e in enemies:
        game_map.spawn_enemy(e)

    game_map.update(0.1)  # якорь создаётся здесь, отсчёт таймаута идёт от этого момента
    assert all(e.is_staging for e in enemies)

    game_map.update(Map.STAGING_MAX_WAIT - 0.2)
    assert all(e.is_staging for e in enemies), "до истечения таймаута кучка ещё ждёт"

    game_map.update(1.0)
    assert all(e.is_staging is False for e in enemies), \
        "по истечении STAGING_MAX_WAIT изолированная кучка должна выступить, даже не набрав порог"


def test_staging_groups_are_tracked_separately_per_faction():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    fauna = [_staged_enemy(Coordinate(100 + i * 5, 100), faction=Faction.FAUNA)
             for i in range(Map.STAGING_GROUP_SIZE - 1)]
    corp = [_staged_enemy(Coordinate(3900 - i * 5, 3900), faction=Faction.CORPORATION)
            for i in range(Map.STAGING_GROUP_SIZE - 1)]
    for e in fauna + corp:
        game_map.spawn_enemy(e)

    game_map.update(0.1)

    assert all(e.is_staging for e in fauna + corp), \
        "ни у одной фракции по отдельности ещё не набралось STAGING_GROUP_SIZE"


def test_dead_staged_enemy_does_not_count_towards_the_group_size():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)

    enemies = [_staged_enemy(Coordinate(100 + i * 5, 100)) for i in range(Map.STAGING_GROUP_SIZE)]
    enemies[0].health = 0
    for e in enemies:
        game_map.spawn_enemy(e)

    game_map.update(0.1)

    survivors = [e for e in enemies if e.is_alive()]
    assert all(e.is_staging for e in survivors), \
        "мёртвый враг не должен засчитываться в размер группы"


def test_ambient_group_formation_ignores_staging_enemies():
    """Обычная (не отложенная) система формирования групп не должна растаскивать
    врагов, ожидающих сбора для отложенной атаки - иначе порог никогда не наберётся."""
    class _AlwaysFormRng:
        def random(self):
            return 0.0

        def choice(self, seq):
            return seq[0]

    system = GroupFormationSystem(rng=_AlwaysFormRng())
    leader = HeavyAssaultDrone(Coordinate(0, 0))
    leader.type_name = "heavy_assault_drone"
    staging_ally = GiantRoach(Coordinate(50, 0))
    staging_ally.type_name = "giant_roach"
    staging_ally.faction = leader.faction
    staging_ally.is_staging = True

    system.update(1.0, [leader, staging_ally])

    assert staging_ally.group_id is None, \
        "враг, ожидающий отложенную атаку, не должен вербоваться в обычную группу на ходу"


def test_game_session_spawn_marks_eligible_enemy_as_staging_without_a_path():
    session = GameSession()
    session.setup_game()

    enemy = session._spawn_enemy_factory("giant_roach")

    assert enemy.is_staging is True
    assert enemy.path == [], "путь до базы выдаётся только после того, как группа наберётся и выступит"


def test_game_session_spawn_gives_scout_an_immediate_path_without_staging():
    session = GameSession()
    session.setup_game()

    scout = session._spawn_enemy_factory("scout_drone", Coordinate(3999, 1))

    assert scout.is_staging is False
    assert len(scout.path) > 0, "разведчик не ждёт сбора группы и сразу получает маршрут"
