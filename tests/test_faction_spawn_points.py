"""Раньше все враги спавнились из общего пула точек (Map.spawn_points),
случайно выбираемого в WaveProtocol.update() — Corporation и Fauna могли
появиться из одной и той же точки на карте. Теперь у каждой фракции
может быть свой набор точек спавна (Map.spawn_points_by_faction), а
позицию для конкретного врага выбирает GameSession._spawn_enemy_factory
через Map.spawn_points_for(faction) — WaveProtocol больше не выбирает
позицию сам, только вызывает spawn_factory(enemy_type) и передаёт
получившегося врага (или None, если точки спавна нет) дальше."""
import random

import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.core.game_session import GameSession
from src.enums import Faction
from src.factories.enemy_factory import EnemyFactory


# --------------------------------------------------------- EnemyFactory.faction_for

def test_faction_for_matches_configured_faction_for_every_registered_type():
    factory = EnemyFactory()
    expected = {
        "drone_walker": Faction.CORPORATION,
        "giant_roach": Faction.FAUNA,
        "scout_drone": Faction.CORPORATION,
        "heavy_assault_drone": Faction.CORPORATION,
        "bio_titan": Faction.FAUNA,
    }
    for type_name, faction in expected.items():
        assert factory.faction_for(type_name) == faction


def test_faction_for_unknown_type_defaults_to_fauna():
    factory = EnemyFactory()
    assert factory.faction_for("totally_unregistered_type") == Faction.FAUNA


# ------------------------------------------------------------- Map.spawn_points_for

def test_spawn_points_for_returns_faction_specific_points_when_configured():
    game_map = Map(width=4000, height=4000)
    corp_points = [Coordinate(0, 0)]
    fauna_points = [Coordinate(4000, 4000)]
    game_map.spawn_points_by_faction = {
        Faction.CORPORATION: corp_points,
        Faction.FAUNA: fauna_points,
    }

    assert game_map.spawn_points_for(Faction.CORPORATION) == corp_points
    assert game_map.spawn_points_for(Faction.FAUNA) == fauna_points


def test_spawn_points_for_falls_back_to_shared_list_when_faction_not_configured():
    game_map = Map(width=4000, height=4000)
    game_map.spawn_points = [Coordinate(100, 100)]

    assert game_map.spawn_points_for(Faction.CORPORATION) == [Coordinate(100, 100)]


def test_faction_spawn_points_are_actually_different_after_setup():
    session = GameSession()
    session.setup_game()

    corp_points = session.map.spawn_points_for(Faction.CORPORATION)
    fauna_points = session.map.spawn_points_for(Faction.FAUNA)

    assert corp_points, "у Corporation должны быть свои точки спавна"
    assert fauna_points, "у Fauna должны быть свои точки спавна"
    assert set((p.x, p.y) for p in corp_points).isdisjoint(set((p.x, p.y) for p in fauna_points)), \
        "фракции не должны делить одни и те же точки спавна"


# --------------------------------------------------------- GameSession._spawn_enemy_factory

def test_spawned_enemy_appears_at_a_point_belonging_to_its_faction():
    session = GameSession()
    session.setup_game()

    corp_points = {(p.x, p.y) for p in session.map.spawn_points_for(Faction.CORPORATION)}
    fauna_points = {(p.x, p.y) for p in session.map.spawn_points_for(Faction.FAUNA)}

    for _ in range(20):
        corp_enemy = session._spawn_enemy_factory("drone_walker")
        assert (corp_enemy.position.x, corp_enemy.position.y) in corp_points

        fauna_enemy = session._spawn_enemy_factory("giant_roach")
        assert (fauna_enemy.position.x, fauna_enemy.position.y) in fauna_points


def test_spawn_factory_returns_none_when_faction_has_no_spawn_points_at_all():
    session = GameSession()
    session.setup_game()
    session.map.spawn_points = []
    session.map.spawn_points_by_faction = {}

    assert session._spawn_enemy_factory("drone_walker") is None


# ---------------------------------------------------------------- WaveProtocol

def test_wave_protocol_calls_spawn_factory_with_only_the_enemy_type():
    from src.systems.wave_protocol import WaveProtocol, WaveConfig

    calls = []

    class _FakeMap:
        def __init__(self):
            self.enemies = []

        def spawn_enemy(self, enemy):
            self.enemies.append(enemy)

    def spy_spawn_factory(enemy_type):
        calls.append(enemy_type)
        return object()

    wp = WaveProtocol()
    wp.set_waves([WaveConfig(["drone_walker"], 1, 0.1)])
    wp.start_next_wave()

    wp.update(0.1, _FakeMap(), spy_spawn_factory)

    assert calls == ["drone_walker"]
