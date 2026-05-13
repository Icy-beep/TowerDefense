from typing import List
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

    def update(self, delta_time: float):
        for enemy in self.enemies[:]:
            if not enemy.is_alive():
                self.enemies.remove(enemy)
                continue
            enemy.move_along_path(self.path, delta_time)

        for module in self.modules:
            fired_proj = module.update(delta_time, self.enemies)
            if fired_proj:
                self.projectiles.append(fired_proj)

        for proj in self.projectiles[:]:
            if not proj.update(delta_time):
                self.projectiles.remove(proj)