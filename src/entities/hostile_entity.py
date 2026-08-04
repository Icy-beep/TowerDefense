import math
from abc import ABC, abstractmethod
from .entity import Entity
from src.core.coordinate import Coordinate
from src.enums import DamageType, ArmorType, Faction
from typing import List, Optional


class HostileEntity(Entity, ABC):
    """Базовый класс для всех врагов."""

    VISION_RADIUS = 140.0

    ATTACK_RANGE = 40.0
    ATTACK_DAMAGE_PER_SECOND = 20.0

    def __init__(self, position: Coordinate, max_health: float, speed: float, armor: ArmorType, reward: int,
                 faction: Optional[Faction] = None, vision_radius: Optional[float] = None):
        """Создаёт врага с базовыми характеристиками."""
        super().__init__(position)
        self.max_health = max_health
        self.health = max_health
        self.speed = speed
        self.armor = armor
        self.reward = reward
        self.faction = faction or Faction.FAUNA
        self.vision_radius = vision_radius if vision_radius is not None else self.VISION_RADIUS
        self.path: List[Coordinate] = []
        self.path_index = 0

        self.group_id: Optional[int] = None
        self.is_group_leader: bool = False
        self.group_leader: Optional["HostileEntity"] = None
        self.formation_offset: Coordinate = Coordinate(0.0, 0.0)

        self.target_tower = None

        self.is_patrolling: bool = False
        self.patrol_angle: Optional[float] = None
        self.patrol_direction: int = 1

        self.is_healing: bool = False
        self.is_fleeing: bool = False
        self.retreat_heal_count: int = 0
        self.replan_retry_cooldown: float = 0.0
        self.replan_failure_streak: int = 0

        self.is_staging: bool = False
        self.stage_angle: Optional[float] = None
        self.stage_direction: int = 1

        self.dodge_timer: float = 0.0
        self._dodge_offset: float = 0.0

    def avoids_danger(self) -> bool:
        """Проверяет, должен ли враг убегать от простреливаемых башнями зон вместо боя."""
        return False

    def is_combatant(self) -> bool:
        """Проверяет, может ли враг атаковать вражеских юнитов и башни."""
        return True

    def heals_allies(self) -> bool:
        """Проверяет, лечит ли враг участников своей группы (см. MedicDrone)."""
        return False

    def stages_before_attacking(self) -> bool:
        """Проверяет, должен ли враг сперва дождаться сбора группы у точки появления
        (см. Map._update_staging_groups), а не сразу идти к базе поодиночке. По умолчанию
        да для всех боевых юнитов; разведчики (avoids_danger) и лекари (heals_allies) сами
        решают, что делать до боя, и в отложенной атаке не участвуют."""
        return self.is_combatant() and not self.avoids_danger() and not self.heals_allies()

    DODGE_AMPLITUDE = 24.0
    DODGE_FREQUENCY = 5.0

    def dodges_projectiles(self) -> bool:
        """Проверяет, должен ли враг уклоняться из стороны в сторону под обстрелом башен."""
        return self.armor == ArmorType.LIGHT

    def set_path(self, path: List[Coordinate]):
        """Назначает врагу маршрут."""
        self.path = path
        self.path_index = 0

    def join_group(self, group_id: int, leader: "HostileEntity", offset: Coordinate):
        """Делает врага ведомым в группе лидера."""
        self.group_id = group_id
        self.group_leader = leader
        self.formation_offset = offset

    def leave_group(self):
        """Выводит врага из группы."""
        self.group_id = None
        self.group_leader = None

    def group_target_tower(self):
        """Возвращает башню, которую сейчас атакует группа этого врага."""
        if self.is_group_leader:
            return self.target_tower
        if self.group_leader is not None:
            return self.group_leader.target_tower
        return None

    def attack_tower(self, tower, delta_time: float):
        """Наносит урон башне."""
        tower.take_damage(self.ATTACK_DAMAGE_PER_SECOND * delta_time, DamageType.KINETIC)

    def attack_enemy(self, other: "HostileEntity", delta_time: float):
        """Наносит урон врагу вражеской фракции."""
        other.take_damage(self.ATTACK_DAMAGE_PER_SECOND * delta_time, DamageType.KINETIC)

    def has_reached_end_of_path(self) -> bool:
        """Проверяет, дошёл ли враг до конца своего маршрута."""
        return self.path_index >= len(self.path)

    def move_towards_point(self, target: Coordinate, delta_time: float):
        """Двигает врага напрямую к точке, не по маршруту."""
        dx = target.x - self.position.x
        dy = target.y - self.position.y
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            return
        step = min(self.speed * delta_time, dist)
        self.position.x += dx / dist * step
        self.position.y += dy / dist * step

    def take_damage(self, amount: float, damage_type: DamageType):
        """Наносит врагу урон с учётом сопротивления брони."""
        if not self.is_alive(): return
        reduction = 0.0
        if self.armor == ArmorType.HEAVY and damage_type == DamageType.KINETIC:
            reduction = 0.5
        elif self.armor == ArmorType.ENERGY_SHIELDED and damage_type == DamageType.ENERGY:
            reduction = 0.5
        elif self.armor == ArmorType.ORGANIC and damage_type == DamageType.EXPLOSIVE:
            reduction = 0.5
        self.health -= amount * (1 - reduction)

    def is_alive(self) -> bool:
        """Проверяет, жив ли враг."""
        return self.health > 0

    def move_along_path(self, delta_time: float) -> bool:
        """Двигает врага к следующей точке маршрута."""
        if not self.path or self.path_index >= len(self.path):
            return True

        move_distance = self.speed * delta_time

        while self.path_index < len(self.path) and move_distance > 0:
            target = self.path[self.path_index]
            dx = target.x - self.position.x
            dy = target.y - self.position.y
            dist = (dx ** 2 + dy ** 2) ** 0.5

            if dist <= move_distance:
                move_distance -= dist
                self.position = Coordinate(target.x, target.y)
                self.path_index += 1
            else:
                self.position.x += (dx / dist) * move_distance
                self.position.y += (dy / dist) * move_distance
                move_distance = 0

        return self.path_index >= len(self.path)

    @abstractmethod
    def act(self, delta_time: float, in_danger: bool = False):
        """Выполняет особое поведение врага на этом кадре."""
        pass

    def is_moving(self) -> bool:
        """Проверяет, может ли враг двигаться по маршруту в этом кадре."""
        return True