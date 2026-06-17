from src.core.map import Map
from src.systems.resource_bank import ResourceBank
from src.systems.wave_protocol import WaveProtocol, WaveConfig
from src.enums import GameState
from src.entities.hostile_entity import HostileEntity
from src.entities.coordinate import Coordinate
from typing import Type


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
        self.map = Map()

        self.map.path = [
            Coordinate(50, 50), Coordinate(250, 50), Coordinate(250, 350),
            Coordinate(650, 350), Coordinate(650, 150), Coordinate(850, 150)
        ]

        print(f"   Путь инициализирован: {len(self.map.path)} точек")
        print(f"   Начало: {self.map.path[0]}")
        print(f"   Конец: {self.map.path[-1]}")

        from src.entities.enemies import DroneWalker, GiantRoach, ScoutDrone
        waves = [
            WaveConfig([DroneWalker], 5, 1.5),
            WaveConfig([DroneWalker, GiantRoach], 8, 1.2),
            WaveConfig([GiantRoach, ScoutDrone], 10, 1.0)
        ]
        self.wave_protocol.set_waves(waves)

    def update(self, delta_time: float):
        if self.state != GameState.PLAYING:
            return

        self.wave_protocol.update(delta_time, self.map, self._spawn_enemy_factory)

        reached_base, killed_enemies = self.map.update(delta_time)

        for _ in reached_base:
            self.base_health -= 10

        for enemy in killed_enemies:
            self.resources.add_reward(enemy.reward)

        if self.base_health <= 0:
            self.state = GameState.GAME_OVER
        elif self.wave_protocol.is_all_waves_complete() and not self.map.enemies:
            self.state = GameState.VICTORY

    def place_turret(self, turret_class: Type, position: Coordinate) -> bool:
        turret = turret_class(position)
        if self.resources.spend(turret.cost):
            self.map.add_module(turret)
            return True
        return False

    def _spawn_enemy_factory(self, cls: Type[HostileEntity], pos: Coordinate) -> HostileEntity:
        return cls(pos)