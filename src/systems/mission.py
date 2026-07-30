"""Задания — необязательный слой поверх основного волнового цикла."""
from abc import ABC, abstractmethod

from src.enums import GameState
from src.localization.loc import loc


class Objective(ABC):
    """Базовый класс для игровых заданий."""

    def __init__(self):
        """Создаёт незавершённое задание."""
        self.completed = False
        self.failed = False

    def is_active(self) -> bool:
        """Проверяет, активно ли ещё задание."""
        return not self.completed and not self.failed

    @abstractmethod
    def update(self, session):
        """Обновляет статус задания по текущему состоянию сессии."""
        pass

    @abstractmethod
    def describe(self, session) -> str:
        """Возвращает текст задания для HUD."""
        pass


class SurviveWavesObjective(Objective):
    """Задание продержаться до определённой волны."""

    def __init__(self, target_wave_count: int):
        """Создаёт задание с целевой волной."""
        super().__init__()
        self.target_wave_count = target_wave_count

    def update(self, session):
        """Проверяет поражение или достижение целевой волны."""
        if session.state == GameState.GAME_OVER:
            self.failed = True
            return
        if session.wave_protocol.current_wave_idx >= self.target_wave_count:
            self.completed = True

    def describe(self, session) -> str:
        """Возвращает текст прогресса задания."""
        current = min(session.wave_protocol.current_wave_idx, self.target_wave_count)
        return loc.get("mission.survive_waves", current=current, target=self.target_wave_count)


class ProtectTowersObjective(Objective):
    """Задание не потерять ни одной башни."""

    def update(self, session):
        """Проверяет, потеряна ли хоть одна башня."""
        if session.map.towers_lost_count > 0:
            self.failed = True
            return
        if session.wave_protocol.is_all_waves_complete():
            self.completed = True

    def describe(self, session) -> str:
        """Возвращает текст прогресса задания."""
        return loc.get("mission.protect_towers", lost=session.map.towers_lost_count)
