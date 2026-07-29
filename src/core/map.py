from typing import List
from src.core.coordinate import Coordinate
from src.entities.defense_module import DefenseModule
from src.entities.hostile_entity import HostileEntity
from src.entities.projectile import Projectile
from src.core.navigation import NavigationGrid


class Map:
    def __init__(self, width=4000, height=4000):
        self.width = width
        self.height = height

        self.modules: List[DefenseModule] = []
        self.enemies: List[HostileEntity] = []
        self.projectiles: List[Projectile] = []

        self.nav_grid = NavigationGrid(width, height, cell_size=32)

        self.spawn_points = []

    def add_module(self, module: DefenseModule):
        """Строим башню и блокируем клетку для врагов"""
        self.modules.append(module)
        self.nav_grid.set_blocked(module.position.x, module.position.y, blocked=True)

    def can_place_module(self, position: Coordinate, min_distance: float = 30.0) -> bool:
        """Проверка допустимости зоны для установки башни."""
        if not (0 <= position.x <= self.width and 0 <= position.y <= self.height):
            return False
        return all(position.distance_to(m.position) >= min_distance for m in self.modules)

    def spawn_enemy(self, enemy: HostileEntity):
        self.enemies.append(enemy)

    def update(self, delta_time: float) -> tuple[List[HostileEntity], List[HostileEntity]]:
        """Возвращает (enemies_reached_base, killed_enemies)"""
        enemies_reached_base = []
        killed_enemies = []
        surviving_enemies = []

        for enemy in self.enemies:
            if not enemy.is_alive():
                killed_enemies.append(enemy)
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
        return enemies_reached_base, killed_enemies