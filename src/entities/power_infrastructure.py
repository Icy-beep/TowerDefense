"""Базовый класс энергетической инфраструктуры (генераторы и пилоны)."""

from src.core.coordinate import Coordinate
from src.entities.defense_module import DefenseModule
from src.entities.hostile_entity import HostileEntity
from src.entities.projectile import Projectile


class PowerInfrastructure(DefenseModule):
    """Постройка энергосети: сама не стреляет, но занимает место на карте, имеет
    HP и уязвима для врагов совершенно так же, как обычная боевая башня (см.
    Map._update_vision, Map._update_group_targets - они работают с self.modules
    целиком, не различая боевые башни и инфраструктуру). range_radius унаследован
    от DefenseModule и переиспользуется как радиус действия энергосети - и для связи
    с другими узлами сети, и для подачи питания на боевые башни поблизости (см.
    Map._update_power_grid), и заодно бесплатно даёт визуализацию этого радиуса при
    выделении постройки (MapRenderer уже рисует range_radius как круг).

    IS_COMBAT_TOWER = False - в отличие от обычных башен, инфраструктура не считается
    угрозой для вражеского ИИ (Map.is_position_covered/_covering_towers её игнорируют),
    иначе враги шарахались бы от генераторов и пилонов, как от вооружённых башен, хотя
    те не могут причинить им вреда. При этом врагов-охотников за башнями
    (Map._update_group_targets) это не касается - для них инфраструктура остаётся
    полноценной целью наравне с боевыми башнями."""

    IS_COMBAT_TOWER = False
    IS_SOURCE = False

    def __init__(self, position: Coordinate, range_radius: float, cost: int, max_health: float = 100.0):
        """Создаёт постройку энергосети с нулевым уроном - она никогда не атакует."""
        super().__init__(position, range_radius=range_radius, damage=0.0, cost=cost, attack_speed=1.0)
        self.max_health = max_health
        self.health = max_health

    def find_target(self, enemies: list[HostileEntity]) -> HostileEntity | None:
        """Инфраструктура никогда не ищет цель - она не умеет стрелять."""
        return None

    def fire(self, target: HostileEntity) -> Projectile | None:
        """Инфраструктура никогда не стреляет."""
        return None
