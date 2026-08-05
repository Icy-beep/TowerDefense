"""Гнёзда фауны: разрушаемые точки спавна, расставляемые один раз при старте игры."""
import math
import random
import types

import pygame
import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.core.game_session import GameSession
from src.entities.fauna_nest import FaunaNest
from src.entities.turrets import LaserTurret
from src.enums import DamageType, Faction


# --- FaunaNest: базовое поведение ---------------------------------------------

def test_nest_starts_at_full_health():
    nest = FaunaNest(Coordinate(0, 0))

    assert nest.health == nest.max_health
    assert nest.is_alive() is True
    assert nest.is_destroyed() is False


def test_take_damage_reduces_health():
    nest = FaunaNest(Coordinate(0, 0), max_health=150.0)

    nest.take_damage(50, DamageType.KINETIC)

    assert nest.health == 100


def test_organic_armor_halves_explosive_damage():
    nest = FaunaNest(Coordinate(0, 0), max_health=150.0)

    nest.take_damage(100, DamageType.EXPLOSIVE)

    assert nest.health == 100, "ORGANIC против EXPLOSIVE должен снижать урон на 50%"


def test_organic_armor_does_not_reduce_other_damage_types():
    nest = FaunaNest(Coordinate(0, 0), max_health=150.0)

    nest.take_damage(50, DamageType.KINETIC)
    nest.take_damage(50, DamageType.ENERGY)

    assert nest.health == 50, "ORGANIC снижает только EXPLOSIVE"


def test_nest_dies_when_health_reaches_zero_or_below():
    nest = FaunaNest(Coordinate(0, 0), max_health=150.0)

    nest.take_damage(1000, DamageType.KINETIC)

    assert nest.is_alive() is False
    assert nest.is_destroyed() is True
    assert nest.health == 0, "здоровье не должно уходить в минус"


def test_damage_is_ignored_after_nest_destroyed():
    nest = FaunaNest(Coordinate(0, 0), max_health=150.0)
    nest.take_damage(1000, DamageType.KINETIC)

    nest.take_damage(50, DamageType.KINETIC)

    assert nest.health == 0


# --- Map: гнёзда как атакуемые цели --------------------------------------------

def test_tower_can_damage_a_fauna_nest():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(20, 0))
    nest = FaunaNest(Coordinate(0, 0), max_health=150.0)
    game_map.modules.append(tower)
    game_map.add_fauna_nest(nest)

    game_map.update(1.0)

    assert nest.health < nest.max_health, "башня в радиусе должна наносить урон гнезду"


def test_destroyed_nest_is_removed_from_map_and_spawn_points():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(20, 0))
    nest = FaunaNest(Coordinate(0, 0), max_health=1.0)
    game_map.modules.append(tower)
    game_map.add_fauna_nest(nest)
    game_map.spawn_points_by_faction = {Faction.FAUNA: [nest.position]}

    game_map.update(1.0)

    assert nest not in game_map.fauna_nests
    assert game_map.spawn_points_by_faction[Faction.FAUNA] == []


def test_nest_defaults_to_a_reward():
    nest = FaunaNest(Coordinate(0, 0))
    assert nest.reward == 200


def test_map_update_returns_nests_destroyed_this_frame():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(20, 0))
    nest = FaunaNest(Coordinate(0, 0), max_health=1.0, reward=250)
    game_map.modules.append(tower)
    game_map.add_fauna_nest(nest)

    _, _, destroyed_nests = game_map.update(1.0)

    assert destroyed_nests == [nest]
    assert destroyed_nests[0].reward == 250


def test_map_update_reports_no_destroyed_nests_when_all_survive():
    game_map = Map(width=4000, height=4000)
    nest = FaunaNest(Coordinate(3000, 3000))
    game_map.add_fauna_nest(nest)

    _, _, destroyed_nests = game_map.update(1.0)

    assert destroyed_nests == []


def test_full_nest_kill_to_reward_pipeline_via_game_session():
    """Полный путь: Map возвращает уничтоженные гнёзда -> GameSession начисляет
    награду в ResourceBank (как для обычных врагов, см. test_damage_system.py)."""
    session = GameSession()
    session.setup_game()
    nest = session.map.fauna_nests[0]
    nest.take_damage(10_000, DamageType.KINETIC)

    credits_before = session.resources.credits
    session.update(delta_time=0.01)

    assert session.resources.credits == credits_before + nest.reward
    assert nest not in session.map.fauna_nests


def test_other_alive_nests_are_kept_when_one_is_destroyed():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(20, 0))
    dying_nest = FaunaNest(Coordinate(0, 0), max_health=1.0)
    safe_nest = FaunaNest(Coordinate(3000, 3000), max_health=150.0)
    game_map.modules.append(tower)
    game_map.add_fauna_nest(dying_nest)
    game_map.add_fauna_nest(safe_nest)
    game_map.spawn_points_by_faction = {Faction.FAUNA: [dying_nest.position, safe_nest.position]}

    game_map.update(1.0)

    assert dying_nest not in game_map.fauna_nests
    assert safe_nest in game_map.fauna_nests
    assert game_map.spawn_points_by_faction[Faction.FAUNA] == [safe_nest.position]


def test_nest_destroyed_event_is_emitted():
    events = []
    game_map = Map(width=4000, height=4000, on_event=lambda name, **data: events.append((name, data)))
    tower = LaserTurret(Coordinate(20, 0))
    nest = FaunaNest(Coordinate(0, 0), max_health=1.0)
    game_map.modules.append(tower)
    game_map.add_fauna_nest(nest)

    game_map.update(1.0)

    assert any(name == "nest_destroyed" for name, _ in events)


def test_map_without_nests_is_unaffected_by_nest_sync_logic():
    """Регрессия: карты без гнёзд (как в большинстве старых тестов) не должны
    задевать spawn_points_by_faction, заданные вручную."""
    game_map = Map(width=4000, height=4000)
    manual_points = [Coordinate(10, 10)]
    game_map.spawn_points_by_faction = {Faction.FAUNA: manual_points}

    game_map.update(1.0)

    assert game_map.spawn_points_by_faction[Faction.FAUNA] == manual_points


def test_can_place_module_rejects_overlap_with_live_nest():
    game_map = Map(width=4000, height=4000)
    nest = FaunaNest(Coordinate(500, 500))
    game_map.add_fauna_nest(nest)

    assert game_map.can_place_module(Coordinate(500, 500)) is False


def test_can_place_module_allows_placement_once_nest_is_destroyed():
    game_map = Map(width=4000, height=4000)
    nest = FaunaNest(Coordinate(500, 500))
    nest.take_damage(1000, DamageType.KINETIC)
    game_map.add_fauna_nest(nest)

    assert game_map.can_place_module(Coordinate(500, 500)) is True


def test_can_place_module_allows_placement_far_from_any_nest():
    game_map = Map(width=4000, height=4000)
    nest = FaunaNest(Coordinate(500, 500))
    game_map.add_fauna_nest(nest)

    assert game_map.can_place_module(Coordinate(3000, 3000)) is True


# --- GameSession._generate_fauna_nests: параметры расстановки -----------------

def test_nest_count_is_within_configured_range():
    session = GameSession()
    session.map = Map()
    session.base_position = Coordinate(session.map.width / 2, session.map.height / 2)

    for seed in range(30):
        nests = session._generate_fauna_nests(rng=random.Random(seed))
        assert session.NEST_COUNT_MIN <= len(nests) <= session.NEST_COUNT_MAX


def test_every_nest_respects_distance_bounds_from_base():
    session = GameSession()
    session.map = Map()
    session.base_position = Coordinate(session.map.width / 2, session.map.height / 2)

    nests = session._generate_fauna_nests(rng=random.Random(7))

    for nest in nests:
        distance = nest.position.distance_to(session.base_position)
        assert session.NEST_MIN_DISTANCE_FROM_BASE - 1e-6 <= distance <= session.NEST_MAX_DISTANCE_FROM_BASE + 1e-6


def test_every_pair_of_nests_respects_minimum_spacing():
    session = GameSession()
    session.map = Map()
    session.base_position = Coordinate(session.map.width / 2, session.map.height / 2)

    nests = session._generate_fauna_nests(rng=random.Random(3))

    for i, a in enumerate(nests):
        for b in nests[i + 1:]:
            assert a.position.distance_to(b.position) >= session.NEST_MIN_SPACING - 1e-6


def test_all_nests_are_within_map_bounds():
    session = GameSession()
    session.map = Map()
    session.base_position = Coordinate(session.map.width / 2, session.map.height / 2)

    nests = session._generate_fauna_nests(rng=random.Random(99))

    for nest in nests:
        assert 0 <= nest.position.x <= session.map.width
        assert 0 <= nest.position.y <= session.map.height


def test_setup_game_populates_map_fauna_nests_and_matching_spawn_points():
    session = GameSession()
    session.setup_game()

    assert session.NEST_COUNT_MIN <= len(session.map.fauna_nests) <= session.NEST_COUNT_MAX
    fauna_spawn_points = session.map.spawn_points_for(Faction.FAUNA)
    nest_positions = [nest.position for nest in session.map.fauna_nests]
    assert fauna_spawn_points == nest_positions


def test_fauna_stops_spawning_once_all_nests_are_destroyed():
    session = GameSession()
    session.setup_game()

    for nest in session.map.fauna_nests:
        nest.take_damage(10_000, DamageType.KINETIC)

    session.map.update(1.0)

    assert session.map.fauna_nests == []
    assert session._spawn_enemy_factory("giant_roach") is None


# --- Renderer: полоска здоровья гнезда -----------------------------------------

def test_renderer_draws_health_bar_for_alive_nests():
    from src.ui.map_renderer import MapRenderer

    renderer = MapRenderer()
    nest = FaunaNest(Coordinate(100, 100))
    nest.health = 75

    rect_calls = []
    original_rect = pygame.draw.rect

    def spy_rect(surface, color, rect, *args, **kwargs):
        rect_calls.append((tuple(color), rect))
        return original_rect(surface, color, rect, *args, **kwargs)

    pygame.draw.rect = spy_rect
    try:
        camera = types.SimpleNamespace(world_to_screen=lambda x, y: (x, y), x=0, y=0, zoom=1.0)
        screen = pygame.Surface((900, 600))
        renderer._draw_fauna_nests(screen, camera, [nest])
    finally:
        pygame.draw.rect = original_rect

    assert len(rect_calls) == 2, "фон полоски + сама полоска здоровья"


def test_renderer_skips_destroyed_nests():
    from src.ui.map_renderer import MapRenderer, FACTION_SPAWN_COLORS

    renderer = MapRenderer()
    nest = FaunaNest(Coordinate(100, 100))
    nest.take_damage(1000, DamageType.KINETIC)

    drawn_colors = []
    original_polygon = pygame.draw.polygon

    def spy_polygon(surface, color, points, *args, **kwargs):
        drawn_colors.append(tuple(color))
        return original_polygon(surface, color, points, *args, **kwargs)

    pygame.draw.polygon = spy_polygon
    try:
        camera = types.SimpleNamespace(world_to_screen=lambda x, y: (x, y), x=0, y=0, zoom=1.0)
        screen = pygame.Surface((900, 600))
        renderer._draw_fauna_nests(screen, camera, [nest])
    finally:
        pygame.draw.polygon = original_polygon

    fauna_color = FACTION_SPAWN_COLORS[Faction.FAUNA]
    assert fauna_color not in drawn_colors, "уничтоженное гнездо не должно рисоваться"
