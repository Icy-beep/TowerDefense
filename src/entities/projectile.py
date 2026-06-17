from dataclasses import dataclass
from .entity import Entity
from .coordinate import Coordinate
from src.enums import DamageType

@dataclass
class Projectile:
    position: Coordinate
    target: Entity
    damage: float
    damage_type: DamageType
    speed: float = 12.0

    def update(self, delta_time: float) -> bool:
        if self.target is None or not hasattr(self.target, 'is_alive') or not self.target.is_alive():
            return False

        dx = self.target.position.x - self.position.x
        dy = self.target.position.y - self.position.y
        dist = (dx ** 2 + dy ** 2) ** 0.5

        if dist < (self.speed * delta_time) + 12.0:
            self.target.take_damage(self.damage, self.damage_type)
            return False

        move_ratio = (self.speed * delta_time) / dist
        self.position.x += dx * move_ratio
        self.position.y += dy * move_ratio
        return True