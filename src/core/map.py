import math
from typing import Dict, List, Optional
from src.core.coordinate import Coordinate
from src.entities.defense_module import DefenseModule
from src.entities.hostile_entity import HostileEntity
from src.entities.projectile import Projectile
from src.core.navigation import NavigationGrid
from src.systems.faction_intel import FactionIntel
from src.enums import Faction


class Map:
    """Игровая карта: башни, враги, снаряды, разведка и пути."""

    def __init__(self, width=4000, height=4000, group_formation=None):
        """Создаёт пустую карту заданного размера."""
        self.width = width
        self.height = height

        self.modules: List[DefenseModule] = []
        self.enemies: List[HostileEntity] = []
        self.projectiles: List[Projectile] = []

        self.nav_grid = NavigationGrid(width, height, cell_size=32)

        self.base_position: Optional[Coordinate] = None
        self.faction_intel: Dict[Faction, FactionIntel] = {faction: FactionIntel() for faction in Faction}

        if group_formation is None:
            from src.systems.group_formation import GroupFormationSystem
            group_formation = GroupFormationSystem()
        self.group_formation = group_formation

        self.spawn_points = []
        self.towers_lost_count = 0

    def add_module(self, module: DefenseModule):
        """Добавляет башню на карту."""
        self.modules.append(module)

    def can_place_module(self, position: Coordinate, min_distance: float = 30.0) -> bool:
        """Проверяет, можно ли поставить башню в этой точке."""
        if not (0 <= position.x <= self.width and 0 <= position.y <= self.height):
            return False
        return all(position.distance_to(m.position) >= min_distance for m in self.modules)

    def snap_to_grid(self, position: Coordinate) -> Coordinate:
        """Привязывает точку к центру ближайшей клетки сетки."""
        node = self.nav_grid.get_node(position.x, position.y)
        if node is None:
            return position
        return self.nav_grid.get_world_pos(node)

    def spawn_enemy(self, enemy: HostileEntity):
        """Добавляет врага на карту."""
        self.enemies.append(enemy)

    def is_position_covered(self, position: Coordinate) -> bool:
        """Проверяет, простреливается ли точка хотя бы одной башней."""
        return any(position.distance_to(m.position) <= m.range_radius for m in self.modules)

    TOWER_AVOIDANCE_COST = 25.0

    def path_to_base(self, start_pos: Coordinate, faction: Faction) -> List[Coordinate]:
        """Строит путь до базы, обходя известные фракции башни."""
        if self.base_position is None:
            return []
        intel = self.faction_intel.setdefault(faction, FactionIntel())
        blocked_nodes = set()
        avoidance_cost: Dict[tuple, float] = {}
        for tower in intel.known_towers():
            if tower.is_destroyed():
                continue
            node = self.nav_grid.get_node(tower.position.x, tower.position.y)
            if node is None:
                continue
            blocked_nodes.add((node.x, node.y))

            radius_cells = int(tower.range_radius / self.nav_grid.cell_size) + 1
            for dx in range(-radius_cells, radius_cells + 1):
                for dy in range(-radius_cells, radius_cells + 1):
                    if math.hypot(dx, dy) * self.nav_grid.cell_size > tower.range_radius:
                        continue
                    key = (node.x + dx, node.y + dy)
                    avoidance_cost[key] = avoidance_cost.get(key, 0.0) + self.TOWER_AVOIDANCE_COST

        path = self.nav_grid.find_path(start_pos, self.base_position,
                                        extra_blocked=blocked_nodes, extra_cost=avoidance_cost)
        if not path and avoidance_cost:
            path = self.nav_grid.find_path(start_pos, self.base_position, extra_blocked=blocked_nodes)
        return path

    def replan_enemy_paths(self, factions: Optional[set] = None):
        """Пересчитывает путь живых врагов до базы."""
        for enemy in self.enemies:
            if not enemy.is_alive():
                continue
            if factions is not None and enemy.faction not in factions:
                continue
            new_path = self.path_to_base(enemy.position, enemy.faction)
            if new_path:
                enemy.set_path(new_path)

    TOWER_HUNT_RADIUS = 300.0

    TOWER_HUNT_RADIUS_OVERRIDES = {
        Faction.FAUNA: 450.0,
    }

    def _hunt_radius_for(self, faction: Faction) -> float:
        """Радиус охоты на башни для фракции."""
        return self.TOWER_HUNT_RADIUS_OVERRIDES.get(faction, self.TOWER_HUNT_RADIUS)

    def _update_group_targets(self, enemies: List[HostileEntity]):
        """Назначает лидерам групп ближайшую известную башню в радиусе охоты."""
        for enemy in enemies:
            if not enemy.is_alive() or not enemy.is_group_leader:
                continue
            if enemy.target_tower is not None and not enemy.target_tower.is_destroyed():
                continue

            intel = self.faction_intel.setdefault(enemy.faction, FactionIntel())
            hunt_radius = self._hunt_radius_for(enemy.faction)
            candidates = [
                tower for tower in intel.known_towers()
                if not tower.is_destroyed()
                and enemy.position.distance_to(tower.position) <= hunt_radius
            ]
            enemy.target_tower = min(candidates, key=lambda t: enemy.position.distance_to(t.position)) \
                if candidates else None

    def _update_vision(self, enemies: List[HostileEntity]) -> set:
        """Открывает фракциям башни, попавшие в радиус обзора их врагов."""
        changed_factions = set()
        for enemy in enemies:
            if not enemy.is_alive():
                continue
            intel = self.faction_intel.setdefault(enemy.faction, FactionIntel())
            for tower in self.modules:
                if intel.knows(tower):
                    continue
                if enemy.position.distance_to(tower.position) <= enemy.vision_radius:
                    if intel.reveal(tower):
                        changed_factions.add(enemy.faction)
        return changed_factions

    def update(self, delta_time: float) -> tuple[List[HostileEntity], List[HostileEntity]]:
        """Обновляет карту на один кадр и возвращает (дошедшие до базы, убитые враги)."""
        destroyed_this_frame = sum(1 for module in self.modules if module.is_destroyed())
        self.towers_lost_count += destroyed_this_frame
        self.modules = [module for module in self.modules if not module.is_destroyed()]

        self._update_group_targets(self.enemies)

        enemies_reached_base = []
        killed_enemies = []
        surviving_enemies = []

        for enemy in self.enemies:
            if not enemy.is_alive():
                killed_enemies.append(enemy)
                continue

            target_tower = enemy.group_target_tower()
            hunting_tower = target_tower is not None and not target_tower.is_destroyed()

            if not hunting_tower and enemy.path_index >= len(enemy.path):
                enemies_reached_base.append(enemy)
                continue

            in_danger = self.is_position_covered(enemy.position)
            enemy.act(delta_time, in_danger)

            if enemy.is_moving():
                if hunting_tower:
                    distance = enemy.position.distance_to(target_tower.position)
                    if distance <= enemy.ATTACK_RANGE:
                        enemy.attack_tower(target_tower, delta_time)
                    else:
                        enemy.move_towards_point(target_tower.position, delta_time)
                else:
                    leader = enemy.group_leader
                    if leader is not None and leader.is_alive() and not leader.has_reached_end_of_path():
                        formation_target = Coordinate(leader.position.x + enemy.formation_offset.x,
                                                        leader.position.y + enemy.formation_offset.y)
                        enemy.move_towards_point(formation_target, delta_time)
                    else:
                        if leader is not None:
                            enemy.leave_group()
                        enemy.move_along_path(delta_time)

            surviving_enemies.append(enemy)

        self.enemies = surviving_enemies
        self.group_formation.update(delta_time, self.enemies)

        changed_factions = self._update_vision(self.enemies)
        if changed_factions:
            self.replan_enemy_paths(factions=changed_factions)

        for module in self.modules:
            projectile = module.update(delta_time, self.enemies)
            if projectile:
                self.projectiles.append(projectile)

        surviving_projectiles = []
        spawned_projectiles = []
        for projectile in self.projectiles:
            alive = projectile.update(delta_time, self.enemies)
            spawned_projectiles.extend(projectile.collect_spawned())
            if alive:
                surviving_projectiles.append(projectile)
        self.projectiles = surviving_projectiles + spawned_projectiles

        return enemies_reached_base, killed_enemies