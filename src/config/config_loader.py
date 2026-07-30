import json
import sys
from pathlib import Path
from typing import Dict


def _default_config_dir() -> Path:
    """Возвращает путь к папке с конфигами по умолчанию."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return base / "data" / "config"


DEFAULT_CONFIG_DIR = _default_config_dir()


class ConfigLoader:
    """Загружает и кэширует конфиги башен и врагов из JSON."""

    def __init__(self, config_dir: Path = None):
        """Создаёт загрузчик с заданной или стандартной папкой конфигов."""
        self.config_dir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
        self._cache: Dict[str, dict] = {}

    def _load_file(self, filename: str) -> dict:
        """Загружает и кэширует JSON-файл конфига."""
        if filename not in self._cache:
            path = self.config_dir / filename
            with open(path, encoding="utf-8") as f:
                self._cache[filename] = json.load(f)
        return self._cache[filename]

    def get_tower_config(self, type_name: str) -> dict:
        """Возвращает параметры башни заданного типа."""
        try:
            return dict(self._load_file("towers.json").get(type_name, {}))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def get_enemy_config(self, type_name: str) -> dict:
        """Возвращает параметры врага заданного типа."""
        try:
            return dict(self._load_file("enemies.json").get(type_name, {}))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
