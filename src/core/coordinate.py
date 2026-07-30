from dataclasses import dataclass
import math

@dataclass
class Coordinate:
    """Точка на карте."""
    x: float
    y: float

    def distance_to(self, other: 'Coordinate') -> float:
        """Расстояние до другой точки."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)

    def __eq__(self, other):
        """Сравнивает координаты по x и y."""
        if isinstance(other, Coordinate):
            return self.x == other.x and self.y == other.y
        return False
