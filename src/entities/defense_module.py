from abc import ABC, abstractmethod
from typing import Optional, List
from .entity import Entity
from src.core.coordinate import Coordinate
from src.enums import DamageType, ModuleStatus
from src.entities.projectile import Projectile


class DefenseModule(Entity, ABC):
    """Базовый класс для всех башен."""

    LANDING_DURATION = 3.5
    LANDING_START_HEIGHT = 600.0
    LANDING_IMPACT_RADIUS = 60.0

    def __init__(self, position: Coordinate, range_radius: float, damage: float, cost: int, attack_speed: float = 1.0):
        """Создаёт башню с базовыми характеристиками."""
        super().__init__(position)

        self.base_range = range_radius
        self.base_damage = damage
        self.base_attack_speed = attack_speed

        self.range_radius = self.base_range
        self.damage = self.base_damage
        self.attack_speed = self.base_attack_speed

        self.cost = cost
        self.status = ModuleStatus.IDLE
        self.cooldown_timer = 0.0

        self.max_health = 100.0
        self.health = self.max_health

        self.level = 1
        self.max_level = 3
        self.upgrade_costs: List[int] = []

        self.is_landing = False
        self.landing_elapsed = 0.0
        self.landing_height = 0.0
        self._pending_landed_event = False

    def start_landing(self):
        """Запускает высадку с орбиты: башня неуязвима и не стреляет, пока не приземлится."""
        self.is_landing = True
        self.landing_elapsed = 0.0
        self.landing_height = self.LANDING_START_HEIGHT

    @property
    def landing_progress(self) -> float:
        """Доля пройденного времени высадки от 0 до 1."""
        return min(1.0, self.landing_elapsed / self.LANDING_DURATION)

    def take_landing_event(self) -> bool:
        """Возвращает True один раз, в момент когда башня только что приземлилась."""
        if self._pending_landed_event:
            self._pending_landed_event = False
            return True
        return False

    def update(self, delta_time: float, enemies: List['HostileEntity']) -> Optional[Projectile]:
        """Обновляет башню на один кадр и стреляет по цели, если готова."""
        if self.is_landing:
            self._advance_landing(delta_time, enemies)
            return None

        if self.status in (ModuleStatus.OVERHEATED, ModuleStatus.OFFLINE):
            return None

        if self.cooldown_timer > 0:
            self.cooldown_timer -= delta_time
            return None

        target = self.find_target(enemies)
        if target:
            self.cooldown_timer = 1.0 / self.attack_speed
            return self.fire(target)

        return None

    def _advance_landing(self, delta_time: float, enemies: List['HostileEntity']):
        """Двигает башню вниз по высоте и наносит урон при приземлении."""
        self.landing_elapsed += delta_time
        t = self.landing_progress
        self.landing_height = self.LANDING_START_HEIGHT * (1 - t) ** 2

        if t >= 1.0:
            self.is_landing = False
            self.landing_height = 0.0
            self._pending_landed_event = True
            self._deal_landing_impact(enemies)

    def _deal_landing_impact(self, enemies: List['HostileEntity']):
        """Наносит урон всем врагам, оказавшимся под точкой приземления."""
        impact_damage = self.damage * 2
        for enemy in enemies:
            if enemy.is_alive() and self.position.distance_to(enemy.position) <= self.LANDING_IMPACT_RADIUS:
                enemy.take_damage(impact_damage, self.damage_type)

    def find_target(self, enemies: List['HostileEntity']) -> Optional['HostileEntity']:
        """Находит ближайшего врага в радиусе действия."""
        valid_targets = [
            e for e in enemies
            if self.position.distance_to(e.position) <= self.range_radius
        ]
        if not valid_targets:
            return None
        return min(valid_targets, key=lambda e: self.position.distance_to(e.position))

    @abstractmethod
    def fire(self, target: 'HostileEntity') -> Optional[Projectile]:
        """Создаёт снаряд по цели."""
        pass

    def get_upgrade_cost(self) -> Optional[int]:
        """Возвращает стоимость следующего уровня или None, если максимум."""
        if self.level >= self.max_level:
            return None
        return self.upgrade_costs[self.level - 1]

    def can_upgrade(self) -> bool:
        """Проверяет, можно ли улучшить башню."""
        return self.level < self.max_level

    def upgrade(self) -> bool:
        """Повышает уровень башни и пересчитывает характеристики."""
        if not self.can_upgrade():
            return False

        self.level += 1

        dmg_mult = 1.0 + (self.level - 1) * 0.4
        rng_mult = 1.0 + (self.level - 1) * 0.2
        spd_mult = 1.0 + (self.level - 1) * 0.25

        self.damage = self.base_damage * dmg_mult
        self.range_radius = self.base_range * rng_mult
        self.attack_speed = self.base_attack_speed * spd_mult

        return True

    def take_damage(self, amount: float, damage_type: DamageType):
        """Наносит урон башне. Пока башня высаживается, она неуязвима."""
        if self.is_landing:
            return
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.status = ModuleStatus.OFFLINE

    def is_destroyed(self) -> bool:
        """Проверяет, уничтожена ли башня."""
        return self.health <= 0