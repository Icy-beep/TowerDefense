"""Групповое поведение врагов."""
import math
import random
from typing import Dict, List, Optional

from src.core.coordinate import Coordinate
from src.entities.hostile_entity import HostileEntity
from src.enums import Faction


class GroupFormationSystem:
    """Случайно формирует группы врагов вокруг лидера."""

    LEADER_TYPES = {"heavy_assault_drone"}
    SOLO_TYPES = {"scout_drone"}

    FORM_CHANCE_PER_SECOND = 0.35
    GROUP_RADIUS = 220.0
    MAX_ESCORT_SIZE = 3
    FORMATION_RADIUS = 45.0

    FACTION_OVERRIDES: Dict[Faction, dict] = {
        Faction.FAUNA: {
            "leader_types": {"giant_roach", "bio_titan"},
            "solo_types": set(),
            "form_chance_per_second": 0.5,
            "group_radius": 300.0,
            "max_escort_size": 4,
            "formation_radius": 55.0,
        },
    }

    def __init__(self, rng: Optional[random.Random] = None):
        """Создаёт систему формирования групп."""
        self._rng = rng or random
        self._next_group_id = 1

    def _profile_for(self, faction: Faction) -> dict:
        """Возвращает профиль группового поведения для фракции."""
        override = self.FACTION_OVERRIDES.get(faction, {})
        return {
            "leader_types": override.get("leader_types", self.LEADER_TYPES),
            "solo_types": override.get("solo_types", self.SOLO_TYPES),
            "form_chance_per_second": override.get("form_chance_per_second", self.FORM_CHANCE_PER_SECOND),
            "group_radius": override.get("group_radius", self.GROUP_RADIUS),
            "max_escort_size": override.get("max_escort_size", self.MAX_ESCORT_SIZE),
            "formation_radius": override.get("formation_radius", self.FORMATION_RADIUS),
        }

    def update(self, delta_time: float, enemies: List[HostileEntity]):
        """Обновляет формирование групп на один кадр."""
        for enemy in enemies:
            if not enemy.is_alive():
                continue

            profile = self._profile_for(enemy.faction)
            if getattr(enemy, "type_name", None) not in profile["leader_types"]:
                continue
            if enemy.group_leader is not None:
                continue

            escort_count = sum(1 for other in enemies if other.group_leader is enemy)
            if enemy.group_id is not None and escort_count >= profile["max_escort_size"]:
                continue

            if self._rng.random() >= profile["form_chance_per_second"] * delta_time:
                continue

            candidates = [
                other for other in enemies
                if other is not enemy
                and other.is_alive()
                and other.group_id is None
                and other.faction == enemy.faction
                and getattr(other, "type_name", None) not in profile["solo_types"]
                and enemy.position.distance_to(other.position) <= profile["group_radius"]
            ]
            if not candidates:
                continue

            recruit = self._rng.choice(candidates)

            if enemy.group_id is None:
                enemy.group_id = self._next_group_id
                self._next_group_id += 1
                enemy.is_group_leader = True

            angle = (2 * math.pi / profile["max_escort_size"]) * escort_count
            offset = Coordinate(math.cos(angle) * profile["formation_radius"],
                                math.sin(angle) * profile["formation_radius"])
            recruit.join_group(enemy.group_id, enemy, offset)
