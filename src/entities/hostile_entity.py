from abc import ABC, abstractmethod
from .entity import Entity
from .coordinate import Coordinate
from src.enums import DamageType, ArmorType
from typing import List


class HostileEntity(Entity, ABC):
    def __init__(self, position: Coordinate, max_health: float, speed: float, armor: ArmorType, reward: int):
        super().__init__(position)
        self.max_health = max_health
        self.health = max_health
        self.speed = speed
        self.armor = armor
        self.reward = reward
        self.path: List[Coordinate] = []
        self.path_index = 0

    def set_path(self, path: List[Coordinate]):
        """Назначить врагу маршрут"""
        self.path = path
        self.path_index = 0

    def take_damage(self, amount: float, damage_type: DamageType):
        if not self.is_alive(): return
        reduction = 0.0
        if self.armor == ArmorType.HEAVY and damage_type == DamageType.KINETIC:
            reduction = 0.5
        elif self.armor == ArmorType.ENERGY_SHIELDED and damage_type == DamageType.ENERGY:
            reduction = 0.5
        self.health -= amount * (1 - reduction)

    def is_alive(self) -> bool:
        return self.health > 0

    def move_along_path(self, delta_time: float) -> bool:
        """Двигаемся к следующей точке маршрута"""
        if not self.path or self.path_index >= len(self.path):
            return True

        move_distance = self.speed * delta_time

        while self.path_index < len(self.path) and move_distance > 0:
            target = self.path[self.path_index]
            dx = target.x - self.position.x
            dy = target.y - self.position.y
            dist = (dx ** 2 + dy ** 2) ** 0.5

            if dist <= move_distance:
                move_distance -= dist
                self.position = Coordinate(target.x, target.y)
                self.path_index += 1
            else:
                self.position.x += (dx / dist) * move_distance
                self.position.y += (dy / dist) * move_distance
                move_distance = 0

        return self.path_index >= len(self.path)

    @abstractmethod
    def act(self, delta_time: float):
        pass