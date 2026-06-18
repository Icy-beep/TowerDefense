from typing import List
from src.entities.coordinate import Coordinate
from src.entities.defense_module import DefenseModule
from src.entities.hostile_entity import HostileEntity
from src.entities.projectile import Projectile
from src.core.navigation import NavigationGrid


class Map:
    def __init__(self, width=4000, height=4000):
        self.modules: List[DefenseModule] = []
        self.enemies: List[HostileEntity] = []
        self.projectiles: List[Projectile] = []

        self.nav_grid = NavigationGrid(width, height, cell_size=32)

        self.spawn_points = []

    def add_module(self, module: DefenseModule):
        """Строим башню и блокируем клетку для врагов"""
        self.modules.append(module)
        self.nav_grid.set_blocked(module.position.x, module.position.y, blocked=True)

    def spawn_enemy(self, enemy: HostileEntity):
        self.enemies.append(enemy)

    def update(self, delta_time: float) -> List[HostileEntity]:
        enemies_reached_base = []
        surviving_enemies = []

        for enemy in self.enemies:
            if not enemy.is_alive():
                continue
            if enemy.path_index >= len(enemy.path):
                enemies_reached_base.append(enemy)
                continue
            enemy.move_along_path(delta_time)
            surviving_enemies.append(enemy)

        self.enemies = surviving_enemies

        for module in self.modules:
            projectile = module.update(delta_time, self.enemies)
            if projectile:
                self.projectiles.append(projectile)

        self.projectiles = [p for p in self.projectiles if p.update(delta_time)]
        return enemies_reached_base