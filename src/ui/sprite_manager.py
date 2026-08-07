"""Загрузка и отдача спрайтов из assets/sprites/."""
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path

import pygame

logger = logging.getLogger(__name__)


def _default_sprites_root() -> str:
    """Путь к папке спрайтов: внутри временной распаковки PyInstaller (_MEIPASS)
    при сборке в .exe, иначе в корне проекта при запуске из исходников (тот же
    принцип, что и у ConfigLoader/Loc - см. src/config/config_loader.py)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return str(base / "assets" / "sprites")


DEFAULT_SPRITES_ROOT = _default_sprites_root()
SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp")


def discover_sprite_files(sprites_root: str) -> dict[str, list[str]]:
    """Сканирует sprites_root и возвращает {ключ: [пути к кадрам]}."""
    result: dict[str, list[str]] = {}
    if not os.path.isdir(sprites_root):
        return result

    for key in sorted(os.listdir(sprites_root)):
        key_dir = os.path.join(sprites_root, key)
        if not os.path.isdir(key_dir):
            continue
        files = [
            os.path.join(key_dir, filename)
            for filename in sorted(os.listdir(key_dir))
            if filename.lower().endswith(SUPPORTED_EXTENSIONS)
        ]
        if files:
            result[key] = files

    return result


class SpriteManager:
    """Отдаёт кадры спрайтов по ключу (тип башни/врага/...).

    Ключи без загруженных спрайтов просто возвращают None из get_frame — рендерер должен
    сам падать обратно на отрисовку примитивами, если спрайта ещё нет. Так можно добавлять
    визуал постепенно, по одной папке, ничего не ломая на полпути."""

    ANIMATION_FPS = 8.0

    def __init__(self, sprites_root: str = DEFAULT_SPRITES_ROOT,
                 on_progress: Callable[[int, int], None] | None = None):
        """Загружает все найденные спрайты; несколько файлов в папке = кадры анимации.

        on_progress(done, total), если задан, вызывается после каждого файла — так же,
        как у SoundManager, чтобы загрузка большого количества спрайтов не подвешивала окно."""
        self.enabled = True
        self._frames: dict[str, list[pygame.Surface]] = {}

        entries_by_key = discover_sprite_files(sprites_root)
        total_files = sum(len(paths) for paths in entries_by_key.values())
        loaded_files = 0

        for key, paths in entries_by_key.items():
            loaded = []
            for path in paths:
                try:
                    image = pygame.image.load(path).convert_alpha()
                except pygame.error:
                    continue
                loaded.append(image)
                loaded_files += 1
                if on_progress:
                    on_progress(loaded_files, total_files)
            if loaded:
                self._frames[key] = self._autocrop_group(loaded)

    def _autocrop_group(self, frames: list[pygame.Surface]) -> list[pygame.Surface]:
        """Обрезает все кадры одной папки по ОДНОЙ общей рамке — объединению непрозрачных
        областей всех кадров, а не каждый кадр по своей собственной. Если обрезать каждый кадр
        индивидуально, у кадров с разной формой силуэта (например, башня повёрнута под разными
        углами — по диагонали силуэт шире, чем по вертикали/горизонтали) получатся разные
        пропорции обрезки, и после масштабирования всех кадров под общий target_size они будут
        визуально отличаться по размеру, хотя на исходных холстах занимали одну и ту же область."""
        try:
            bounds_list = [frame.get_bounding_rect(min_alpha=1) for frame in frames]
        except Exception:
            logger.warning("Не удалось вычислить общую рамку обрезки спрайтов", exc_info=True)
            return frames
        bounds_list = [b for b in bounds_list if b.width > 0 and b.height > 0]
        if not bounds_list:
            return frames

        min_x = min(b.x for b in bounds_list)
        min_y = min(b.y for b in bounds_list)
        max_x = max(b.x + b.width for b in bounds_list)
        max_y = max(b.y + b.height for b in bounds_list)

        first = frames[0]
        if min_x == 0 and min_y == 0 and max_x == first.get_width() and max_y == first.get_height():
            return frames

        union_rect = (min_x, min_y, max_x - min_x, max_y - min_y)
        try:
            return [frame.subsurface(union_rect).copy() for frame in frames]
        except Exception:
            logger.warning("Не удалось обрезать спрайты по общей рамке %r", union_rect, exc_info=True)
            return frames

    def has_sprite_for(self, key: str) -> bool:
        """Проверяет, загружен ли хотя бы один спрайт для данного ключа."""
        return bool(self._frames.get(key))

    def get_frame(self, key: str, elapsed_time: float = 0.0) -> pygame.Surface | None:
        """Возвращает текущий кадр спрайта для ключа, или None, если спрайтов нет.

        Один файл в папке — статичный спрайт, всегда отдаётся он же. Несколько файлов —
        кадры анимации, циклически сменяются по ANIMATION_FPS в зависимости от elapsed_time."""
        frames = self._frames.get(key)
        if not frames:
            return None
        if len(frames) == 1:
            return frames[0]
        frame_index = int(elapsed_time * self.ANIMATION_FPS) % len(frames)
        return frames[frame_index]

    def get_frame_for_angle(self, key: str, angle_degrees: float = 0.0) -> pygame.Surface | None:
        """Возвращает кадр, ближайший к заданному азимуту (0° = кадр frame_01, "вверх/север",
        дальше по часовой стрелке) — для спрайтов, где несколько файлов в папке означают не
        кадры анимации, а вид объекта под разными углами поворота (например, направленные
        кадры башни). Шаг между кадрами вычисляется как 360° / количество файлов."""
        frames = self._frames.get(key)
        if not frames:
            return None
        if len(frames) == 1:
            return frames[0]
        step = 360.0 / len(frames)
        frame_index = round((angle_degrees % 360.0) / step) % len(frames)
        return frames[frame_index]
