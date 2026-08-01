"""Загрузка и проигрывание фоновой музыки (OST) из assets/music/."""
import os
import random
from typing import Dict, List, Optional

import pygame

DEFAULT_MUSIC_ROOT = os.path.join("assets", "music")
SUPPORTED_EXTENSIONS = (".mp3", ".ogg", ".wav")


def discover_music_files(music_root: str) -> Dict[str, List[str]]:
    """Сканирует music_root и возвращает {категория: [пути к трекам]}."""
    result: Dict[str, List[str]] = {}
    if not os.path.isdir(music_root):
        return result

    for category in sorted(os.listdir(music_root)):
        category_dir = os.path.join(music_root, category)
        if not os.path.isdir(category_dir):
            continue
        files = [
            os.path.join(category_dir, filename)
            for filename in sorted(os.listdir(category_dir))
            if filename.lower().endswith(SUPPORTED_EXTENSIONS)
        ]
        if files:
            result[category] = files

    return result


class MusicManager:
    """Проигрывает фоновую музыку по категориям (menu/gameplay) через pygame.mixer.music.

    В отличие от SoundManager, треки не грузятся целиком в память — pygame.mixer.music
    стримит файл с диска, что подходит для длинных OST-композиций."""

    FADE_IN_MS = 800

    def __init__(self, music_root: str = DEFAULT_MUSIC_ROOT, volume: float = 0.35,
                 rng: Optional[random.Random] = None):
        """Индексирует доступные треки по категориям, не начиная проигрывание."""
        self._rng = rng or random
        self.volume = volume
        self.enabled = True
        self._tracks = discover_music_files(music_root)
        self.current_category: Optional[str] = None

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.set_volume(self.volume)
        except pygame.error:
            self.enabled = False

    def play_category(self, category: str, loop: bool = True):
        """Переключает музыку на случайный трек категории с фейд-ином; повторный вызов той же
        категории ничего не делает, чтобы не перезапускать уже играющий трек."""
        if not self.enabled or category == self.current_category:
            return
        tracks = self._tracks.get(category)
        if not tracks:
            return
        track = self._rng.choice(tracks)
        try:
            pygame.mixer.music.load(track)
            pygame.mixer.music.play(loops=-1 if loop else 0, fade_ms=self.FADE_IN_MS)
        except pygame.error:
            return
        self.current_category = category

    def stop(self):
        """Останавливает музыку с плавным затуханием."""
        if not self.enabled or self.current_category is None:
            return
        pygame.mixer.music.fadeout(self.FADE_IN_MS)
        self.current_category = None

    def set_volume(self, volume: float):
        """Задаёт громкость музыки от 0.0 до 1.0."""
        self.volume = max(0.0, min(1.0, volume))
        if self.enabled:
            pygame.mixer.music.set_volume(self.volume)

    def has_tracks_for(self, category: str) -> bool:
        """Проверяет, есть ли треки для данной категории."""
        return bool(self._tracks.get(category))
