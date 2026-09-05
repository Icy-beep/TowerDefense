"""Живой оперативник: прямое управление и автономная защита позиций."""
import math
from types import SimpleNamespace

from src.core.coordinate import Coordinate
from src.entities.projectile import BulletProjectile
from src.enums import DamageType


class Operator:
    CLASSES = {
        "assault": {"health": 180, "speed": 190, "damage": 18, "rate": 5},
        "engineer": {"health": 120, "speed": 210, "damage": 14, "rate": 3},
    }
    RANGE = 420
    RADIUS = 10

    def __init__(self, kind, position):
        self.kind = kind
        stats = self.CLASSES[kind]
        self.position = Coordinate(position.x, position.y)
        self.max_health = stats["health"]
        self.health = self.max_health
        self.manual = False
        self.move_input = (0, 0)
        self.aim = Coordinate(position.x + 100, position.y)
        self.trigger = False
        self.cooldown = 0.0
        self.ability_cooldown = 0.0
        self.boost_time = 0.0
        self.guard = None
        self.retreat_limit = None
        self.path = []
        self.path_timer = 0.0

    def is_alive(self):
        return self.health > 0

    def is_destroyed(self):
        return not self.is_alive()

    def take_damage(self, amount, damage_type):
        self.health = max(0, self.health - amount * (0.6 if self.boost_time > 0 else 1))

    def stop_input(self):
        self.move_input = (0, 0)
        self.trigger = False

    @staticmethod
    def blocked_cells(game_map):
        blocked = set()
        for obj in game_map.modules + game_map.fauna_nests:
            if not obj.is_destroyed():
                blocked.update(game_map._footprint_cells(obj.position))
        return blocked

    def can_stand(self, position, game_map, blocked):
        for ox, oy in ((0, 0), (10, 0), (-10, 0), (0, 10), (0, -10)):
            x, y = position.x + ox, position.y + oy
            if not (0 <= x < game_map.width and 0 <= y < game_map.height):
                return False
            node = game_map.nav_grid.get_node(x, y)
            if node is None or not game_map.nav_grid.is_walkable(node) or (node.x, node.y) in blocked:
                return False
        return True

    def move(self, dx, dy, dt, game_map, blocked):
        length = math.hypot(dx, dy)
        if not length:
            return
        distance = self.CLASSES[self.kind]["speed"] * dt
        steps = max(1, math.ceil(distance / 6))
        dx, dy = dx / length * distance / steps, dy / length * distance / steps
        for _ in range(steps):
            for sx, sy in ((dx, 0), (0, dy)):
                point = Coordinate(self.position.x + sx, self.position.y + sy)
                if self.can_stand(point, game_map, blocked):
                    self.position = point

    def select_guard(self, game_map):
        towers = [t for t in game_map.modules if t.IS_COMBAT_TOWER and not t.is_destroyed()]
        if self.retreat_limit is not None:
            towers = [t for t in towers
                      if t.position.distance_to(game_map.base_position) < self.retreat_limit]
        chosen = min(towers, key=lambda t: self.position.distance_to(t.position), default=None)
        if chosen is None and self.guard is None:
            return
        self.guard = chosen
        self.path = []
        self.path_timer = 0

    def leave_manual(self, game_map):
        self.manual = False
        self.stop_input()
        self.retreat_limit = None
        self.select_guard(game_map)

    def autonomous_move(self, dt, game_map, blocked):
        if self.guard is not None and (self.guard.is_destroyed()
                                      or self.guard not in game_map.modules):
            self.retreat_limit = self.guard.position.distance_to(game_map.base_position)
            self.select_guard(game_map)
        elif self.guard is None:
            self.select_guard(game_map)
        destination = self.guard.position if self.guard else game_map.base_position
        if self.position.distance_to(destination) <= 120:
            return
        self.path_timer -= dt
        if self.path_timer <= 0:
            self.path_timer = 2
            # Конечная точка рядом с башней, а не внутри её непроходимого основания.
            candidates = [Coordinate(destination.x + math.cos(a * math.pi / 4) * 100,
                                     destination.y + math.sin(a * math.pi / 4) * 100)
                          for a in range(8)]
            candidates.sort(key=lambda p: self.position.distance_to(p))
            self.path = []
            for point in candidates:
                if self.can_stand(point, game_map, blocked):
                    path = game_map.nav_grid.find_path(self.position, point, extra_blocked=blocked)
                    if path:
                        self.path = path
                        break
        while self.path and self.position.distance_to(self.path[0]) < 12:
            self.path.pop(0)
        if self.path:
            point = self.path[0]
            self.move(point.x - self.position.x, point.y - self.position.y, dt, game_map, blocked)

    def use_ability(self, game_map):
        if not self.is_alive() or self.ability_cooldown > 0:
            return False
        if self.kind == "assault":
            self.boost_time = 5
            self.ability_cooldown = 15
        else:
            towers = [t for t in game_map.modules if not t.is_destroyed() and not t.is_landing
                      and t.health < t.max_health and self.position.distance_to(t.position) <= 180]
            if not towers and self.health >= self.max_health:
                return False
            for tower in towers:
                tower.health = min(tower.max_health, tower.health + 45)
            self.health = min(self.max_health, self.health + 20)
            self.ability_cooldown = 8
        return True

    def update(self, dt, game_map):
        if not self.is_alive():
            self.stop_input()
            return
        self.cooldown = max(0, self.cooldown - dt)
        self.ability_cooldown = max(0, self.ability_cooldown - dt)
        self.boost_time = max(0, self.boost_time - dt)
        blocked = self.blocked_cells(game_map)
        if self.manual:
            self.move(*self.move_input, dt, game_map, blocked)
        else:
            self.autonomous_move(dt, game_map, blocked)
            targets = [e for e in game_map.enemies + game_map.fauna_nests
                       if e.is_alive() and self.position.distance_to(e.position) <= self.RANGE]
            target = min(targets, key=lambda e: self.position.distance_to(e.position), default=None)
            self.trigger = target is not None
            if target:
                self.aim = Coordinate(target.position.x, target.position.y)
        if self.boost_time > 0:
            for tower in game_map.modules:
                if tower.IS_COMBAT_TOWER and self.position.distance_to(tower.position) <= 220:
                    tower.cooldown_timer = max(0, tower.cooldown_timer - dt * 0.35)
        if self.trigger and self.cooldown <= 0 and self.position.distance_to(self.aim) > 1:
            stats = self.CLASSES[self.kind]
            self.cooldown = 1 / (stats["rate"] * (1.5 if self.boost_time > 0 else 1))
            game_map.projectiles.append(BulletProjectile(
                self.position, SimpleNamespace(position=self.aim), stats["damage"],
                DamageType.KINETIC, speed=650, max_distance=self.RANGE, spread_degrees=2))

    def to_dict(self):
        return {"kind": self.kind, "x": self.position.x, "y": self.position.y,
                "health": self.health, "manual": self.manual, "cooldown": self.cooldown,
                "ability_cooldown": self.ability_cooldown, "boost_time": self.boost_time,
                "retreat_limit": self.retreat_limit,
                "guard": [self.guard.position.x, self.guard.position.y] if self.guard else None}

    @classmethod
    def from_dict(cls, data, game_map):
        operator = cls(data["kind"], Coordinate(data["x"], data["y"]))
        operator.health = max(0, min(operator.max_health, data.get("health", operator.max_health)))
        operator.manual = bool(data.get("manual", False)) and operator.is_alive()
        for key in ("cooldown", "ability_cooldown", "boost_time"):
            setattr(operator, key, max(0, data.get(key, 0)))
        operator.retreat_limit = data.get("retreat_limit")
        guard = data.get("guard")
        operator.guard = next((t for t in game_map.modules
                               if [t.position.x, t.position.y] == guard), None)
        if guard and operator.guard is None:
            lost_distance = Coordinate(*guard).distance_to(game_map.base_position)
            operator.retreat_limit = min(operator.retreat_limit, lost_distance) \
                if operator.retreat_limit is not None else lost_distance
        return operator
