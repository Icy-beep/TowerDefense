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


# У каждого типа урона есть один "жёсткий контр" среди типов брони - 50% сопротивление.
# Общая таблица нужна и HostileEntity.take_damage (расчёт урона), и DefenseModule.find_target
# (ИИ-модуль "игнорировать стойких к себе") - раньше значения были захардкожены только в
# take_damage, второму месту взять их было неоткуда.
ARMOR_RESISTANCE: dict[tuple[ArmorType, DamageType], float] = {
    (ArmorType.HEAVY, DamageType.KINETIC): 0.5,
    (ArmorType.ENERGY_SHIELDED, DamageType.ENERGY): 0.5,
    (ArmorType.ORGANIC, DamageType.EXPLOSIVE): 0.5,
}


def damage_reduction_for(armor: ArmorType, damage_type: DamageType) -> float:
    """Возвращает долю снижения урона (0.0-1.0) от брони armor против damage_type."""
    return ARMOR_RESISTANCE.get((armor, damage_type), 0.0)


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
