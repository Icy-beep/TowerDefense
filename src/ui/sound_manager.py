"""Загрузка и проигрывание звуков из assets/sounds/."""
import array
import os
import random
import sys
from collections.abc import Callable
from pathlib import Path

import pygame

from src.systems.pitch_shift import resample_pitch


def _default_sounds_root() -> str:
    """Путь к папке звуков: внутри временной распаковки PyInstaller (_MEIPASS)
    при сборке в .exe, иначе в корне проекта при запуске из исходников (тот же
    принцип, что и у ConfigLoader/Loc - см. src/config/config_loader.py)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return str(base / "assets" / "sounds")


DEFAULT_SOUNDS_ROOT = _default_sounds_root()
SUPPORTED_EXTENSIONS = (".wav", ".ogg", ".mp3")
RARE_SUBFOLDER_NAME = "rare"
COMMON_FILE_WEIGHT = 1.0
RARE_FILE_WEIGHT = 0.1


def discover_sound_files(sounds_root: str) -> dict[str, list[tuple[str, float]]]:
    """Сканирует sounds_root и возвращает {имя_события: [(путь, вес), ...]}.

    Файлы из подпапки rare/ получают заниженный вес — редкие вариации звука."""
    result: dict[str, list[tuple[str, float]]] = {}
    if not os.path.isdir(sounds_root):
        return result

    for event_name in sorted(os.listdir(sounds_root)):
        event_dir = os.path.join(sounds_root, event_name)
        if not os.path.isdir(event_dir):
            continue

        entries = _collect_weighted_files(event_dir, COMMON_FILE_WEIGHT)
        rare_dir = os.path.join(event_dir, RARE_SUBFOLDER_NAME)
        if os.path.isdir(rare_dir):
            entries += _collect_weighted_files(rare_dir, RARE_FILE_WEIGHT)

        if entries:
            result[event_name] = entries

    return result


def _collect_weighted_files(directory: str, weight: float) -> list[tuple[str, float]]:
    """Возвращает список (путь, weight) для звуковых файлов прямо в directory."""
    return [
        (os.path.join(directory, filename), weight)
        for filename in sorted(os.listdir(directory))
        if os.path.isfile(os.path.join(directory, filename)) and filename.lower().endswith(SUPPORTED_EXTENSIONS)
    ]


class SoundManager:
    """Проигрывает случайный звук из assets/sounds/<событие>/ по имени события."""

    NUM_CHANNELS = 32
    PITCH_VARIATION = 0.06
    PITCH_VARIANTS = 4

    def __init__(self, sounds_root: str = DEFAULT_SOUNDS_ROOT, volume: float = 0.45,
                 rng: random.Random | None = None,
                 on_progress: Callable[[int, int], None] | None = None):
        """Загружает все звуки, найденные в sounds_root, по подпапкам-событиям.

        on_progress(done, total), если задан, вызывается после каждого обработанного файла —
        расчёт вариаций питча небыстрый (доли секунды на файл), и без периодических пауз на
        откачку событий ОС считает окно игры зависшим на время всей загрузки."""
        self._rng = rng or random
        self.volume = volume
        self.enabled = True
        self._sounds: dict[str, list[list[pygame.mixer.Sound]]] = {}
        self._weights: dict[str, list[float]] = {}
        self._cooldowns: dict[str, float] = {}

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.set_num_channels(self.NUM_CHANNELS)
        except pygame.error:
            self.enabled = False
            return

        entries_by_event = discover_sound_files(sounds_root)
        total_files = sum(len(entries) for entries in entries_by_event.values())
        loaded_files = 0

        for event_name, entries in entries_by_event.items():
            loaded_variant_groups = []
            loaded_weights = []
            for path, weight in entries:
                try:
                    base_sound = pygame.mixer.Sound(path)
                except pygame.error:
                    continue
                loaded_variant_groups.append(self._build_pitch_variants(base_sound))
                loaded_weights.append(weight)
                loaded_files += 1
                if on_progress:
                    on_progress(loaded_files, total_files)
            if loaded_variant_groups:
                self._sounds[event_name] = loaded_variant_groups
                self._weights[event_name] = loaded_weights

    def _build_pitch_variants(self, sound: "pygame.mixer.Sound") -> list["pygame.mixer.Sound"]:
        """Один раз при загрузке считает несколько готовых вариаций питча звука, чтобы
        play() не занимался ресемплингом на лету (это и вызывало статтер при частых звуках)."""
        variants = [sound]
        init = pygame.mixer.get_init()
        if not init or abs(init[1]) != 16:
            return variants
        try:
            samples = array.array("h")
            samples.frombytes(sound.get_raw())
        except (ValueError, pygame.error):
            return variants

        channels = init[2]
        step = (2 * self.PITCH_VARIATION) / max(1, self.PITCH_VARIANTS - 1) if self.PITCH_VARIANTS > 1 else 0.0
        for i in range(self.PITCH_VARIANTS):
            offset = -self.PITCH_VARIATION + step * i if self.PITCH_VARIANTS > 1 else self.PITCH_VARIATION
            pitch_factor = 1.0 + offset
            try:
                shifted = resample_pitch(samples, channels=channels, pitch_factor=pitch_factor)
                variants.append(pygame.mixer.Sound(buffer=shifted.tobytes()))
            except (ValueError, pygame.error):
                continue
        return variants

    def update(self, delta_time: float):
        """Уменьшает таймеры кулдаунов звуковых событий на время кадра."""
        for event_name in list(self._cooldowns):
            remaining = self._cooldowns[event_name] - delta_time
            if remaining <= 0.0:
                del self._cooldowns[event_name]
            else:
                self._cooldowns[event_name] = remaining

    def play(self, event_name: str, volume_multiplier: float = 1.0, cooldown: float = 0.0):
        """Проигрывает случайный звук для события, если не идёт его кулдаун; варьирует питч и громкость."""
        if not self.enabled or volume_multiplier <= 0.0:
            return
        file_variants = self._sounds.get(event_name)
        if not file_variants:
            return
        if cooldown > 0.0:
            if self._cooldowns.get(event_name, 0.0) > 0.0:
                return
            self._cooldowns[event_name] = cooldown
        variants = self._rng.choices(file_variants, weights=self._weights[event_name], k=1)[0]
        sound_to_play = self._rng.choice(variants)
        sound_to_play.set_volume(self.volume * volume_multiplier)
        sound_to_play.play()

    def has_sounds_for(self, event_name: str) -> bool:
        """Проверяет, загружены ли звуки для данного события."""
        return bool(self._sounds.get(event_name))

    def set_volume(self, volume: float):
        """Задаёт громкость воспроизведения от 0.0 до 1.0."""
        self.volume = max(0.0, min(1.0, volume))
