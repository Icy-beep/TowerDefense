import pygame
import sys
from src.core.game_session import GameSession
from src.entities.coordinate import Coordinate
from src.ui.game_controller import GameController
from src.entities.turrets import LaserTurret, BulletTurret, MortarTurret
from src.enums import GameState

class Camera:
    def __init__(self, width, height):
        self.x = 0.0
        self.y = 0.0
        self.width, self.height = width, height
        self.map_width, self.map_height = 4000, 4000
        self.zoom = 1.0
        self.min_zoom, self.max_zoom = 0.3, 2.5

    def move(self, dx, dy):
        self.x += dx;
        self.y += dy
        self.x = max(0, min(self.x, self.map_width - self.width))
        self.y = max(0, min(self.y, self.map_height - self.height))

    def zoom_at_mouse(self, mx, my, factor):
        wx = (mx - self.width / 2) / self.zoom + self.x
        wy = (my - self.height / 2) / self.zoom + self.y
        new_z = max(self.min_zoom, min(self.max_zoom, self.zoom * factor))
        if abs(new_z - self.zoom) < 0.001: return
        self.x = wx - (mx - self.width / 2) / new_z
        self.y = wy - (my - self.height / 2) / new_z
        self.zoom = new_z
        self.move(0, 0)

    def world_to_screen(self, wx, wy):
        return (wx - self.x) * self.zoom, (wy - self.y) * self.zoom

    def screen_to_world(self, sx, sy):
        return sx / self.zoom + self.x, sy / self.zoom + self.y


class GameView:
    def __init__(self, session: GameSession):
        self.session = session
        self.controller = GameController(session)
        pygame.init()
        self.width, self.height = 900, 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Tower Defense - A* Pathfinding")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.small_font = pygame.font.SysFont("Arial", 14)
        self.running = True

        self.camera = Camera(self.width, self.height)
        self.camera_speed = 400.0

        if hasattr(session, 'base_position'):
            self.camera.x = session.base_position.x - self.width // 2
            self.camera.y = session.base_position.y - self.height // 2

    def run(self):
        self.session.setup_game()
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update_camera(dt)
            self.session.update(dt)
            self.render()
            pygame.display.flip()
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                self.camera.zoom_at_mouse(mx, my, 1.1 if event.y > 0 else 0.9)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    self.controller.select_tower("laser")
                elif event.key == pygame.K_2:
                    self.controller.select_tower("bullet")
                elif event.key == pygame.K_3:
                    self.controller.select_tower("mortar")
                elif event.key == pygame.K_SPACE:
                    self.controller.start_next_wave()
                elif event.key == pygame.K_u:
                    self.controller.upgrade_selected()
                elif event.key == pygame.K_p:
                    self.controller.pause_game()
                elif event.key == pygame.K_r:
                    self.camera.zoom = 1.0
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    wx, wy = self.camera.screen_to_world(event.pos[0], event.pos[1])
                    self.controller.handle_click(Coordinate(wx, wy))
                elif event.button == 3:
                    self.controller.deselect()

    def update_camera(self, dt):
        keys = pygame.key.get_pressed()
        spd = self.camera_speed * dt
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: self.camera.move(-spd, 0)
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.camera.move(spd, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]: self.camera.move(0, -spd)
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: self.camera.move(0, spd)

    def render(self):
        self.screen.fill((20, 24, 28))

        rect = pygame.Rect(-self.camera.x * self.camera.zoom, -self.camera.y * self.camera.zoom,
                           4000 * self.camera.zoom, 4000 * self.camera.zoom)
        pygame.draw.rect(self.screen, (50, 50, 50), rect, 3)

        self.draw_base()
        self.draw_modules()
        self.draw_enemies()
        self.draw_projectiles()
        self.draw_ui_overlay()
        self.draw_game_over_screen()

    def draw_base(self):
        if hasattr(self.session, 'base_position'):
            sx, sy = self.camera.world_to_screen(self.session.base_position.x, self.session.base_position.y)
            pygame.draw.circle(self.screen, (255, 50, 50), (int(sx), int(sy)), 25)
            pygame.draw.circle(self.screen, (255, 200, 200), (int(sx), int(sy)), 30, 3)
            hp = self.session.base_health / self.session.max_base_health
            pygame.draw.rect(self.screen, (0, 255, 0), (int(sx) - 20, int(sy) - 40, 40 * hp, 6))

    def draw_modules(self):
        for module in self.session.map.modules:
            color = (100, 100, 100)
            is_sel = (module == self.controller.selected_module)
            if isinstance(module, LaserTurret):
                color = (0, 255, 255)
            elif isinstance(module, BulletTurret):
                color = (255, 255, 0)
            elif isinstance(module, MortarTurret):
                color = (255, 100, 0)

            sx, sy = self.camera.world_to_screen(module.position.x, module.position.y)

            if is_sel:
                pygame.draw.circle(self.screen, (255, 255, 255), (int(sx), int(sy)),
                                   int(module.range_radius * self.camera.zoom) + 5, 2)

            pygame.draw.circle(self.screen, (*color, 40), (int(sx), int(sy)),
                               int(module.range_radius * self.camera.zoom), 1)
            pygame.draw.circle(self.screen, color, (int(sx), int(sy)), 14 * self.camera.zoom)

    def draw_enemies(self):
        for enemy in self.session.map.enemies:
            sx, sy = self.camera.world_to_screen(enemy.position.x, enemy.position.y)
            if -50 < sx < self.width + 50 and -50 < sy < self.height + 50:
                hp = enemy.health / enemy.max_health
                pygame.draw.rect(self.screen, (50, 50, 50), (int(sx) - 12, int(sy) - 18, 24, 4))
                pygame.draw.rect(self.screen, (0, 255, 0) if hp > 0.5 else (255, 50, 50),
                                 (int(sx) - 12, int(sy) - 18, int(24 * hp), 4))
                pygame.draw.circle(self.screen, (220, 50, 50), (int(sx), int(sy)), 10)

    def draw_projectiles(self):
        for proj in self.session.map.projectiles:
            sx, sy = self.camera.world_to_screen(proj.position.x, proj.position.y)
            pygame.draw.circle(self.screen, (255, 255, 200), (int(sx), int(sy)), 3)

    def draw_ui_overlay(self):
        state = self.controller.get_game_state()
        self.screen.blit(self.font.render(f"Credits: {state['credits']}", True, (255, 215, 0)), (15, 15))
        t = self.controller.get_next_wave_time()
        self.screen.blit(self.small_font.render(f"Next: {t:.1f}s", True, (200, 200, 200)), (15, self.height - 30))

    def draw_game_over_screen(self):
        if self.session.state == GameState.GAME_OVER:
            self._overlay("DEFEAT", (255, 50, 50))
        elif self.session.state == GameState.VICTORY:
            self._overlay("VICTORY", (50, 255, 50))

    def _overlay(self, text, col):
        s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (0, 0))
        txt = pygame.font.SysFont("Arial", 48, bold=True).render(text, True, col)
        self.screen.blit(txt, txt.get_rect(center=(self.width // 2, self.height // 2)))