import math
import random
from typing import Callable, Dict, List, Optional, Set, Tuple
from collections import deque
from src.core.coordinate import Coordinate
from src.entities.defense_module import DefenseModule
from src.entities.hostile_entity import HostileEntity
from src.entities.fauna_nest import FaunaNest
from src.entities.power_infrastructure import PowerInfrastructure
from src.entities.projectile import Projectile
from src.core.navigation import NavigationGrid
from src.systems.faction_intel import FactionIntel
from src.enums import Faction


class Map:
    """Игровая карта: башни, враги, снаряды, разведка и пути."""

    def __init__(self, width=6000, height=6000, group_formation=None, on_event=None, rng=None):
        """Создаёт пустую карту заданного размера."""
        self.width = width
        self.height = height
        self.on_event: Optional[Callable[[str], None]] = on_event
        self._rng = rng or random
        self._avoid_danger_searches_this_frame = 0

        self.modules: List[DefenseModule] = []
        self.enemies: List[HostileEntity] = []
        self.fauna_nests: List[FaunaNest] = []
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

        # Энергосеть выключена по умолчанию, чтобы карты, созданные напрямую (как в
        # большинстве существующих тестов) без генераторов/пилонов, вели себя как
        # раньше - лимит по питанию действует только там, где GameSession явно включил
        # его в setup_game(). См. _update_power_grid.
        self.power_grid_enabled = False
        self.power_links: List[Tuple[Coordinate, Coordinate]] = []
        self._elapsed_time = 0.0
        self._staging_anchor: Dict[Faction, List[Coordinate]] = {}
        self._staging_anchor_created_at: Dict[int, float] = {}

    def add_module(self, module: DefenseModule):
        """Добавляет башню на карту."""
        self.modules.append(module)

    def add_fauna_nest(self, nest: FaunaNest):
        """Добавляет гнездо фауны на карту."""
        self.fauna_nests.append(nest)

    def _emit(self, event_name: str, **data):
        """Уведомляет подписчика (например, звуковую систему) об игровом событии."""
        if self.on_event:
            self.on_event(event_name, **data)

    def spawn_points_for(self, faction: Faction) -> List[Coordinate]:
        """Возвращает точки спавна фракции."""
        if faction in self.spawn_points_by_faction:
            return self.spawn_points_by_faction[faction]
        return self.spawn_points

    def _footprint_cells(self, position: Coordinate) -> Set[Tuple[int, int]]:
        """Возвращает клетки сетки (DefenseModule.FOOTPRINT_CELLS x FOOTPRINT_CELLS),
        которые займёт башня с центром в position."""
        node = self.nav_grid.get_node(position.x, position.y)
        if node is None:
            return set()
        radius = DefenseModule.FOOTPRINT_CELLS // 2
        return {
            (node.x + dx, node.y + dy)
            for dx in range(-radius, radius + 1)
            for dy in range(-radius, radius + 1)
        }

    def can_place_module(self, position: Coordinate) -> bool:
        """Проверяет, можно ли поставить башню в этой точке: в пределах карты, без
        пересечения её footprint (3x3 клетки) с уже стоящими башнями (чтобы спрайты
        соседних башен не наезжали друг на друга) и не поверх ещё живого гнезда фауны."""
        if not (0 <= position.x <= self.width and 0 <= position.y <= self.height):
            return False
        footprint = self._footprint_cells(position)
        if not footprint:
            return False
        if not all(not footprint & self._footprint_cells(module.position) for module in self.modules):
            return False
        return all(not footprint & self._footprint_cells(nest.position)
                   for nest in self.fauna_nests if nest.is_alive())

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
        """Проверяет, простреливается ли точка хотя бы одной боевой башней. Инфраструктура
        энергосети (генераторы/пилоны) не учитывается - она не стреляет и не должна
        считаться угрозой (см. DefenseModule.IS_COMBAT_TOWER)."""
        return any(position.distance_to(m.position) <= m.range_radius
                   for m in self.modules if m.IS_COMBAT_TOWER)

    TOWER_AVOIDANCE_COST = 25.0

    def path_to_base(self, start_pos: Coordinate, faction: Faction, avoid_danger: bool = False) -> List[Coordinate]:
        """Строит путь до базы, обходя известные фракции башни."""
        if self.base_position is None:
            return []
        intel = self.faction_intel.setdefault(faction, FactionIntel())
        blocked_nodes = set()
        avoidance_cost: Dict[tuple, float] = {}
        covered_nodes = set()
        for tower in intel.known_towers():
            if tower.is_destroyed():
                continue
            node = self.nav_grid.get_node(tower.position.x, tower.position.y)
            if node is None:
                continue
            blocked_nodes |= self._footprint_cells(tower.position)

            if not tower.IS_COMBAT_TOWER:
                # Инфраструктура энергосети физически блокирует свою клетку (см. выше),
                # но не стреляет - обходить её радиус действия как зону обстрела не нужно.
                continue

            radius_cells = int(tower.range_radius / self.nav_grid.cell_size) + 1
            for dx in range(-radius_cells, radius_cells + 1):
                for dy in range(-radius_cells, radius_cells + 1):
                    if math.hypot(dx, dy) * self.nav_grid.cell_size > tower.range_radius:
                        continue
                    key = (node.x + dx, node.y + dy)
                    avoidance_cost[key] = avoidance_cost.get(key, 0.0) + self.TOWER_AVOIDANCE_COST
                    covered_nodes.add(key)

        if avoid_danger:
            hard_blocked = blocked_nodes | covered_nodes
            return self.nav_grid.find_path(start_pos, self.base_position, extra_blocked=hard_blocked)

        path = self.nav_grid.find_path(start_pos, self.base_position,
                                        extra_blocked=blocked_nodes, extra_cost=avoidance_cost)
        if not path and avoidance_cost:
            path = self.nav_grid.find_path(start_pos, self.base_position, extra_blocked=blocked_nodes)
        return path

    MAX_AVOID_DANGER_SEARCHES_PER_FRAME = 1

    def path_to_base_within_budget(self, start_pos: Coordinate, faction: Faction,
                                    avoid_danger: bool = False) -> List[Coordinate]:
        """Как path_to_base, но дорогие avoid_danger=True поиски (жёсткий обход ВСЕХ
        известных башен) дополнительно делят один общий бюджет
        MAX_AVOID_DANGER_SEARCHES_PER_FRAME на кадр между всеми вызывающими местами
        (спавн врага, массовый replan_enemy_paths при раскрытии башни, и собственный
        повтор _advance_honestly_or_give_up) - иначе несколько таких поисков могут
        совпасть в одном кадре и дать заметный фриз. При исчерпанном бюджете просто
        возвращает пустой путь, как будто честного пути сейчас нет - вызывающий код и
        так рассчитан на этот случай и попробует снова позже."""
        if avoid_danger:
            if self._avoid_danger_searches_this_frame >= self.MAX_AVOID_DANGER_SEARCHES_PER_FRAME:
                return []
            self._avoid_danger_searches_this_frame += 1
        return self.path_to_base(start_pos, faction, avoid_danger=avoid_danger)

    def replan_enemy_paths(self, factions: Optional[set] = None):
        """Пересчитывает путь живых врагов до базы (в рамках общего бюджета дорогих
        поисков на кадр - см. path_to_base_within_budget)."""
        for enemy in self.enemies:
            if not enemy.is_alive():
                continue
            if factions is not None and enemy.faction not in factions:
                continue
            new_path = self.path_to_base_within_budget(enemy.position, enemy.faction,
                                                         avoid_danger=enemy.avoids_danger())
            if new_path:
                enemy.set_path(new_path)

    # Раньше было 300 - меньше боевого радиуса почти всех башен первого уровня (350-400),
    # из-за чего группа узнавала о башне и назначала её целью, уже фактически стоя внутри
    # её обстрела. Для SniperDrone (ATTACK_RANGE 430) это означало, что он почти никогда не
    # успевал открыть огонь снаружи чужого радиуса - поднято, чтобы отряд начинал реагировать
    # на известную башню ещё на подходе, оставляя дальнобойным юнитам реальный шанс отстреливаться
    # издалека.
    TOWER_HUNT_RADIUS = 420.0

    TOWER_HUNT_RADIUS_OVERRIDES = {
        Faction.FAUNA: 500.0,
    }

    def _hunt_radius_for(self, faction: Faction) -> float:
        """Радиус охоты на башни для фракции."""
        return self.TOWER_HUNT_RADIUS_OVERRIDES.get(faction, self.TOWER_HUNT_RADIUS)

    def _update_group_targets(self, enemies: List[HostileEntity]):
        """Назначает лидерам групп ближайшую известную башню в радиусе охоты."""
        for enemy in enemies:
            if not enemy.is_alive() or not enemy.is_group_leader:
                continue
            if enemy.is_healing:
                enemy.target_tower = None
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
        """Движение к базе: патрулирует периметр, если известная башня
        перекрывает направление, иначе идёт по маршруту."""
        if self.base_position is None:
            enemy.move_along_path(delta_time)
            return

        if enemy.avoids_danger():
            self._advance_honestly_or_give_up(enemy, delta_time)
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

    GIVE_UP_RETREAT_STEP = 400.0
    GIVE_UP_REPLAN_COOLDOWN = 2.0
    GIVE_UP_REPLAN_COOLDOWN_MAX = 16.0
    GIVE_UP_REPLAN_JITTER = 0.5

    def _advance_honestly_or_give_up(self, enemy: HostileEntity, delta_time: float):
        """Ведёт избегающего опасности врага в обход известных башен; если маршрута нет -
        отступает вместо прорыва. Повторный дорогой поиск с avoid_danger=True не пробуется
        каждый кадр, а со всё увеличивающимся кулдауном (2с, 4с, 8с... до потолка в
        GIVE_UP_REPLAN_COOLDOWN_MAX) - если враг уже несколько раз подряд не нашёл честного
        пути, он почти наверняка застрял надолго (известные башни не пропадают сами по
        себе). К кулдауну добавляется случайный разброс. Число таких поисков за кадр
        дополнительно ограничено общим бюджетом MAX_AVOID_DANGER_SEARCHES_PER_FRAME (см.
        path_to_base_within_budget) - если бюджет уже потрачен другими врагами в этом
        кадре, попытка просто откладывается без штрафа (кулдаун не растёт)."""
        enemy.is_patrolling = False
        enemy.replan_retry_cooldown = max(0.0, enemy.replan_retry_cooldown - delta_time)
        needs_path = not enemy.path or enemy.path_index >= len(enemy.path)

        can_afford_search = self._avoid_danger_searches_this_frame < self.MAX_AVOID_DANGER_SEARCHES_PER_FRAME
        if needs_path and enemy.replan_retry_cooldown <= 0.0 and can_afford_search:
            safe_path = self.path_to_base_within_budget(enemy.position, enemy.faction, avoid_danger=True)
            if safe_path:
                enemy.set_path(safe_path)
                enemy.replan_failure_streak = 0
                needs_path = False
            else:
                enemy.replan_failure_streak += 1
                base_cooldown = min(
                    self.GIVE_UP_REPLAN_COOLDOWN * (2 ** (enemy.replan_failure_streak - 1)),
                    self.GIVE_UP_REPLAN_COOLDOWN_MAX,
                )
                enemy.replan_retry_cooldown = base_cooldown * (1.0 + self._rng.random() * self.GIVE_UP_REPLAN_JITTER)

        if needs_path:
            self._advance_giving_up(enemy, delta_time)
            return
        enemy.move_along_path(delta_time)

    def _advance_giving_up(self, enemy: HostileEntity, delta_time: float):
        """Отступает к точке спавна фракции или прочь от базы, если
        точек спавна нет."""
        spawn_points = self.spawn_points_for(enemy.faction)
        if spawn_points:
            nearest = min(spawn_points, key=lambda p: enemy.position.distance_to(p))
            if enemy.position.distance_to(nearest) > self.HEAL_ARRIVAL_RADIUS:
                enemy.move_towards_point(nearest, delta_time)
            return

        if self.base_position is None:
            return
        dx = enemy.position.x - self.base_position.x
        dy = enemy.position.y - self.base_position.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            dx, dy, dist = 1.0, 0.0, 1.0
        target = Coordinate(
            max(0.0, min(self.width, enemy.position.x + dx / dist * self.GIVE_UP_RETREAT_STEP)),
            max(0.0, min(self.height, enemy.position.y + dy / dist * self.GIVE_UP_RETREAT_STEP)),
        )
        enemy.move_towards_point(target, delta_time)

    STAGING_GROUP_SIZE = 6
    STAGING_ORBIT_RADIUS = 160.0
    STAGING_ANGULAR_SPEED = 0.4
    STAGING_FORMATION_RADIUS = 50.0
    STAGING_JOIN_RADIUS = 300.0
    STAGING_MAX_WAIT = 30.0

    def _stage_eligible(self, enemy: HostileEntity) -> bool:
        """Проверяет, ждёт ли враг сбора группы для отложенной атаки прямо сейчас."""
        return enemy.is_staging and enemy.is_alive() and enemy.group_id is None

    def _find_or_create_anchor(self, faction: Faction, position: Coordinate) -> Coordinate:
        """Возвращает существующий якорь сбора этой фракции рядом с position (в пределах
        STAGING_JOIN_RADIUS), иначе создаёт новый прямо на месте - враги на разных
        концах карты (например, разные точки спавна Fauna или далёкие друг от друга
        высадки Corporation) не должны тянуться к одному общему месту сбора."""
        anchors = self._staging_anchor.setdefault(faction, [])
        for anchor in anchors:
            if anchor.distance_to(position) <= self.STAGING_JOIN_RADIUS:
                return anchor
        new_anchor = Coordinate(position.x, position.y)
        anchors.append(new_anchor)
        self._staging_anchor_created_at[id(new_anchor)] = self._elapsed_time
        return new_anchor

    def _update_staging_groups(self, enemies: List[HostileEntity]):
        """Раз в кадр распределяет ожидающих врагов каждой фракции по якорям сбора -
        каждый якорь - это отдельная формирующаяся группа рядом с тем местом, где её
        участники появились (см. _find_or_create_anchor), а не одна общая точка на всю
        фракцию. Как только у якоря набирается STAGING_GROUP_SIZE живых участников, вся
        его группа разом снимается со сбора и бросается в атаку на базу единой массой
        (см. _commit_staging_group). Пока порог не набран, враги кружат у своего якоря -
        см. _advance_staging. Изолированная кучка (например, отряд Corporation, высадившийся
        далеко от всех остальных) может никогда не набрать STAGING_GROUP_SIZE сама по себе -
        чтобы она не кружила вечно, по истечении STAGING_MAX_WAIT она тоже выступает, каким
        бы малым ни был её состав."""
        by_faction: Dict[Faction, List[HostileEntity]] = {}
        for enemy in enemies:
            if self._stage_eligible(enemy):
                by_faction.setdefault(enemy.faction, []).append(enemy)

        for faction in list(self._staging_anchor.keys()):
            if faction not in by_faction:
                self._staging_anchor[faction] = []

        live_anchor_ids = set()
        for faction, members in by_faction.items():
            for enemy in members:
                if enemy.stage_anchor is None:
                    enemy.stage_anchor = self._find_or_create_anchor(faction, enemy.position)

            clusters: Dict[int, List[HostileEntity]] = {}
            for enemy in members:
                clusters.setdefault(id(enemy.stage_anchor), []).append(enemy)

            live_anchors = []
            for cluster_members in clusters.values():
                anchor = cluster_members[0].stage_anchor
                waited = self._elapsed_time - self._staging_anchor_created_at.get(id(anchor), self._elapsed_time)
                if len(cluster_members) >= self.STAGING_GROUP_SIZE or waited >= self.STAGING_MAX_WAIT:
                    self._commit_staging_group(cluster_members)
                else:
                    live_anchors.append(anchor)
                    live_anchor_ids.add(id(anchor))
            self._staging_anchor[faction] = live_anchors

        self._staging_anchor_created_at = {
            anchor_id: created_at for anchor_id, created_at in self._staging_anchor_created_at.items()
            if anchor_id in live_anchor_ids
        }

    def _commit_staging_group(self, members: List[HostileEntity]):
        """Снимает набранную группу со сбора и отправляет её всей массой к базе -
        один участник становится лидером с маршрутом до базы, остальные пристраиваются
        к нему ведомыми (как в обычной групповой атаке, см. GroupFormationSystem)."""
        leader, *escorts = members
        leader.is_staging = False
        leader.is_group_leader = True
        leader.group_id = self.group_formation.allocate_group_id()
        path = self.path_to_base_within_budget(leader.position, leader.faction,
                                                avoid_danger=leader.avoids_danger())
        if path:
            leader.set_path(path)

        escort_count = max(len(escorts), 1)
        for i, escort in enumerate(escorts):
            escort.is_staging = False
            angle = (2 * math.pi / escort_count) * i
            offset = Coordinate(math.cos(angle) * self.STAGING_FORMATION_RADIUS,
                                 math.sin(angle) * self.STAGING_FORMATION_RADIUS)
            escort.join_group(leader.group_id, leader, offset)

    def _advance_staging(self, enemy: HostileEntity, delta_time: float):
        """Кружит врага у его якоря сбора в ожидании, пока группа не наберёт
        STAGING_GROUP_SIZE живых участников - см. _update_staging_groups."""
        anchor = enemy.stage_anchor or enemy.position
        if enemy.stage_angle is None:
            enemy.stage_angle = math.atan2(enemy.position.y - anchor.y, enemy.position.x - anchor.x)
            enemy.stage_direction = 1 if id(enemy) % 2 == 0 else -1
        enemy.stage_angle += enemy.stage_direction * self.STAGING_ANGULAR_SPEED * delta_time
        target = Coordinate(
            anchor.x + math.cos(enemy.stage_angle) * self.STAGING_ORBIT_RADIUS,
            anchor.y + math.sin(enemy.stage_angle) * self.STAGING_ORBIT_RADIUS,
        )
        enemy.move_towards_point(target, delta_time)

    def _nearest_covering_tower(self, position: Coordinate, margin: float = 0.0) -> Optional[DefenseModule]:
        """Возвращает ближайшую башню, простреливающую точку (с необязательным
        запасом margin к радиусу), или None."""
        covering = self._covering_towers(position, margin)
        if not covering:
            return None
        return min(covering, key=lambda m: position.distance_to(m.position))

    def _covering_towers(self, position: Coordinate, margin: float = 0.0) -> List[DefenseModule]:
        """Возвращает все боевые башни, простреливающие точку (с запасом margin).
        Инфраструктура энергосети не в счёт - см. is_position_covered."""
        return [m for m in self.modules
                if m.IS_COMBAT_TOWER and position.distance_to(m.position) <= m.range_radius + margin]

    FLEE_EXIT_MARGIN = 60.0
    FLEE_TARGET_DISTANCE = 80.0

    def _flee_target_from_towers(self, position: Coordinate, towers: List[DefenseModule]) -> Coordinate:
        """Точка бегства - шаг прочь от всех угрожающих башен сразу."""
        push_x = push_y = 0.0
        for tower in towers:
            dx = position.x - tower.position.x
            dy = position.y - tower.position.y
            dist = math.hypot(dx, dy)
            if dist < 1e-6:
                dx, dy, dist = 1.0, 0.0, 1.0
            depth = max(1.0, tower.range_radius + self.FLEE_EXIT_MARGIN - dist)
            push_x += dx / dist * depth
            push_y += dy / dist * depth

        length = math.hypot(push_x, push_y)
        if length < 1e-6:
            nearest = min(towers, key=lambda t: position.distance_to(t.position))
            dx = position.x - nearest.position.x
            dy = position.y - nearest.position.y
            push_x, push_y = -dy, dx
            length = math.hypot(push_x, push_y) or 1.0

        return Coordinate(
            position.x + push_x / length * self.FLEE_TARGET_DISTANCE,
            position.y + push_y / length * self.FLEE_TARGET_DISTANCE,
        )

    WOUNDED_HEALTH_RATIO = 0.3
    HEAL_ARRIVAL_RADIUS = 40.0
    HEAL_RADIUS = 150.0
    HEAL_RATE_PER_SECOND = 0.15
    LOW_ENEMY_COUNT_NO_RETREAT = 4
    MAX_RETREAT_HEALS = 1

    FACTIONS_WITHOUT_RETREAT_HEALING = {Faction.CORPORATION}

    def _is_wounded(self, enemy: HostileEntity) -> bool:
        """Проверяет, ранен ли враг настолько, что ему пора отступать лечиться."""
        return enemy.health < enemy.max_health * self.WOUNDED_HEALTH_RATIO

    def _can_start_new_retreat(self, enemy: HostileEntity) -> bool:
        """Проверяет, не исчерпал ли враг лимит отступлений на лечение (MAX_RETREAT_HEALS) -
        после лимита он продолжает сражаться раненым вместо очередного похода к спавну."""
        return enemy.retreat_heal_count < self.MAX_RETREAT_HEALS

    def _group_needs_healing(self, enemy: HostileEntity) -> bool:
        """Проверяет, ранен ли кто-то в группе врага. Отступление на лечение доступно только
        группам - одиночный враг вне группы теперь дерётся до конца вместо похода к спавну,
        чтобы враги реже мотались туда-сюда от башни к базе фракции поодиночке."""
        if enemy.group_id is None:
            return False
        members = [e for e in self.enemies if e.group_id == enemy.group_id and e.is_alive()]
        return any(self._is_wounded(member) for member in members)

    def _group_fully_healed(self, enemy: HostileEntity) -> bool:
        """Проверяет, что сам враг (и все члены его группы) полностью излечились."""
        if enemy.group_id is None:
            return enemy.health >= enemy.max_health
        members = [e for e in self.enemies if e.group_id == enemy.group_id and e.is_alive()]
        return all(member.health >= member.max_health for member in members)

    def _advance_retreat(self, enemy: HostileEntity, delta_time: float):
        """Двигает врага к ближайшей точке спавна его фракции, чтобы там подлечиться."""
        spawn_points = self.spawn_points_for(enemy.faction)
        if not spawn_points:
            enemy.is_healing = False
            return
        nearest = min(spawn_points, key=lambda p: enemy.position.distance_to(p))
        if enemy.position.distance_to(nearest) > self.HEAL_ARRIVAL_RADIUS:
            enemy.move_towards_point(nearest, delta_time)

    def _is_near_own_spawn(self, enemy: HostileEntity) -> bool:
        """Проверяет, находится ли враг рядом с одной из точек спавна своей фракции."""
        spawn_points = self.spawn_points_for(enemy.faction)
        return any(enemy.position.distance_to(p) <= self.HEAL_RADIUS for p in spawn_points)

    HEALER_JOIN_RADIUS = 60.0
    HEALER_HEAL_RADIUS = 120.0
    HEALER_HEAL_RATE_PER_SECOND = 0.12

    def _find_nearest_ally_group_leader(self, enemy: HostileEntity) -> Optional[HostileEntity]:
        """Находит ближайшего живого лидера группы своей фракции."""
        leaders = [
            other for other in self.enemies
            if other is not enemy
            and other.is_alive()
            and other.is_group_leader
            and other.faction == enemy.faction
        ]
        if not leaders:
            return None
        return min(leaders, key=lambda leader: enemy.position.distance_to(leader.position))

    def _advance_healer_seeking(self, enemy: HostileEntity, delta_time: float):
        """Двигает лечащего врага к ближайшей группе союзников и присоединяет к ней вблизи."""
        leader = self._find_nearest_ally_group_leader(enemy)
        if leader is None:
            self._advance_towards_base(enemy, delta_time)
            return
        if enemy.position.distance_to(leader.position) <= self.HEALER_JOIN_RADIUS:
            offset = Coordinate(-self.HEALER_JOIN_RADIUS * 0.4, 0.0)
            enemy.join_group(leader.group_id, leader, offset)
        else:
            enemy.move_towards_point(leader.position, delta_time)

    def _apply_ally_healing(self, healer: HostileEntity, delta_time: float):
        """Лечит участников группы лечащего врага в радиусе его действия."""
        for member in self.enemies:
            if not member.is_alive() or member.group_id != healer.group_id:
                continue
            if healer.position.distance_to(member.position) > self.HEALER_HEAL_RADIUS:
                continue
            member.health = min(member.max_health,
                                 member.health + member.max_health * self.HEALER_HEAL_RATE_PER_SECOND * delta_time)

    def _apply_dodge(self, enemy: HostileEntity, delta_time: float, pre_move_position: Coordinate):
        """Добавляет боковое покачивание к движению врага, уклоняющегося от обстрела."""
        dx = enemy.position.x - pre_move_position.x
        dy = enemy.position.y - pre_move_position.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return
        perp_x, perp_y = -dy / dist, dx / dist

        enemy.dodge_timer += delta_time
        wiggle = enemy.DODGE_AMPLITUDE * math.sin(enemy.dodge_timer * enemy.DODGE_FREQUENCY)
        delta_wiggle = wiggle - enemy._dodge_offset
        enemy._dodge_offset = wiggle

        enemy.position.x += perp_x * delta_wiggle
        enemy.position.y += perp_y * delta_wiggle

    def _in_flee_danger(self, enemy: HostileEntity, in_danger: bool, was_fleeing: bool) -> bool:
        """Опасность для бегства с гистерезисом - убегающий враг считается
        в опасности, пока не выйдет за пределы FLEE_EXIT_MARGIN."""
        if in_danger:
            return True
        if was_fleeing:
            return self._nearest_covering_tower(enemy.position, margin=self.FLEE_EXIT_MARGIN) is not None
        return False

    SHIELD_BIAS = 0.8

    def _shield_offset(self, offset: Coordinate, tower_position: Coordinate,
                        leader_position: Coordinate) -> Coordinate:
        """Смещает слот построения эскорта в сторону башни, обстреливающей
        лидера, сохраняя расстояние до него."""
        radius = math.hypot(offset.x, offset.y)
        if radius < 1e-6:
            return offset
        original_angle = math.atan2(offset.y, offset.x)
        tower_angle = math.atan2(tower_position.y - leader_position.y, tower_position.x - leader_position.x)
        diff = (tower_angle - original_angle + math.pi) % (2 * math.pi) - math.pi
        blended_angle = original_angle + diff * self.SHIELD_BIAS
        return Coordinate(math.cos(blended_angle) * radius, math.sin(blended_angle) * radius)

    ENEMY_COMBAT_DETECTION_RADIUS = 350.0

    def _find_enemy_combat_target(self, enemy: HostileEntity) -> Optional[HostileEntity]:
        """Находит ближайшего живого врага чужой фракции в радиусе обнаружения.
        Это отдельный (и заметно больший) радиус от vision_radius - тот отвечает
        за туман войны над башнями, и если завязывать стычки между фракциями на
        него же, они происходят слишком редко и почти незаметны в игре."""
        candidates = [
            other for other in self.enemies
            if other is not enemy
            and other.is_alive()
            and other.faction != enemy.faction
            and enemy.position.distance_to(other.position) <= self.ENEMY_COMBAT_DETECTION_RADIUS
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

    # База сама даёт бесплатное питание в небольшом радиусе вокруг себя - иначе
    # игрок не мог бы поставить вообще ни одной боевой башни, пока не построит первый
    # генератор. За пределами этого радиуса требуется энергосеть: генераторы (сами
    # всегда под напряжением) и пилоны (только в цепочке, доходящей до базы или
    # генератора) - см. _update_power_grid. Радиус действия самих узлов сети - это
    # их собственный range_radius (PowerInfrastructure переиспользует его как радиус
    # подачи энергии, а не атаки - см. PowerInfrastructure), а не общая константа:
    # у генератора и пилона он разный, и апгрейд/баланс одного не должен молча менять
    # дальнобойность другого.
    BASE_POWER_RADIUS = 550.0

    def _update_power_grid(self):
        """Пересчитывает энергосеть на один кадр: какие узлы сети (генераторы и
        пилоны) под напряжением и какие боевые башни от них запитаны. Работает только
        если power_grid_enabled - на картах без него (почти все существующие тесты,
        создающие Map() напрямую) башни всегда считаются запитанными, как и было
        раньше (см. DefenseModule.is_powered)."""
        if not self.power_grid_enabled or self.base_position is None:
            return

        nodes = [m for m in self.modules
                 if isinstance(m, PowerInfrastructure) and not m.is_destroyed() and not m.is_landing]

        self.power_links = []
        energized_ids = set()
        frontier = deque()

        for node in nodes:
            if self.base_position.distance_to(node.position) <= self.BASE_POWER_RADIUS:
                energized_ids.add(id(node))
                frontier.append(node)
                self.power_links.append((self.base_position, node.position))
            elif node.IS_SOURCE:
                energized_ids.add(id(node))
                frontier.append(node)

        while frontier:
            current = frontier.popleft()
            for other in nodes:
                if id(other) in energized_ids:
                    continue
                if current.position.distance_to(other.position) <= current.range_radius:
                    energized_ids.add(id(other))
                    frontier.append(other)
                    self.power_links.append((current.position, other.position))

        for node in nodes:
            node.is_powered = node.IS_SOURCE or id(node) in energized_ids

        energized_nodes = [n for n in nodes if id(n) in energized_ids]
        for module in self.modules:
            if isinstance(module, PowerInfrastructure):
                continue
            near_base = self.base_position.distance_to(module.position) <= self.BASE_POWER_RADIUS
            near_energized_node = any(
                n.position.distance_to(module.position) <= n.range_radius for n in energized_nodes
            )
            module.is_powered = near_base or near_energized_node

    def update(self, delta_time: float) -> tuple[List[HostileEntity], List[HostileEntity]]:
        """Обновляет карту на один кадр."""
        self._elapsed_time += delta_time
        self._avoid_danger_searches_this_frame = 0
        destroyed_this_frame = sum(1 for module in self.modules if module.is_destroyed())
        self.towers_lost_count += destroyed_this_frame
        self.modules = [module for module in self.modules if not module.is_destroyed()]

        self._update_power_grid()

        self._update_group_targets(self.enemies)
        self._update_staging_groups(self.enemies)

        enemies_reached_base = []
        killed_enemies = []
        surviving_enemies = []

        alive_enemies_count = sum(1 for e in self.enemies if e.is_alive())
        allow_retreat = alive_enemies_count > self.LOW_ENEMY_COUNT_NO_RETREAT

        for enemy in self.enemies:
            if not enemy.is_alive():
                killed_enemies.append(enemy)
                continue

            if not allow_retreat:
                enemy.is_healing = False

            target_tower = enemy.group_target_tower() if enemy.is_combatant() else None
            hunting_tower = target_tower is not None and not target_tower.is_destroyed()

            combat_target = self._find_enemy_combat_target(enemy) if enemy.is_combatant() else None
            in_combat = combat_target is not None

            uses_retreat_healing = enemy.faction not in self.FACTIONS_WITHOUT_RETREAT_HEALING
            can_start_retreat = self._can_start_new_retreat(enemy) and self._group_needs_healing(enemy)
            retreating_now = (allow_retreat and uses_retreat_healing and enemy.group_leader is None
                               and (enemy.is_healing or can_start_retreat))

            if (not hunting_tower and not in_combat and not retreating_now
                    and enemy.path and enemy.path_index >= len(enemy.path)):
                enemies_reached_base.append(enemy)
                continue

            in_danger = self.is_position_covered(enemy.position)
            enemy.act(delta_time, in_danger)

            if self._is_near_own_spawn(enemy):
                enemy.health = min(enemy.max_health,
                                    enemy.health + enemy.max_health * self.HEAL_RATE_PER_SECOND * delta_time)

            if enemy.heals_allies() and enemy.group_leader is not None:
                self._apply_ally_healing(enemy, delta_time)

            if enemy.is_moving():
                pre_move_position = Coordinate(enemy.position.x, enemy.position.y)
                was_fleeing = enemy.is_fleeing
                enemy.is_fleeing = False

                if retreating_now:
                    if not enemy.is_healing:
                        enemy.retreat_heal_count += 1
                    enemy.is_healing = True
                    if self._group_fully_healed(enemy):
                        enemy.is_healing = False
                        new_path = self.path_to_base(enemy.position, enemy.faction)
                        if new_path:
                            enemy.set_path(new_path)
                        self._advance_towards_base(enemy, delta_time)
                    else:
                        self._advance_retreat(enemy, delta_time)
                elif in_combat:
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
                elif enemy.is_staging:
                    self._advance_staging(enemy, delta_time)
                elif enemy.avoids_danger() and self._in_flee_danger(enemy, in_danger, was_fleeing):
                    threatening_towers = self._covering_towers(enemy.position, margin=self.FLEE_EXIT_MARGIN)
                    if threatening_towers:
                        intel = self.faction_intel.setdefault(enemy.faction, FactionIntel())
                        for tower in threatening_towers:
                            intel.reveal(tower)
                        enemy.is_fleeing = True
                        enemy.is_patrolling = False
                        flee_point = self._flee_target_from_towers(enemy.position, threatening_towers)
                        enemy.move_towards_point(flee_point, delta_time)
                    else:
                        self._advance_towards_base(enemy, delta_time)
                else:
                    leader = enemy.group_leader
                    if leader is not None and leader.is_alive() and not leader.has_reached_end_of_path():
                        offset = enemy.formation_offset
                        if enemy.is_combatant() and self.is_position_covered(leader.position):
                            threatening_tower = self._nearest_covering_tower(leader.position)
                            if threatening_tower is not None:
                                offset = self._shield_offset(offset, threatening_tower.position, leader.position)
                        formation_target = Coordinate(leader.position.x + offset.x, leader.position.y + offset.y)
                        enemy.move_towards_point(formation_target, delta_time)
                    else:
                        if leader is not None:
                            enemy.leave_group()
                        if enemy.heals_allies():
                            self._advance_healer_seeking(enemy, delta_time)
                        else:
                            if was_fleeing:
                                new_path = self.path_to_base_within_budget(
                                    enemy.position, enemy.faction, avoid_danger=enemy.avoids_danger())
                                if new_path:
                                    enemy.set_path(new_path)
                                elif enemy.avoids_danger():
                                    enemy.path = []
                                    enemy.path_index = 0
                            self._advance_towards_base(enemy, delta_time)

                if in_danger and enemy.dodges_projectiles():
                    self._apply_dodge(enemy, delta_time, pre_move_position)

            surviving_enemies.append(enemy)

        self.enemies = surviving_enemies
        self.group_formation.update(delta_time, self.enemies)

        changed_factions = self._update_vision(self.enemies)
        if changed_factions:
            self.replan_enemy_paths(factions=changed_factions)

        attackable_targets = self.enemies + self.fauna_nests

        for module in self.modules:
            projectile = module.update(delta_time, attackable_targets)
            if projectile:
                self.projectiles.append(projectile)
                self._emit("tower_fired", tower_type=getattr(module, "type_name", None), position=module.position)
            if module.take_landing_event():
                self._emit("tower_placed", tower_type=getattr(module, "type_name", None), position=module.position)

        surviving_projectiles = []
        spawned_projectiles = []
        for projectile in self.projectiles:
            alive = projectile.update(delta_time, attackable_targets)
            spawned_projectiles.extend(projectile.collect_spawned())
            if alive:
                surviving_projectiles.append(projectile)
            else:
                event_name = projectile.landed_event_name()
                if event_name:
                    self._emit(event_name, position=projectile.position)
        self.projectiles = surviving_projectiles + spawned_projectiles

        if self.fauna_nests:
            destroyed_nests = [nest for nest in self.fauna_nests if not nest.is_alive()]
            for nest in destroyed_nests:
                self._emit("nest_destroyed", position=nest.position)
            self.fauna_nests = [nest for nest in self.fauna_nests if nest.is_alive()]
            self.spawn_points_by_faction[Faction.FAUNA] = [nest.position for nest in self.fauna_nests]

        return enemies_reached_base, killed_enemies
