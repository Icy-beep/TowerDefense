"""Загрузка и отдача спрайтов из assets/sprites/."""
import os
from typing import Callable, Dict, List, Optional

import pygame

DEFAULT_SPRITES_ROOT = os.path.join("assets", "sprites")
SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp")


def discover_sprite_files(sprites_root: str) -> Dict[str, List[str]]:
    """Сканирует sprites_root и возвращает {ключ: [пути к кадрам]}."""
    result: Dict[str, List[str]] = {}
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
                 on_progress: Optional[Callable[[int, int], None]] = None):
        """Загружает все найденные спрайты; несколько файлов в папке = кадры анимации.

        on_progress(done, total), если задан, вызывается после каждого файла — так же,
        как у SoundManager, чтобы загрузка большого количества спрайтов не подвешивала окно."""
        self.enabled = True
        self._frames: Dict[str, List[pygame.Surface]] = {}

        entries_by_key = discover_sprite_files(sprites_root)
        total_files = sum(len(paths) for paths in entries_by_key.values())
        loaded_files = 0

        for key, paths in entries_by_key.items():
            loaded = []
            for path in paths:
                try:
                    image = pygame.image.load(path).convert_alpha()
                    loaded.append(self._autocrop(image))
                except pygame.error:
                    continue
                loaded_files += 1
                if on_progress:
                    on_progress(loaded_files, total_files)
            if loaded:
                self._frames[key] = loaded

    def _autocrop(self, image: pygame.Surface) -> pygame.Surface:
        """Обрезает прозрачные поля вокруг рисунка: если в PNG вокруг турели/врага/т.п.
        осталось пустое место, оно иначе съедает часть итогового размера при масштабировании
        под фиксированный target_size — рисунок выглядит мельче, чем должен."""
        try:
            bounds = image.get_bounding_rect(min_alpha=1)
        except Exception:
            return image
        if bounds.width <= 0 or bounds.height <= 0:
            return image
        if bounds.width == image.get_width() and bounds.height == image.get_height():
            return image
        return image.subsurface(bounds).copy()

    def has_sprite_for(self, key: str) -> bool:
        """Проверяет, загружен ли хотя бы один спрайт для данного ключа."""
        return bool(self._frames.get(key))

    def get_frame(self, key: str, elapsed_time: float = 0.0) -> Optional[pygame.Surface]:
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
