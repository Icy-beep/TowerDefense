"""Настройки игрока (экран, звук, язык) с сохранением в JSON рядом с игрой."""
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Tuple

DISPLAY_MODE_WINDOWED = "windowed"
DISPLAY_MODE_BORDERLESS = "borderless"
DISPLAY_MODE_FULLSCREEN = "fullscreen"
DISPLAY_MODES = [DISPLAY_MODE_WINDOWED, DISPLAY_MODE_BORDERLESS, DISPLAY_MODE_FULLSCREEN]

RESOLUTIONS = [
    (900, 600),
    (1024, 768),
    (1280, 720),
    (1366, 768),
    (1600, 900),
    (1920, 1080),
]

VOLUME_STEP = 0.1

AUTOSAVE_STEP_SECONDS = 30
AUTOSAVE_MIN_SECONDS = 0  # 0 = автосохранение выключено
AUTOSAVE_MAX_SECONDS = 300


def default_settings_path() -> Path:
    """Путь к settings.json: рядом с исполняемым файлом при сборке PyInstaller,
    иначе в корне проекта (при запуске из исходников)."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return base / "settings.json"


@dataclass
class Settings:
    """Настройки игрока. Значения по умолчанию совпадают с прежним поведением игры
    (оконный режим 900x600, прежние базовые громкости SoundManager/MusicManager)."""

    display_mode: str = DISPLAY_MODE_WINDOWED
    resolution: Tuple[int, int] = (900, 600)
    music_volume: float = 0.35
    sfx_volume: float = 0.45
    language: str = "ru"
    autosave_interval_seconds: float = 60.0

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Settings":
        """Читает настройки из JSON; при отсутствии файла или ошибке чтения — значения
        по умолчанию. Неизвестные ключи в файле игнорируются, чтобы старый settings.json
        не ломал загрузку после добавления новых полей."""
        path = path or default_settings_path()
        settings = cls()
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return settings

        if not isinstance(data, dict):
            return settings

        for field_name in settings.__dataclass_fields__:
            if field_name in data:
                setattr(settings, field_name, data[field_name])

        if isinstance(settings.resolution, list):
            settings.resolution = tuple(settings.resolution)

        return settings

    def save(self, path: Optional[Path] = None):
        """Сохраняет настройки в JSON. Ошибки записи (нет прав на диск и т.п.) тихо
        игнорируются — отсутствие сохранения не должно ронять игру."""
        path = path or default_settings_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def clamp_volumes(self):
        """Ограничивает громкости диапазоном 0.0-1.0 после ручного изменения."""
        self.music_volume = round(max(0.0, min(1.0, self.music_volume)), 2)
        self.sfx_volume = round(max(0.0, min(1.0, self.sfx_volume)), 2)

    def clamp_autosave_interval(self):
        """Ограничивает промежуток автосохранения диапазоном
        [AUTOSAVE_MIN_SECONDS, AUTOSAVE_MAX_SECONDS] после ручного изменения. 0 -
        автосохранение выключено (см. GameView._tick_autosave)."""
        self.autosave_interval_seconds = max(AUTOSAVE_MIN_SECONDS,
                                              min(AUTOSAVE_MAX_SECONDS, self.autosave_interval_seconds))
