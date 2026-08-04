"""Настройки игрока: загрузка/сохранение в JSON, значения по умолчанию, клэмп громкости."""
from src.core.settings import Settings, DISPLAY_MODE_WINDOWED, DISPLAY_MODE_FULLSCREEN


def test_load_returns_defaults_when_file_missing(tmp_path):
    settings = Settings.load(tmp_path / "does_not_exist.json")

    assert settings.display_mode == DISPLAY_MODE_WINDOWED
    assert settings.resolution == (900, 600)
    assert settings.language == "ru"


def test_load_returns_defaults_for_malformed_json(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not valid json", encoding="utf-8")

    settings = Settings.load(path)

    assert settings == Settings()


def test_save_then_load_roundtrips_all_fields(tmp_path):
    path = tmp_path / "settings.json"
    original = Settings(display_mode=DISPLAY_MODE_FULLSCREEN, resolution=(1920, 1080),
                         music_volume=0.2, sfx_volume=0.7, language="en")

    original.save(path)
    loaded = Settings.load(path)

    assert loaded == original


def test_load_ignores_unknown_keys(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"language": "en", "totally_unknown_field": 123}', encoding="utf-8")

    settings = Settings.load(path)

    assert settings.language == "en"
    assert not hasattr(settings, "totally_unknown_field")


def test_load_converts_resolution_list_to_tuple(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"resolution": [1600, 900]}', encoding="utf-8")

    settings = Settings.load(path)

    assert settings.resolution == (1600, 900)
    assert isinstance(settings.resolution, tuple)


def test_save_ignores_write_errors(tmp_path):
    settings = Settings()
    unwritable_dir_as_file_path = tmp_path / "not_a_directory"
    unwritable_dir_as_file_path.write_text("x", encoding="utf-8")

    settings.save(unwritable_dir_as_file_path / "settings.json")


def test_clamp_volumes_keeps_values_in_zero_one_range():
    settings = Settings(music_volume=1.5, sfx_volume=-0.3)

    settings.clamp_volumes()

    assert settings.music_volume == 1.0
    assert settings.sfx_volume == 0.0
