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
from src.ui.sound_manager import SoundManager
from src.ui.music_manager import MusicManager
from src.systems.spatial_audio import volume_for_position


class GameView:
    """Окно игры: инициализация pygame, игровой цикл и ввод."""

    MIN_WIDTH = 640
    MIN_HEIGHT = 480
    SOUND_EVENTS = {
        "tower_placed": "tower_placed",
        "base_hit": "base_hit",
        "mortar_explosion": "mortar_explosion",
        "laser_hit": "laser_hit",
        "bullet_hit": "bullet_hit",
        "victory": "victory",
        "defeat": "defeat",
    }
    SOUND_COOLDOWNS = {
        "base_hit": 7.0,
        "laser_hit": 0.08,
        "bullet_hit": 0.06,
        "mortar_explosion": 0.15,
    }
    SOUND_VOLUME_MULTIPLIERS = {
        "laser_hit": 0.6,
        "bullet_hit": 0.6,
        "mortar_explosion": 0.85,
    }
    ALWAYS_AUDIBLE_EVENTS = {"base_hit"}

    def __init__(self, session: GameSession):
        """Создаёт окно и рендереры для заданной игровой сессии."""
        self.session = session
        self.controller: GameController | None = None

        pygame.init()
        self.width, self.height = 900, 600
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
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

        self._show_loading_screen("Loading sounds...")
        self.sound_manager = SoundManager(on_progress=self._on_sound_loading_progress)
        self._show_loading_screen("Loading music...")
        self.music_manager = MusicManager()
        self._menu_music_pending = True

    def _on_sound_loading_progress(self, done: int, total: int):
        """Перерисовывает экран загрузки и откачивает события после каждого загруженного звука —
        расчёт вариаций питча небыстрый, и без этого ОС считает окно зависшим на время загрузки."""
        percent = int(done / total * 100) if total else 100
        self._show_loading_screen(f"Loading sounds... {percent}%")

    def _show_loading_screen(self, text_line: str = "Loading..."):
        """Рисует кадр загрузки с текстом и откачивает очередь событий — вызывается регулярно
        во время долгой загрузки ассетов, иначе ОС считает не обновляющееся окно зависшим."""
        self.screen.fill((20, 24, 28))
        text = self.title_font.render(text_line, True, (255, 255, 255))
        rect = text.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(text, rect)
        pygame.display.flip()
        pygame.event.pump()

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
                self.sound_manager.update(dt)
            self.render()
            pygame.display.flip()
            if self._menu_music_pending:
                self.music_manager.play_category("menu")
                self._menu_music_pending = False
        pygame.quit()
        sys.exit()

    def handle_events(self):
        """Обрабатывает очередь событий pygame."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self._handle_resize(event.w, event.h)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
            elif self.session.state == GameState.MENU:
                self._handle_menu_input(event)
            elif self.controller:
                self.controller.handle_input(event)

    def _handle_resize(self, width, height):
        """Пересоздаёт поверхность экрана под новый размер окна и подстраивает камеру."""
        self.width = max(self.MIN_WIDTH, width)
        self.height = max(self.MIN_HEIGHT, height)
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        if self.controller:
            self.controller.camera.resize(self.width, self.height)

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
        self.session.on_event = self._handle_game_event
        self.controller = GameController(self.session, self.width, self.height)
        self.music_manager.play_category("gameplay")

    def _handle_game_event(self, event_name, **data):
        """Проигрывает звук, привязанный к игровому событию, приглушая его вне вида камеры и с учётом кулдауна."""
        position = data.get("position")
        if event_name in self.ALWAYS_AUDIBLE_EVENTS:
            volume_multiplier = 1.0
        else:
            volume_multiplier = volume_for_position(self.camera, position) if (position and self.controller) else 1.0
        volume_multiplier *= self.SOUND_VOLUME_MULTIPLIERS.get(event_name, 1.0)
        cooldown = self.SOUND_COOLDOWNS.get(event_name, 0.0)

        if event_name == "tower_fired":
            self.sound_manager.play(f"{data.get('tower_type')}_fire", volume_multiplier)
        elif event_name in self.SOUND_EVENTS:
            self.sound_manager.play(self.SOUND_EVENTS[event_name], volume_multiplier, cooldown=cooldown)

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
