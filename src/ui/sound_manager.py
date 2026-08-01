"""Загрузка и проигрывание звуков из assets/sounds/."""
import os
import random
from typing import Dict, List, Optional

import pygame

DEFAULT_SOUNDS_ROOT = os.path.join("assets", "sounds")
SUPPORTED_EXTENSIONS = (".wav", ".ogg", ".mp3")


def discover_sound_files(sounds_root: str) -> Dict[str, List[str]]:
    """Сканирует sounds_root и возвращает {имя_события: [пути к файлам]}."""
    result: Dict[str, List[str]] = {}
    if not os.path.isdir(sounds_root):
        return result

    for event_name in sorted(os.listdir(sounds_root)):
        event_dir = os.path.join(sounds_root, event_name)
        if not os.path.isdir(event_dir):
            continue
        files = [
            os.path.join(event_dir, filename)
            for filename in sorted(os.listdir(event_dir))
            if filename.lower().endswith(SUPPORTED_EXTENSIONS)
        ]
        if files:
            result[event_name] = files

    return result


class SoundManager:
    """Проигрывает случайный звук из assets/sounds/<событие>/ по имени события."""

    NUM_CHANNELS = 32

    def __init__(self, sounds_root: str = DEFAULT_SOUNDS_ROOT, volume: float = 0.45,
                 rng: Optional[random.Random] = None):
        """Загружает все звуки, найденные в sounds_root, по подпапкам-событиям."""
        self._rng = rng or random
        self.volume = volume
        self.enabled = True
        self._sounds: Dict[str, List[pygame.mixer.Sound]] = {}

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.set_num_channels(self.NUM_CHANNELS)
        except pygame.error:
            self.enabled = False
            return

        for event_name, paths in discover_sound_files(sounds_root).items():
            loaded = []
            for path in paths:
                try:
                    loaded.append(pygame.mixer.Sound(path))
                except pygame.error:
                    continue
            if loaded:
                self._sounds[event_name] = loaded

    def play(self, event_name: str, volume_multiplier: float = 1.0):
        """Проигрывает случайный звук для события с учётом множителя громкости."""
        if not self.enabled or volume_multiplier <= 0.0:
            return
        sounds = self._sounds.get(event_name)
        if not sounds:
            return
        sound = self._rng.choice(sounds)
        sound.set_volume(self.volume * volume_multiplier)
        sound.play()

    def has_sounds_for(self, event_name: str) -> bool:
        """Проверяет, загружены ли звуки для данного события."""
        return bool(self._sounds.get(event_name))

    def set_volume(self, volume: float):
        """Задаёт громкость воспроизведения от 0.0 до 1.0."""
        self.volume = max(0.0, min(1.0, volume))
