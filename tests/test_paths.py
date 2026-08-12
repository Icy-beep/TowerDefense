"""Пути к пользовательским данным (см. src/core/paths.py) - регрессия на жалобу
пользователя: скачанный .exe запускается прямо из Загрузок, и без выделенной
папки в %LOCALAPPDATA% сохранения/настройки писались бы туда же, вперемешку с
другими файлами."""
from pathlib import Path

from src.core.paths import user_data_dir
from src.core.settings import default_settings_path
from src.save_load.save_manager import default_saves_dir


def test_user_data_dir_is_project_root_when_not_frozen(monkeypatch):
    monkeypatch.delattr("sys.frozen", raising=False)

    result = user_data_dir()

    assert (result / "pyproject.toml").is_file(), "должен указывать на корень проекта"


def test_user_data_dir_uses_local_app_data_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    result = user_data_dir()

    assert result == tmp_path / "Concession"


def test_user_data_dir_falls_back_without_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = user_data_dir()

    assert result == tmp_path / ".local" / "share" / "Concession"


def test_default_saves_dir_is_a_saves_subfolder_of_user_data_dir():
    assert default_saves_dir() == user_data_dir() / "saves"


def test_default_settings_path_is_settings_json_in_user_data_dir():
    assert default_settings_path() == user_data_dir() / "settings.json"
