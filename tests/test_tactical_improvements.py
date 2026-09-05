import pygame
import pytest

from src.core.camera import Camera
from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.core.settings import Settings
from src.entities.enemies import DroneWalker
from src.entities.turrets import LaserTurret
from src.enums import ArmorType, GameState, damage_reduction_for
from src.factories.tower_factory import TowerFactory
from src.save_load.serializer import apply_dict_to_session, session_to_dict
from src.ui.game_window import GameView
from src.ui.tactical_overlay import TacticalOverlay


def test_tower_status_tracks_actual_target_and_disabled_states():
    tower = LaserTurret(Coordinate(0, 0))
    target = DroneWalker(Coordinate(50, 0))
    tower.update(0.01, [target])
    assert tower.current_target is target
    assert tower.activity_reason == "reloading"
    target.health = 0
    tower.update(0.01, [target])
    assert tower.current_target is None
    assert tower.activity_reason == "out_of_range"
    tower.is_powered = False
    tower.update(0.01, [target])
    assert tower.activity_reason == "unpowered"
    tower.start_landing()
    assert tower.activity_reason == "landing"


def test_mission_requires_sector_nest_and_survival_and_survives_save():
    session = GameSession()
    session.setup_game(story=True)
    session.threat_strategies = {}
    session.elapsed_time = session.survive_duration_target
    session.update(0)
    assert session.state == GameState.PLAYING
    nest = session.map.fauna_nests[0]
    assert session.unlock_sector_at(nest.position)
    session.update(0)
    assert session.state == GameState.PLAYING
    nest.health = 0
    session.update(0)
    assert session.state == GameState.VICTORY
    restored = GameSession()
    apply_dict_to_session(restored, session_to_dict(session))
    restored.threat_strategies = {}
    assert restored.story
    assert restored.destroyed_nests_count == 1
    restored.update(0)
    assert restored.state == GameState.VICTORY


def test_mission_cannot_win_before_survival_timer():
    session = GameSession()
    session.setup_game(story=True)
    session.threat_strategies = {}
    nest = session.map.fauna_nests[0]
    session.unlock_sector_at(nest.position)
    nest.health = 0
    session.update(0)
    assert session.state == GameState.PLAYING
    session.elapsed_time = session.survive_duration_target
    session.base_health = 0
    session.update(0)
    assert session.state == GameState.GAME_OVER


def test_mission_nest_can_be_destroyed_using_a_powered_expansion():
    session = GameSession()
    session.setup_game(story=True)
    session.threat_strategies = {}
    nest = session.map.fauna_nests[0]
    assert session.unlock_sector_at(nest.position)
    for kind, x in (("pylon", 3400), ("pylon", 3800), ("laser", 4020)):
        assert session.place_turret(kind, Coordinate(x, 3000))
    tower = session.map.modules[-1]
    for _ in range(300):
        session.update(0.05)
        if not session.map.fauna_nests:
            break
    assert tower.is_powered
    assert session.destroyed_nests_count == 1
    assert not session.map.fauna_nests
    assert session.state == GameState.PLAYING


def test_actual_tower_damage_emits_attack_event(monkeypatch):
    session = GameSession()
    session.setup_game()
    tower = LaserTurret(Coordinate(3100, 3000))
    session.map.modules.append(tower)
    class Hit:
        def update(self, delta_time, targets):
            tower.health -= 10
            return False
        def collect_spawned(self):
            return []
        def landed_event_name(self):
            return None
    session.map.projectiles.append(Hit())
    events = []
    session.on_event = lambda name, **data: events.append((name, data))
    session.map.update(0)
    assert ("tower_hit", {"position": tower.position}) in events


@pytest.mark.parametrize("dx,dy", [(2000, 0), (-2000, 0), (0, 2000), (0, -2000)])
def test_offscreen_markers_follow_direction_and_stay_at_viewport_edge(dx, dy):
    camera = Camera(900, 600)
    camera.center_on(Coordinate(3000, 3000))
    viewport = pygame.Rect(22, 84, 856, 362)
    point, angle = TacticalOverlay.marker_position(
        camera, Coordinate(3000 + dx, 3000 + dy), viewport)
    assert viewport.left <= point[0] <= viewport.right
    assert viewport.top <= point[1] <= viewport.bottom
    if dx:
        assert (point[0] > viewport.centerx) == (dx > 0)
    if dy:
        assert (point[1] > viewport.centery) == (dy > 0)


def test_notifications_are_bounded_and_expire():
    overlay = TacticalOverlay()
    for i in range(12):
        overlay.handle_event("ai_module_dropped", 0, module_key="hunt_leaders")
        overlay.handle_event("tower_hit", 0, position=Coordinate(i, 0))
    assert len(overlay.drops) == 3
    assert len(overlay.attacks) == 8
    view = GameView(GameSession(), Settings())
    view._start_game(story=True)
    view.hud_renderer.tactical_overlay = overlay
    view.session.elapsed_time = 10
    view.render()
    assert not overlay.drops
    assert not overlay.attacks


def test_both_languages_render_mission_tower_and_drop():
    from src.localization.loc import loc
    view = GameView(GameSession(), Settings())
    view._start_game(story=True)
    view.controller.select_tower("laser")
    assert view.controller.active_mode.place_tower(Coordinate(3100, 3000))
    view.controller.active_mode.selected_module = view.session.map.modules[-1]
    for language in ("en", "ru"):
        loc.set_language(language)
        view._handle_game_event("ai_module_dropped", module_key="hunt_leaders")
        view.render()


def test_configured_towers_have_different_armor_advantages():
    factory = TowerFactory()
    laser = factory.create("laser", Coordinate(0, 0))
    bullet = factory.create("bullet", Coordinate(0, 0))
    mortar = factory.create("mortar", Coordinate(0, 0))
    def efficiency(tower, armor):
        return (tower.damage * tower.attack_speed / tower.cost
                * (1 - damage_reduction_for(armor, tower.damage_type)))
    assert efficiency(laser, ArmorType.HEAVY) > efficiency(bullet, ArmorType.HEAVY)
    assert efficiency(bullet, ArmorType.ENERGY_SHIELDED) > efficiency(laser, ArmorType.ENERGY_SHIELDED)
    assert mortar.range_radius > laser.range_radius > bullet.range_radius


@pytest.mark.real_assets
def test_game_view_still_loads_actual_sounds_and_sprites():
    view = GameView(GameSession(), Settings())
    assert view.sound_manager.has_sounds_for("bullet_fire")
    assert view.sprite_manager.has_sprite_for("tower_laser")
