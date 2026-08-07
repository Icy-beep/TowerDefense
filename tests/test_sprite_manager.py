"""Загрузка спрайтов и смена кадров анимации в SpriteManager."""
from src.ui.sprite_manager import SpriteManager, discover_sprite_files


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


class _FakeRect:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def width(self):
        return self.w

    @property
    def height(self):
        return self.h


class _FakeSurface:
    def __init__(self, path, size=(10, 10), content_rect=None):
        self.path = path
        self.size = size
        self.content_rect = content_rect or _FakeRect(0, 0, size[0], size[1])
        self.cropped_to = None

    def convert_alpha(self):
        return self

    def get_width(self):
        return self.size[0]

    def get_height(self):
        return self.size[1]

    def get_bounding_rect(self, min_alpha=1):
        return self.content_rect

    def subsurface(self, rect):
        if isinstance(rect, tuple):
            x, y, w, h = rect
        else:
            x, y, w, h = rect.x, rect.y, rect.width, rect.height
        cropped = _FakeSurface(self.path, size=(w, h))
        cropped.cropped_to = (x, y, w, h)
        return cropped

    def copy(self):
        return self


class _FakeImageModule:
    def load(self, path):
        if "broken" in path:
            raise _FakeError("не удалось загрузить изображение")
        if "padded" in path:
            return _FakeSurface(path, size=(10, 10), content_rect=_FakeRect(2, 2, 4, 4))
        if "shape_tall" in path:
            return _FakeSurface(path, size=(20, 20), content_rect=_FakeRect(5, 2, 10, 16))
        if "shape_wide" in path:
            return _FakeSurface(path, size=(20, 20), content_rect=_FakeRect(2, 5, 16, 10))
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


def test_sprite_manager_autocrops_transparent_padding(tmp_path, monkeypatch):
    root = _make_sprite_root(tmp_path, "tower_laser", ["padded.png"])
    monkeypatch.setattr("src.ui.sprite_manager.pygame", _FakePygame())

    manager = SpriteManager(sprites_root=root)

    frame = manager.get_frame("tower_laser")
    assert frame.size == (4, 4)
    assert frame.cropped_to == (2, 2, 4, 4)


def test_sprite_manager_does_not_crop_when_content_fills_canvas(tmp_path, monkeypatch):
    root = _make_sprite_root(tmp_path, "base", ["only.png"])
    monkeypatch.setattr("src.ui.sprite_manager.pygame", _FakePygame())

    manager = SpriteManager(sprites_root=root)

    frame = manager.get_frame("base")
    assert frame.cropped_to is None


def test_sprite_manager_crops_multi_frame_group_to_one_shared_box(tmp_path, monkeypatch):
    """Регрессия: раньше каждый кадр обрезался по своей собственной рамке, из-за чего у
    кадров с разной формой силуэта (например, повёрнутая по диагонали башня против
    повёрнутой прямо) получались разные пропорции — и после масштабирования под общий
    target_size они визуально отличались по размеру. Теперь у всех кадров одной папки
    общая рамка обрезки."""
    root = _make_sprite_root(tmp_path, "tower_laser", ["shape_tall.png", "shape_wide.png"])
    monkeypatch.setattr("src.ui.sprite_manager.pygame", _FakePygame())

    manager = SpriteManager(sprites_root=root)
    frames = manager._frames["tower_laser"]

    assert frames[0].size == frames[1].size == (16, 16)
    assert frames[0].cropped_to == (2, 2, 16, 16)
    assert frames[1].cropped_to == (2, 2, 16, 16)


def test_get_frame_for_angle_single_file_ignores_angle(tmp_path, monkeypatch):
    root = _make_sprite_root(tmp_path, "tower_laser", ["only.png"])
    monkeypatch.setattr("src.ui.sprite_manager.pygame", _FakePygame())

    manager = SpriteManager(sprites_root=root)

    at_zero = manager.get_frame_for_angle("tower_laser", 0.0)
    at_180 = manager.get_frame_for_angle("tower_laser", 180.0)
    assert at_zero is at_180
    assert at_zero.path.endswith("only.png")


def test_get_frame_for_angle_picks_nearest_directional_frame(tmp_path, monkeypatch):
    root = _make_sprite_root(tmp_path, "tower_laser",
                              ["dir_00.png", "dir_01.png", "dir_02.png", "dir_03.png"])
    monkeypatch.setattr("src.ui.sprite_manager.pygame", _FakePygame())

    manager = SpriteManager(sprites_root=root)

    assert manager.get_frame_for_angle("tower_laser", 10.0).path.endswith("dir_00.png")
    assert manager.get_frame_for_angle("tower_laser", 100.0).path.endswith("dir_01.png")
    assert manager.get_frame_for_angle("tower_laser", 200.0).path.endswith("dir_02.png")


def test_get_frame_for_angle_wraps_around_360_degrees(tmp_path, monkeypatch):
    root = _make_sprite_root(tmp_path, "tower_laser",
                              ["dir_00.png", "dir_01.png", "dir_02.png", "dir_03.png"])
    monkeypatch.setattr("src.ui.sprite_manager.pygame", _FakePygame())

    manager = SpriteManager(sprites_root=root)

    assert manager.get_frame_for_angle("tower_laser", 350.0).path.endswith("dir_00.png")
    assert manager.get_frame_for_angle("tower_laser", -10.0).path.endswith("dir_00.png")
