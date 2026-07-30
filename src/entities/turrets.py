from typing import List, Optional
from src.entities.defense_module import DefenseModule
from src.entities.projectile import Projectile, HitscanBeam, BulletProjectile, MortarShell
from src.entities.hostile_entity import HostileEntity
from src.enums import DamageType
from src.core.coordinate import Coordinate

class LaserTurret(DefenseModule):
    """Быстрая башня с энергетическим уроном."""

    def __init__(self, position: Coordinate, range_radius: float = 120, damage: float = 15,
                 cost: int = 50, attack_speed: float = 2.0, upgrade_costs: Optional[List[int]] = None):
        """Создаёт лазерную башню."""
        super().__init__(position, range_radius=range_radius, damage=damage, cost=cost, attack_speed=attack_speed)
        self.damage_type = DamageType.ENERGY
        self.upgrade_costs = list(upgrade_costs) if upgrade_costs is not None else [80, 120]

    def fire(self, target: HostileEntity) -> Projectile:
        """Выпускает мгновенный лазерный луч по цели."""
        return HitscanBeam(
            position=Coordinate(self.position.x, self.position.y),
            target=target,
            damage=self.damage,
            damage_type=self.damage_type,
        )

class BulletTurret(DefenseModule):
    """Средняя башня с кинетическим уроном."""

    def __init__(self, position: Coordinate, range_radius: float = 150, damage: float = 30,
                 cost: int = 100, attack_speed: float = 1.0, upgrade_costs: Optional[List[int]] = None):
        """Создаёт пулемётную башню."""
        super().__init__(position, range_radius=range_radius, damage=damage, cost=cost, attack_speed=attack_speed)
        self.damage_type = DamageType.KINETIC
        self.upgrade_costs = list(upgrade_costs) if upgrade_costs is not None else [150, 200]

    def fire(self, target: HostileEntity) -> Projectile:
        """Выпускает пулю по цели."""
        return BulletProjectile(
            position=Coordinate(self.position.x, self.position.y),
            target=target,
            damage=self.damage,
            damage_type=self.damage_type,
            speed=420.0,
            max_distance=self.range_radius + 200.0,
        )

class MortarTurret(DefenseModule):
    """Медленная башня с мощным взрывным уроном."""

    def __init__(self, position: Coordinate, range_radius: float = 200, damage: float = 80,
                 cost: int = 200, attack_speed: float = 0.5, upgrade_costs: Optional[List[int]] = None):
        """Создаёт миномётную башню."""
        super().__init__(position, range_radius=range_radius, damage=damage, cost=cost, attack_speed=attack_speed)
        self.damage_type = DamageType.EXPLOSIVE
        self.upgrade_costs = list(upgrade_costs) if upgrade_costs is not None else [250, 300]

    def fire(self, target: HostileEntity) -> Projectile:
        """Выпускает миномётный снаряд по цели."""
        return MortarShell(
            position=Coordinate(self.position.x, self.position.y),
            target=target,
            damage=self.damage,
            damage_type=self.damage_type,
        )
