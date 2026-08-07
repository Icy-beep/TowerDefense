"""Гнездо фауны - неподвижная разрушаемая точка спавна."""
from src.core.coordinate import Coordinate
from src.entities.entity import Entity
from src.enums import ArmorType, DamageType, Faction


class FaunaNest(Entity):
    """Точка появления врагов Fauna. Расставляются один раз при старте игры и не
    появляются заново - после уничтожения гнезда враги там больше не спавнятся, а
    когда уничтожены все гнёзда, фракция Fauna перестаёт спавниться вовсе (см.
    GameSession._generate_fauna_nests и Map.spawn_points_for)."""

    def __init__(self, position: Coordinate, max_health: float = 150.0, reward: int = 200):
        """Создаёт гнездо заданного здоровья в указанной точке. reward - разовая награда
        игроку за уничтожение (гнездо не респавнится, поэтому награда крупнее, чем за
        обычного врага - см. GameSession.update)."""
        super().__init__(position)
        self.max_health = max_health
        self.health = max_health
        self.reward = reward
        self.faction = Faction.FAUNA
        self.armor = ArmorType.ORGANIC
        self.type_name = "fauna_nest"

    def is_alive(self) -> bool:
        """Проверяет, цело ли гнездо."""
        return self.health > 0

    def is_destroyed(self) -> bool:
        """Проверяет, уничтожено ли гнездо."""
        return not self.is_alive()

    def take_damage(self, amount: float, damage_type: DamageType):
        """Наносит гнезду урон с учётом сопротивления органической брони взрывному урону."""
        if not self.is_alive():
            return
        reduction = 0.5 if damage_type == DamageType.EXPLOSIVE else 0.0
        self.health -= amount * (1 - reduction)
        if self.health < 0:
            self.health = 0
