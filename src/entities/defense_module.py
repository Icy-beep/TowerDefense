from abc import ABC, abstractmethod
from typing import Optional, List
from .entity import Entity
from .coordinate import Coordinate
from src.enums.enums import DamageType, ModuleStatus
from src.entities.projectile import Projectile


class DefenseModule(Entity, ABC):
    """Абстрактный класс для всех защитных модулей (башен)"""

    def __init__(self, position: Coordinate, range_radius: float, damage: float, cost: int, attack_speed: float = 1.0):
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

        self.level = 1
        self.max_level = 3
        self.upgrade_costs: List[int] = []

    def update(self, delta_time: float, enemies: List['HostileEntity']) -> Optional[Projectile]:
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

    def find_target(self, enemies: List['HostileEntity']) -> Optional['HostileEntity']:
        valid_targets = [
            e for e in enemies
            if self.position.distance_to(e.position) <= self.range_radius
        ]
        if not valid_targets:
            return None
        return min(valid_targets, key=lambda e: self.position.distance_to(e.position))

    @abstractmethod
    def fire(self, target: 'HostileEntity') -> Optional[Projectile]:
        """Создает снаряд по цели"""
        pass

    def get_upgrade_cost(self) -> Optional[int]:
        """Возвращает стоимость следующего уровня или None, если макс."""
        if self.level >= self.max_level:
            return None
        return self.upgrade_costs[self.level - 1]

    def can_upgrade(self) -> bool:
        return self.level < self.max_level

    def upgrade(self) -> bool:
        """Применяет апгрейд: повышает уровень и пересчитывает статы"""
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

    def _apply_level_stats(self):
        """Пересчитывает статы в зависимости от текущего уровня"""
        dmg_mult = 1 + (self.level - 1) * 0.4
        rng_mult = 1 + (self.level - 1) * 0.2
        spd_mult = 1 + (self.level - 1) * 0.25

        self.damage = self.base_damage * dmg_mult
        self.range_radius = self.base_range * rng_mult
        self.fire_rate = self.base_fire_rate * spd_mult

    def take_damage(self, amount: float, damage_type: DamageType):
        print(f"Module at {self.position} took {amount} damage!")