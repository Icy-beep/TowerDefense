
from src.core.coordinate import Coordinate
from src.entities.hostile_entity import HostileEntity
from src.entities.projectile import EnemyHitscanBeam, HitscanBeam
from src.enums import ArmorType, DamageType, Faction


class DroneWalker(HostileEntity):
    """Быстрый и слабый механический дрон корпорации."""

    def __init__(self, position: Coordinate, max_health: float = 60, speed: float = 50,
                 armor: ArmorType = ArmorType.LIGHT, reward: int = 15,
                 faction: Faction = Faction.CORPORATION, vision_radius: float | None = None):
        """Создаёт лёгкого дрона."""
        super().__init__(position, max_health=max_health, speed=speed, armor=armor, reward=reward, faction=faction,
                          vision_radius=vision_radius)

    def act(self, delta_time: float, in_danger: bool = False):
        """Не выполняет особых действий."""
        pass

class HeavyAssaultDrone(HostileEntity):
    """Тяжёлый штурмовой дрон корпорации."""

    def __init__(self, position: Coordinate, max_health: float = 180, speed: float = 35,
                 armor: ArmorType = ArmorType.HEAVY, reward: int = 45,
                 faction: Faction = Faction.CORPORATION, vision_radius: float | None = None):
        """Создаёт тяжёлого штурмового дрона."""
        super().__init__(position, max_health=max_health, speed=speed, armor=armor, reward=reward, faction=faction,
                          vision_radius=vision_radius)

    def act(self, delta_time: float, in_danger: bool = False):
        """Не выполняет особых действий."""
        pass

class GiantRoach(HostileEntity):
    """Медленный и живучий гигантский таракан фауны планеты. При потере большей части
    здоровья впадает в ярость - становится быстрее и бьёт сильнее (см. act)."""

    ENRAGE_HEALTH_RATIO = 0.4
    ENRAGE_SPEED_MULTIPLIER = 1.6
    ENRAGE_DAMAGE_MULTIPLIER = 1.5

    def __init__(self, position: Coordinate, max_health: float = 300, speed: float = 20,
                 armor: ArmorType = ArmorType.HEAVY, reward: int = 40,
                 faction: Faction = Faction.FAUNA, vision_radius: float | None = None):
        """Создаёт гигантского таракана."""
        super().__init__(position, max_health=max_health, speed=speed, armor=armor, reward=reward, faction=faction,
                          vision_radius=vision_radius)
        self._base_speed = speed
        self.is_enraged = False

    def act(self, delta_time: float, in_danger: bool = False):
        """Проверяет порог ярости - разовый переход (обратно не снимается, даже если
        таракана потом подлечат), как только здоровье падает до ENRAGE_HEALTH_RATIO
        от максимума: скорость и урон в ближнем бою умножаются на постоянные
        множители."""
        if self.is_enraged or not self.is_alive():
            return
        if self.health > self.max_health * self.ENRAGE_HEALTH_RATIO:
            return
        self.is_enraged = True
        self.speed = self._base_speed * self.ENRAGE_SPEED_MULTIPLIER
        self.ATTACK_DAMAGE_PER_SECOND = self.ATTACK_DAMAGE_PER_SECOND * self.ENRAGE_DAMAGE_MULTIPLIER

class ScoutDrone(HostileEntity):
    """Дрон-разведчик корпорации: только разведка, убегает от башен, не участвует в группах."""

    VISION_RADIUS = 300.0

    def __init__(self, position: Coordinate, max_health: float = 100, speed: float = 70,
                 armor: ArmorType = ArmorType.ENERGY_SHIELDED, reward: int = 60,
                 faction: Faction = Faction.CORPORATION, vision_radius: float | None = None):
        """Создаёт дрона-разведчика."""
        super().__init__(position, max_health=max_health, speed=speed, armor=armor, reward=reward, faction=faction,
                          vision_radius=vision_radius)

    def act(self, delta_time: float, in_danger: bool = False):
        """Не выполняет особых действий — вся логика бегства находится в Map.update()."""
        pass

    def avoids_danger(self) -> bool:
        """Разведчик всегда убегает от простреливаемых зон вместо боя."""
        return True

class SniperDrone(HostileEntity):
    """Дрон-снайпер корпорации: бьёт башню издалека своим увеличенным ATTACK_RANGE,
    не заходя в радиус большинства турелей первого уровня - чтобы его достать,
    игроку нужна прокачанная башня или миномёт."""

    ATTACK_RANGE = 430.0
    ATTACK_DAMAGE_PER_SECOND = 10.0

    def __init__(self, position: Coordinate, max_health: float = 70, speed: float = 40,
                 armor: ArmorType = ArmorType.LIGHT, reward: int = 55,
                 faction: Faction = Faction.CORPORATION, vision_radius: float | None = None):
        """Создаёт дрона-снайпера."""
        super().__init__(position, max_health=max_health, speed=speed, armor=armor, reward=reward, faction=faction,
                          vision_radius=vision_radius)

    def act(self, delta_time: float, in_danger: bool = False):
        """Не выполняет особых действий - дальнобойность реализована через ATTACK_RANGE."""
        pass

    def attack_tower(self, tower, delta_time: float):
        """Стреляет по башне лучом - урон мгновенный, как и у базовой реализации, но
        выстрел виден на карте так же, как у LaserTurret (см. EnemyHitscanBeam)."""
        return EnemyHitscanBeam(
            position=self.position,
            target=tower,
            damage=self.ATTACK_DAMAGE_PER_SECOND * delta_time,
            damage_type=DamageType.KINETIC,
        )

    def attack_enemy(self, other: HostileEntity, delta_time: float):
        """Стреляет по вражескому юниту лучом с тем же видимым эффектом выстрела."""
        return HitscanBeam(
            position=self.position,
            target=other,
            damage=self.ATTACK_DAMAGE_PER_SECOND * delta_time,
            damage_type=DamageType.KINETIC,
        )

class MedicDrone(HostileEntity):
    """Дрон-медик корпорации: не атакует, ищет ближайшую группу союзников,
    присоединяется к ней и лечит - пока не в группе, избегает башен."""

    def __init__(self, position: Coordinate, max_health: float = 90, speed: float = 55,
                 armor: ArmorType = ArmorType.ENERGY_SHIELDED, reward: int = 50,
                 faction: Faction = Faction.CORPORATION, vision_radius: float | None = None):
        """Создаёт дрона-медика."""
        super().__init__(position, max_health=max_health, speed=speed, armor=armor, reward=reward, faction=faction,
                          vision_radius=vision_radius)

    def act(self, delta_time: float, in_danger: bool = False):
        """Не выполняет особых действий - поиск группы и лечение находятся в Map.update()."""
        pass

    def is_combatant(self) -> bool:
        """Медик никогда не атакует врагов и не участвует в захвате башен."""
        return False

    def heals_allies(self) -> bool:
        """Медик лечит участников своей группы, пока состоит в ней."""
        return True

    def avoids_danger(self) -> bool:
        """Пока не присоединился к группе - избегает простреливаемых зон;
        в группе (занят лечением) - игнорирует обстрел и не убегает."""
        return self.group_leader is None

class BioTitan(HostileEntity):
    """Огромный и живучий органический титан фауны планеты - пробивной юнит: не
    выжидает брешь в обороне (Map._advance_towards_base) и не отступает на лечение
    (Map.update), пока жив - см. breaks_through."""

    def __init__(self, position: Coordinate, max_health: float = 400, speed: float = 20,
                 armor: ArmorType = ArmorType.ORGANIC, reward: int = 70,
                 faction: Faction = Faction.FAUNA, vision_radius: float | None = None):
        """Создаёт био-титана."""
        super().__init__(position, max_health=max_health, speed=speed, armor=armor, reward=reward, faction=faction,
                          vision_radius=vision_radius)

    def act(self, delta_time: float, in_danger: bool = False):
        """Не выполняет особых действий."""
        pass

    def breaks_through(self) -> bool:
        """Титан прёт напролом: не патрулирует границу известных башен в ожидании
        бреши и не отступает лечиться, пока жив (см. Map._advance_towards_base,
        Map.update)."""
        return True
