"""Снаряды башен."""
import math
import random
from abc import ABC, abstractmethod
from typing import Optional

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
    def update(self, delta_time: float, enemies: list["HostileEntity"]) -> bool:
        """Обновляет снаряд на один кадр. Возвращает False, если снаряд нужно убрать с карты."""
        pass

    def collect_spawned(self) -> list["Projectile"]:
        """Возвращает снаряды, порождённые этим (например, шрапнель)."""
        return []

    def landed_event_name(self) -> str | None:
        """Имя звукового события при исчезновении снаряда с карты, если оно есть."""
        return None

    def _find_collision(self, enemies: list["HostileEntity"],
                         hit_radius: float | None = None) -> Optional["HostileEntity"]:
        """Находит ближайшего живого врага в радиусе поражения снаряда."""
        radius = hit_radius if hit_radius is not None else self.HIT_RADIUS
        candidates = [e for e in enemies if e.is_alive() and self.position.distance_to(e.position) <= radius]
        if not candidates:
            return None
        return min(candidates, key=lambda e: self.position.distance_to(e.position))

    @staticmethod
    def _find_path_collision(start: Coordinate, end: Coordinate, enemies: list["HostileEntity"],
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
    """Мгновенный лазерный луч: урон наносится сразу, луч виден ещё BEAM_LIFETIME секунд."""

    BEAM_LIFETIME = 0.08

    def __init__(self, position: Coordinate, target: "HostileEntity", damage: float, damage_type: DamageType):
        """Создаёт луч от башни до цели и сразу наносит урон."""
        super().__init__(Coordinate(position.x, position.y), damage, damage_type)
        self.origin = Coordinate(position.x, position.y)
        self.end = Coordinate(target.position.x, target.position.y)
        self._target = target
        self._time_left = self.BEAM_LIFETIME
        self._hit = self._target.is_alive()
        if self._hit:
            self._target.take_damage(self.damage, self.damage_type)

    def update(self, delta_time: float, enemies: list["HostileEntity"]) -> bool:
        """Отсчитывает время жизни луча на экране (урон уже нанесён при создании)."""
        self._time_left -= delta_time
        return self._time_left > 0

    def landed_event_name(self) -> str | None:
        """Имя звукового события попадания лазера, если цель была поражена."""
        return "laser_hit" if self._hit else None


class EnemyHitscanBeam(HitscanBeam):
    """Мгновенный лучевой выстрел врага (например, SniperDrone) по башне - тот же
    визуальный эффект, что и у HitscanBeam лазерной башни (MapRenderer различает их
    только по классу, отрисовка общая). Отдельный класс нужен потому, что целью здесь
    является DefenseModule, а не HostileEntity: у башни другой интерфейс проверки
    жизни - is_destroyed(), а не is_alive()."""

    def __init__(self, position: Coordinate, target, damage: float, damage_type: DamageType):
        """Создаёт луч от врага до башни-цели и сразу наносит ей урон."""
        Projectile.__init__(self, Coordinate(position.x, position.y), damage, damage_type)
        self.origin = Coordinate(position.x, position.y)
        self.end = Coordinate(target.position.x, target.position.y)
        self._target = target
        self._time_left = self.BEAM_LIFETIME
        self._hit = not target.is_destroyed()
        if self._hit:
            target.take_damage(self.damage, self.damage_type)


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
        self._hit_something = False

    def update(self, delta_time: float, enemies: list["HostileEntity"]) -> bool:
        """Двигает снаряд вперёд и проверяет столкновение с врагами."""
        step = self.speed * delta_time
        start = Coordinate(self.position.x, self.position.y)
        self.position.x += self.direction[0] * step
        self.position.y += self.direction[1] * step
        self.traveled += step

        hit = self._find_path_collision(start, self.position, enemies, self.HIT_RADIUS)
        if hit:
            hit.take_damage(self.damage, self.damage_type)
            self._hit_something = True
            return False

        return self.traveled < self.max_distance


class BulletProjectile(_LinearProjectile):
    """Пуля, летящая по прямой к позиции цели на момент выстрела."""

    def __init__(self, position: Coordinate, target: "HostileEntity", damage: float, damage_type: DamageType,
                 speed: float, max_distance: float = 900.0, spread_degrees: float = 0.0,
                 rng: random.Random | None = None):
        """Создаёт пулю, летящую в сторону цели с необязательным случайным
        разбросом направления в пределах ±spread_degrees/2."""
        direction = (target.position.x - position.x, target.position.y - position.y)
        if spread_degrees:
            rng = rng or random
            angle = math.radians(rng.uniform(-spread_degrees / 2, spread_degrees / 2))
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            direction = (
                direction[0] * cos_a - direction[1] * sin_a,
                direction[0] * sin_a + direction[1] * cos_a,
            )
        super().__init__(Coordinate(position.x, position.y), direction, damage, damage_type, speed, max_distance)

    def landed_event_name(self) -> str | None:
        """Имя звукового события попадания пули, если она во что-то попала."""
        return "bullet_hit" if self._hit_something else None


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
                 rng: random.Random | None = None):
        """Создаёт миномётный снаряд, летящий в точку цели на момент выстрела."""
        super().__init__(Coordinate(position.x, position.y), damage, damage_type)
        self.start = Coordinate(position.x, position.y)
        self.target_pos = Coordinate(target.position.x, target.position.y)
        distance = self.start.distance_to(self.target_pos)
        self.flight_time = max(distance / self.SHELL_SPEED, 0.1)
        self.elapsed = 0.0
        self.height = 0.0
        self._landed = False
        self._spawned: list[Projectile] = []
        self._rng = rng or random

    @property
    def progress(self) -> float:
        """Доля пройденного пути полёта от 0 до 1."""
        return min(1.0, self.elapsed / self.flight_time)

    def update(self, delta_time: float, enemies: list["HostileEntity"]) -> bool:
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

    def landed_event_name(self) -> str | None:
        """Имя звукового события взрыва миномётного снаряда."""
        return "mortar_explosion"

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

    def collect_spawned(self) -> list[Projectile]:
        """Возвращает и очищает список созданных осколков шрапнели."""
        spawned, self._spawned = self._spawned, []
        return spawned
