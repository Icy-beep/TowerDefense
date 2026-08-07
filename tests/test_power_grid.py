"""Энергосеть: боевые башни стреляют только когда подключены к базе или генератору
через (при необходимости) цепочку пилонов; уничтожение узла сети отключает всё,
что зависело только от него."""
import types

import pygame

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.core.map import Map
from src.entities.enemies import DroneWalker
from src.entities.power_generator import PowerGenerator
from src.entities.power_pylon import PowerPylon
from src.entities.turrets import LaserTurret
from src.enums import DamageType
from src.factories.tower_factory import TowerFactory

# --- Инфраструктура: базовое поведение -----------------------------------------

def test_infrastructure_never_finds_a_target():
    node = PowerGenerator(Coordinate(0, 0), range_radius=1000.0)
    enemy = DroneWalker(Coordinate(10, 10))

    assert node.find_target([enemy]) is None


def test_infrastructure_never_fires():
    node = PowerGenerator(Coordinate(0, 0))
    enemy = DroneWalker(Coordinate(10, 10))

    assert node.fire(enemy) is None


def test_infrastructure_is_not_a_combat_tower():
    assert PowerGenerator(Coordinate(0, 0)).IS_COMBAT_TOWER is False
    assert PowerPylon(Coordinate(0, 0)).IS_COMBAT_TOWER is False
    assert LaserTurret(Coordinate(0, 0)).IS_COMBAT_TOWER is True


def test_generator_is_a_source_pylon_is_not():
    assert PowerGenerator(Coordinate(0, 0)).IS_SOURCE is True
    assert PowerPylon(Coordinate(0, 0)).IS_SOURCE is False


def test_infrastructure_cannot_be_upgraded():
    node = PowerPylon(Coordinate(0, 0))

    assert node.can_upgrade() is False
    assert node.get_upgrade_cost() is None


def test_infrastructure_is_vulnerable_like_a_regular_tower():
    node = PowerPylon(Coordinate(0, 0), max_health=60.0)

    node.take_damage(1000, DamageType.KINETIC)

    assert node.is_destroyed() is True


# --- DefenseModule: is_powered гейтит стрельбу -----------------------------------

def test_tower_defaults_to_powered():
    tower = LaserTurret(Coordinate(0, 0))
    assert tower.is_powered is True


def test_unpowered_tower_does_not_fire_even_with_target_in_range():
    tower = LaserTurret(Coordinate(0, 0))
    tower.is_powered = False
    enemy = DroneWalker(Coordinate(10, 0))

    projectile = tower.update(0.1, [enemy])

    assert projectile is None
    assert enemy.health == enemy.max_health, "невозможно нанести урон без питания"


def test_powered_tower_fires_normally():
    tower = LaserTurret(Coordinate(0, 0))
    enemy = DroneWalker(Coordinate(10, 0))

    projectile = tower.update(0.1, [enemy])

    assert projectile is not None
    assert enemy.health < enemy.max_health


# --- Map._update_power_grid: связность сети -------------------------------------

def _map_with_power(base_position=Coordinate(3000, 3000)):
    game_map = Map(width=6000, height=6000)
    game_map.power_grid_enabled = True
    game_map.base_position = base_position
    return game_map


def test_power_grid_disabled_by_default_keeps_towers_powered_regardless_of_distance():
    """Регрессия: карты без power_grid_enabled (как почти все существующие тесты)
    не должны трогать is_powered вообще."""
    game_map = Map(width=6000, height=6000)
    game_map.base_position = Coordinate(3000, 3000)
    tower = LaserTurret(Coordinate(0, 0))
    game_map.modules.append(tower)

    game_map.update(0.1)

    assert tower.is_powered is True


def test_tower_within_base_radius_is_powered_without_any_infrastructure():
    game_map = _map_with_power()
    tower = LaserTurret(Coordinate(3000, 3100))
    game_map.modules.append(tower)

    game_map.update(0.1)

    assert tower.is_powered is True


def test_tower_far_from_base_without_infrastructure_is_unpowered():
    game_map = _map_with_power()
    tower = LaserTurret(Coordinate(100, 100))
    game_map.modules.append(tower)

    game_map.update(0.1)

    assert tower.is_powered is False


def test_far_tower_does_not_actually_fire_without_power():
    game_map = _map_with_power()
    tower = LaserTurret(Coordinate(100, 100), range_radius=1000.0)
    tower.cooldown_timer = 0.0
    enemy = DroneWalker(Coordinate(110, 100))
    game_map.modules.append(tower)
    game_map.spawn_enemy(enemy)

    game_map.update(0.1)

    assert enemy.health == enemy.max_health, "без питания башня не должна наносить урон"


def test_generator_powers_nearby_tower_far_from_base():
    game_map = _map_with_power()
    generator = PowerGenerator(Coordinate(100, 100), range_radius=300.0)
    tower = LaserTurret(Coordinate(150, 100))
    game_map.modules.append(generator)
    game_map.modules.append(tower)

    game_map.update(0.1)

    assert generator.is_powered is True, "генератор всегда под напряжением сам по себе"
    assert tower.is_powered is True


def test_pylon_alone_provides_no_power_since_it_has_no_source():
    game_map = _map_with_power()
    pylon = PowerPylon(Coordinate(100, 100), range_radius=300.0)
    tower = LaserTurret(Coordinate(150, 100))
    game_map.modules.append(pylon)
    game_map.modules.append(tower)

    game_map.update(0.1)

    assert pylon.is_powered is False
    assert tower.is_powered is False


def test_pylon_chained_to_base_powers_a_distant_tower():
    game_map = _map_with_power()
    # Пилон в радиусе бесплатного питания базы (BASE_POWER_RADIUS=550) продолжает
    # цепочку дальше, к башне, которая сама уже слишком далеко от базы.
    pylon = PowerPylon(Coordinate(3500, 3000), range_radius=600.0)
    tower = LaserTurret(Coordinate(4050, 3000))
    game_map.modules.append(pylon)
    game_map.modules.append(tower)

    game_map.update(0.1)

    assert pylon.is_powered is True
    assert tower.is_powered is True


def test_two_pylons_relay_power_transitively_from_a_generator():
    game_map = _map_with_power(base_position=Coordinate(0, 0))
    # Генератор далеко от базы - но он свой собственный источник.
    generator = PowerGenerator(Coordinate(5000, 5000), range_radius=300.0)
    pylon_1 = PowerPylon(Coordinate(5280, 5000), range_radius=300.0)
    pylon_2 = PowerPylon(Coordinate(5560, 5000), range_radius=300.0)
    tower = LaserTurret(Coordinate(5820, 5000))
    for node in (generator, pylon_1, pylon_2, tower):
        game_map.modules.append(node)

    game_map.update(0.1)

    assert pylon_1.is_powered is True
    assert pylon_2.is_powered is True
    assert tower.is_powered is True


def test_breaking_the_chain_by_destroying_a_pylon_cuts_power_downstream():
    game_map = _map_with_power(base_position=Coordinate(0, 0))
    generator = PowerGenerator(Coordinate(5000, 5000), range_radius=300.0)
    pylon_1 = PowerPylon(Coordinate(5280, 5000), range_radius=300.0)
    pylon_2 = PowerPylon(Coordinate(5560, 5000), range_radius=300.0)
    tower = LaserTurret(Coordinate(5820, 5000))
    for node in (generator, pylon_1, pylon_2, tower):
        game_map.modules.append(node)

    game_map.update(0.1)
    assert tower.is_powered is True

    pylon_1.health = 0
    game_map.update(0.1)

    assert tower.is_powered is False, "потеря промежуточного узла должна отключать всё за ним"


def test_isolated_generator_is_always_powered_even_when_disconnected():
    game_map = _map_with_power(base_position=Coordinate(0, 0))
    generator = PowerGenerator(Coordinate(5000, 5000))
    game_map.modules.append(generator)

    game_map.update(0.1)

    assert generator.is_powered is True


# --- Инфраструктура не считается угрозой для вражеского ИИ ----------------------

def test_is_position_covered_ignores_power_infrastructure():
    game_map = Map(width=4000, height=4000)
    generator = PowerGenerator(Coordinate(0, 0), range_radius=1000.0)
    game_map.modules.append(generator)

    assert game_map.is_position_covered(Coordinate(0, 0)) is False


def test_is_position_covered_still_detects_combat_towers():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(0, 0), range_radius=1000.0)
    game_map.modules.append(tower)

    assert game_map.is_position_covered(Coordinate(0, 0)) is True


def test_covering_towers_excludes_infrastructure():
    game_map = Map(width=4000, height=4000)
    generator = PowerGenerator(Coordinate(0, 0), range_radius=1000.0)
    tower = LaserTurret(Coordinate(5, 0), range_radius=1000.0)
    game_map.modules.extend([generator, tower])

    covering = game_map._covering_towers(Coordinate(0, 0))

    assert generator not in covering
    assert tower in covering


# --- GameSession: подключение фичи -----------------------------------------------

def test_setup_game_enables_the_power_grid():
    session = GameSession()
    session.setup_game()

    assert session.map.power_grid_enabled is True


def test_tower_factory_can_build_generator_and_pylon():
    factory = TowerFactory()

    assert "generator" in factory.available_types()
    assert "pylon" in factory.available_types()
    assert factory.create("generator", Coordinate(0, 0)) is not None
    assert factory.create("pylon", Coordinate(0, 0)) is not None


def test_placing_a_generator_through_the_session_deducts_its_cost():
    session = GameSession()
    session.setup_game()
    credits_before = session.resources.credits

    success = session.place_turret("generator", Coordinate(3100, 3000))

    assert success is True
    assert session.resources.credits < credits_before
    placed = session.map.modules[-1]
    assert isinstance(placed, PowerGenerator)


def test_towers_near_base_work_out_of_the_box_after_setup_game():
    """У базы должен быть небольшой бесплатный радиус питания, иначе нельзя
    построить вообще ни одной работающей башни в начале игры."""
    session = GameSession()
    session.setup_game()
    near_base = Coordinate(session.base_position.x + 100, session.base_position.y)

    assert session.place_turret("laser", near_base) is True
    session.map.update(0.1)

    tower = session.map.modules[-1]
    assert tower.is_powered is True


# --- Renderer -----------------------------------------------------------------

def test_renderer_draws_power_links():
    from src.ui.map_renderer import MapRenderer

    renderer = MapRenderer()
    session = types.SimpleNamespace(map=types.SimpleNamespace(
        power_links=[(Coordinate(0, 0), Coordinate(100, 0))]
    ))

    line_calls = []
    original_line = pygame.draw.line

    def spy_line(surface, color, start, end, *args, **kwargs):
        line_calls.append(tuple(color))
        return original_line(surface, color, start, end, *args, **kwargs)

    pygame.draw.line = spy_line
    try:
        camera = types.SimpleNamespace(world_to_screen=lambda x, y: (x, y), x=0, y=0, zoom=1.0)
        screen = pygame.Surface((900, 600))
        renderer._draw_power_links(screen, camera, session)
    finally:
        pygame.draw.line = original_line

    assert len(line_calls) == 1


def test_renderer_marks_unpowered_tower_with_a_warning_ring():
    import types as _types

    from src.ui.map_renderer import MapRenderer

    renderer = MapRenderer()
    tower = LaserTurret(Coordinate(100, 100))
    tower.is_powered = False
    session = _types.SimpleNamespace(map=_types.SimpleNamespace(modules=[tower], nav_grid=_types.SimpleNamespace(cell_size=32)))
    controller = _types.SimpleNamespace(selected_module=None)
    tower_options = [{"type": "laser", "name": "Laser", "color": (0, 255, 255)}]

    circle_colors = []
    original_circle = pygame.draw.circle

    def spy_circle(surface, color, center, radius, *args, **kwargs):
        circle_colors.append(tuple(color))
        return original_circle(surface, color, center, radius, *args, **kwargs)

    pygame.draw.circle = spy_circle
    try:
        camera = types.SimpleNamespace(world_to_screen=lambda x, y: (x, y), x=0, y=0, zoom=1.0)
        screen = pygame.Surface((900, 600))
        renderer._draw_modules(screen, camera, session, controller, tower_options)
    finally:
        pygame.draw.circle = original_circle

    assert (255, 60, 60) in circle_colors, "должно быть визуальное предупреждение об отсутствии питания"
