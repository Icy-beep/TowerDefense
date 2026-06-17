from typing import List, Tuple
from src.entities.coordinate import Coordinate
from src.entities.defense_module import DefenseModule
from src.entities.hostile_entity import HostileEntity
from src.entities.projectile import Projectile

class Map:
    def __init__(self):
        self.modules: List[DefenseModule] = []
        self.enemies: List[HostileEntity] = []
        self.projectiles: List[Projectile] = []
        self.path: List[Coordinate] = []

    def add_module(self, module: DefenseModule):
        self.modules.append(module)

    def spawn_enemy(self, enemy: HostileEntity):
        self.enemies.append(enemy)

    def update(self, delta_time: float) -> Tuple[List[HostileEntity], List[HostileEntity]]:
        enemies_reached_base = []
        enemies_killed = []
        surviving_enemies = []

        for enemy in self.enemies:
            if not enemy.is_alive():
                enemies_killed.append(enemy)
                continue
            if enemy.path_index >= len(self.path):
                enemies_reached_base.append(enemy)
                continue
            enemy.move_along_path(self.path, delta_time)
            surviving_enemies.append(enemy)

        self.enemies = surviving_enemies

        for module in self.modules:
            projectile = module.update(delta_time, self.enemies)
            if projectile:
                self.projectiles.append(projectile)

        self.projectiles = [p for p in self.projectiles if p.update(delta_time)]

        return enemies_reached_base, enemies_killed