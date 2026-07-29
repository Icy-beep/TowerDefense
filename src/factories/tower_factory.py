"""TowerFactory — фабрика башен.

Это единственное место, которое
знает о конкретных классах башен. Контроллер и View работают только со
строками ("laser", "bullet", "mortar") — это и есть точка расширения под
TowerConfig/towers.json: чтобы добавить новую башню, будет
достаточно зарегистрировать её здесь, ничего не трогая в UI/контроллере.
"""
from typing import Dict, Optional, Type

from src.entities.defense_module import DefenseModule
from src.core.coordinate import Coordinate
from src.entities.turrets import LaserTurret, BulletTurret, MortarTurret


class TowerFactory:
    def __init__(self):
        self._registry: Dict[str, Type[DefenseModule]] = {}
        self.register("laser", LaserTurret)
        self.register("bullet", BulletTurret)
        self.register("mortar", MortarTurret)

    def register(self, type_name: str, tower_class: Type[DefenseModule]) -> None:
        self._registry[type_name] = tower_class

    def create(self, type_name: str, position: Coordinate) -> Optional[DefenseModule]:
        tower_class = self._registry.get(type_name)
        if tower_class is None:
            return None
        tower = tower_class(position)
        tower.type_name = type_name
        return tower

    def get_class(self, type_name: str) -> Optional[Type[DefenseModule]]:
        """Только для View (нужно узнать range/цвет для превью) —
        не для создания объектов, для этого есть create()."""
        return self._registry.get(type_name)

    def available_types(self) -> list:
        return list(self._registry.keys())
