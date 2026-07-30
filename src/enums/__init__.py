from enum import Enum


class ZoneType(Enum):
    """Тип зоны на карте."""
    SPAWN = "Spawn"
    FAUNA = "Fauna"
    SHELTER = "Shelter"
    BASE = "Base"


class DamageType(Enum):
    """Тип наносимого урона."""
    KINETIC = "Kinetic"
    ENERGY = "Energy"
    EMP = "EMP"
    EXPLOSIVE = "Explosive"


class ArmorType(Enum):
    """Тип брони врага."""
    LIGHT = "Light"
    HEAVY = "Heavy"
    ENERGY_SHIELDED = "EnergyShielded"
    ORGANIC = "Organic"


class Faction(Enum):
    """Фракция врага."""
    CORPORATION = "Corporation"
    FAUNA = "Fauna"


class ModuleStatus(Enum):
    """Состояние башни."""
    IDLE = "Idle"
    ACTIVE = "Active"
    OVERHEATED = "Overheated"
    OFFLINE = "Offline"


class CommanderState(Enum):
    """Состояние командира."""
    IN_TRANSIT = "InTransit"
    AVAILABLE = "Available"
    ACTIVE = "Active"
    DEAD = "Dead"


class GameMode(Enum):
    """Режим игры."""
    HERO = "HeroMode"
    TOWER_DEFENSE = "TowerDefenseMode"


class GameState(Enum):
    """Состояние игровой сессии."""
    MENU = "Menu"
    PLAYING = "Playing"
    PAUSED = "Paused"
    GAME_OVER = "GameOver"
    VICTORY = "Victory"
