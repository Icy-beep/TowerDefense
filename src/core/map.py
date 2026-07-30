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
        self.spawn_points_by_faction: Dict[Faction, List[Coordinate]] = {}
        self.towers_lost_count = 0

    def add_module(self, module: DefenseModule):
        """Добавляет башню на карту."""
        self.modules.append(module)

    def spawn_points_for(self, faction: Faction) -> List[Coordinate]:
        """Возвращает точки спавна фракции, а если для неё отдельных не задано — общий список."""
        return self.spawn_points_by_faction.get(faction) or self.spawn_points

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

    PATROL_ANGULAR_SPEED = 0.5
    PATROL_RADIUS_PADDING = 150.0
    GAP_ANGULAR_WINDOW = math.radians(25)

    def _bearing_from_base(self, position: Coordinate) -> float:
        """Угол точки относительно базы, в радианах."""
        return math.atan2(position.y - self.base_position.y, position.x - self.base_position.x)

    def _is_gap_at_angle(self, angle: float, known_towers: List[DefenseModule]) -> bool:
        """Правда ли, что в этом направлении от базы нет известной башни поблизости."""
        for tower in known_towers:
            tower_angle = self._bearing_from_base(tower.position)
            diff = abs((tower_angle - angle + math.pi) % (2 * math.pi) - math.pi)
            if diff <= self.GAP_ANGULAR_WINDOW:
                return False
        return True

    def _advance_patrol(self, enemy: HostileEntity, delta_time: float, known_towers: List[DefenseModule]):
        """Двигает врага по кругу вокруг базы на радиусе патрулирования."""
        patrol_radius = self.PATROL_RADIUS_PADDING + max((t.range_radius for t in known_towers), default=0.0)
        if enemy.patrol_angle is None:
            enemy.patrol_angle = self._bearing_from_base(enemy.position)
            enemy.patrol_direction = 1 if id(enemy) % 2 == 0 else -1
        enemy.patrol_angle += enemy.patrol_direction * self.PATROL_ANGULAR_SPEED * delta_time
        target = Coordinate(
            self.base_position.x + math.cos(enemy.patrol_angle) * patrol_radius,
            self.base_position.y + math.sin(enemy.patrol_angle) * patrol_radius,
        )
        enemy.move_towards_point(target, delta_time)

    def _advance_towards_base(self, enemy: HostileEntity, delta_time: float):
        """Движение к базе: патрулирует периметр, если известная башня перекрывает
        текущее направление, иначе идёт по обычному маршруту."""
        if self.base_position is None:
            enemy.move_along_path(delta_time)
            return

        intel = self.faction_intel.setdefault(enemy.faction, FactionIntel())
        known_towers = [t for t in intel.known_towers() if not t.is_destroyed()]
        bearing = self._bearing_from_base(enemy.position)
        gap_here = self._is_gap_at_angle(bearing, known_towers)

        if enemy.is_patrolling:
            if gap_here:
                enemy.is_patrolling = False
                new_path = self.path_to_base(enemy.position, enemy.faction)
                if new_path:
                    enemy.set_path(new_path)
                enemy.move_along_path(delta_time)
            else:
                self._advance_patrol(enemy, delta_time, known_towers)
            return

        if known_towers and not gap_here:
            enemy.is_patrolling = True
            self._advance_patrol(enemy, delta_time, known_towers)
            return

        enemy.move_along_path(delta_time)

    def _nearest_covering_tower(self, position: Coordinate) -> Optional[DefenseModule]:
        """Возвращает ближайшую башню, простреливающую точку, или None."""
        covering = [m for m in self.modules if position.distance_to(m.position) <= m.range_radius]
        if not covering:
            return None
        return min(covering, key=lambda m: position.distance_to(m.position))

    def _flee_point_from(self, position: Coordinate, tower: DefenseModule) -> Coordinate:
        """Точка вдали от башни, противоположная её направлению от врага."""
        dx = position.x - tower.position.x
        dy = position.y - tower.position.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            dx, dy, dist = 1.0, 0.0, 1.0
        flee_distance = tower.range_radius + 50.0
        return Coordinate(tower.position.x + dx / dist * flee_distance, tower.position.y + dy / dist * flee_distance)

    def _find_enemy_combat_target(self, enemy: HostileEntity) -> Optional[HostileEntity]:
        """Находит ближайшего живого врага чужой фракции в радиусе обзора."""
        candidates = [
            other for other in self.enemies
            if other is not enemy
            and other.is_alive()
            and other.faction != enemy.faction
            and enemy.position.distance_to(other.position) <= enemy.vision_radius
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda other: enemy.position.distance_to(other.position))

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

            combat_target = self._find_enemy_combat_target(enemy)
            in_combat = combat_target is not None

            if not hunting_tower and not in_combat and enemy.path_index >= len(enemy.path):
                enemies_reached_base.append(enemy)
                continue

            in_danger = self.is_position_covered(enemy.position)
            enemy.act(delta_time, in_danger)

            if enemy.is_moving():
                if in_combat:
                    distance = enemy.position.distance_to(combat_target.position)
                    if distance <= enemy.ATTACK_RANGE:
                        enemy.attack_enemy(combat_target, delta_time)
                    else:
                        enemy.move_towards_point(combat_target.position, delta_time)
                elif hunting_tower:
                    distance = enemy.position.distance_to(target_tower.position)
                    if distance <= enemy.ATTACK_RANGE:
                        enemy.attack_tower(target_tower, delta_time)
                    else:
                        enemy.move_towards_point(target_tower.position, delta_time)
                elif in_danger and enemy.avoids_danger():
                    threatening_tower = self._nearest_covering_tower(enemy.position)
                    if threatening_tower is not None:
                        enemy.is_patrolling = False
                        flee_point = self._flee_point_from(enemy.position, threatening_tower)
                        enemy.move_towards_point(flee_point, delta_time)
                    else:
                        self._advance_towards_base(enemy, delta_time)
                else:
                    leader = enemy.group_leader
                    if leader is not None and leader.is_alive() and not leader.has_reached_end_of_path():
                        formation_target = Coordinate(leader.position.x + enemy.formation_offset.x,
                                                        leader.position.y + enemy.formation_offset.y)
                        enemy.move_towards_point(formation_target, delta_time)
                    else:
                        if leader is not None:
                            enemy.leave_group()
                        self._advance_towards_base(enemy, delta_time)

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