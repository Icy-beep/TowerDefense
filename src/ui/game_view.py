import pygame
import sys
from src.core.game_session import GameSession
from src.entities.coordinate import Coordinate
from src.ui.game_controller import GameController
from src.entities.turrets import LaserTurret, BulletTurret, MortarTurret
from src.enums import GameState


class GameView:
    def __init__(self, session: GameSession):
        self.session = session
        self.controller = GameController(session)
        pygame.init()
        self.width, self.height = 900, 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Tower Defense OOP Project")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.small_font = pygame.font.SysFont("Arial", 14)
        self.running = True
        self.selected_tower_idx = None

        self.tower_options = [
            {"key": pygame.K_1, "class": LaserTurret, "name": "Laser (50)", "color": (0, 255, 255)},
            {"key": pygame.K_2, "class": BulletTurret, "name": "Bullet (100)", "color": (255, 255, 0)},
            {"key": pygame.K_3, "class": MortarTurret, "name": "Mortar (200)", "color": (255, 100, 0)},
        ]

    def run(self):
        self.session.setup_game()
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.session.update(dt)
            self.render()
            pygame.display.flip()
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

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
                elif event.key == pygame.K_ESCAPE:
                    self.running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    pos = Coordinate(event.pos[0], event.pos[1])
                    self.controller.handle_click(pos)
                elif event.button == 3:
                    self.controller.deselect()

    def render(self):
        self.screen.fill((20, 24, 28))
        self.draw_path()
        self.draw_enemies()
        self.draw_modules()
        self.draw_projectiles()
        self.draw_ui_overlay()
        self.draw_game_over_screen()

    def draw_path(self):
        if self.session.map.path:
            points = [(int(p.x), int(p.y)) for p in self.session.map.path]

            pygame.draw.lines(self.screen, (60, 60, 70), False, points, 40)

            for pt in points:
                pygame.draw.circle(self.screen, (60, 60, 70), pt, 20)
                
            pygame.draw.lines(self.screen, (40, 40, 50), False, points, 2)

    def draw_modules(self):
        for module in self.session.map.modules:
            color = (100, 100, 100)
            is_selected = (module == self.controller.selected_module)
            for opt in self.tower_options:
                if isinstance(module, opt["class"]):
                    color = opt["color"]
                    break

            if is_selected:
                pygame.draw.circle(self.screen, (255, 255, 255),
                                   (int(module.position.x), int(module.position.y)),
                                   int(module.range_radius) + 4, 2)

            pygame.draw.circle(self.screen, (*color[:3], 40),
                               (int(module.position.x), int(module.position.y)),
                               int(module.range_radius), 1)

            pygame.draw.circle(self.screen, color,
                               (int(module.position.x), int(module.position.y)), 14)

            for i in range(module.level):
                pygame.draw.circle(self.screen, (255, 215, 0),
                                   (int(module.position.x) - 5 + i * 5, int(module.position.y) - 20), 3)

    def draw_enemies(self):
        for enemy in self.session.map.enemies:
            hp_ratio = enemy.health / enemy.max_health
            pygame.draw.rect(self.screen, (50, 50, 50),
                             (int(enemy.position.x) - 12, int(enemy.position.y) - 18, 24, 4))
            pygame.draw.rect(self.screen, (0, 255, 0) if hp_ratio > 0.5 else (255, 50, 50),
                             (int(enemy.position.x) - 12, int(enemy.position.y) - 18, int(24 * hp_ratio), 4))
            pygame.draw.circle(self.screen, (220, 50, 50),
                               (int(enemy.position.x), int(enemy.position.y)), 10)

    def draw_projectiles(self):
        for proj in self.session.map.projectiles:
            pygame.draw.circle(self.screen, (255, 255, 200),
                               (int(proj.position.x), int(proj.position.y)), 3)

    def draw_ui_overlay(self):
        state = self.controller.get_game_state()
        y = 15
        self.screen.blit(self.font.render(f"Credits: {state['credits']}", True, (255, 215, 0)), (15, y))
        y += 30
        self.screen.blit(
            self.font.render(f"Base HP: {state['base_health']}/{state['max_base_health']}", True, (255, 255, 255)),
            (15, y))
        y += 30
        self.screen.blit(
            self.font.render(f"Wave: {state['current_wave']}/{state['total_waves']}", True, (100, 200, 255)), (15, y))
        y += 30

        if state['selected_tower']:
            self.screen.blit(self.font.render(f"Building: {state['selected_tower']}", True, (0, 255, 255)), (15, y))
            y += 25

        if hasattr(self.controller, 'get_next_wave_time'):
            time_left = self.controller.get_next_wave_time()
            if time_left > 0:
                self.screen.blit(
                    self.small_font.render(f"Next wave: {time_left:.1f}s | [SPACE] force", True, (200, 200, 200)),
                    (15, self.height - 55))
            elif state['is_wave_active']:
                self.screen.blit(self.small_font.render("Wave in progress...", True, (255, 100, 100)),
                                 (15, self.height - 55))

        hints = "[1] Laser  [2] Bullet  [3] Mortar  |  [U] Upgrade  |  [P] Pause  |  [ESC] Quit"
        self.screen.blit(self.small_font.render(hints, True, (150, 150, 150)), (15, self.height - 30))

        if self.controller.selected_module:
            mod = self.controller.selected_module
            cost = mod.get_upgrade_cost()
            if cost:
                txt = f"[U] Upgrade Lv.{mod.level + 1} | Cost: {cost}"
                col = (100, 255, 100) if state['credits'] >= cost else (255, 100, 100)
            else:
                txt = "MAX LEVEL ⭐⭐⭐"
                col = (255, 215, 0)
            self.screen.blit(self.small_font.render(txt, True, col), (15, self.height - 80))

    def draw_game_over_screen(self):
        if self.session.state == GameState.GAME_OVER:
            self._draw_overlay("DEFEAT", (255, 50, 50))
        elif self.session.state == GameState.VICTORY:
            self._draw_overlay("VICTORY", (50, 255, 50))

    def _draw_overlay(self, text, color):
        s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (0, 0))
        big_font = pygame.font.SysFont("Arial", 48, bold=True)
        txt = big_font.render(text, True, color)
        rect = txt.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(txt, rect)