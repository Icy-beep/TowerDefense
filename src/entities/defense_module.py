from abc import ABC, abstractmethod
from typing import Optional, List
from .entity import Entity
from .coordinate import Coordinate
from src.enums.enums import DamageType, ModuleStatus
from src.entities.projectile import Projectile


class DefenseModule(Entity, ABC):
    """Абстрактный класс для всех защитных модулей (башен)"""

    def __init__(self, position: Coordinate, range_radius: float, damage: float, cost: int):
        super().__init__(position)
        self.range_radius = range_radius
        self.damage = damage
        self.cost = cost
        self.status = ModuleStatus.IDLE
        self.cooldown_timer = 0.0
        self.attack_speed = 1.0

    def update(self, delta_time: float, enemies: List['HostileEntity']):
        if self.status == ModuleStatus.OVERHEATED or self.status == ModuleStatus.OFFLINE:
            return

        if self.cooldown_timer > 0:
            self.cooldown_timer -= delta_time

        if self.cooldown_timer <= 0:
            target = self.find_target(enemies)
            if target:
                self.fire(target)
                self.cooldown_timer = 1.0 / self.attack_speed

    def find_target(self, enemies: List['HostileEntity']) -> Optional['HostileEntity']:
        """Ищет ближайшего врага в радиусе действия"""
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

    def take_damage(self, amount: float, damage_type: DamageType):
        print(f"Module at {self.position} took {amount} damage!")