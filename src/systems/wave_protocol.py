from typing import List, Type, Callable
from src.entities.hostile_entity import HostileEntity
from src.core.map import Map

class WaveConfig:
    def __init__(self, enemy_classes: List[Type[HostileEntity]], count: int, interval: float):
        self.enemy_classes = enemy_classes
        self.count = count
        self.interval = interval

class WaveProtocol:
    def __init__(self):
        self.current_wave_idx = 0
        self.waves: List[WaveConfig] = []
        self.spawn_timer = 0.0
        self.enemies_spawned = 0
        self.is_active = False
        self.finished = False

    def set_waves(self, waves: List[WaveConfig]):
        self.waves = waves

    def start_next_wave(self):
        if self.current_wave_idx < len(self.waves):
            self.is_active = True
            self.enemies_spawned = 0
            self.spawn_timer = 0.0
        else:
            self.finished = True

    def update(self, delta_time: float, game_map: Map, spawn_factory: Callable):
        if not self.is_active or self.finished:
            return

        self.spawn_timer += delta_time
        config = self.waves[self.current_wave_idx]

        if self.spawn_timer >= config.interval and self.enemies_spawned < config.count:
            cls = config.enemy_classes[self.enemies_spawned % len(config.enemy_classes)]
            spawn_pos = game_map.path[0] if game_map.path else None
            if spawn_pos:
                enemy = spawn_factory(cls, spawn_pos)
                game_map.spawn_enemy(enemy)
                self.enemies_spawned += 1
                self.spawn_timer = 0.0

        if self.enemies_spawned >= config.count and not game_map.enemies:
            self.is_active = False
            self.current_wave_idx += 1
            self.start_next_wave()

    def is_all_waves_complete(self) -> bool:
        return self.finished