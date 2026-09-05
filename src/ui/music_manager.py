import os
import random
import sys
from pathlib import Path

import pygame


def _default_music_root() -> str:
    """Путь к папке музыки"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return str(base / "assets" / "music")


DEFAULT_MUSIC_ROOT = _default_music_root()
SUPPORTED_EXTENSIONS = (".mp3", ".ogg", ".wav")


def discover_music_files(music_root: str) -> dict[str, list[str]]:
    """Сканирует music_root и возвращает {категория: [пути к трекам]}."""
    result: dict[str, list[str]] = {}
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
    """Проигрывает фоновую музыку по категориям (menu/gameplay) через pygame.mixer.music"""

    FADE_IN_MS = 800

    def __init__(self, music_root: str = DEFAULT_MUSIC_ROOT, volume: float = 0.35,
                 rng: random.Random | None = None):
        """Индексирует доступные треки по категориям, не начиная проигрывание."""
        self._rng = rng or random
        self.volume = volume
        self.enabled = True
        self._tracks = discover_music_files(music_root)
        self.current_category: str | None = None
        self._current_track: str | None = None
        self._loop_playlist = True

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.set_volume(self.volume)
        except pygame.error:
            self.enabled = False

    def play_category(self, category: str, loop: bool = True):
        """Переключает музыку на случайный трек категории с фейд-ином"""
        if not self.enabled or category == self.current_category:
            return
        tracks = self._tracks.get(category)
        if not tracks:
            return
        if not self._start_track(self._pick_track(tracks)):
            return
        self.current_category = category
        self._loop_playlist = loop

    def update(self, delta_time: float):
        """Раз в кадр проверяет, не доиграл ли текущий трек"""
        if not self.enabled or self.current_category is None or not self._loop_playlist:
            return
        if pygame.mixer.music.get_busy():
            return
        tracks = self._tracks.get(self.current_category)
        if not tracks:
            return
        self._start_track(self._pick_track(tracks, avoid=self._current_track))

    def _pick_track(self, tracks: list[str], avoid: str | None = None) -> str:
        """Выбирает случайный трек из списка"""
        choices = [t for t in tracks if t != avoid] if avoid is not None and len(tracks) > 1 else tracks
        return self._rng.choice(choices or tracks)

    def _start_track(self, track: str) -> bool:
        """Загружает и запускает трек с фейд-ином"""
        try:
            pygame.mixer.music.load(track)
            pygame.mixer.music.play(loops=0, fade_ms=self.FADE_IN_MS)
        except pygame.error:
            return False
        self._current_track = track
        return True

    def stop(self):
        """Останавливает музыку с плавным затуханием"""
        if not self.enabled or self.current_category is None:
            return
        pygame.mixer.music.fadeout(self.FADE_IN_MS)
        self.current_category = None
        self._current_track = None

    def set_volume(self, volume: float):
        """Задаёт громкость музыки от 0.0 до 1.0"""
        self.volume = max(0.0, min(1.0, volume))
        if self.enabled:
            pygame.mixer.music.set_volume(self.volume)

    def has_tracks_for(self, category: str) -> bool:
        """Проверяет, есть ли треки для данной категории"""
        return bool(self._tracks.get(category))
