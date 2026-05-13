from dataclasses import dataclass
from .entity import Entity
from .coordinate import Coordinate
from src.enums.enums import DamageType


@dataclass
class Projectile:
    """Снаряд, летящий от башни к врагу"""
    position: Coordinate
    target: Entity
    damage: float
    damage_type: DamageType
    speed: float = 5.0

    def update(self, delta_time: float):
        """Движение к цели"""
        if not self.target:
            return False

        direction = (self.target.position.x - self.position.x,
                     self.target.position.y - self.position.y)
        dist = (direction[0] ** 2 + direction[1] ** 2) ** 0.5

        if dist < self.speed * delta_time:

            self.target.take_damage(self.damage, self.damage_type)
            return False

        move_ratio = (self.speed * delta_time) / dist
        self.position.x += direction[0] * move_ratio
        self.position.y += direction[1] * move_ratio
        return True