"""Загрузка и проигрывание фоновой музыки (OST) из assets/music/."""
import os
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pygame


def _default_music_root() -> str:
    """Путь к папке музыки: внутри временной распаковки PyInstaller (_MEIPASS)
    при сборке в .exe, иначе в корне проекта при запуске из исходников (тот же
    принцип, что и у ConfigLoader/Loc - см. src/config/config_loader.py)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return str(base / "assets" / "music")


DEFAULT_MUSIC_ROOT = _default_music_root()
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
        self._current_track: Optional[str] = None
        self._loop_playlist = True

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.set_volume(self.volume)
        except pygame.error:
            self.enabled = False

    def play_category(self, category: str, loop: bool = True):
        """Переключает музыку на случайный трек категории с фейд-ином; повторный вызов той же
        категории ничего не делает, чтобы не перезапускать уже играющий трек. loop=True (по
        умолчанию) - категория играет как плейлист (см. update): когда трек доигрывает,
        запускается следующий случайный трек той же категории, а не тишина."""
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
        """Раз в кадр проверяет, не доиграл ли текущий трек. play_category запускает ровно
        один трек (без pygame loops=-1 на весь геймплей одной и той же композицией) - здесь
        подхватывается его окончание и, если категория в режиме плейлиста, запускается
        следующий случайный трек той же категории, по возможности не повторяя предыдущий."""
        if not self.enabled or self.current_category is None or not self._loop_playlist:
            return
        if pygame.mixer.music.get_busy():
            return
        tracks = self._tracks.get(self.current_category)
        if not tracks:
            return
        self._start_track(self._pick_track(tracks, avoid=self._current_track))

    def _pick_track(self, tracks: List[str], avoid: Optional[str] = None) -> str:
        """Выбирает случайный трек из списка, по возможности не совпадающий с avoid -
        чтобы плейлист не проигрывал одну и ту же композицию два раза подряд, когда в
        категории есть другие варианты."""
        choices = [t for t in tracks if t != avoid] if avoid is not None and len(tracks) > 1 else tracks
        return self._rng.choice(choices or tracks)

    def _start_track(self, track: str) -> bool:
        """Загружает и запускает трек с фейд-ином. Возвращает False, не трогая состояние
        менеджера, если pygame не смог загрузить файл (например, он битый)."""
        try:
            pygame.mixer.music.load(track)
            pygame.mixer.music.play(loops=0, fade_ms=self.FADE_IN_MS)
        except pygame.error:
            return False
        self._current_track = track
        return True

    def stop(self):
        """Останавливает музыку с плавным затуханием."""
        if not self.enabled or self.current_category is None:
            return
        pygame.mixer.music.fadeout(self.FADE_IN_MS)
        self.current_category = None
        self._current_track = None

    def set_volume(self, volume: float):
        """Задаёт громкость музыки от 0.0 до 1.0."""
        self.volume = max(0.0, min(1.0, volume))
        if self.enabled:
            pygame.mixer.music.set_volume(self.volume)

    def has_tracks_for(self, category: str) -> bool:
        """Проверяет, есть ли треки для данной категории."""
        return bool(self._tracks.get(category))
