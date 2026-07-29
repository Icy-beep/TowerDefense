"""
EnemyFactory — фабрика врагов, тот же принцип, что и TowerFactory.
"""
from typing import Dict, Optional, Type

from src.entities.hostile_entity import HostileEntity
from src.core.coordinate import Coordinate
from src.entities.enemies import DroneWalker, GiantRoach, ScoutDrone


class EnemyFactory:
    def __init__(self):
        self._registry: Dict[str, Type[HostileEntity]] = {}
        self.register("drone_walker", DroneWalker)
        self.register("giant_roach", GiantRoach)
        self.register("scout_drone", ScoutDrone)

    def register(self, type_name: str, enemy_class: Type[HostileEntity]) -> None:
        self._registry[type_name] = enemy_class

    def create(self, type_name: str, position: Coordinate) -> Optional[HostileEntity]:
        enemy_class = self._registry.get(type_name)
        if enemy_class is None:
            return None
        enemy = enemy_class(position)
        enemy.type_name = type_name
        return enemy

    def available_types(self) -> list:
        return list(self._registry.keys())
