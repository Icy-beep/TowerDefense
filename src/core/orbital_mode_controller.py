from typing import TYPE_CHECKING

import pygame

from src.core.camera import Camera
from src.core.coordinate import Coordinate
from src.core.game_mode_controller import IGameModeController
from src.core.map import Map
from src.enums import GameState

if TYPE_CHECKING:
    from src.core.game_session import GameSession

_KEY_TO_TOWER_TYPE = {
    pygame.K_1: "laser",
    pygame.K_2: "bullet",
    pygame.K_3: "mortar",
    pygame.K_4: "generator",
    pygame.K_5: "pylon",
}


class OrbitalModeController(IGameModeController):
    """Свободная камера и строительство башен - RTS-режим обзора."""

    ENEMY_SELECT_RADIUS = 16

    def __init__(self, session: "GameSession", screen_w: int = 900, screen_h: int = 600):
        """Создаёт контроллер орбитального режима для сессии."""
        self.selected_tower_type = None
        self.selected_module = None
        self.selected_enemy = None
        self.dragging_camera = False
        self._last_mouse_pos = None
        self.show_power_radii = False
        self.show_tower_ranges = False
        super().__init__(session, screen_w, screen_h)

        if session.base_position is not None:
            self.camera.center_on(session.base_position)

    def _create_camera(self):
        """Создаёт камеру для орбитального режима под текущий размер окна и реальный
        размер карты сессии (а не зашитую константу - иначе камера не узнает об
        увеличенной карте и будет считать себя на маленькой). Map.DEFAULT_WIDTH/HEIGHT -
        только запасной вариант на случай, если камера создаётся до setup_game()."""
        map_w = self.session.map.width if self.session.map else Map.DEFAULT_WIDTH
        map_h = self.session.map.height if self.session.map else Map.DEFAULT_HEIGHT
        return Camera(self.screen_w, self.screen_h, map_w=map_w, map_h=map_h)

    def update(self, delta_time: float):
        """Обновляет камеру и снимает выделение с исчезнувшего врага."""
        keys = pygame.key.get_pressed()
        self.camera.update(delta_time, keys)
        if self.selected_enemy is not None and self.selected_enemy not in self.session.map.enemies:
            self.selected_enemy = None

    def handle_input(self, event) -> bool:
        """Обрабатывает событие ввода: зум, клавиши, клики, перетаскивание камеры."""
        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            self.camera.zoom_at_mouse(mx, my, 1.1 if event.y > 0 else 0.9)
            return True

        if event.type == pygame.KEYDOWN:
            if event.key in _KEY_TO_TOWER_TYPE:
                self.select_tower(_KEY_TO_TOWER_TYPE[event.key])
            elif event.key == pygame.K_u:
                self.upgrade_selected()
            elif event.key == pygame.K_p:
                self.pause_game()
            elif event.key == pygame.K_r:
                self.camera.zoom = 1.0
                if self.session.base_position is not None:
                    self.camera.center_on(self.session.base_position)
            elif event.key == pygame.K_g:
                self.toggle_power_radii()
            elif event.key == pygame.K_t:
                self.toggle_tower_ranges()
            return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            wx, wy = self.camera.screen_to_world(*event.pos)
            pos = Coordinate(wx, wy)
            if event.button == 1:
                if pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self.try_unlock_sector(pos)
                    return True
                result = self.handle_click(pos)
                if result == "none":
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
                self.camera.move((lx - mx) / self.camera.zoom, (ly - my) / self.camera.zoom)
                self._last_mouse_pos = event.pos
                return True
            return False

        return False

    def select_tower(self, tower_type: str) -> bool:
        """Выбирает тип башни для постройки."""
        if tower_type in self.session.tower_factory.available_types():
            self.selected_tower_type = tower_type
            return True
        return False

    def handle_click(self, pos: Coordinate) -> str:
        """Обрабатывает клик по карте: выбор башни, постройка, выбор врага."""
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

    def try_unlock_sector(self, pos: Coordinate) -> bool:
        """Пытается открыть за кредиты сектор под точкой (см. GameSession.unlock_sector_at).
        Отдельный метод, а не часть handle_click - обычный клик по пустому месту служит для
        перетаскивания камеры (см. handle_input), и молча тратить кредиты на любой такой
        клик внутри закрытого сектора было бы неожиданным для игрока. Вызывается по
        Ctrl+ЛКМ (см. handle_input)."""
        return self.session.unlock_sector_at(pos)

    def place_tower(self, position: Coordinate) -> bool:
        """Ставит выбранную башню в указанную точку."""
        if self.selected_tower_type is None:
            return False
        success = self.session.place_turret(self.selected_tower_type, position)
        if success:
            self.selected_tower_type = None
        return success

    def upgrade_selected(self) -> bool:
        """Улучшает выбранную башню, если хватает денег."""
        if not self.selected_module or not self.selected_module.can_upgrade():
            return False
        cost = self.selected_module.get_upgrade_cost()
        if self.session.resources.spend(cost):
            self.selected_module.upgrade()
            return True
        return False

    def toggle_power_radii(self) -> bool:
        """Переключает постоянный показ радиусов охвата энергосети (пилоны/генераторы -
        см. MapRenderer._draw_modules). Раньше их радиус было видно только у выделенной
        постройки или пока держишь ALT вместе со всеми башнями сразу - для энергосети
        отдельно от боевых башен этого не хватало (см. запрос пользователя)."""
        self.show_power_radii = not self.show_power_radii
        return self.show_power_radii

    def toggle_tower_ranges(self) -> bool:
        """Переключает постоянный показ радиусов атаки боевых башен. ALT по-прежнему
        временно показывает радиусы всех построек разом (см. MapRenderer._draw_modules) -
        это отдельная, независимая от временного ALT постоянная подсветка."""
        self.show_tower_ranges = not self.show_tower_ranges
        return self.show_tower_ranges

    def deselect(self):
        """Снимает любое текущее выделение."""
        self.selected_module = None
        self.selected_tower_type = None
        self.selected_enemy = None

    def pause_game(self):
        """Переключает игру между паузой и продолжением."""
        if self.session.state == GameState.PLAYING:
            self.session.state = GameState.PAUSED
        elif self.session.state == GameState.PAUSED:
            self.session.state = GameState.PLAYING

    def get_game_state(self) -> dict:
        """Собирает состояние игры для HUD."""
        return {
            "credits": self.session.resources.credits,
            "base_health": self.session.base_health,
            "max_base_health": self.session.max_base_health,
            "elapsed_time": self.session.elapsed_time,
            "survive_duration_target": self.session.survive_duration_target,
            "endless": self.session.endless,
            "game_state": self.session.state,
            "selected_tower": self.selected_tower_type,
            "show_power_radii": self.show_power_radii,
            "show_tower_ranges": self.show_tower_ranges,
        }

    def _is_valid_position(self, position: Coordinate) -> bool:
        """Алиас для GameView (превью размещения при наведении курсора)."""
        return self.session.map.can_place_module(position)
