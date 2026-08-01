"""Задания - слой целей поверх непрерывного давления фракций угроз."""
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


class SurviveDurationObjective(Objective):
    """Задание продержаться заданное время под непрерывным давлением угроз."""

    def __init__(self, target_seconds: float):
        """Создаёт задание с целевой длительностью в секундах."""
        super().__init__()
        self.target_seconds = target_seconds

    def update(self, session):
        """Проверяет поражение или достижение целевого времени."""
        if session.state == GameState.GAME_OVER:
            self.failed = True
            return
        if session.elapsed_time >= self.target_seconds:
            self.completed = True

    def describe(self, session) -> str:
        """Возвращает текст прогресса задания."""
        current = min(session.elapsed_time, self.target_seconds)
        return loc.get("mission.survive_duration", current=int(current), target=int(self.target_seconds))


class ProtectTowersObjective(Objective):
    """Задание не потерять ни одной башни."""

    def update(self, session):
        """Проверяет, потеряна ли хоть одна башня."""
        if session.map.towers_lost_count > 0:
            self.failed = True
            return
        if session.state == GameState.VICTORY:
            self.completed = True

    def describe(self, session) -> str:
        """Возвращает текст прогресса задания."""
        return loc.get("mission.protect_towers", lost=session.map.towers_lost_count)
