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
        self.cooldown_time = 5.0
        self.cooldown_timer = self.cooldown_time
        self.spawn_points = []

    def set_waves(self, waves: List[WaveConfig]):
        self.waves = waves

    def start_next_wave(self):
        if self.finished or self.is_active:
            return False
        if self.current_wave_idx < len(self.waves):
            self.is_active = True
            self.enemies_spawned = 0
            self.spawn_timer = 0.0
            return True
        else:
            self.finished = True
            return False

    def force_start_next_wave(self):
        """Мгновенный запуск волны"""
        if not self.is_active and not self.finished:
            self.cooldown_timer = 0
            self.start_next_wave()

    def update(self, delta_time: float, game_map: Map, spawn_factory: Callable):
        if self.finished:
            return

        if self.is_active:
            self.spawn_timer += delta_time
            config = self.waves[self.current_wave_idx]

            if self.spawn_timer >= config.interval and self.enemies_spawned < config.count:
                cls = config.enemy_classes[self.enemies_spawned % len(config.enemy_classes)]
                import random
                spawn_pos = random.choice(game_map.spawn_points) if hasattr(game_map, 'spawn_points') else \
                game_map.path[0]
                if spawn_pos:
                    enemy = spawn_factory(cls, spawn_pos)
                    game_map.spawn_enemy(enemy)
                    self.enemies_spawned += 1
                    self.spawn_timer = 0.0

            if (self.enemies_spawned >= config.count and
                    not game_map.enemies):
                self.is_active = False
                self.current_wave_idx += 1
                self.cooldown_timer = self.cooldown_time
        else:
            if self.current_wave_idx < len(self.waves):
                self.cooldown_timer -= delta_time
                if self.cooldown_timer <= 0:
                    self.cooldown_timer = 0.0
                    self.start_next_wave()

    def get_time_until_next_wave(self) -> float:
        if self.finished or self.is_active:
            return 0.0
        return max(0.0, self.cooldown_timer)

    def is_all_waves_complete(self) -> bool:
        return self.finished