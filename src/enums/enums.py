from enum import Enum

class ZoneType(Enum):
    SPAWN = "Spawn"
    FAUNA = "Fauna"
    SHELTER = "Shelter"
    BASE = "Base"

class DamageType(Enum):
    KINETIC = "Kinetic"
    ENERGY = "Energy"
    EMP = "EMP"
    EXPLOSIVE = "Explosive"

class ArmorType(Enum):
    LIGHT = "Light"
    HEAVY = "Heavy"
    ENERGY_SHIELDED = "EnergyShielded"
    ORGANIC = "Organic"

class ModuleStatus(Enum):
    IDLE = "Idle"
    ACTIVE = "Active"
    OVERHEATED = "Overheated"
    OFFLINE = "Offline"

class CommanderState(Enum):
    IN_TRANSIT = "InTransit"
    AVAILABLE = "Available"
    ACTIVE = "Active"
    DEAD = "Dead"

class GameMode(Enum):
    HERO = "HeroMode"
    TOWER_DEFENSE = "TowerDefenseMode"

class GameState(Enum):
    MENU = "Menu"
    PLAYING = "Playing"
    PAUSED = "Paused"
    GAME_OVER = "GameOver"
    VICTORY = "Victory"