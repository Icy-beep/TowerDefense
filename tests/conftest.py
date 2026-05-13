import pytest
from src.entities.coordinate import Coordinate
from src.entities.turrets import LaserTurret, BulletTurret
from src.entities.enemies import DroneWalker, GiantRoach
from src.core.map import Map
from src.systems.resource_bank import ResourceBank
from src.systems.wave_protocol import WaveProtocol, WaveConfig


@pytest.fixture
def coord():
    """Создает координату"""
    return Coordinate(100, 100)


@pytest.fixture
def resource_bank():
    """Создает банк ресурсов с начальными 100 кредитами"""
    return ResourceBank(start_credits=100)


@pytest.fixture
def game_map():
    """Создает карту с путем"""
    map_instance = Map()
    map_instance.path = [
        Coordinate(0, 100),
        Coordinate(200, 100),
        Coordinate(400, 100)
    ]
    return map_instance


@pytest.fixture
def laser_turret(coord):
    """Создает лазерную башню"""
    return LaserTurret(coord)


@pytest.fixture
def bullet_turret(coord):
    """Создает пулеметную башню"""
    return BulletTurret(coord)


@pytest.fixture
def drone_enemy(coord):
    """Создает врага-дрона"""
    return DroneWalker(coord)


@pytest.fixture
def roach_enemy(coord):
    """Создает врага-таракана"""
    return GiantRoach(coord)