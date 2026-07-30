"""Окно приложения и игровой цикл."""
import pygame
import sys

from src.core.game_session import GameSession
from src.core.game_controller import GameController
from src.enums import GameState
from src.ui.map_renderer import MapRenderer
from src.ui.hud_renderer import HudRenderer
from src.ui.game_over_screen import GameOverScreen
from src.ui.menu_screen import MenuScreen


class GameView:
    """Окно игры: инициализация pygame, игровой цикл и ввод."""

    def __init__(self, session: GameSession):
        """Создаёт окно и рендереры для заданной игровой сессии."""
        self.session = session
        self.controller: GameController | None = None

        pygame.init()
        self.width, self.height = 900, 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Tower Defense - Camera & Zoom")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.small_font = pygame.font.SysFont("Arial", 14)
        self.title_font = pygame.font.SysFont("Arial", 40, bold=True)
        self.running = True

        self.tower_options = [
            {"key": pygame.K_1, "type": "laser", "name": "Laser (50)", "color": (0, 255, 255)},
            {"key": pygame.K_2, "type": "bullet", "name": "Bullet (100)", "color": (255, 255, 0)},
            {"key": pygame.K_3, "type": "mortar", "name": "Mortar (200)", "color": (255, 100, 0)},
        ]

        self.map_renderer = MapRenderer()
        self.hud_renderer = HudRenderer()
        self.game_over_screen = GameOverScreen()
        self.menu_screen = MenuScreen()

    @property
    def camera(self):
        """Камера активного контроллера."""
        return self.controller.camera

    def run(self):
        """Запускает основной игровой цикл."""
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            if self.session.state != GameState.MENU and self.controller:
                self.controller.update(dt)
                self.session.update(dt)
            self.render()
            pygame.display.flip()
        pygame.quit()
        sys.exit()

    def handle_events(self):
        """Обрабатывает очередь событий pygame."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
            elif self.session.state == GameState.MENU:
                self._handle_menu_input(event)
            elif self.controller:
                self.controller.handle_input(event)

    def _handle_menu_input(self, event):
        """Обрабатывает клики по кнопкам главного меню."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = self.menu_screen.handle_click(event.pos, self.width, self.height)
            if action == "start":
                self._start_game()
            elif action == "exit":
                self.running = False

    def _start_game(self):
        """Настраивает новую игру и создаёт контроллер."""
        self.session.setup_game()
        self.controller = GameController(self.session)

    def render(self):
        """Рисует текущий кадр игры."""
        if self.session.state == GameState.MENU:
            self.menu_screen.render(self.screen, self.width, self.height, self.font, self.title_font)
            return

        self.screen.fill((20, 24, 28))

        self.map_renderer.render(
            self.screen, self.camera, self.session, self.controller,
            self.tower_options, self.width, self.height
        )
        self.hud_renderer.render(
            self.screen, self.camera, self.session, self.controller,
            self.tower_options, self.width, self.height, self.font, self.small_font
        )
        self.game_over_screen.render(self.screen, self.session, self.width, self.height)
