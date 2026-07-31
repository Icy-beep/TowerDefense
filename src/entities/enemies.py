from typing import Optional
from src.entities.hostile_entity import HostileEntity
from src.enums import ArmorType, Faction
from src.core.coordinate import Coordinate

class DroneWalker(HostileEntity):
    """Быстрый и слабый механический дрон корпорации."""

    def __init__(self, position: Coordinate, max_health: float = 60, speed: float = 50,
                 armor: ArmorType = ArmorType.LIGHT, reward: int = 15,
                 faction: Faction = Faction.CORPORATION, vision_radius: Optional[float] = None):
        """Создаёт лёгкого дрона."""
        super().__init__(position, max_health=max_health, speed=speed, armor=armor, reward=reward, faction=faction,
                          vision_radius=vision_radius)

    def act(self, delta_time: float, in_danger: bool = False):
        """Не выполняет особых действий."""
        pass

class HeavyAssaultDrone(HostileEntity):
    """Тяжёлый штурмовой дрон корпорации."""

    def __init__(self, position: Coordinate, max_health: float = 180, speed: float = 35,
                 armor: ArmorType = ArmorType.HEAVY, reward: int = 45,
                 faction: Faction = Faction.CORPORATION, vision_radius: Optional[float] = None):
        """Создаёт тяжёлого штурмового дрона."""
        super().__init__(position, max_health=max_health, speed=speed, armor=armor, reward=reward, faction=faction,
                          vision_radius=vision_radius)

    def act(self, delta_time: float, in_danger: bool = False):
        """Не выполняет особых действий."""
        pass

class GiantRoach(HostileEntity):
    """Медленный и живучий гигантский таракан фауны планеты."""

    def __init__(self, position: Coordinate, max_health: float = 250, speed: float = 25,
                 armor: ArmorType = ArmorType.HEAVY, reward: int = 40,
                 faction: Faction = Faction.FAUNA, vision_radius: Optional[float] = None):
        """Создаёт гигантского таракана."""
        super().__init__(position, max_health=max_health, speed=speed, armor=armor, reward=reward, faction=faction,
                          vision_radius=vision_radius)

    def act(self, delta_time: float, in_danger: bool = False):
        """Не выполняет особых действий."""
        pass

class ScoutDrone(HostileEntity):
    """Дрон-разведчик корпорации: только разведка, убегает от башен, не участвует в группах."""

    VISION_RADIUS = 260.0

    def __init__(self, position: Coordinate, max_health: float = 100, speed: float = 70,
                 armor: ArmorType = ArmorType.ENERGY_SHIELDED, reward: int = 60,
                 faction: Faction = Faction.CORPORATION, vision_radius: Optional[float] = None):
        """Создаёт дрона-разведчика."""
        super().__init__(position, max_health=max_health, speed=speed, armor=armor, reward=reward, faction=faction,
                          vision_radius=vision_radius)

    def act(self, delta_time: float, in_danger: bool = False):
        """Не выполняет особых действий — вся логика бегства находится в Map.update()."""
        pass

    def avoids_danger(self) -> bool:
        """Разведчик всегда убегает от простреливаемых зон вместо боя."""
        return True

class MedicDrone(HostileEntity):
    """Дрон-медик корпорации: не атакует, ищет ближайшую группу союзников,
    присоединяется к ней и лечит - пока не в группе, избегает башен."""

    def __init__(self, position: Coordinate, max_health: float = 90, speed: float = 55,
                 armor: ArmorType = ArmorType.ENERGY_SHIELDED, reward: int = 50,
                 faction: Faction = Faction.CORPORATION, vision_radius: Optional[float] = None):
        """Создаёт дрона-медика."""
        super().__init__(position, max_health=max_health, speed=speed, armor=armor, reward=reward, faction=faction,
                          vision_radius=vision_radius)

    def act(self, delta_time: float, in_danger: bool = False):
        """Не выполняет особых действий - поиск группы и лечение находятся в Map.update()."""
        pass

    def is_combatant(self) -> bool:
        """Медик никогда не атакует врагов и не участвует в захвате башен."""
        return False

    def heals_allies(self) -> bool:
        """Медик лечит участников своей группы, пока состоит в ней."""
        return True

    def avoids_danger(self) -> bool:
        """Пока не присоединился к группе - избегает простреливаемых зон;
        в группе (занят лечением) - игнорирует обстрел и не убегает."""
        return self.group_leader is None

class BioTitan(HostileEntity):
    """Огромный и живучий органический титан фауны планеты."""

    def __init__(self, position: Coordinate, max_health: float = 400, speed: float = 20,
                 armor: ArmorType = ArmorType.ORGANIC, reward: int = 70,
                 faction: Faction = Faction.FAUNA, vision_radius: Optional[float] = None):
        """Создаёт био-титана."""
        super().__init__(position, max_health=max_health, speed=speed, armor=armor, reward=reward, faction=faction,
                          vision_radius=vision_radius)

    def act(self, delta_time: float, in_danger: bool = False):
        """Не выполняет особых действий."""
        pass
