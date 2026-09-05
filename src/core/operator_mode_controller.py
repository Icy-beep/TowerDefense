import pygame

from src.core.camera import Camera
from src.core.coordinate import Coordinate
from src.core.game_mode_controller import IGameModeController
from src.core.orbital_mode_controller import OrbitalModeController
from src.enums import GameState


class OperatorModeController(IGameModeController):
    selected_tower_type = None
    selected_module = None
    selected_enemy = None
    show_power_radii = False
    show_tower_ranges = False

    def _create_camera(self):
        return Camera(self.screen_w, self.screen_h,
                      map_w=self.session.map.width, map_h=self.session.map.height)

    def on_enter(self):
        self.session.operator.manual = True
        self.camera.center_on(self.session.operator.position)

    def on_exit(self):
        if self.session.operator:
            self.session.operator.leave_manual(self.session.map)

    def update(self, delta_time):
        operator = self.session.operator
        operator.stop_input()
        if self.session.state != GameState.PLAYING or not operator.is_alive():
            return
        self.camera.center_on(operator.position)
        if getattr(self, "input_blocked", False) or not pygame.key.get_focused():
            return
        keys = pygame.key.get_pressed()
        operator.move_input = (int(keys[pygame.K_d]) - int(keys[pygame.K_a]),
                               int(keys[pygame.K_s]) - int(keys[pygame.K_w]))
        mx, my = pygame.mouse.get_pos()
        operator.aim = Coordinate(*self.camera.screen_to_world(mx, my))
        operator.trigger = bool(pygame.mouse.get_pressed()[0]) and 60 < my < self.camera.screen_h - 130

    def handle_input(self, event):
        if self.session.state != GameState.PLAYING:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_e:
            self.session.operator.use_ability(self.session.map)
            return True
        return False

    def get_game_state(self):
        return OrbitalModeController.get_game_state(self)

    def _is_valid_position(self, position):
        return False
