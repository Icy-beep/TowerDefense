"""
Также содержит регрессионный тест на найденный баг: is_all_waves_complete()
раньше никогда не становился True после прохождения последней волны."""
from src.systems.wave_protocol import WaveProtocol, WaveConfig
from src.entities.enemies import DroneWalker
from src.core.coordinate import Coordinate


class FakeMapNoSurvivors:
    """Эмулирует поле, которое всегда успевает зачистить волну раньше,
    чем заспавнится следующий враг — враги 'спавнятся' и сразу считаются
    уничтоженными (в self.enemies не попадают)."""

    def __init__(self):
        self.enemies = []

    def spawn_enemy(self, enemy):
        pass


def fake_spawn_factory(cls):
    """Позицию точки спавна WaveProtocol больше не выбирает сам — это
    теперь дело spawn_factory (в реальной игре — GameSession.
    _spawn_enemy_factory, знающий про фракцию врага и точки спавна её
    фракции). Здесь для теста позиция не важна."""
    return cls(Coordinate(0, 0))


def test_wave_spawns_correct_number_and_type_of_enemies():
    wp = WaveProtocol()
    wp.set_waves([WaveConfig([DroneWalker], 3, 0.5)])
    wp.start_next_wave()

    spawned = []
    game_map = FakeMapNoSurvivors()
    game_map.spawn_enemy = lambda e: spawned.append(e)

    for _ in range(20):
        wp.update(0.5, game_map, fake_spawn_factory)

    assert len(spawned) == 3
    assert all(isinstance(e, DroneWalker) for e in spawned)


def test_wave_does_not_spawn_more_than_configured_count():
    wp = WaveProtocol()
    wp.set_waves([WaveConfig([DroneWalker], 2, 0.1)])
    wp.start_next_wave()

    spawned = []
    game_map = FakeMapNoSurvivors()
    game_map.spawn_enemy = lambda e: spawned.append(e)

    for _ in range(500):  # намного больше, чем нужно для 2 врагов
        wp.update(0.1, game_map, fake_spawn_factory)

    assert len(spawned) == 2, "не должно спавниться больше врагов, чем задано в WaveConfig"


def test_is_all_waves_complete_becomes_true_after_last_wave():
    """Регрессионный тест на баг: раньше update() вызывал
    start_next_wave() (единственное место, где выставлялся finished=True)
    только пока current_wave_idx < len(waves). После того как счётчик
    достигал конца списка волн, эта ветка переставала срабатывать, и
    finished оставался False навсегда — is_all_waves_complete() был
    недостижимым условием победы."""
    wp = WaveProtocol()
    wp.set_waves([
        WaveConfig([DroneWalker], 2, 0.1),
        WaveConfig([DroneWalker], 2, 0.1),
    ])
    wp.start_next_wave()
    game_map = FakeMapNoSurvivors()

    assert wp.is_all_waves_complete() is False, "не должно быть True в начале"

    for _ in range(200):
        wp.update(0.1, game_map, fake_spawn_factory)
        if wp.is_all_waves_complete():
            break

    assert wp.is_all_waves_complete() is True, "БАГ НЕ ПОЧИНЕН: finished так и не стал True"
    assert wp.current_wave_idx == 2


def test_is_all_waves_complete_false_while_enemies_remain_on_field():
    wp = WaveProtocol()
    wp.set_waves([WaveConfig([DroneWalker], 1, 0.1)])
    wp.start_next_wave()

    class MapWithSurvivor:
        def __init__(self):
            self.enemies = [object()]  # один противник навсегда остаётся на поле

        def spawn_enemy(self, e):
            pass

    game_map = MapWithSurvivor()
    for _ in range(50):
        wp.update(0.1, game_map, fake_spawn_factory)

    assert wp.is_all_waves_complete() is False, "волна не может завершиться, пока противник жив на поле"


def test_force_start_next_wave_skips_cooldown():
    wp = WaveProtocol()
    wp.set_waves([WaveConfig([DroneWalker], 1, 5.0), WaveConfig([DroneWalker], 1, 5.0)])
    wp.start_next_wave()
    wp.is_active = False
    wp.current_wave_idx = 1
    wp.cooldown_timer = 999.0

    wp.force_start_next_wave()

    assert wp.is_active is True
    assert wp.cooldown_timer == 0


def test_start_next_wave_returns_false_when_already_active():
    wp = WaveProtocol()
    wp.set_waves([WaveConfig([DroneWalker], 1, 1.0)])
    wp.start_next_wave()

    assert wp.start_next_wave() is False, "нельзя запустить новую волну, пока текущая активна"
