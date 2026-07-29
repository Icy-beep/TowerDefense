from typing import TYPE_CHECKING
import pygame

from src.core.game_mode_controller import IGameModeController
from src.core.camera import Camera
from src.core.coordinate import Coordinate
from src.enums import GameState

if TYPE_CHECKING:
    from src.core.game_session import GameSession

_KEY_TO_TOWER_TYPE = {
    pygame.K_1: "laser",
    pygame.K_2: "bullet",
    pygame.K_3: "mortar",
}


class OrbitalModeController(IGameModeController):
    """Свободная камера, строительство башен, управление волнами."""

    ENEMY_SELECT_RADIUS = 16

    def __init__(self, session: "GameSession"):
        self.selected_tower_type = None
        self.selected_module = None
        self.selected_enemy = None
        self.dragging_camera = False
        self._last_mouse_pos = None
        super().__init__(session)

        if hasattr(session, "base_position"):
            self.camera.center_on(session.base_position)

    def _create_camera(self):
        return Camera(900, 600, map_w=4000, map_h=4000)

    def update(self, delta_time: float):
        keys = pygame.key.get_pressed()
        self.camera.update(delta_time, keys)
        if self.selected_enemy is not None and self.selected_enemy not in self.session.map.enemies:
            # Враг умер/дошёл до базы — панель выбора не должна показывать
            # застывшую информацию о цели, которой больше нет на поле.
            self.selected_enemy = None

    def handle_input(self, event) -> bool:
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            self.camera.zoom_at_mouse(mx, my, 1.1 if event.y > 0 else 0.9)
            return True

        if event.type == pygame.KEYDOWN:
            if event.key in _KEY_TO_TOWER_TYPE:
                self.select_tower(_KEY_TO_TOWER_TYPE[event.key])
            elif event.key == pygame.K_SPACE:
                self.start_next_wave()
            elif event.key == pygame.K_u:
                self.upgrade_selected()
            elif event.key == pygame.K_p:
                self.pause_game()
            elif event.key == pygame.K_r:
                self.camera.zoom = 1.0
                if hasattr(self.session, "base_position"):
                    self.camera.center_on(self.session.base_position)
            return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            wx, wy = self.camera.screen_to_world(*event.pos)
            pos = Coordinate(wx, wy)
            if event.button == 1:
                result = self.handle_click(pos)
                if result == "none":
                    # Клик не попал по башне и постройка не выбрана —
                    # начинаем перетаскивание камеры вместо холостого клика.
                    self.dragging_camera = True
                    self._last_mouse_pos = event.pos
            elif event.button == 3:
                self.deselect()
            return True

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging_camera = False
                self._last_mouse_pos = None
            return True

        if event.type == pygame.MOUSEMOTION:
            if self.dragging_camera and self._last_mouse_pos is not None:
                mx, my = event.pos
                lx, ly = self._last_mouse_pos
                # Тащим мышью вправо/вниз -> камера смещается влево/вверх,
                # чтобы поле "ехало" за курсором, как при перетаскивании.
                self.camera.move((lx - mx) / self.camera.zoom, (ly - my) / self.camera.zoom)
                self._last_mouse_pos = event.pos
                return True
            return False

        return False

    def select_tower(self, tower_type: str) -> bool:
        """tower_type — строка ("laser"/"bullet"/"mortar"), сверяется
        с реестром живой TowerFactory, а не с захардкоженным словарём —
        новая башня, зарегистрированная в фабрике, тут же станет доступна."""
        if tower_type in self.session.tower_factory.available_types():
            self.selected_tower_type = tower_type
            return True
        return False

    def handle_click(self, pos: Coordinate) -> str:
        for module in self.session.map.modules:
            if pos.distance_to(module.position) < 20:
                self.selected_module = module
                self.selected_enemy = None
                return "selected"
        if self.selected_tower_type:
            return "placed" if self.place_tower(pos) else "fail"
        for enemy in self.session.map.enemies:
            if pos.distance_to(enemy.position) < self.ENEMY_SELECT_RADIUS:
                self.selected_enemy = enemy
                self.selected_module = None
                return "selected_enemy"
        return "none"

    def place_tower(self, position: Coordinate) -> bool:
        if self.selected_tower_type is None:
            return False
        success = self.session.place_turret(self.selected_tower_type, position)
        if success:
            self.selected_tower_type = None
        return success

    def upgrade_selected(self) -> bool:
        if not self.selected_module or not self.selected_module.can_upgrade():
            return False
        cost = self.selected_module.get_upgrade_cost()
        if self.session.resources.spend(cost):
            self.selected_module.upgrade()
            return True
        return False

    def deselect(self):
        self.selected_module = None
        self.selected_tower_type = None
        self.selected_enemy = None

    def start_next_wave(self) -> bool:
        if self.session.wave_protocol.is_active:
            return False
        self.session.wave_protocol.force_start_next_wave()
        return True

    def pause_game(self):
        if self.session.state == GameState.PLAYING:
            self.session.state = GameState.PAUSED
        elif self.session.state == GameState.PAUSED:
            self.session.state = GameState.PLAYING

    def get_next_wave_time(self) -> float:
        return self.session.wave_protocol.get_time_until_next_wave()

    def get_game_state(self) -> dict:
        return {
            "credits": self.session.resources.credits,
            "base_health": self.session.base_health,
            "max_base_health": self.session.max_base_health,
            "current_wave": self.session.wave_protocol.current_wave_idx + 1,
            "total_waves": len(self.session.wave_protocol.waves),
            "game_state": self.session.state,
            "is_wave_active": self.session.wave_protocol.is_active,
            "selected_tower": self.selected_tower_type,
        }

    def _is_valid_position(self, position: Coordinate) -> bool:
        """Алиас для GameView (превью размещения при наведении курсора)."""
        return self.session.map.can_place_module(position)
