"""Снаряды башен."""
import math
import random
from abc import ABC, abstractmethod
from typing import List, Optional

from src.core.coordinate import Coordinate
from src.enums import DamageType


class Projectile(ABC):
    """Базовый класс для всех снарядов."""

    HIT_RADIUS = 12.0

    def __init__(self, position: Coordinate, damage: float, damage_type: DamageType):
        """Создаёт снаряд с уроном и типом урона."""
        self.position = position
        self.damage = damage
        self.damage_type = damage_type

    @abstractmethod
    def update(self, delta_time: float, enemies: List["HostileEntity"]) -> bool:
        """Обновляет снаряд на один кадр. Возвращает False, если снаряд нужно убрать с карты."""
        pass

    def collect_spawned(self) -> List["Projectile"]:
        """Возвращает снаряды, порождённые этим (например, шрапнель)."""
        return []

    def _find_collision(self, enemies: List["HostileEntity"],
                         hit_radius: Optional[float] = None) -> Optional["HostileEntity"]:
        """Находит ближайшего живого врага в радиусе поражения снаряда."""
        radius = hit_radius if hit_radius is not None else self.HIT_RADIUS
        candidates = [e for e in enemies if e.is_alive() and self.position.distance_to(e.position) <= radius]
        if not candidates:
            return None
        return min(candidates, key=lambda e: self.position.distance_to(e.position))

    @staticmethod
    def _find_path_collision(start: Coordinate, end: Coordinate, enemies: List["HostileEntity"],
                              hit_radius: float) -> Optional["HostileEntity"]:
        """Находит врага, столкнувшегося со снарядом на пути от start до end."""
        dx, dy = end.x - start.x, end.y - start.y
        length_sq = dx * dx + dy * dy

        best_enemy = None
        best_t = None
        for e in enemies:
            if not e.is_alive():
                continue
            if length_sq == 0:
                t = 0.0
                closest = start
            else:
                t = ((e.position.x - start.x) * dx + (e.position.y - start.y) * dy) / length_sq
                t = max(0.0, min(1.0, t))
                closest = Coordinate(start.x + dx * t, start.y + dy * t)
            if closest.distance_to(e.position) <= hit_radius and (best_t is None or t < best_t):
                best_t = t
                best_enemy = e
        return best_enemy


class HitscanBeam(Projectile):
    """Мгновенный лазерный луч."""

    def __init__(self, position: Coordinate, target: "HostileEntity", damage: float, damage_type: DamageType):
        """Создаёт луч от башни до цели."""
        super().__init__(Coordinate(position.x, position.y), damage, damage_type)
        self.origin = Coordinate(position.x, position.y)
        self.end = Coordinate(target.position.x, target.position.y)
        self._target = target

    def update(self, delta_time: float, enemies: List["HostileEntity"]) -> bool:
        """Наносит урон цели и завершает существование луча."""
        if self._target.is_alive():
            self._target.take_damage(self.damage, self.damage_type)
        return False


class _LinearProjectile(Projectile):
    """Снаряд, летящий по прямой в фиксированном направлении."""

    def __init__(self, position: Coordinate, direction: tuple, damage: float, damage_type: DamageType,
                 speed: float, max_distance: float):
        """Создаёт снаряд с направлением, скоростью и дальностью полёта."""
        super().__init__(position, damage, damage_type)
        length = math.hypot(direction[0], direction[1]) or 1.0
        self.direction = (direction[0] / length, direction[1] / length)
        self.speed = speed
        self.max_distance = max_distance
        self.traveled = 0.0

    def update(self, delta_time: float, enemies: List["HostileEntity"]) -> bool:
        """Двигает снаряд вперёд и проверяет столкновение с врагами."""
        step = self.speed * delta_time
        start = Coordinate(self.position.x, self.position.y)
        self.position.x += self.direction[0] * step
        self.position.y += self.direction[1] * step
        self.traveled += step

        hit = self._find_path_collision(start, self.position, enemies, self.HIT_RADIUS)
        if hit:
            hit.take_damage(self.damage, self.damage_type)
            return False

        return self.traveled < self.max_distance


class BulletProjectile(_LinearProjectile):
    """Пуля, летящая по прямой к позиции цели на момент выстрела."""

    def __init__(self, position: Coordinate, target: "HostileEntity", damage: float, damage_type: DamageType,
                 speed: float, max_distance: float = 900.0):
        """Создаёт пулю, летящую в сторону цели."""
        direction = (target.position.x - position.x, target.position.y - position.y)
        super().__init__(Coordinate(position.x, position.y), direction, damage, damage_type, speed, max_distance)


class ShrapnelPellet(_LinearProjectile):
    """Осколок взрыва мортиры."""
    pass


class MortarShell(Projectile):
    """Миномётный снаряд, летящий по параболе и разлетающийся шрапнелью при падении."""

    SHELL_SPEED = 250.0
    PEAK_HEIGHT = 120.0
    SHRAPNEL_COUNT = 8
    SHRAPNEL_RANGE = 90.0
    SHRAPNEL_SPEED = 200.0

    def __init__(self, position: Coordinate, target: "HostileEntity", damage: float, damage_type: DamageType,
                 rng: Optional[random.Random] = None):
        """Создаёт миномётный снаряд, летящий в точку цели на момент выстрела."""
        super().__init__(Coordinate(position.x, position.y), damage, damage_type)
        self.start = Coordinate(position.x, position.y)
        self.target_pos = Coordinate(target.position.x, target.position.y)
        distance = self.start.distance_to(self.target_pos)
        self.flight_time = max(distance / self.SHELL_SPEED, 0.1)
        self.elapsed = 0.0
        self.height = 0.0
        self._landed = False
        self._spawned: List[Projectile] = []
        self._rng = rng or random

    @property
    def progress(self) -> float:
        """Доля пройденного пути полёта от 0 до 1."""
        return min(1.0, self.elapsed / self.flight_time)

    def update(self, delta_time: float, enemies: List["HostileEntity"]) -> bool:
        """Двигает снаряд по параболе и взрывается по приземлении."""
        if self._landed:
            return False

        self.elapsed += delta_time
        t = self.progress
        self.position.x = self.start.x + (self.target_pos.x - self.start.x) * t
        self.position.y = self.start.y + (self.target_pos.y - self.start.y) * t
        self.height = 4 * self.PEAK_HEIGHT * t * (1 - t)

        if t >= 1.0:
            self._land()
            return False
        return True

    def _land(self):
        """Взрывается и создаёт осколки шрапнели вокруг точки падения."""
        self._landed = True
        self.height = 0.0
        pellet_damage = self.damage / self.SHRAPNEL_COUNT
        base_angle = self._rng.uniform(0, 2 * math.pi)
        for i in range(self.SHRAPNEL_COUNT):
            angle = base_angle + (2 * math.pi / self.SHRAPNEL_COUNT) * i
            direction = (math.cos(angle), math.sin(angle))
            self._spawned.append(ShrapnelPellet(
                position=Coordinate(self.position.x, self.position.y),
                direction=direction,
                damage=pellet_damage,
                damage_type=self.damage_type,
                speed=self.SHRAPNEL_SPEED,
                max_distance=self.SHRAPNEL_RANGE,
            ))

    def collect_spawned(self) -> List[Projectile]:
        """Возвращает и очищает список созданных осколков шрапнели."""
        spawned, self._spawned = self._spawned, []
        return spawned
