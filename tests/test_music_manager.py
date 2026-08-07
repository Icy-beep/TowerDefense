"""Категории фоновой музыки и MusicManager."""
from src.ui.music_manager import MusicManager, discover_music_files


def test_discover_music_files_groups_by_subfolder_and_filters_extensions(tmp_path):
    (tmp_path / "menu").mkdir()
    (tmp_path / "menu" / "a.mp3").write_bytes(b"x")
    (tmp_path / "menu" / "b.ogg").write_bytes(b"x")
    (tmp_path / "menu" / "notes.txt").write_bytes(b"x")
    (tmp_path / "empty_category").mkdir()

    result = discover_music_files(str(tmp_path))

    assert set(result.keys()) == {"menu"}
    assert len(result["menu"]) == 2


def test_discover_music_files_returns_empty_dict_for_missing_root(tmp_path):
    assert discover_music_files(str(tmp_path / "does_not_exist")) == {}


class _FakeError(Exception):
    pass


class _FakeMusic:
    def __init__(self, fail_load=False):
        self._fail_load = fail_load
        self.loaded_path = None
        self.play_calls = []
        self.volume = None
        self.fadeout_calls = []
        # Свежепоставленный трек считается играющим, пока тест явно не скажет,
        # что он закончился (см. update() в MusicManager).
        self.busy = True

    def load(self, path):
        if self._fail_load:
            raise _FakeError("не удалось загрузить трек")
        self.loaded_path = path

    def play(self, loops=0, fade_ms=0):
        self.play_calls.append((loops, fade_ms))
        self.busy = True

    def get_busy(self):
        return self.busy

    def fadeout(self, ms):
        self.fadeout_calls.append(ms)

    def set_volume(self, volume):
        self.volume = volume


class _FakeMixer:
    def __init__(self, fail_load=False, fail_init=False):
        self._initialized = False
        self._fail_init = fail_init
        self.music = _FakeMusic(fail_load=fail_load)

    def get_init(self):
        return (44100, -16, 2) if self._initialized else None

    def init(self):
        if self._fail_init:
            raise _FakeError("нет звукового устройства")
        self._initialized = True


class _FakePygame:
    def __init__(self, fail_load=False, fail_init=False):
        self.mixer = _FakeMixer(fail_load=fail_load, fail_init=fail_init)
        self.error = _FakeError


class _FirstChoiceRng:
    def choice(self, seq):
        return seq[0]


def _make_music_root(tmp_path, category, filenames):
    category_dir = tmp_path / category
    category_dir.mkdir()
    for filename in filenames:
        (category_dir / filename).write_bytes(b"x")
    return str(tmp_path)


def test_music_manager_plays_random_track_from_category_with_fade_in(tmp_path, monkeypatch):
    root = _make_music_root(tmp_path, "menu", ["a.mp3"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.music_manager.pygame", fake_pygame)

    manager = MusicManager(music_root=root, volume=0.3, rng=_FirstChoiceRng())
    manager.play_category("menu")

    assert fake_pygame.mixer.music.loaded_path.endswith("a.mp3")
    # loops=0, а не -1: один и тот же трек больше не крутится бесконечно сам по себе -
    # следующий выбирает update(), когда текущий доиграет (см. тесты ниже).
    assert fake_pygame.mixer.music.play_calls == [(0, manager.FADE_IN_MS)]
    assert manager.current_category == "menu"


def test_music_manager_does_not_restart_the_same_category(tmp_path, monkeypatch):
    root = _make_music_root(tmp_path, "menu", ["a.mp3"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.music_manager.pygame", fake_pygame)

    manager = MusicManager(music_root=root, rng=_FirstChoiceRng())
    manager.play_category("menu")
    manager.play_category("menu")

    assert len(fake_pygame.mixer.music.play_calls) == 1, "повторный вызов той же категории не перезапускает трек"


def test_music_manager_switches_between_categories(tmp_path, monkeypatch):
    _make_music_root(tmp_path, "menu", ["a.mp3"])
    _make_music_root(tmp_path, "gameplay", ["b.mp3"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.music_manager.pygame", fake_pygame)

    manager = MusicManager(music_root=str(tmp_path), rng=_FirstChoiceRng())
    manager.play_category("menu")
    manager.play_category("gameplay")

    assert fake_pygame.mixer.music.loaded_path.endswith("b.mp3")
    assert len(fake_pygame.mixer.music.play_calls) == 2
    assert manager.current_category == "gameplay"


def test_music_manager_play_category_is_a_no_op_for_unknown_category(tmp_path, monkeypatch):
    root = _make_music_root(tmp_path, "menu", ["a.mp3"])
    monkeypatch.setattr("src.ui.music_manager.pygame", _FakePygame())

    manager = MusicManager(music_root=root, rng=_FirstChoiceRng())
    manager.play_category("no_such_category")

    assert manager.current_category is None


def test_music_manager_play_category_leaves_state_untouched_on_load_failure(tmp_path, monkeypatch):
    root = _make_music_root(tmp_path, "menu", ["a.mp3"])
    monkeypatch.setattr("src.ui.music_manager.pygame", _FakePygame(fail_load=True))

    manager = MusicManager(music_root=root, rng=_FirstChoiceRng())
    manager.play_category("menu")

    assert manager.current_category is None


def test_music_manager_stop_fades_out_and_clears_current_category(tmp_path, monkeypatch):
    root = _make_music_root(tmp_path, "menu", ["a.mp3"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.music_manager.pygame", fake_pygame)

    manager = MusicManager(music_root=root, rng=_FirstChoiceRng())
    manager.play_category("menu")
    manager.stop()

    assert fake_pygame.mixer.music.fadeout_calls == [manager.FADE_IN_MS]
    assert manager.current_category is None


def test_music_manager_set_volume_clamps_and_applies_to_mixer_music(tmp_path, monkeypatch):
    root = _make_music_root(tmp_path, "menu", ["a.mp3"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.music_manager.pygame", fake_pygame)

    manager = MusicManager(music_root=root, rng=_FirstChoiceRng())
    manager.set_volume(1.5)

    assert manager.volume == 1.0
    assert fake_pygame.mixer.music.volume == 1.0


def test_music_manager_disables_itself_when_mixer_init_fails(tmp_path, monkeypatch):
    root = _make_music_root(tmp_path, "menu", ["a.mp3"])
    monkeypatch.setattr("src.ui.music_manager.pygame", _FakePygame(fail_init=True))

    manager = MusicManager(music_root=root, rng=_FirstChoiceRng())

    assert manager.enabled is False
    manager.play_category("menu")
    assert manager.current_category is None


def test_update_starts_next_track_when_current_one_finishes(tmp_path, monkeypatch):
    root = _make_music_root(tmp_path, "gameplay", ["a.mp3", "b.mp3"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.music_manager.pygame", fake_pygame)

    manager = MusicManager(music_root=root, rng=_FirstChoiceRng())
    manager.play_category("gameplay")
    fake_pygame.mixer.music.busy = False

    manager.update(0.1)

    assert len(fake_pygame.mixer.music.play_calls) == 2


def test_update_does_nothing_while_track_still_playing(tmp_path, monkeypatch):
    root = _make_music_root(tmp_path, "gameplay", ["a.mp3", "b.mp3"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.music_manager.pygame", fake_pygame)

    manager = MusicManager(music_root=root, rng=_FirstChoiceRng())
    manager.play_category("gameplay")

    manager.update(0.1)

    assert len(fake_pygame.mixer.music.play_calls) == 1


def test_update_avoids_repeating_same_track_immediately_when_alternatives_exist(tmp_path, monkeypatch):
    root = _make_music_root(tmp_path, "gameplay", ["a.mp3", "b.mp3"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.music_manager.pygame", fake_pygame)

    manager = MusicManager(music_root=root, rng=_FirstChoiceRng())
    manager.play_category("gameplay")
    first_track = fake_pygame.mixer.music.loaded_path
    fake_pygame.mixer.music.busy = False

    manager.update(0.1)

    assert fake_pygame.mixer.music.loaded_path != first_track


def test_update_does_not_advance_when_loop_is_false(tmp_path, monkeypatch):
    root = _make_music_root(tmp_path, "gameplay", ["a.mp3", "b.mp3"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.music_manager.pygame", fake_pygame)

    manager = MusicManager(music_root=root, rng=_FirstChoiceRng())
    manager.play_category("gameplay", loop=False)
    fake_pygame.mixer.music.busy = False

    manager.update(0.1)

    assert len(fake_pygame.mixer.music.play_calls) == 1


def test_update_is_a_no_op_when_nothing_is_playing(tmp_path, monkeypatch):
    root = _make_music_root(tmp_path, "gameplay", ["a.mp3"])
    fake_pygame = _FakePygame()
    monkeypatch.setattr("src.ui.music_manager.pygame", fake_pygame)

    manager = MusicManager(music_root=root, rng=_FirstChoiceRng())

    manager.update(0.1)  # не должно падать

    assert fake_pygame.mixer.music.play_calls == []


def test_music_manager_has_tracks_for(tmp_path, monkeypatch):
    root = _make_music_root(tmp_path, "menu", ["a.mp3"])
    monkeypatch.setattr("src.ui.music_manager.pygame", _FakePygame())

    manager = MusicManager(music_root=root, rng=_FirstChoiceRng())

    assert manager.has_tracks_for("menu") is True
    assert manager.has_tracks_for("gameplay") is False
