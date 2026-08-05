from abc import ABC, abstractmethod
from dataclasses import dataclass
from src.core.coordinate import Coordinate
from src.enums import DamageType


@dataclass
class Entity(ABC):
    """Базовый класс для всех игровых объектов."""
    position: Coordinate

    def get_position(self) -> Coordinate:
        """Возвращает позицию объекта."""
        return self.position

    def set_position(self, new_pos: Coordinate):
        """Задаёт позицию объекта."""
        self.position = new_pos

    @abstractmethod
    def take_damage(self, amount: float, damage_type: DamageType):
        """Наносит объекту урон."""
        pass