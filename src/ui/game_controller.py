from typing import Optional
from src.core.game_session import GameSession
from src.entities.coordinate import Coordinate
from src.entities.turrets import LaserTurret, BulletTurret, MortarTurret


class Camera:
    """Камера — часть контроллера, управляет видом на мир"""

    def __init__(self, screen_w, screen_h, map_w=900, map_h=600):
        self.x = 0.0
        self.y = 0.0
        self.screen_w, self.screen_h = screen_w, screen_h
        self.map_w, self.map_h = map_w, map_h
        self.zoom = 1.0
        self.min_zoom, self.max_zoom = 0.3, 2.5
        self.speed = 400.0

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        vis_w = self.screen_w / self.zoom
        vis_h = self.screen_h / self.zoom
        self.x = max(0, min(self.x, self.map_w - vis_w))
        self.y = max(0, min(self.y, self.map_h - vis_h))

    def zoom_at_mouse(self, mx, my, factor):
        wx = (mx - self.screen_w / 2) / self.zoom + self.x
        wy = (my - self.screen_h / 2) / self.zoom + self.y
        new_zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * factor))
        if abs(new_zoom - self.zoom) < 0.001: return
        self.x = wx - (mx - self.screen_w / 2) / new_zoom
        self.y = wy - (my - self.screen_h / 2) / new_zoom
        self.zoom = new_zoom
        self.move(0, 0)

    def world_to_screen(self, wx, wy):
        return (wx - self.x) * self.zoom, (wy - self.y) * self.zoom

    def screen_to_world(self, sx, sy):
        return sx / self.zoom + self.x, sy / self.zoom + self.y

    def update(self, dt, keys):
        """Обновление позиции камеры (WASD)"""
        dx, dy = 0.0, 0.0
        speed = self.speed * dt
        import pygame
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy = -speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy = speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx = -speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx = speed
        if dx != 0 or dy != 0:
            self.move(dx, dy)


class GameController:
    def __init__(self, session: GameSession):
        self.session = session
        self.selected_tower_type = None
        self.selected_module = None
        self.camera = Camera(900, 600, map_w=900, map_h=600)

        if hasattr(session, 'base_position'):
            self.camera.x = session.base_position.x - 450
            self.camera.y = session.base_position.y - 300

    def update(self, dt):
        """Обновление контроллера (камера и т.д.)"""
        import pygame
        keys = pygame.key.get_pressed()
        self.camera.update(dt, keys)

    def handle_input(self, event):
        """Обработка событий ввода"""
        import pygame

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()
            self.camera.zoom_at_mouse(mx, my, 1.1 if event.y > 0 else 0.9)
            return True

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.select_tower("laser")
            elif event.key == pygame.K_2:
                self.select_tower("bullet")
            elif event.key == pygame.K_3:
                self.select_tower("mortar")
            elif event.key == pygame.K_SPACE:
                self.start_next_wave()
            elif event.key == pygame.K_u:
                self.upgrade_selected()
            elif event.key == pygame.K_p:
                self.pause_game()
            elif event.key == pygame.K_r:
                self.camera.zoom = 1.0
                if hasattr(self.session, 'base_position'):
                    self.camera.x = self.session.base_position.x - 450
                    self.camera.y = self.session.base_position.y - 300
            elif event.key == pygame.K_ESCAPE:
                return False
            return True

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                wx, wy = self.camera.screen_to_world(event.pos[0], event.pos[1])
                self.handle_click(Coordinate(wx, wy))
            elif event.button == 3:
                self.deselect()
            return True

        return False

    def select_tower(self, tower_type: str) -> bool:
        tower_classes = {"laser": LaserTurret, "bullet": BulletTurret, "mortar": MortarTurret}
        if tower_type in tower_classes:
            self.selected_tower_type = tower_classes[tower_type]
            return True
        return False

    def handle_click(self, pos: Coordinate) -> str:
        for module in self.session.map.modules:
            if pos.distance_to(module.position) < 20:
                self.selected_module = module
                return "selected"
        if self.selected_tower_type:
            return "placed" if self.place_tower(pos) else "fail"
        return "none"

    def place_tower(self, position: Coordinate) -> bool:
        if self.selected_tower_type is None: return False
        if not self._is_valid_position(position): return False
        success = self.session.place_turret(self.selected_tower_type, position)
        if success: self.selected_tower_type = None
        return success

    def upgrade_selected(self) -> bool:
        if not self.selected_module or not self.selected_module.can_upgrade(): return False
        cost = self.selected_module.get_upgrade_cost()
        if self.session.resources.spend(cost):
            self.selected_module.upgrade()
            return True
        return False

    def deselect(self):
        self.selected_module = None
        self.selected_tower_type = None

    def start_next_wave(self) -> bool:
        if self.session.wave_protocol.is_active: return False
        self.session.wave_protocol.force_start_next_wave()
        return True

    def pause_game(self):
        from src.enums import GameState
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
            "selected_tower": self.selected_tower_type.__name__ if self.selected_tower_type else None
        }

    def _is_valid_position(self, position: Coordinate) -> bool:
        if not (0 <= position.x <= 4000 and 0 <= position.y <= 4000):
            return False
        for module in self.session.map.modules:
            if position.distance_to(module.position) < 30:
                return False
        return True