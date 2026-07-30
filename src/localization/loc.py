"""Хранилище текста интерфейса."""
import json
import sys
from pathlib import Path
from typing import Dict, Optional

DEFAULT_LANGUAGE = "ru"


def _default_locale_dir() -> Path:
    """Возвращает путь к папке с файлами локализации по умолчанию."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return base / "data" / "locale"


DEFAULT_LOCALE_DIR = _default_locale_dir()


class Loc:
    """Загружает и возвращает переведённые строки интерфейса."""

    def __init__(self, language: str = DEFAULT_LANGUAGE, locale_dir: Optional[Path] = None):
        """Создаёт локализацию для заданного языка."""
        self.language = language
        self.locale_dir = Path(locale_dir) if locale_dir else DEFAULT_LOCALE_DIR
        self._cache: Dict[str, dict] = {}

    def _strings(self) -> dict:
        """Загружает и кэширует словарь строк текущего языка."""
        if self.language not in self._cache:
            path = self.locale_dir / f"{self.language}.json"
            try:
                with open(path, encoding="utf-8") as f:
                    self._cache[self.language] = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                self._cache[self.language] = {}
        return self._cache[self.language]

    def get(self, key: str, **kwargs) -> str:
        """Возвращает строку по ключу с подстановкой значений."""
        template = self._strings().get(key)
        if template is None:
            return f"[{key}]"
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return template


loc = Loc()
