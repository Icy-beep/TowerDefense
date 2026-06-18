import pygame
import sys
from src.core.game_session import GameSession
from src.entities.coordinate import Coordinate
from src.ui.game_controller import GameController
from src.entities.turrets import LaserTurret, BulletTurret, MortarTurret
from src.enums import GameState


class Camera:
    """Камера с поддержкой плавного зума к курсору"""

    def __init__(self, width, height):
        self.x = 0.0
        self.y = 0.0
        self.width = width
        self.height = height
        self.map_width = 4000
        self.map_height = 4000
        self.zoom = 1.0
        self.min_zoom = 0.3
        self.max_zoom = 2.5

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        self.x = max(0, min(self.x, self.map_width - self.width))
        self.y = max(0, min(self.y, self.map_height - self.height))

    def zoom_at_mouse(self, mouse_x, mouse_y, zoom_factor):
        world_x = (mouse_x - self.width / 2) / self.zoom + self.x
        world_y = (mouse_y - self.height / 2) / self.zoom + self.y
        new_zoom = self.zoom * zoom_factor
        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))
        if abs(new_zoom - self.zoom) < 0.001:
            return
        self.x = world_x - (mouse_x - self.width / 2) / new_zoom
        self.y = world_y - (mouse_y - self.height / 2) / new_zoom
        self.zoom = new_zoom
        self.move(0, 0)

    def world_to_screen(self, wx, wy):
        sx = (wx - self.x) * self.zoom
        sy = (wy - self.y) * self.zoom
        return sx, sy

    def screen_to_world(self, sx, sy):
        wx = sx / self.zoom + self.x
        wy = sy / self.zoom + self.y
        return wx, wy


class GameView:
    def __init__(self, session: GameSession):
        self.session = session
        self.controller = GameController(session)
        pygame.init()
        self.width, self.height = 900, 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Tower Defense - Camera & Zoom")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.small_font = pygame.font.SysFont("Arial", 14)
        self.running = True

        self.camera = Camera(self.width, self.height)
        self.camera_speed = 400.0

        self.tower_options = [
            {"key": pygame.K_1, "class": LaserTurret, "name": "Laser (50)", "color": (0, 255, 255)},
            {"key": pygame.K_2, "class": BulletTurret, "name": "Bullet (100)", "color": (255, 255, 0)},
            {"key": pygame.K_3, "class": MortarTurret, "name": "Mortar (200)", "color": (255, 100, 0)},
        ]

    def run(self):
        self.session.setup_game()
        if hasattr(self.session, 'base_position'):
            self.camera.x = self.session.base_position.x - self.width // 2
            self.camera.y = self.session.base_position.y - self.height // 2

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
                mouse_x, mouse_y = pygame.mouse.get_pos()
                zoom_factor = 1.1 if event.y > 0 else 0.9
                self.camera.zoom_at_mouse(mouse_x, mouse_y, zoom_factor)

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
                    if hasattr(self.session, 'base_position'):
                        self.camera.x = self.session.base_position.x - self.width // 2
                        self.camera.y = self.session.base_position.y - self.height // 2
                elif event.key == pygame.K_ESCAPE:
                    self.running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    wx, wy = self.camera.screen_to_world(event.pos[0], event.pos[1])
                    pos = Coordinate(wx, wy)
                    self.controller.handle_click(pos)
                elif event.button == 3:
                    self.controller.deselect()

    def update_camera(self, dt):
        """Непрерывное движение камеры (WASD)"""
        keys = pygame.key.get_pressed()
        move_speed = self.camera_speed * dt

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.camera.move(-move_speed, 0)
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.camera.move(move_speed, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.camera.move(0, -move_speed)
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.camera.move(0, move_speed)

    def render(self):
        self.screen.fill((20, 24, 28))

        border_rect = pygame.Rect(
            -self.camera.x * self.camera.zoom,
            -self.camera.y * self.camera.zoom,
            4000 * self.camera.zoom,
            4000 * self.camera.zoom
        )
        pygame.draw.rect(self.screen, (50, 50, 50), border_rect, 3)

        self.draw_path()
        self.draw_base()
        self.draw_modules()
        self.draw_enemies()
        self.draw_projectiles()

        self.draw_placement_preview()

        self.draw_ui_overlay()
        self.draw_game_over_screen()

    def draw_placement_preview(self):
        """Показывает радиус башни под курсором при выборе"""
        if not self.controller.selected_tower_type:
            return

        mouse_x, mouse_y = pygame.mouse.get_pos()
        wx, wy = self.camera.screen_to_world(mouse_x, mouse_y)
        pos = Coordinate(wx, wy)

        tower_range = 100
        tower_color = (255, 255, 255)
        if self.controller.selected_tower_type == LaserTurret:
            tower_range, tower_color = 120, (0, 255, 255)
        elif self.controller.selected_tower_type == BulletTurret:
            tower_range, tower_color = 150, (255, 255, 0)
        elif self.controller.selected_tower_type == MortarTurret:
            tower_range, tower_color = 200, (255, 100, 0)

        valid = self.controller._is_valid_position(pos)

        screen_radius = int(tower_range * self.camera.zoom)
        alpha_color = (*tower_color, 60 if valid else 30)

        preview_surf = pygame.Surface((screen_radius * 2, screen_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(preview_surf, alpha_color, (screen_radius, screen_radius), screen_radius, 2)
        self.screen.blit(preview_surf, (mouse_x - screen_radius, mouse_y - screen_radius))

        marker_color = (0, 255, 0) if valid else (255, 0, 0)
        pygame.draw.circle(self.screen, marker_color, (mouse_x, mouse_y), 6)
        pygame.draw.circle(self.screen, (255, 255, 255), (mouse_x, mouse_y), 6, 2)

    def draw_base(self):
        if hasattr(self.session, 'base_position'):
            sx, sy = self.camera.world_to_screen(
                self.session.base_position.x,
                self.session.base_position.y
            )
            pygame.draw.circle(self.screen, (255, 50, 50), (int(sx), int(sy)), 25)
            pygame.draw.circle(self.screen, (255, 200, 200), (int(sx), int(sy)), 30, 3)
            hp_ratio = self.session.base_health / self.session.max_base_health
            pygame.draw.rect(self.screen, (50, 50, 50), (int(sx) - 20, int(sy) - 40, 40, 6))
            pygame.draw.rect(self.screen, (0, 255, 0) if hp_ratio > 0.5 else (255, 50, 50),
                             (int(sx) - 20, int(sy) - 40, int(40 * hp_ratio), 6))

    def draw_path(self):
        if hasattr(self.session.map, 'path') and self.session.map.path:
            points = [self.camera.world_to_screen(p.x, p.y) for p in self.session.map.path]
            pygame.draw.lines(self.screen, (60, 60, 70), False, points, 40)
            pygame.draw.lines(self.screen, (40, 40, 50), False, points, 2)

    def draw_modules(self):
        for module in self.session.map.modules:
            color = (100, 100, 100)
            is_selected = (module == self.controller.selected_module)
            for opt in self.tower_options:
                if isinstance(module, opt["class"]):
                    color = opt["color"]
                    break

            sx, sy = self.camera.world_to_screen(module.position.x, module.position.y)

            if is_selected:
                pygame.draw.circle(self.screen, (255, 255, 255),
                                   (int(sx), int(sy)), int(module.range_radius * self.camera.zoom) + 5, 2)

            pygame.draw.circle(self.screen, (*color[:3], 40),
                               (int(sx), int(sy)), int(module.range_radius * self.camera.zoom), 1)
            pygame.draw.circle(self.screen, color, (int(sx), int(sy)), int(14 * self.camera.zoom))

            for i in range(module.level):
                pygame.draw.circle(self.screen, (255, 215, 0),
                                   (int(sx) - 6 + i * 6, int(sy) - 20), 3)

    def draw_enemies(self):
        for enemy in self.session.map.enemies:
            sx, sy = self.camera.world_to_screen(enemy.position.x, enemy.position.y)
            if -50 < sx < self.width + 50 and -50 < sy < self.height + 50:
                hp_ratio = enemy.health / enemy.max_health
                pygame.draw.rect(self.screen, (50, 50, 50),
                                 (int(sx) - 12, int(sy) - 18, 24, 4))
                pygame.draw.rect(self.screen, (0, 255, 0) if hp_ratio > 0.5 else (255, 50, 50),
                                 (int(sx) - 12, int(sy) - 18, int(24 * hp_ratio), 4))
                pygame.draw.circle(self.screen, (220, 50, 50), (int(sx), int(sy)), 10)

    def draw_projectiles(self):
        for proj in self.session.map.projectiles:
            sx, sy = self.camera.world_to_screen(proj.position.x, proj.position.y)
            pygame.draw.circle(self.screen, (255, 255, 200), (int(sx), int(sy)), 3)

    def draw_ui_overlay(self):
        state = self.controller.get_game_state()
        alpha = 170
        pad = 10

        surf1 = pygame.Surface((250, 100), pygame.SRCALPHA)
        surf1.fill((20, 25, 35, alpha))
        self.screen.blit(surf1, (pad, pad))

        self.screen.blit(self.font.render(f"Деньги: {state['credits']}", True, (255, 215, 0)), (pad + 10, pad + 10))
        self.screen.blit(
            self.font.render(f"Целостность базы: {state['base_health']}/{state['max_base_health']}", True, (255, 100, 100)),
            (pad + 10, pad + 40))
        self.screen.blit(
            self.font.render(f"Волна: {state['current_wave']}/{state['total_waves']}", True, (100, 200, 255)),
            (pad + 10, pad + 70))

        surf2 = pygame.Surface((300, 120), pygame.SRCALPHA)
        surf2.fill((20, 25, 35, alpha))
        self.screen.blit(surf2, (pad, self.height - 130))

        self.screen.blit(self.small_font.render(
            f"Позиция камеры: {int(self.camera.x)}, {int(self.camera.y)} | Зум: {int(self.camera.zoom * 100)}%", True,
            (180, 180, 180)), (pad + 10, self.height - 120))
        self.screen.blit(self.small_font.render("WASD: Ходить | SCROLL: Зум | R: Камеру на базу", True, (150, 150, 150)),
                         (pad + 10, self.height - 100))
        self.screen.blit(self.small_font.render("1-3: Выбрать башню | SPACE: Начать волну", True, (150, 150, 150)),
                         (pad + 10, self.height - 80))
        self.screen.blit(self.small_font.render("ЛКМ: Поставить/Выбрать | ПКМ: Отменить выбор", True, (150, 150, 150)),
                         (pad + 10, self.height - 60))
        self.screen.blit(self.small_font.render("U: Улучшить башню | P: Пауза | ESC: Закрыть игру", True, (150, 150, 150)),
                         (pad + 10, self.height - 40))
        info_lines = []
        if state['selected_tower']:
            info_lines.append(f"Строить: {state['selected_tower']}")
            info_lines.append("ЛКМ: Поставить | ПКМ: Отмена")
        elif self.controller.selected_module:
            mod = self.controller.selected_module
            info_lines.append(f"Уровень башни{mod.level} / {mod.max_level}")
            if mod.can_upgrade():
                cost = mod.get_upgrade_cost()
                can_afford = state['credits'] >= cost
                info_lines.append(f"Улучшить: {cost} cr {'ДА' if can_afford else 'НЕТ'}")
            else:
                info_lines.append("Макс. уровень")
        else:
            info_lines.append("Ничего не выбрано")

        w3 = max(len(line) * 8 for line in info_lines) + 40
        h3 = len(info_lines) * 22 + 25
        surf3 = pygame.Surface((w3, h3), pygame.SRCALPHA)
        surf3.fill((20, 25, 35, alpha))
        x3 = (self.width - w3) // 2
        y3 = self.height - h3 - 10
        self.screen.blit(surf3, (x3, y3))

        for i, line in enumerate(info_lines):
            col = (255, 255, 255)
            if "НЕТ" in line:
                col = (255, 100, 100)
            elif "ДА" in line:
                col = (100, 255, 100)
            elif "МАКСИМУМ" in line:
                col = (255, 215, 0)
            self.screen.blit(self.small_font.render(line, True, col), (x3 + 10, y3 + 10 + i * 22))

    def draw_game_over_screen(self):
        if self.session.state == GameState.GAME_OVER:
            self._draw_overlay("ПОБЕДА", (255, 50, 50))
        elif self.session.state == GameState.VICTORY:
            self._draw_overlay("ПОРАЖЕНИЕ", (50, 255, 50))

    def _draw_overlay(self, text, color):
        s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (0, 0))
        big_font = pygame.font.SysFont("Arial", 48, bold=True)
        txt = big_font.render(text, True, color)
        self.screen.blit(txt, txt.get_rect(center=(self.width // 2, self.height // 2)))