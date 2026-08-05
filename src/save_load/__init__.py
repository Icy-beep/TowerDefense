"""Сохранение/загрузка игры: именованные слоты + быстрое сохранение (JSON,
см. save_manager.py и serializer.py)."""
from src.save_load.save_manager import SaveManager, QUICKSAVE_SLOT_ID

__all__ = ["SaveManager", "QUICKSAVE_SLOT_ID"]
