from abc import ABC, abstractmethod
from .entity import Entity
from .coordinate import Coordinate
from src.enums.enums import DamageType, ArmorType
from typing import List


class HostileEntity(Entity, ABC):
    """Базовый класс для всех врагов"""

    def __init__(self, position: Coordinate, max_health: float, speed: float, armor: ArmorType, reward: int):
        super().__init__(position)
        self.max_health = max_health
        self.health = max_health
        self.speed = speed
        self.armor = armor
        self.reward = reward
        self.path_index = 0

    def take_damage(self, amount: float, damage_type: DamageType):
        reduction = 0.0
        if self.armor == ArmorType.HEAVY and damage_type == DamageType.KINETIC:
            reduction = 0.5
        elif self.armor == ArmorType.ENERGY_SHIELDED and damage_type == DamageType.ENERGY:
            reduction = 0.5

        final_damage = amount * (1 - reduction)
        self.health -= final_damage
        print(f"Enemy at {self.position} took {final_damage} dmg. HP: {self.health}")

    def is_alive(self) -> bool:
        return self.health > 0

    def move_along_path(self, path: List[Coordinate], delta_time: float) -> bool:
        if not path or self.path_index >= len(path):
            return True

        move_distance = self.speed * delta_time

        while self.path_index < len(path) and move_distance > 0:
            target_point = path[self.path_index]
            dx = target_point.x - self.position.x
            dy = target_point.y - self.position.y
            dist = (dx ** 2 + dy ** 2) ** 0.5

            if dist <= move_distance:
                move_distance -= dist
                self.position = target_point
                self.path_index += 1
            else:
                self.position.x += (dx / dist) * move_distance
                self.position.y += (dy / dist) * move_distance
                move_distance = 0

        return self.path_index >= len(path)

    @abstractmethod
    def act(self, delta_time: float):
        pass