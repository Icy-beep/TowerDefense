from src.core.map import Map
from src.systems.resource_bank import ResourceBank
from src.systems.wave_protocol import WaveProtocol, WaveConfig
from src.enums.enums import GameState
from src.entities.hostile_entity import HostileEntity
from src.entities.coordinate import Coordinate
from typing import List, Type


class GameSession:
    def __init__(self):
        self.map = Map()
        self.resources = ResourceBank()
        self.wave_protocol = WaveProtocol()
        self.state = GameState.MENU
        self.base_health = 100
        self.max_base_health = 100

    def setup_game(self):
        """Инициализация перед стартом"""
        self.state = GameState.PLAYING
        self.base_health = self.max_base_health
        self.resources = ResourceBank(start_credits=150)
        self.map = Map()

        self.map.path = [
            Coordinate(0, 300), Coordinate(200, 300),
            Coordinate(200, 100), Coordinate(600, 100),
            Coordinate(600, 500), Coordinate(800, 500)
        ]

        from src.entities.enemies import DroneWalker, GiantRoach, ScoutDrone
        waves = [
            WaveConfig([DroneWalker], 5, 1.5),
            WaveConfig([DroneWalker, GiantRoach], 8, 1.2),
            WaveConfig([GiantRoach, ScoutDrone], 10, 1.0)
        ]
        self.wave_protocol.set_waves(waves)
        self.wave_protocol.start_next_wave()

    def update(self, delta_time: float):
        if self.state != GameState.PLAYING:
            return

        self.map.update(delta_time)

        self.wave_protocol.update(delta_time, self.map, self._spawn_enemy_factory)

        for enemy in self.map.enemies[:]:
            if enemy.path_index >= len(self.map.path):
                self.base_health -= 10
                self.map.enemies.remove(enemy)
                print(f"Base took damage! Health: {self.base_health}")

        if self.base_health <= 0:
            self.state = GameState.GAME_OVER
        elif self.wave_protocol.is_all_waves_complete() and not self.map.enemies:
            self.state = GameState.VICTORY

    def place_turret(self, turret_class: Type, position: Coordinate) -> bool:
        """Размещение башни с проверкой ресурсов"""
        turret = turret_class(position)
        if self.resources.spend(turret.cost):
            self.map.add_module(turret)
            return True
        return False

    def _spawn_enemy_factory(self, cls: Type[HostileEntity], pos: Coordinate) -> HostileEntity:
        """Фабрика для создания врагов (нужна для WaveProtocol)"""
        return cls(pos)