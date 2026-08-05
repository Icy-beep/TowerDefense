"""Источники угрозы (src/systems/threat_strategy.py): высадка кораблей и спавн фауны."""
import random
import types

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.enums import Faction
from src.systems.threat_strategy import ShipLandingStrategy, NestSpawnStrategy, PendingLanding, ThreatStrategy


class _FakeMap:
    """Минимальная замена Map: только то, что нужно стратегиям угроз. По умолчанию
    ведёт себя как карта без секторов прогрессии (см. src/systems/sector.py) - всё
    открыто, ровно как настоящая Map с пустым self.sectors."""

    def __init__(self, width=4000, height=4000, fauna_spawn_points=None, unlocked=True):
        self.width = width
        self.height = height
        self.enemies = []
        self._fauna_spawn_points = fauna_spawn_points if fauna_spawn_points is not None else [Coordinate(0, 0)]
        self._unlocked = unlocked

    def spawn_enemy(self, enemy):
        self.enemies.append(enemy)

    def is_position_unlocked(self, position):
        return self._unlocked

    def unlocked_fauna_spawn_points(self):
        return self._fauna_spawn_points


def _spawn_factory_spy(calls, faction=Faction.CORPORATION):
    """Возвращает spawn_factory-заглушку, которая запоминает вызовы и
    создаёт лёгкий фейковый объект врага вместо настоящего HostileEntity."""

    def factory(enemy_type, position=None):
        calls.append((enemy_type, position))
        return types.SimpleNamespace(is_alive=lambda: True, faction=faction,
                                      type_name=enemy_type, position=position)

    return factory



def test_ship_landing_creates_no_marker_before_base_interval_elapses():
    strategy = ShipLandingStrategy(enemy_types=["drone_walker"], base_interval=10.0)
    game_map = _FakeMap()
    calls = []

    strategy.update(1.0, game_map, _spawn_factory_spy(calls))

    assert strategy.pending_landings == []
    assert calls == []


def test_ship_landing_marker_appears_after_base_interval():
    strategy = ShipLandingStrategy(enemy_types=["drone_walker"], base_interval=5.0, warning_time=3.0)
    game_map = _FakeMap()
    calls = []

    strategy.update(5.0, game_map, _spawn_factory_spy(calls))

    assert len(strategy.pending_landings) == 1
    assert calls == [], "отряд появляется только после истечения warning_time"


def test_ship_landing_marker_sits_on_map_border():
    strategy = ShipLandingStrategy(enemy_types=["drone_walker"], base_interval=1.0, rng=random.Random(1))
    game_map = _FakeMap(width=4000, height=4000)

    strategy.update(1.0, game_map, _spawn_factory_spy([]))

    landing = strategy.pending_landings[0]
    on_border = (landing.position.x in (0, game_map.width - 1) or landing.position.y in (0, game_map.height - 1))
    assert on_border, "точка высадки должна лежать на границе карты"


def test_ship_landing_spawns_squad_once_warning_time_elapses():
    strategy = ShipLandingStrategy(enemy_types=["drone_walker"], squad_size_range=(3, 3),
                                    base_interval=5.0, warning_time=2.0)
    game_map = _FakeMap()
    calls = []
    spawn_factory = _spawn_factory_spy(calls)

    strategy.update(5.0, game_map, spawn_factory)
    strategy.update(2.0, game_map, spawn_factory)

    assert len(calls) == 3
    assert all(c[0] == "drone_walker" for c in calls)
    assert strategy.pending_landings == []
    assert len(game_map.enemies) == 3


def test_ship_landing_eventually_spawns_every_registered_type_even_with_small_squads():
    """Регрессия: если типов больше, чем максимальный размер отряда, индекс типа внутри
    одного отряда (i % len) никогда не доходил до последних типов - счётчик спавна теперь
    общий и не сбрасывается на каждый отряд, так что рано или поздно выпадают все типы."""
    types = ["a", "b", "c", "d", "e"]
    strategy = ShipLandingStrategy(enemy_types=types, squad_size_range=(2, 4),
                                    base_interval=1.0, warning_time=0.0, rng=random.Random(0))
    game_map = _FakeMap()
    calls = []
    spawn_factory = _spawn_factory_spy(calls)

    for _ in range(20):
        strategy.update(1.0, game_map, spawn_factory)

    spawned_types = {c[0] for c in calls}
    assert spawned_types == set(types), \
        f"не все зарегистрированные типы когда-либо выпали: {spawned_types}"


def test_ship_landing_squad_spawns_at_the_landing_position():
    strategy = ShipLandingStrategy(enemy_types=["drone_walker"], squad_size_range=(1, 1),
                                    base_interval=1.0, warning_time=1.0)
    game_map = _FakeMap()
    calls = []

    strategy.update(1.0, game_map, _spawn_factory_spy(calls))
    landing_position = strategy.pending_landings[0].position
    strategy.update(1.0, game_map, _spawn_factory_spy(calls))

    assert calls[0][1] == landing_position


def test_ship_landing_interval_shrinks_towards_minimum_over_time():
    strategy = ShipLandingStrategy(enemy_types=["drone_walker"], base_interval=20.0,
                                    min_interval=5.0, interval_decay_per_second=1.0)

    strategy.elapsed = 100.0
    assert strategy._current_interval() == 5.0, "интервал не должен уходить ниже min_interval"

    strategy.elapsed = 0.0
    assert strategy._current_interval() == 20.0


def test_ship_landing_does_nothing_without_enemy_types():
    strategy = ShipLandingStrategy(enemy_types=[], base_interval=0.1)
    game_map = _FakeMap()
    calls = []

    for _ in range(10):
        strategy.update(1.0, game_map, _spawn_factory_spy(calls))

    assert strategy.pending_landings == []
    assert calls == []



def test_nest_spawn_does_not_spawn_before_interval_elapses():
    strategy = NestSpawnStrategy(enemy_types=["giant_roach"], base_interval=6.0)
    game_map = _FakeMap()
    calls = []

    strategy.update(1.0, game_map, _spawn_factory_spy(calls, faction=Faction.FAUNA))

    assert calls == []
    assert game_map.enemies == []


def test_nest_spawn_spawns_one_enemy_after_interval():
    strategy = NestSpawnStrategy(enemy_types=["giant_roach"], base_interval=3.0)
    game_map = _FakeMap()
    calls = []

    strategy.update(3.0, game_map, _spawn_factory_spy(calls, faction=Faction.FAUNA))

    assert len(calls) == 1
    assert calls[0][0] == "giant_roach"
    assert len(game_map.enemies) == 1


def test_nest_spawn_cycles_through_enemy_types_in_order():
    strategy = NestSpawnStrategy(enemy_types=["giant_roach", "bio_titan"], base_interval=1.0, min_interval=1.0)
    game_map = _FakeMap()
    calls = []
    spawn_factory = _spawn_factory_spy(calls, faction=Faction.FAUNA)

    for _ in range(4):
        strategy.update(1.0, game_map, spawn_factory)

    assert [c[0] for c in calls] == ["giant_roach", "bio_titan", "giant_roach", "bio_titan"]


def test_nest_spawn_respects_max_active_population_cap():
    strategy = NestSpawnStrategy(enemy_types=["giant_roach"], base_interval=1.0, max_active=2)
    game_map = _FakeMap()
    game_map.enemies = [
        types.SimpleNamespace(is_alive=lambda: True, faction=Faction.FAUNA)
        for _ in range(2)
    ]
    calls = []

    strategy.update(1.0, game_map, _spawn_factory_spy(calls, faction=Faction.FAUNA))

    assert calls == [], "не должно спавниться сверх лимита одновременно живых врагов фракции"


def test_nest_spawn_ignores_dead_enemies_when_counting_population():
    strategy = NestSpawnStrategy(enemy_types=["giant_roach"], base_interval=1.0, max_active=1)
    game_map = _FakeMap()
    game_map.enemies = [
        types.SimpleNamespace(is_alive=lambda: False, faction=Faction.FAUNA)
    ]
    calls = []

    strategy.update(1.0, game_map, _spawn_factory_spy(calls, faction=Faction.FAUNA))

    assert len(calls) == 1, "мёртвые враги не должны учитываться в лимите популяции"


def test_nest_spawn_skips_cycle_when_no_nests_are_in_unlocked_sectors():
    """Секторы прогрессии (см. src/systems/sector.py) - если ни одно гнездо не лежит в
    открытом секторе, спавнить не из чего, и цикл просто пропускается."""
    strategy = NestSpawnStrategy(enemy_types=["giant_roach"], base_interval=1.0)
    game_map = _FakeMap(fauna_spawn_points=[])
    calls = []

    strategy.update(1.0, game_map, _spawn_factory_spy(calls, faction=Faction.FAUNA))

    assert calls == []
    assert game_map.enemies == []


def test_nest_spawn_resumes_once_a_sector_with_nests_unlocks():
    game_map = _FakeMap(fauna_spawn_points=[])
    strategy = NestSpawnStrategy(enemy_types=["giant_roach"], base_interval=1.0, min_interval=1.0)
    calls = []
    spawn_factory = _spawn_factory_spy(calls, faction=Faction.FAUNA)

    strategy.update(1.0, game_map, spawn_factory)
    assert calls == []

    game_map._fauna_spawn_points = [Coordinate(500, 500)]
    strategy.update(1.0, game_map, spawn_factory)

    assert len(calls) == 1
    assert calls[0][1] == Coordinate(500, 500)


def test_ship_landing_ignores_sector_lock_state_by_design():
    """В отличие от гнёзд фауны, высадка Corporation намеренно не гейтится секторами -
    см. докстринг ShipLandingStrategy.update. Даже если вся карта "заблокирована"
    (is_position_unlocked всегда False), высадка всё равно происходит."""
    strategy = ShipLandingStrategy(enemy_types=["drone_walker"], base_interval=1.0)
    game_map = _FakeMap(unlocked=False)

    strategy.update(1.0, game_map, _spawn_factory_spy([]))

    assert len(strategy.pending_landings) == 1


def test_nest_spawn_does_nothing_without_enemy_types():
    strategy = NestSpawnStrategy(enemy_types=[], base_interval=0.1)
    game_map = _FakeMap()
    calls = []

    for _ in range(10):
        strategy.update(1.0, game_map, _spawn_factory_spy(calls, faction=Faction.FAUNA))

    assert calls == []



def test_pending_landing_stores_position_and_warning_time():
    landing = PendingLanding(Coordinate(10, 20), warning_time=4.0)

    assert (landing.position.x, landing.position.y) == (10, 20)
    assert landing.time_remaining == 4.0


def test_threat_strategy_cannot_be_instantiated_directly():
    try:
        ThreatStrategy()
        assert False, "ThreatStrategy — абстрактный класс, не должен создаваться напрямую"
    except TypeError:
        pass



def test_setup_game_wires_threat_strategies_per_faction():
    session = GameSession()
    session.setup_game()

    assert isinstance(session.threat_strategies[Faction.CORPORATION], ShipLandingStrategy)
    assert isinstance(session.threat_strategies[Faction.FAUNA], NestSpawnStrategy)


def test_game_session_no_longer_has_wave_protocol():
    session = GameSession()
    session.setup_game()

    assert not hasattr(session, "wave_protocol")


def test_game_session_border_landings_get_a_valid_path_to_base():
    """Граничная точка ровно на width/height не должна давать пустой путь до базы."""
    session = GameSession()
    session.setup_game()
    strategy = session.threat_strategies[Faction.CORPORATION]

    for _ in range(200):
        point = strategy._random_border_point(session.map)
        path = session.map.path_to_base(point, Faction.CORPORATION)
        assert path, f"нет пути от граничной точки {point}"


def test_game_session_spawns_enemies_over_time_without_waves():
    session = GameSession()
    session.setup_game()

    spawned_at_some_point = False
    for _ in range(400):
        session.update(delta_time=0.5)
        if session.map.enemies:
            spawned_at_some_point = True
            break

    assert spawned_at_some_point, "враги должны появляться сами по себе без волновой системы"
