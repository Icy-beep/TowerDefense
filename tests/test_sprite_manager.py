"""Загрузка спрайтов и смена кадров анимации в SpriteManager."""
from src.ui.sprite_manager import discover_sprite_files, SpriteManager


def test_discover_sprite_files_groups_by_subfolder_and_filters_extensions(tmp_path):
    (tmp_path / "tower_laser").mkdir()
    (tmp_path / "tower_laser" / "a.png").write_bytes(b"x")
    (tmp_path / "tower_laser" / "b.png").write_bytes(b"x")
    (tmp_path / "tower_laser" / "notes.txt").write_bytes(b"x")
    (tmp_path / "empty_key").mkdir()

    result = discover_sprite_files(str(tmp_path))

    assert set(result.keys()) == {"tower_laser"}
    assert len(result["tower_laser"]) == 2


def test_discover_sprite_files_returns_empty_dict_for_missing_root(tmp_path):
    assert discover_sprite_files(str(tmp_path / "does_not_exist")) == {}


class _FakeError(Exception):
    pass


class _FakeSurface:
    def __init__(self, path):
        self.path = path

    def convert_alpha(self):
        return self


class _FakeImageModule:
    def load(self, path):
        if "broken" in path:
            raise _FakeError("не удалось загрузить изображение")
        return _FakeSurface(path)


class _FakePygame:
    def __init__(self):
        self.image = _FakeImageModule()
        self.error = _FakeError


def _make_sprite_root(tmp_path, key, filenames):
    key_dir = tmp_path / key
    key_dir.mkdir()
    for filename in filenames:
        (key_dir / filename).write_bytes(b"x")
    return str(tmp_path)


def test_sprite_manager_loads_valid_files_and_skips_broken_ones(tmp_path, monkeypatch):
    root = _make_sprite_root(tmp_path, "tower_laser", ["a.png", "broken.png"])
    monkeypatch.setattr("src.ui.sprite_manager.pygame", _FakePygame())

    manager = SpriteManager(sprites_root=root)

    assert manager.has_sprite_for("tower_laser") is True
    assert len(manager._frames["tower_laser"]) == 1


def test_sprite_manager_get_frame_returns_none_for_unknown_key(tmp_path, monkeypatch):
    root = _make_sprite_root(tmp_path, "tower_laser", ["a.png"])
    monkeypatch.setattr("src.ui.sprite_manager.pygame", _FakePygame())

    manager = SpriteManager(sprites_root=root)

    assert manager.get_frame("no_such_key") is None
    assert manager.has_sprite_for("no_such_key") is False


def test_sprite_manager_single_file_is_a_static_sprite(tmp_path, monkeypatch):
    root = _make_sprite_root(tmp_path, "base", ["only.png"])
    monkeypatch.setattr("src.ui.sprite_manager.pygame", _FakePygame())

    manager = SpriteManager(sprites_root=root)

    frame_at_0 = manager.get_frame("base", elapsed_time=0.0)
    frame_at_5 = manager.get_frame("base", elapsed_time=5.0)

    assert frame_at_0 is frame_at_5
    assert frame_at_0.path.endswith("only.png")


def test_sprite_manager_multiple_files_cycle_as_animation(tmp_path, monkeypatch):
    root = _make_sprite_root(tmp_path, "enemy_drone_walker", ["frame_1.png", "frame_2.png"])
    monkeypatch.setattr("src.ui.sprite_manager.pygame", _FakePygame())

    manager = SpriteManager(sprites_root=root)
    step = 1.0 / manager.ANIMATION_FPS

    first = manager.get_frame("enemy_drone_walker", elapsed_time=0.0)
    second = manager.get_frame("enemy_drone_walker", elapsed_time=step)
    back_to_first = manager.get_frame("enemy_drone_walker", elapsed_time=step * 2)

    assert first.path.endswith("frame_1.png")
    assert second.path.endswith("frame_2.png")
    assert back_to_first.path.endswith("frame_1.png")


def test_sprite_manager_reports_progress_after_each_file(tmp_path, monkeypatch):
    (tmp_path / "tower_laser").mkdir()
    (tmp_path / "tower_laser" / "a.png").write_bytes(b"x")
    (tmp_path / "tower_laser" / "b.png").write_bytes(b"x")
    (tmp_path / "base").mkdir()
    (tmp_path / "base" / "only.png").write_bytes(b"x")
    monkeypatch.setattr("src.ui.sprite_manager.pygame", _FakePygame())

    calls = []
    SpriteManager(sprites_root=str(tmp_path), on_progress=lambda done, total: calls.append((done, total)))

    assert calls == [(1, 3), (2, 3), (3, 3)]
