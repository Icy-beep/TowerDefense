"""Событийные хуки Map/GameSession и загрузка звуков в SoundManager."""
import os

import pytest

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.core.map import Map
from src.entities.enemies import DroneWalker
from src.entities.turrets import LaserTurret
from src.ui.sound_manager import discover_sound_files, SoundManager


def test_discover_sound_files_groups_by_subfolder_and_filters_extensions(tmp_path):
    (tmp_path / "laser_fire").mkdir()
    (tmp_path / "laser_fire" / "a.wav").write_bytes(b"x")
    (tmp_path / "laser_fire" / "b.ogg").write_bytes(b"x")
    (tmp_path / "laser_fire" / "notes.txt").write_bytes(b"x")
    (tmp_path / "empty_event").mkdir()

    result = discover_sound_files(str(tmp_path))

    assert set(result.keys()) == {"laser_fire"}
    assert len(result["laser_fire"]) == 2


def test_discover_sound_files_returns_empty_dict_for_missing_root(tmp_path):
    assert discover_sound_files(str(tmp_path / "does_not_exist")) == {}


class _FakeError(Exception):
    pass


class _FakeSound:
    created_via_buffer = []

    def __init__(self, path=None, buffer=None):
        if path is not None and "broken" in path:
            raise _FakeError("не удалось загрузить файл")
        self.path = path
        self.buffer = buffer
        self.volume = None
        self.play_calls = 0
        if buffer is not None:
            _FakeSound.created_via_buffer.append(self)

    def get_raw(self):
        return self.buffer if self.buffer is not None else (b"\x00\x00\x10\x00\x20\x00\x30\x00" * 20)

    def set_volume(self, volume):
        self.volume = volume

    def play(self):
        self.play_calls += 1


class _FakeMixer:
    def __init__(self, fail_init=False):
        self._initialized = False
        self._fail_init = fail_init

    def get_init(self):
        return (44100, -16, 2) if self._initialized else None

    def init(self):
        if self._fail_init:
            raise _FakeError("нет звукового устройства")
        self._initialized = True

    def set_num_channels(self, count):
        self.num_channels = count

    Sound = _FakeSound


class _FakePygame:
    def __init__(self, fail_init=False):
        self.mixer = _FakeMixer(fail_init=fail_init)
        self.error = _FakeError


class _FirstChoiceRng:
    def choice(self, seq):
        return seq[0]

    def uniform(self, a, b):
        return 0.0


class _FixedPitchRng:
    def __init__(self, pitch_offset):
        self._pitch_offset = pitch_offset

    def choice(self, seq):
        return seq[0]

    def uniform(self, a, b):
        return self._pitch_offset


def _make_sound_root(tmp_path, event_name, filenames):
    event_dir = tmp_path / event_name
    event_dir.mkdir()
    for filename in filenames:
        (event_dir / filename).write_bytes(b"x")
    return str(tmp_path)


def test_sound_manager_loads_valid_files_and_skips_broken_ones(tmp_path, monkeypatch):
    root = _make_sound_root(tmp_path, "laser_fire", ["a.wav", "broken.wav"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.sound_manager.pygame", fake_pygame)

    manager = SoundManager(sounds_root=root, rng=_FirstChoiceRng())

    assert manager.enabled is True
    assert manager.has_sounds_for("laser_fire") is True
    assert len(manager._sounds["laser_fire"]) == 1


def test_sound_manager_play_uses_rng_and_sets_volume(tmp_path, monkeypatch):
    root = _make_sound_root(tmp_path, "base_hit", ["hit.wav"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.sound_manager.pygame", fake_pygame)

    manager = SoundManager(sounds_root=root, volume=0.4, rng=_FirstChoiceRng())
    manager.play("base_hit")

    played = manager._sounds["base_hit"][0]
    assert played.play_calls == 1
    assert played.volume == 0.4


def test_sound_manager_play_applies_random_pitch_variation(tmp_path, monkeypatch):
    root = _make_sound_root(tmp_path, "base_hit", ["hit.wav"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.sound_manager.pygame", fake_pygame)
    _FakeSound.created_via_buffer = []

    manager = SoundManager(sounds_root=root, volume=0.4, rng=_FixedPitchRng(0.05))
    manager.play("base_hit")

    original = manager._sounds["base_hit"][0]
    assert original.play_calls == 0, "должен проигрываться ресемплированный клон, а не сам оригинал"
    assert len(_FakeSound.created_via_buffer) == 1
    pitched = _FakeSound.created_via_buffer[0]
    assert pitched.play_calls == 1
    assert pitched.volume == 0.4


def test_sound_manager_play_skips_pitch_shift_when_variation_is_zero(tmp_path, monkeypatch):
    root = _make_sound_root(tmp_path, "base_hit", ["hit.wav"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.sound_manager.pygame", fake_pygame)
    _FakeSound.created_via_buffer = []

    manager = SoundManager(sounds_root=root, volume=0.4, rng=_FirstChoiceRng())
    manager.play("base_hit")

    assert _FakeSound.created_via_buffer == [], "нулевая вариация питча не должна создавать копию звука"


def test_sound_manager_play_is_a_no_op_for_unknown_event(tmp_path, monkeypatch):
    root = _make_sound_root(tmp_path, "base_hit", ["hit.wav"])
    monkeypatch.setattr("src.ui.sound_manager.pygame", _FakePygame())

    manager = SoundManager(sounds_root=root, rng=_FirstChoiceRng())
    manager.play("no_such_event")


def test_sound_manager_raises_channel_count_to_avoid_cutting_off_overlapping_shots(tmp_path, monkeypatch):
    root = _make_sound_root(tmp_path, "bullet_fire", ["a.wav"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.sound_manager.pygame", fake_pygame)

    manager = SoundManager(sounds_root=root, rng=_FirstChoiceRng())

    assert fake_pygame.mixer.num_channels == manager.NUM_CHANNELS
    assert manager.NUM_CHANNELS > 8, "дефолтных 8 каналов pygame не хватает при частой стрельбе"


def test_sound_manager_disables_itself_when_mixer_init_fails(tmp_path, monkeypatch):
    root = _make_sound_root(tmp_path, "base_hit", ["hit.wav"])
    monkeypatch.setattr("src.ui.sound_manager.pygame", _FakePygame(fail_init=True))

    manager = SoundManager(sounds_root=root, rng=_FirstChoiceRng())

    assert manager.enabled is False
    manager.play("base_hit")


def test_map_emits_tower_fired_event_when_a_tower_shoots():
    events = []
    game_map = Map(width=4000, height=4000, on_event=lambda name, **data: events.append((name, data)))
    tower = LaserTurret(Coordinate(0, 0))
    tower.type_name = "laser"
    tower.cooldown_timer = 0
    game_map.modules.append(tower)

    enemy = DroneWalker(Coordinate(10, 0))
    game_map.spawn_enemy(enemy)

    game_map.update(0.1)

    assert ("tower_fired", {"tower_type": "laser", "position": Coordinate(0, 0)}) in events


def test_game_session_emits_tower_placed_event():
    session = GameSession()
    session.setup_game()
    events = []
    session.on_event = lambda name, **data: events.append((name, data))

    success = session.place_turret("laser", Coordinate(2300, 2000))

    assert success is True
    placed_position = session.map.modules[-1].position
    assert ("tower_placed", {"tower_type": "laser", "position": placed_position}) in events


def test_game_session_emits_enemy_died_event():
    session = GameSession()
    session.setup_game()
    enemy = session.enemy_factory.create("drone_walker", Coordinate(0, 0))
    enemy.health = 0
    session.map.enemies = [enemy]

    events = []
    session.on_event = lambda name, **data: events.append((name, data))
    session.update(delta_time=0.016)

    assert ("enemy_died", {"enemy_type": "drone_walker", "position": Coordinate(0, 0)}) in events


def test_game_session_emits_base_hit_event():
    session = GameSession()
    session.setup_game()
    enemy = DroneWalker(Coordinate(0, 0))
    enemy.set_path([Coordinate(0, 0)])
    enemy.path_index = 1
    session.map.enemies = [enemy]

    events = []
    session.on_event = lambda name, **data: events.append((name, data))
    session.update(delta_time=0.016)

    assert ("base_hit", {"position": Coordinate(2000, 2000)}) in events


def test_game_session_emits_victory_event():
    session = GameSession()
    session.setup_game()
    session.elapsed_time = session.survive_duration_target
    session.map.enemies = []

    events = []
    session.on_event = lambda name, **data: events.append((name, data))
    session.update(delta_time=0.016)

    assert ("victory", {}) in events


def test_game_session_emits_defeat_event():
    session = GameSession()
    session.setup_game()
    session.base_health = 5
    enemy = DroneWalker(Coordinate(0, 0))
    enemy.set_path([Coordinate(0, 0)])
    enemy.path_index = 1
    session.map.enemies = [enemy]

    events = []
    session.on_event = lambda name, **data: events.append((name, data))
    session.update(delta_time=0.016)

    assert ("defeat", {}) in events
