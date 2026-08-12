"""Папка для пользовательских данных (сохранения, settings.json) - общая логика
для SaveManager.default_saves_dir и Settings.default_settings_path."""
import os
import sys
from pathlib import Path

APP_NAME = "Concession"


def user_data_dir() -> Path:
    """Папка для сохранений/настроек: %LOCALAPPDATA%/Concession при сборке
    PyInstaller, иначе корень проекта при запуске из исходников.

    Игрок обычно скачивает один портативный .exe и запускает его прямо из
    Загрузок, не распаковывая в отдельную папку - раньше файлы писались рядом с
    .exe, то есть прямо в Загрузки вперемешку с другими файлами (см. жалобу
    пользователя). %LOCALAPPDATA% - стандартное место Windows для
    пользовательских данных приложения, не зависящее от того, где лежит .exe."""
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
        return base / APP_NAME
    return Path(__file__).resolve().parent.parent.parent
