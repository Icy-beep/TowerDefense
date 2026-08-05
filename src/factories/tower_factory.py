"""Фабрика башен."""
from typing import Dict, Optional, Type

from src.entities.defense_module import DefenseModule
from src.core.coordinate import Coordinate
from src.entities.turrets import LaserTurret, BulletTurret, MortarTurret
from src.entities.power_generator import PowerGenerator
from src.entities.power_pylon import PowerPylon
from src.config.config_loader import ConfigLoader


class TowerFactory:
    """Создаёт башни по имени типа."""

    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        """Создаёт фабрику и регистрирует стандартные типы башен."""
        self._registry: Dict[str, Type[DefenseModule]] = {}
        self._config_loader = config_loader or ConfigLoader()
        self.register("laser", LaserTurret)
        self.register("bullet", BulletTurret)
        self.register("mortar", MortarTurret)
        self.register("generator", PowerGenerator)
        self.register("pylon", PowerPylon)

    def register(self, type_name: str, tower_class: Type[DefenseModule]) -> None:
        """Регистрирует новый тип башни."""
        self._registry[type_name] = tower_class

    def create(self, type_name: str, position: Coordinate) -> Optional[DefenseModule]:
        """Создаёт башню заданного типа в указанной позиции."""
        tower_class = self._registry.get(type_name)
        if tower_class is None:
            return None
        config = self._config_loader.get_tower_config(type_name)
        tower = tower_class(position, **config)
        tower.type_name = type_name
        return tower

    def get_class(self, type_name: str) -> Optional[Type[DefenseModule]]:
        """Возвращает класс башни по имени типа."""
        return self._registry.get(type_name)

    def available_types(self) -> list:
        """Возвращает список зарегистрированных типов башен."""
        return list(self._registry.keys())
