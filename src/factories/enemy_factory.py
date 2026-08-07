"""Фабрика врагов."""

from src.config.config_loader import ConfigLoader
from src.core.coordinate import Coordinate
from src.entities.enemies import (
    BioTitan,
    DroneWalker,
    GiantRoach,
    HeavyAssaultDrone,
    MedicDrone,
    ScoutDrone,
    SniperDrone,
)
from src.entities.hostile_entity import HostileEntity
from src.enums import ArmorType, Faction


class EnemyFactory:
    """Создаёт врагов по имени типа."""

    def __init__(self, config_loader: ConfigLoader | None = None):
        """Создаёт фабрику и регистрирует стандартные типы врагов."""
        self._registry: dict[str, type[HostileEntity]] = {}
        self._config_loader = config_loader or ConfigLoader()
        self.register("drone_walker", DroneWalker)
        self.register("giant_roach", GiantRoach)
        self.register("scout_drone", ScoutDrone)
        self.register("heavy_assault_drone", HeavyAssaultDrone)
        self.register("bio_titan", BioTitan)
        self.register("medic_drone", MedicDrone)
        self.register("sniper_drone", SniperDrone)

    def register(self, type_name: str, enemy_class: type[HostileEntity]) -> None:
        """Регистрирует новый тип врага."""
        self._registry[type_name] = enemy_class

    def create(self, type_name: str, position: Coordinate) -> HostileEntity | None:
        """Создаёт врага заданного типа в указанной позиции."""
        enemy_class = self._registry.get(type_name)
        if enemy_class is None:
            return None
        config = self._config_loader.get_enemy_config(type_name)
        if "armor" in config:
            config["armor"] = ArmorType(config["armor"])
        if "faction" in config:
            config["faction"] = Faction(config["faction"])
        enemy = enemy_class(position, **config)
        enemy.type_name = type_name
        return enemy

    def available_types(self) -> list:
        """Возвращает список зарегистрированных типов врагов."""
        return list(self._registry.keys())

    def faction_for(self, type_name: str) -> Faction:
        """Возвращает фракцию врага заданного типа, не создавая его."""
        config = self._config_loader.get_enemy_config(type_name)
        if "faction" in config:
            return Faction(config["faction"])
        return Faction.FAUNA
