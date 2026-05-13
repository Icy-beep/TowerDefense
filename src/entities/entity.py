from abc import ABC, abstractmethod
from dataclasses import dataclass
from .coordinate import Coordinate
from src.enums.enums import DamageType


@dataclass
class Entity(ABC):
    """Базовый класс для всех игровых объектов"""
    position: Coordinate

    def get_position(self) -> Coordinate:
        return self.position

    def set_position(self, new_pos: Coordinate):
        self.position = new_pos

    @abstractmethod
    def take_damage(self, amount: float, damage_type: DamageType):
        """Метод получения урона (должен быть реализован в наследниках)"""
        pass