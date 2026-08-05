"""Генератор энергии - независимый источник питания энергосети."""
from src.entities.power_infrastructure import PowerInfrastructure
from src.core.coordinate import Coordinate


class PowerGenerator(PowerInfrastructure):
    """Автономная электростанция: сама по себе всегда под напряжением (не требует
    подключения к базе) и снабжает энергией всё в радиусе range_radius - как боевые
    башни напрямую, так и другие узлы сети (пилоны, другие генераторы) для дальнейшей
    ретрансляции. См. Map._update_power_grid."""

    IS_SOURCE = True

    def __init__(self, position: Coordinate, range_radius: float = 500.0, cost: int = 220,
                 max_health: float = 150.0):
        """Создаёт генератор энергии."""
        super().__init__(position, range_radius=range_radius, cost=cost, max_health=max_health)
