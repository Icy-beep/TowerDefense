from src.entities.hostile_entity import HostileEntity
from src.enums.enums import ArmorType
from src.entities.coordinate import Coordinate

class DroneWalker(HostileEntity):
    """Быстрый, слабый, легкая броня"""
    def __init__(self, position: Coordinate):
        super().__init__(position, max_health=60, speed=50, armor=ArmorType.LIGHT, reward=15)

    def act(self, delta_time: float):
        pass

class GiantRoach(HostileEntity):
    """Медленный, живой, тяжелая броня"""
    def __init__(self, position: Coordinate):
        super().__init__(position, max_health=250, speed=25, armor=ArmorType.HEAVY, reward=40)

    def act(self, delta_time: float):
        pass

class ScoutDrone(HostileEntity):
    """Разведчик, средняя броня, высокая награда"""
    def __init__(self, position: Coordinate):
        super().__init__(position, max_health=100, speed=70, armor=ArmorType.ENERGY_SHIELDED, reward=60)

    def act(self, delta_time: float):
        pass