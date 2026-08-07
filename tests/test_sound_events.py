"""Событийные хуки Map/GameSession и загрузка звуков в SoundManager."""
import os
import random

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.core.map import Map
from src.entities.enemies import DroneWalker
from src.entities.turrets import LaserTurret
from src.ui.sound_manager import SoundManager, discover_sound_files


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


def test_discover_sound_files_assigns_lower_weight_to_rare_subfolder(tmp_path):
    event_dir = tmp_path / "base_hit"
    event_dir.mkdir()
    (event_dir / "common.wav").write_bytes(b"x")
    rare_dir = event_dir / "rare"
    rare_dir.mkdir()
    (rare_dir / "alarm.wav").write_bytes(b"x")

    result = discover_sound_files(str(tmp_path))

    weights = {os.path.basename(path): weight for path, weight in result["base_hit"]}
    assert weights["common.wav"] == 1.0
    assert 0.0 < weights["alarm.wav"] < weights["common.wav"]


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

    def choices(self, population, weights=None, k=1):
        return [population[0]] * k

    def uniform(self, a, b):
        return 0.0


class _SeededRng:
    """Настоящий взвешенный/случайный выбор через random.Random с фиксированным seed."""

    def __init__(self, seed):
        self._random = random.Random(seed)

    def choice(self, seq):
        return self._random.choice(seq)

    def choices(self, population, weights=None, k=1):
        return self._random.choices(population, weights=weights, k=k)


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

    played = manager._sounds["base_hit"][0][0]
    assert played.play_calls == 1
    assert played.volume == 0.4


def test_sound_manager_reports_progress_after_each_file(tmp_path, monkeypatch):
    (tmp_path / "laser_fire").mkdir()
    (tmp_path / "laser_fire" / "a.wav").write_bytes(b"x")
    (tmp_path / "laser_fire" / "b.wav").write_bytes(b"x")
    (tmp_path / "base_hit").mkdir()
    (tmp_path / "base_hit" / "hit.wav").write_bytes(b"x")
    monkeypatch.setattr("src.ui.sound_manager.pygame", _FakePygame())

    calls = []
    SoundManager(sounds_root=str(tmp_path), rng=_FirstChoiceRng(),
                 on_progress=lambda done, total: calls.append((done, total)))

    assert calls == [(1, 3), (2, 3), (3, 3)], (
        "колбэк должен звать после каждого файла с нарастающим прогрессом — иначе загрузка "
        "звуков снова блокирует окно без откачки событий"
    )


def test_sound_manager_skips_progress_callback_when_not_given(tmp_path, monkeypatch):
    root = _make_sound_root(tmp_path, "base_hit", ["hit.wav"])
    monkeypatch.setattr("src.ui.sound_manager.pygame", _FakePygame())

    SoundManager(sounds_root=root, rng=_FirstChoiceRng())


def test_sound_manager_precomputes_pitch_variants_at_load_time(tmp_path, monkeypatch):
    root = _make_sound_root(tmp_path, "base_hit", ["hit.wav"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.sound_manager.pygame", fake_pygame)
    _FakeSound.created_via_buffer = []

    manager = SoundManager(sounds_root=root, rng=_FirstChoiceRng())

    variants = manager._sounds["base_hit"][0]
    assert len(variants) == manager.PITCH_VARIANTS + 1, "оригинал + заранее просчитанные вариации питча"
    assert len(_FakeSound.created_via_buffer) == manager.PITCH_VARIANTS


def test_sound_manager_play_does_not_resample_at_playback_time(tmp_path, monkeypatch):
    root = _make_sound_root(tmp_path, "base_hit", ["hit.wav"])
    monkeypatch.setattr("src.ui.sound_manager.pygame", _FakePygame())
    _FakeSound.created_via_buffer = []

    manager = SoundManager(sounds_root=root, rng=_FirstChoiceRng())
    created_at_load = len(_FakeSound.created_via_buffer)

    for _ in range(50):
        manager.play("base_hit")

    assert len(_FakeSound.created_via_buffer) == created_at_load, (
        "play() не должен ресемплировать на лету (это и вызывало статтер) — "
        "только переиспользовать готовые вариации"
    )


def test_sound_manager_play_respects_cooldown_between_calls(tmp_path, monkeypatch):
    root = _make_sound_root(tmp_path, "base_hit", ["hit.wav"])
    monkeypatch.setattr("src.ui.sound_manager.pygame", _FakePygame())

    manager = SoundManager(sounds_root=root, rng=_FirstChoiceRng())
    sound = manager._sounds["base_hit"][0][0]

    manager.play("base_hit", cooldown=2.0)
    manager.play("base_hit", cooldown=2.0)
    manager.play("base_hit", cooldown=2.0)

    assert sound.play_calls == 1, "повторные вызовы внутри кулдауна не должны проигрывать звук снова"

    manager.update(2.0)
    manager.play("base_hit", cooldown=2.0)

    assert sound.play_calls == 2, "после истечения кулдауна звук должен проиграться снова"


def test_sound_manager_update_ticks_down_cooldown_partially(tmp_path, monkeypatch):
    root = _make_sound_root(tmp_path, "base_hit", ["hit.wav"])
    monkeypatch.setattr("src.ui.sound_manager.pygame", _FakePygame())

    manager = SoundManager(sounds_root=root, rng=_FirstChoiceRng())
    sound = manager._sounds["base_hit"][0][0]

    manager.play("base_hit", cooldown=2.0)
    manager.update(1.0)
    manager.play("base_hit", cooldown=2.0)

    assert sound.play_calls == 1, "кулдаун ещё не истёк полностью"


def test_sound_manager_play_without_cooldown_always_plays(tmp_path, monkeypatch):
    root = _make_sound_root(tmp_path, "tower_placed", ["a.wav"])
    monkeypatch.setattr("src.ui.sound_manager.pygame", _FakePygame())

    manager = SoundManager(sounds_root=root, rng=_FirstChoiceRng())
    sound = manager._sounds["tower_placed"][0][0]

    manager.play("tower_placed")
    manager.play("tower_placed")

    assert sound.play_calls == 2, "события без кулдауна должны проигрываться каждый раз"


def test_sound_manager_rarely_plays_files_from_the_rare_subfolder(tmp_path, monkeypatch):
    event_dir = tmp_path / "base_hit"
    event_dir.mkdir()
    (event_dir / "common.wav").write_bytes(b"x")
    rare_dir = event_dir / "rare"
    rare_dir.mkdir()
    (rare_dir / "alarm.wav").write_bytes(b"x")
    monkeypatch.setattr("src.ui.sound_manager.pygame", _FakePygame())

    manager = SoundManager(sounds_root=str(tmp_path), rng=_SeededRng(seed=1))
    common_variants = next(g for g in manager._sounds["base_hit"] if g[0].path.endswith("common.wav"))
    rare_variants = next(g for g in manager._sounds["base_hit"] if g[0].path.endswith("alarm.wav"))

    for _ in range(2000):
        manager.play("base_hit")

    common_plays = sum(s.play_calls for s in common_variants)
    rare_plays = sum(s.play_calls for s in rare_variants)
    rare_share = rare_plays / (common_plays + rare_plays)
    assert rare_share < 0.15, "файл из rare/ не должен звучать почти так же часто, как обычный"


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


def test_game_session_place_turret_does_not_emit_tower_placed_immediately():
    session = GameSession()
    session.setup_game()
    events = []
    session.on_event = lambda name, **data: events.append((name, data))

    success = session.place_turret("laser", Coordinate(2300, 2000))

    assert success is True
    assert not any(e[0] == "tower_placed" for e in events), (
        "звук установки должен играть при приземлении башни, а не сразу при клике"
    )


def test_game_session_emits_tower_placed_event_once_the_tower_lands():
    session = GameSession()
    session.setup_game()
    success = session.place_turret("laser", Coordinate(2300, 2000))
    assert success is True
    placed_position = session.map.modules[-1].position

    events = []
    session.on_event = lambda name, **data: events.append((name, data))
    for _ in range(50):
        session.map.update(0.1)

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

    assert ("base_hit", {"position": session.base_position}) in events


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
