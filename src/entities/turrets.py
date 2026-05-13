from src.entities.defense_module import DefenseModule
from src.entities.projectile import Projectile
from src.entities.hostile_entity import HostileEntity
from src.enums.enums import DamageType
from src.entities.coordinate import Coordinate

class LaserTurret(DefenseModule):
    """Быстрая башня, малый урон, энергетический тип"""
    def __init__(self, position: Coordinate):
        super().__init__(position, range_radius=120, damage=15, cost=50)
        self.attack_speed = 2.0
        self.damage_type = DamageType.ENERGY

    def fire(self, target: HostileEntity) -> Projectile:
        return Projectile(
            position=Coordinate(self.position.x, self.position.y),
            target=target,
            damage=self.damage,
            damage_type=self.damage_type,
            speed=10.0
        )

class BulletTurret(DefenseModule):
    """Средняя башня, кинетический урон"""
    def __init__(self, position: Coordinate):
        super().__init__(position, range_radius=150, damage=30, cost=100)
        self.attack_speed = 1.0
        self.damage_type = DamageType.KINETIC

    def fire(self, target: HostileEntity) -> Projectile:
        return Projectile(
            position=Coordinate(self.position.x, self.position.y),
            target=target,
            damage=self.damage,
            damage_type=self.damage_type,
            speed=7.0
        )

class MortarTurret(DefenseModule):
    """Медленная башня, большой урон, взрывной тип"""
    def __init__(self, position: Coordinate):
        super().__init__(position, range_radius=200, damage=80, cost=200)
        self.attack_speed = 0.5
        self.damage_type = DamageType.EXPLOSIVE

    def fire(self, target: HostileEntity) -> Projectile:
        return Projectile(
            position=Coordinate(self.position.x, self.position.y),
            target=target,
            damage=self.damage,
            damage_type=self.damage_type,
            speed=4.0
        )