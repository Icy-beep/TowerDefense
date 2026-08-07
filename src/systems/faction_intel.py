"""Разведданные одной фракции о постройках игрока."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.entities.defense_module import DefenseModule


class FactionIntel:
    """Хранит башни, известные одной фракции."""

    def __init__(self):
        """Создаёт пустые разведданные."""
        self._known_towers: dict[int, DefenseModule] = {}

    def reveal(self, tower: "DefenseModule") -> bool:
        """Отмечает башню как известную. Возвращает True, если она стала известна только сейчас."""
        key = id(tower)
        if key in self._known_towers:
            return False
        self._known_towers[key] = tower
        return True

    def knows(self, tower: "DefenseModule") -> bool:
        """Проверяет, известна ли башня."""
        return id(tower) in self._known_towers

    def known_towers(self) -> list["DefenseModule"]:
        """Возвращает список известных башен."""
        return list(self._known_towers.values())
