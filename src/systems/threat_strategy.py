"""Источники угрозы: каждая фракция появляется на карте по своей логике."""
import random
from abc import ABC, abstractmethod
from collections.abc import Callable

from src.core.coordinate import Coordinate
from src.enums import Faction


class PendingLanding:
    """Телеграфируемая точка высадки: маркер на карте до того, как там
    материализуется отряд."""

    def __init__(self, position: Coordinate, warning_time: float):
        """Создаёт маркер высадки с оставшимся временем до прибытия отряда."""
        self.position = position
        self.time_remaining = warning_time


class ThreatStrategy(ABC):
    """Определяет, как и когда на карте появляются новые враги одной
    фракции."""

    @abstractmethod
    def update(self, delta_time: float, game_map, spawn_factory: Callable) -> None:
        """Обновляет состояние источника угрозы, при необходимости спавнит
        врагов через spawn_factory."""
        pass


class ShipLandingStrategy(ThreatStrategy):
    """Corporation высаживается с кораблей: маркер на границе карты, затем через warning_time отряд."""

    def __init__(self, enemy_types: list[str], squad_size_range=(2, 4),
                 base_interval: float = 14.0, min_interval: float = 5.0,
                 interval_decay_per_second: float = 0.03, warning_time: float = 3.0,
                 rng: random.Random | None = None):
        """Создаёт стратегию высадки с заданными типами врагов и темпом
        эскалации."""
        self.enemy_types = enemy_types
        self.squad_size_range = squad_size_range
        self.base_interval = base_interval
        self.min_interval = min_interval
        self.interval_decay_per_second = interval_decay_per_second
        self.warning_time = warning_time
        self.rng = rng or random.Random()

        self.elapsed = 0.0
        self.timer = base_interval
        self.pending_landings: list[PendingLanding] = []
        self._spawn_count = 0

    def _current_interval(self) -> float:
        """Интервал до следующей высадки, сокращающийся по ходу партии."""
        return max(self.min_interval, self.base_interval - self.elapsed * self.interval_decay_per_second)

    def _random_border_point(self, game_map) -> Coordinate:
        """Случайная точка на границе карты, чуть отступая от самого края для NavigationGrid."""
        max_x = max(0.0, game_map.width - 1)
        max_y = max(0.0, game_map.height - 1)
        side = self.rng.choice(("top", "bottom", "left", "right"))
        if side == "top":
            return Coordinate(self.rng.uniform(0, max_x), 0)
        if side == "bottom":
            return Coordinate(self.rng.uniform(0, max_x), max_y)
        if side == "left":
            return Coordinate(0, self.rng.uniform(0, max_y))
        return Coordinate(max_x, self.rng.uniform(0, max_y))

    def _spawn_squad(self, position: Coordinate, game_map, spawn_factory: Callable) -> None:
        """Спавнит отряд случайного размера в указанной точке. Тип каждого юнита берётся
        по общему счётчику высадок (не сбрасывается на каждый отряд) - иначе при
        squad_size_range с потолком меньше числа зарегистрированных типов часть типов
        (например, последний в списке) вообще никогда бы не выпадала."""
        squad_size = self.rng.randint(*self.squad_size_range)
        for _ in range(squad_size):
            enemy_type = self.enemy_types[self._spawn_count % len(self.enemy_types)]
            self._spawn_count += 1
            enemy = spawn_factory(enemy_type, position)
            if enemy is not None:
                game_map.spawn_enemy(enemy)

    def update(self, delta_time: float, game_map, spawn_factory: Callable) -> None:
        """Обновляет предупреждающие маркеры и таймер высадки нового отряда."""
        if not self.enemy_types:
            return

        self.elapsed += delta_time

        still_pending = []
        for landing in self.pending_landings:
            landing.time_remaining -= delta_time
            if landing.time_remaining > 0:
                still_pending.append(landing)
                continue
            self._spawn_squad(landing.position, game_map, spawn_factory)
        self.pending_landings = still_pending

        self.timer -= delta_time
        if self.timer <= 0:
            # Высадка Corporation намеренно НЕ гейтится секторами прогрессии (см.
            # src/systems/sector.py), в отличие от гнёзд фауны (NestSpawnStrategy) -
            # стартовый открытый сектор в сетке (там, где база) никогда не касается
            # границы карты, а именно на границе всегда высаживается Corporation.
            # Строгий гейтинг "точка высадки должна быть в открытом секторе" на практике
            # означал бы полное отсутствие давления Corporation, пока игрок сам не
            # додумается купить открытие какого-то из угловых/краевых секторов - реальный
            # риск "мёртвого" начала партии, подтверждённый прогоном (~50% партий без
            # единого спавна за 300 игровых секунд). Гнёзда фауны безопаснее: часть из них
            # и так может оказаться в стартовом секторе по случайной генерации.
            self.pending_landings.append(PendingLanding(self._random_border_point(game_map), self.warning_time))
            self.timer = self._current_interval()


class NestSpawnStrategy(ThreatStrategy):
    """Fauna спавнит одного врага по таймеру с ограничением на число живых врагов фракции."""

    def __init__(self, enemy_types: list[str], base_interval: float = 6.0,
                 min_interval: float = 1.5, interval_decay_per_second: float = 0.02,
                 max_active: int = 25, rng: random.Random | None = None):
        """Создаёт стратегию спавна с заданными типами врагов и лимитом
        популяции."""
        self.enemy_types = enemy_types
        self.base_interval = base_interval
        self.min_interval = min_interval
        self.interval_decay_per_second = interval_decay_per_second
        self.max_active = max_active
        self.rng = rng or random.Random()

        self.elapsed = 0.0
        self.timer = base_interval
        self._spawn_count = 0

    def _current_interval(self) -> float:
        """Интервал до следующего спавна, сокращающийся по ходу партии."""
        return max(self.min_interval, self.base_interval - self.elapsed * self.interval_decay_per_second)

    def update(self, delta_time: float, game_map, spawn_factory: Callable) -> None:
        """Обновляет таймер и, если пора, спавнит одного врага."""
        if not self.enemy_types:
            return

        self.elapsed += delta_time
        self.timer -= delta_time
        if self.timer > 0:
            return
        self.timer = self._current_interval()

        active_count = sum(1 for e in game_map.enemies if e.is_alive() and e.faction == Faction.FAUNA)
        if active_count >= self.max_active:
            return

        # Секторы прогрессии (см. src/systems/sector.py) - спавнить можно только из гнёзд
        # в уже открытых секторах; если таких нет (весь фронт ещё закрыт), просто
        # пропускаем цикл - таймер уже сброшен выше. На картах без секторов (self.sectors
        # пуст) unlocked_fauna_spawn_points возвращает все живые гнёзда - поведение не
        # меняется.
        spawn_points = game_map.unlocked_fauna_spawn_points()
        if not spawn_points:
            return

        enemy_type = self.enemy_types[self._spawn_count % len(self.enemy_types)]
        self._spawn_count += 1
        position = self.rng.choice(spawn_points)
        enemy = spawn_factory(enemy_type, position)
        if enemy is not None:
            game_map.spawn_enemy(enemy)
