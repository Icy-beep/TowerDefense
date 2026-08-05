"""Секторы карты: экономическая прогрессия открытия территории (см.
docs/DESIGN_RTS_TRANSITION.md, раздел 10). Карта делится на равную сетку
grid_size x grid_size секторов; сектор, где стоит база, открыт с самого начала,
остальные закрыты - строить в них нельзя (см. Map.can_place_module), источники
угрозы там неактивны (см. NestSpawnStrategy/ShipLandingStrategy), и они темнее
отрисовываются (см. MapRenderer). Открываются за кредиты (GameSession.unlock_sector_at) -
задания, привязанные к сектору, пока не реализованы (см. дизайн-док)."""
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class Sector:
    """Один сектор сетки карты. bounds - (x_min, y_min, x_max, y_max) в мировых
    координатах, границы полуоткрытые: [x_min, x_max) x [y_min, y_max) - так каждая
    точка карты принадлежит ровно одному сектору, без зазоров и пересечений на
    стыках."""

    row: int
    col: int
    bounds: Tuple[float, float, float, float]
    unlocked: bool = False

    def contains(self, position) -> bool:
        """Проверяет, лежит ли точка внутри границ сектора."""
        x_min, y_min, x_max, y_max = self.bounds
        return x_min <= position.x < x_max and y_min <= position.y < y_max


def build_sector_grid(width: float, height: float, grid_size: int,
                       base_position: Optional[object] = None) -> List[Sector]:
    """Строит равномерную сетку grid_size x grid_size секторов над картой
    width x height (последняя строка/столбец растягивается до точного края карты,
    чтобы не терять полоску от деления с остатком). Сектор, содержащий
    base_position (если задан), открывается сразу - это стартовая территория
    игрока; все остальные закрыты."""
    cell_w = width / grid_size
    cell_h = height / grid_size
    sectors: List[Sector] = []
    for row in range(grid_size):
        for col in range(grid_size):
            x_min = col * cell_w
            y_min = row * cell_h
            x_max = width if col == grid_size - 1 else x_min + cell_w
            y_max = height if row == grid_size - 1 else y_min + cell_h
            sectors.append(Sector(row=row, col=col, bounds=(x_min, y_min, x_max, y_max)))

    if base_position is not None:
        for sector in sectors:
            if sector.contains(base_position):
                sector.unlocked = True
                break

    return sectors
