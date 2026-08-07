"""Файловое хранилище сохранений: несколько именованных слотов + один слот
быстрого сохранения (см. Settings.autosave_interval_seconds и
GameView._tick_autosave). Формат файлов - JSON (см. serializer.py)."""
import json
import sys
from datetime import datetime
from pathlib import Path

from src.save_load.serializer import apply_dict_to_session, session_to_dict

QUICKSAVE_SLOT_ID = "_quicksave"


def default_saves_dir() -> Path:
    """Путь к папке сохранений: рядом с исполняемым файлом при сборке PyInstaller,
    иначе в корне проекта при запуске из исходников (тот же принцип, что и у
    Settings.default_settings_path)."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return base / "saves"


class SaveManager:
    """Сохраняет/загружает GameSession в именованные JSON-слоты и слот быстрого
    сохранения. Ошибки чтения/записи (нет прав, битый файл) не бросают исключений -
    возвращают False/None, чтобы не ронять игру из-за проблем с диском."""

    def __init__(self, saves_dir: Path | None = None):
        """Создаёт менеджер сохранений с заданной или стандартной папкой."""
        self.saves_dir = Path(saves_dir) if saves_dir else default_saves_dir()

    def _path_for(self, slot_id: str) -> Path:
        """Путь к файлу слота по его id."""
        return self.saves_dir / f"{slot_id}.json"

    def _write(self, slot_id: str, session) -> bool:
        """Сериализует сессию и пишет её в файл слота."""
        try:
            self.saves_dir.mkdir(parents=True, exist_ok=True)
            data = session_to_dict(session)
            data["saved_at"] = datetime.now().isoformat(timespec="seconds")
            with open(self._path_for(slot_id), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except OSError:
            return False

    def save_to_new_slot(self, session) -> str | None:
        """Создаёт новый именованный слот с уникальным именем по текущему времени.
        Возвращает id созданного слота, или None при ошибке записи."""
        stamp = datetime.now().strftime("save_%Y%m%d_%H%M%S")
        slot_id = stamp
        suffix = 1
        while self._path_for(slot_id).exists():
            suffix += 1
            slot_id = f"{stamp}_{suffix}"
        return slot_id if self._write(slot_id, session) else None

    def save_to_slot(self, session, slot_id: str) -> bool:
        """Перезаписывает существующий именованный слот."""
        return self._write(slot_id, session)

    def quicksave(self, session) -> bool:
        """Перезаписывает единственный слот быстрого сохранения."""
        return self._write(QUICKSAVE_SLOT_ID, session)

    def load_slot(self, session, slot_id: str) -> bool:
        """Загружает слот в сессию. Возвращает False, если файл не найден/битый -
        сессия в этом случае не трогается."""
        try:
            with open(self._path_for(slot_id), encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return False
        try:
            apply_dict_to_session(session, data)
        except (KeyError, TypeError, ValueError, AttributeError):
            return False
        return True

    def list_slots(self) -> list[dict]:
        """Метаданные всех именованных слотов (без быстрого сохранения),
        отсортированные от новых к старым."""
        return self._read_metadata(include_quicksave=False)

    def quicksave_info(self) -> dict | None:
        """Метаданные слота быстрого сохранения, или None, если его ещё нет."""
        path = self._path_for(QUICKSAVE_SLOT_ID)
        if not path.exists():
            return None
        return self._read_one(path, QUICKSAVE_SLOT_ID)

    def has_any_save(self) -> bool:
        """Есть ли хоть одно сохранение (именованное или быстрое) - используется
        кнопкой "Продолжить" в главном меню."""
        return bool(self.list_slots()) or self.quicksave_info() is not None

    def most_recent_slot_id(self) -> str | None:
        """Id самого свежего по времени сохранения (именованного или быстрого) -
        используется кнопкой "Продолжить" в главном меню."""
        candidates = self.list_slots()
        quicksave = self.quicksave_info()
        if quicksave:
            candidates = candidates + [quicksave]
        if not candidates:
            return None
        return max(candidates, key=lambda info: info["saved_at"])["slot_id"]

    def _read_metadata(self, include_quicksave: bool) -> list[dict]:
        """Читает метаданные (без полного состояния карты) из всех файлов слотов."""
        if not self.saves_dir.is_dir():
            return []
        results = []
        for path in sorted(self.saves_dir.glob("*.json")):
            slot_id = path.stem
            if slot_id == QUICKSAVE_SLOT_ID and not include_quicksave:
                continue
            info = self._read_one(path, slot_id)
            if info:
                results.append(info)
        results.sort(key=lambda info: info["saved_at"], reverse=True)
        return results

    def _read_one(self, path: Path, slot_id: str) -> dict | None:
        """Читает метаданные одного файла слота, не поднимая исключений при ошибке."""
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None
        if not isinstance(data, dict):
            return None
        return {
            "slot_id": slot_id,
            "saved_at": data.get("saved_at", ""),
            "endless": data.get("endless", False),
            "elapsed_time": data.get("elapsed_time", 0.0),
        }
