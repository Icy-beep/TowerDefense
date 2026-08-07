"""Пилон - дешёвый ретранслятор энергосети без собственной генерации."""
from src.core.coordinate import Coordinate
from src.entities.power_infrastructure import PowerInfrastructure


class PowerPylon(PowerInfrastructure):
    """Ретранслятор энергосети: сам не генерирует энергию и включается, только когда
    оказывается в цепочке связанных узлов, доходящей до базы или генератора (см.
    Map._update_power_grid). Дешевле генератора и с меньшим запасом прочности - его
    роль не производство, а протягивание сети дальше от источника."""

    IS_SOURCE = False

    def __init__(self, position: Coordinate, range_radius: float = 600.0, cost: int = 60,
                 max_health: float = 60.0):
        """Создаёт пилон энергосети."""
        super().__init__(position, range_radius=range_radius, cost=cost, max_health=max_health)
