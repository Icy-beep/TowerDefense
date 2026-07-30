"""
- корректность нанесения урона противнику
- корректность удаления уничтоженного противника
- корректность начисления награды за уничтожение противника
"""
from src.core.coordinate import Coordinate
from src.entities.enemies import DroneWalker, GiantRoach, BioTitan  # DroneWalker: LIGHT/60hp/reward15; GiantRoach: HEAVY/250hp; BioTitan: ORGANIC/400hp
from src.enums import DamageType
from src.core.map import Map

def test_take_damage_reduces_health():
    enemy = DroneWalker(Coordinate(0, 0))

    enemy.take_damage(20, DamageType.KINETIC)

    assert enemy.health == 40


def test_heavy_armor_halves_kinetic_damage():
    enemy = GiantRoach(Coordinate(0, 0))  # HEAVY armor, 250 hp

    enemy.take_damage(100, DamageType.KINETIC)

    assert enemy.health == 200, "HEAVY против KINETIC должен снижать урон на 50%"


def test_heavy_armor_does_not_reduce_energy_damage():
    enemy = GiantRoach(Coordinate(0, 0))

    enemy.take_damage(100, DamageType.ENERGY)

    assert enemy.health == 150, "HEAVY снижает только KINETIC — ENERGY проходит полностью"


def test_organic_armor_halves_explosive_damage():
    """Раньше EXPLOSIVE (мортира) не имел ни одного контр-типа брони —
    лучший ответ на всё без исключения. ORGANIC (BioTitan) теперь режет
    его вдвое, как HEAVY режет KINETIC."""
    enemy = BioTitan(Coordinate(0, 0))  # ORGANIC armor, 400 hp

    enemy.take_damage(100, DamageType.EXPLOSIVE)

    assert enemy.health == 350, "ORGANIC против EXPLOSIVE должен снижать урон на 50%"


def test_organic_armor_does_not_reduce_kinetic_or_energy_damage():
    enemy = BioTitan(Coordinate(0, 0))

    enemy.take_damage(100, DamageType.KINETIC)
    enemy.take_damage(100, DamageType.ENERGY)

    assert enemy.health == 200, "ORGANIC снижает только EXPLOSIVE — остальное проходит полностью"


def test_heavy_armor_does_not_reduce_explosive_damage():
    enemy = GiantRoach(Coordinate(0, 0))  # HEAVY armor

    enemy.take_damage(100, DamageType.EXPLOSIVE)

    assert enemy.health == 150, "HEAVY не защищает от EXPLOSIVE — это работа ORGANIC"


def test_enemy_dies_when_health_reaches_zero_or_below():
    enemy = DroneWalker(Coordinate(0, 0))  # 60 hp

    enemy.take_damage(1000, DamageType.KINETIC)

    assert enemy.is_alive() is False


def test_damage_is_ignored_after_death():
    enemy = DroneWalker(Coordinate(0, 0))
    enemy.take_damage(1000, DamageType.KINETIC)
    health_after_death = enemy.health

    enemy.take_damage(50, DamageType.KINETIC)  # добивание уже мёртвой цели

    assert enemy.health == health_after_death, "take_damage должен игнорировать уже мёртвую цель"


def test_map_removes_dead_enemy_from_active_list():
    game_map = Map()
    enemy = DroneWalker(Coordinate(100, 100))
    enemy.set_path([Coordinate(200, 100)])
    game_map.spawn_enemy(enemy)
    enemy.health = 0  # уничтожен снарядом на предыдущем шаге

    reached_base, killed = game_map.update(delta_time=0.1)

    assert enemy not in game_map.enemies, "уничтоженный противник должен исчезать из активного списка"
    assert enemy in killed
    assert reached_base == []


def test_map_keeps_alive_enemies_in_active_list():
    game_map = Map()
    enemy = DroneWalker(Coordinate(100, 100))
    enemy.set_path([Coordinate(200, 100)])
    game_map.spawn_enemy(enemy)

    _, killed = game_map.update(delta_time=0.1)

    assert enemy in game_map.enemies
    assert killed == []

def test_map_reports_killed_enemy_with_correct_reward_amount():
    game_map = Map()
    enemy = DroneWalker(Coordinate(100, 100))  # reward = 15
    enemy.set_path([Coordinate(200, 100)])
    game_map.spawn_enemy(enemy)
    enemy.health = 0

    _, killed = game_map.update(delta_time=0.1)

    assert len(killed) == 1
    assert killed[0].reward == 15


def test_full_kill_to_reward_pipeline_via_game_session():
    """Полный путь: Map возвращает killed_enemies -> GameSession начисляет
    награду в ResourceBank."""
    from src.core.game_session import GameSession

    session = GameSession()
    session.setup_game()

    enemy = DroneWalker(Coordinate(100, 100))  # reward = 15
    enemy.set_path([Coordinate(200, 100)])
    session.map.spawn_enemy(enemy)
    enemy.health = 0

    credits_before = session.resources.credits
    session.update(delta_time=0.01)  # маленький шаг, чтобы не задеть спавн новой волны

    assert session.resources.credits == credits_before + enemy.reward
    assert enemy not in session.map.enemies
