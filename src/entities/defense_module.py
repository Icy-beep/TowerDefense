import math
from abc import ABC, abstractmethod
from typing import Optional

from src.core.coordinate import Coordinate
from src.entities.hostile_entity import HostileEntity
from src.entities.projectile import Projectile
from src.enums import DamageType, ModuleStatus

from .entity import Entity


class DefenseModule(Entity, ABC):
    """Базовый класс для всех башен."""

    LANDING_DURATION = 3.5
    LANDING_START_HEIGHT = 600.0
    LANDING_IMPACT_RADIUS = 60.0

    FOOTPRINT_CELLS = 3

    # Считается ли эта постройка боевой угрозой для вражеского ИИ (см.
    # Map.is_position_covered/_covering_towers). Переопределяется в False у
    # PowerInfrastructure - генераторы и пилоны не стреляют, поэтому враги не должны
    # шарахаться от них и обходить их радиус как радиус атаки.
    IS_COMBAT_TOWER = True

    def __init__(self, position: Coordinate, range_radius: float, damage: float, cost: int, attack_speed: float = 1.0):
        """Создаёт башню с базовыми характеристиками."""
        super().__init__(position)

        self.base_range = range_radius
        self.base_damage = damage
        self.base_attack_speed = attack_speed

        self.range_radius = self.base_range
        self.damage = self.base_damage
        self.attack_speed = self.base_attack_speed

        self.cost = cost
        self.status = ModuleStatus.IDLE
        self.cooldown_timer = 0.0

        self.max_health = 100.0
        self.health = self.max_health

        self.level = 1
        self.max_level = 3
        self.upgrade_costs: list[int] = []

        self.is_landing = False
        self.landing_elapsed = 0.0
        self.landing_height = 0.0
        self._pending_landed_event = False

        self.facing_angle = 0.0

        # Подключена ли башня к энергосети - см. Map._update_power_grid. По умолчанию
        # True, чтобы башни, созданные напрямую (без Map/GameSession, как в большинстве
        # существующих тестов), продолжали стрелять как раньше - лимит по питанию
        # применяется только на картах с включённой энергосетью
        # (Map.power_grid_enabled).
        self.is_powered = True

    def start_landing(self):
        """Запускает высадку с орбиты: башня неуязвима и не стреляет, пока не приземлится."""
        self.is_landing = True
        self.landing_elapsed = 0.0
        self.landing_height = self.LANDING_START_HEIGHT

    @property
    def landing_progress(self) -> float:
        """Доля пройденного времени высадки от 0 до 1."""
        return min(1.0, self.landing_elapsed / self.LANDING_DURATION)

    def take_landing_event(self) -> bool:
        """Возвращает True один раз, в момент когда башня только что приземлилась."""
        if self._pending_landed_event:
            self._pending_landed_event = False
            return True
        return False

    def update(self, delta_time: float, enemies: list[HostileEntity]) -> Projectile | None:
        """Обновляет башню на один кадр и стреляет по цели, если готова."""
        if self.is_landing:
            self._advance_landing(delta_time, enemies)
            return None

        if self.status in (ModuleStatus.OVERHEATED, ModuleStatus.OFFLINE):
            return None

        if not self.is_powered:
            return None

        target = self.find_target(enemies)
        if target:
            self._face_towards(target.position)

        if self.cooldown_timer > 0:
            self.cooldown_timer -= delta_time
            return None

        if target:
            self.cooldown_timer = 1.0 / self.attack_speed
            return self.fire(target)

        return None

    def _face_towards(self, point: Coordinate):
        """Обновляет facing_angle — азимут (0° = вверх/север, растёт по часовой стрелке) на
        текущую цель, чтобы спрайт с направленными кадрами (см. SpriteManager.get_frame_for_angle)
        мог развернуться к ней. Если цели нет, башня сохраняет последнее направление."""
        dx = point.x - self.position.x
        dy = point.y - self.position.y
        if dx == 0 and dy == 0:
            return
        self.facing_angle = math.degrees(math.atan2(dx, -dy)) % 360.0

    def _advance_landing(self, delta_time: float, enemies: list[HostileEntity]):
        """Двигает башню вниз по высоте и наносит урон при приземлении."""
        self.landing_elapsed += delta_time
        t = self.landing_progress
        self.landing_height = self.LANDING_START_HEIGHT * (1 - t) ** 2

        if t >= 1.0:
            self.is_landing = False
            self.landing_height = 0.0
            self._pending_landed_event = True
            self._deal_landing_impact(enemies)

    def _deal_landing_impact(self, enemies: list[HostileEntity]):
        """Наносит урон всем врагам, оказавшимся под точкой приземления. Инфраструктура
        энергосети (генератор/пилон) создаётся с damage=0.0 и никогда не задаёт
        self.damage_type (см. PowerInfrastructure) - она физически не может атаковать,
        поэтому при её приземлении удар по врагам пропускается вообще, а не считается
        с несуществующим типом урона."""
        if self.damage <= 0:
            return
        impact_damage = self.damage * 2
        for enemy in enemies:
            if enemy.is_alive() and self.position.distance_to(enemy.position) <= self.LANDING_IMPACT_RADIUS:
                enemy.take_damage(impact_damage, self.damage_type)

    def find_target(self, enemies: list[HostileEntity]) -> Optional[HostileEntity]:
        """Находит ближайшего врага в радиусе действия."""
        valid_targets = [
            e for e in enemies
            if self.position.distance_to(e.position) <= self.range_radius
        ]
        if not valid_targets:
            return None
        return min(valid_targets, key=lambda e: self.position.distance_to(e.position))

    @abstractmethod
    def fire(self, target: HostileEntity) -> Projectile | None:
        """Создаёт снаряд по цели."""
        pass

    def get_upgrade_cost(self) -> int | None:
        """Возвращает стоимость следующего уровня или None, если максимум."""
        if self.level >= self.max_level:
            return None
        return self.upgrade_costs[self.level - 1]

    def can_upgrade(self) -> bool:
        """Проверяет, можно ли улучшить башню."""
        return self.level < self.max_level

    def upgrade(self) -> bool:
        """Повышает уровень башни и пересчитывает характеристики."""
        if not self.can_upgrade():
            return False

        self.level += 1

        dmg_mult = 1.0 + (self.level - 1) * 0.4
        rng_mult = 1.0 + (self.level - 1) * 0.2
        spd_mult = 1.0 + (self.level - 1) * 0.25

        self.damage = self.base_damage * dmg_mult
        self.range_radius = self.base_range * rng_mult
        self.attack_speed = self.base_attack_speed * spd_mult

        return True

    def take_damage(self, amount: float, damage_type: DamageType):
        """Наносит урон башне. Пока башня высаживается, она неуязвима."""
        if self.is_landing:
            return
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.status = ModuleStatus.OFFLINE

    def is_destroyed(self) -> bool:
        """Проверяет, уничтожена ли башня."""
        return self.health <= 0