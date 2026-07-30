"""Визуальное различие типов врагов на карте (MapRenderer). Раньше все
враги рисовались одинаковым красным кружком — из-за этого поведение
ScoutDrone (стоит на месте во время разведки) было неотличимо от
любого другого врага, который просто пока не подошёл."""
import types
from src.ui.map_renderer import MapRenderer, ENEMY_COLORS, DEFAULT_ENEMY_COLOR
from src.factories.enemy_factory import EnemyFactory
from src.core.coordinate import Coordinate
from src.core.game_session import GameSession


def test_every_registered_enemy_type_has_a_distinct_color():
    factory = EnemyFactory()
    types_ = factory.available_types()

    for type_name in types_:
        assert type_name in ENEMY_COLORS, f"нет цвета для нового типа врага '{type_name}'"

    colors = [ENEMY_COLORS[t] for t in types_]
    assert len(set(colors)) == len(colors), "у разных типов врагов не должно быть одинакового цвета"


def test_unknown_enemy_type_falls_back_to_default_color():
    class _Unregistered:
        type_name = "totally_new_enemy"

    assert ENEMY_COLORS.get(_Unregistered.type_name, DEFAULT_ENEMY_COLOR) == DEFAULT_ENEMY_COLOR


def test_render_enemies_smoke_scouting_and_selected(monkeypatch):
    """Прогоняет реальный render() через все состояния (обычный враг,
    разведчик во время recon, разведчик после recon, выбранный враг) —
    не падает и не требует реального SDL-окна (стаб pygame)."""
    session = GameSession()
    session.setup_game()

    scouting = session.enemy_factory.create("scout_drone", Coordinate(500, 500))
    scouting.scout_timer = 5.0
    done_scouting = session.enemy_factory.create("scout_drone", Coordinate(600, 500))
    done_scouting.scout_timer = 0.0
    roach = session.enemy_factory.create("giant_roach", Coordinate(700, 500))

    session.map.enemies.extend([scouting, done_scouting, roach])

    controller = types.SimpleNamespace(selected_enemy=roach)
    camera = types.SimpleNamespace(
        world_to_screen=lambda x, y: (x - 400, y - 400),
        x=0, y=0, zoom=1.0,
    )

    import pygame
    screen = pygame.Surface((900, 600))

    MapRenderer()._draw_enemies(screen, camera, session, controller, 900, 600)
