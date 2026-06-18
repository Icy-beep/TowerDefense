from src.core.map import Map
from src.systems.resource_bank import ResourceBank
from src.systems.wave_protocol import WaveProtocol, WaveConfig
from src.enums import GameState
from src.entities.hostile_entity import HostileEntity
from src.entities.coordinate import Coordinate
from typing import List, Type
import random


class GameSession:
    def __init__(self):
        self.map = None
        self.resources = ResourceBank()
        self.wave_protocol = WaveProtocol()
        self.state = GameState.MENU
        self.base_health = 100
        self.max_base_health = 100

    def setup_game(self):
        self.state = GameState.PLAYING
        self.base_health = self.max_base_health
        self.resources = ResourceBank(start_credits=300)

        self.map = Map(width=4000, height=4000)
        self.base_position = Coordinate(2000, 2000)
        self.map.nav_grid.set_blocked(self.base_position.x, self.base_position.y, blocked=True)
        self.map.spawn_points = [
            Coordinate(200, 200),
            Coordinate(3800, 200),
            Coordinate(200, 3800),
            Coordinate(3800, 3800)
        ]

        print(f"✅ Карта инициализирована")
        print(f"🏠 База: {self.base_position}")
        print(f"👾 Враги будут атаковать с углов")

        from src.entities.enemies import DroneWalker, GiantRoach, ScoutDrone
        waves = [
            WaveConfig([DroneWalker], 5, 1.5),
            WaveConfig([DroneWalker, GiantRoach], 8, 1.2),
        ]
        self.wave_protocol.set_waves(waves)
        self.wave_protocol.start_next_wave()

    def update(self, delta_time: float):
        if self.state != GameState.PLAYING:
            return

        self.wave_protocol.update(delta_time, self.map, self._spawn_enemy_factory)
        reached_base = self.map.update(delta_time)

        for _ in reached_base:
            self.base_health -= 10

        if self.base_health <= 0:
            self.state = GameState.GAME_OVER

    def place_turret(self, turret_class: Type, position: Coordinate) -> bool:
        turret = turret_class(position)
        if self.resources.spend(turret.cost):
            self.map.add_module(turret)
            return True
        return False

    def _spawn_enemy_factory(self, cls: Type[HostileEntity], pos: Coordinate) -> HostileEntity:
        enemy = cls(pos)
        path = self.map.nav_grid.find_path(pos, self.base_position)
        if path:
            enemy.set_path(path)
        else:
            print(f"Ошибка пути! Враг застрянет.")

        return enemy