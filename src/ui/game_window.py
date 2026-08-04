"""Окно приложения и игровой цикл."""
import pygame
import sys

from src.core.game_session import GameSession
from src.core.game_controller import GameController
from src.core.settings import (
    DISPLAY_MODE_BORDERLESS, DISPLAY_MODE_FULLSCREEN, DISPLAY_MODE_WINDOWED,
    RESOLUTIONS, Settings, VOLUME_STEP,
)
from src.enums import GameState
from src.localization.loc import loc
from src.ui.map_renderer import MapRenderer
from src.ui.hud_renderer import HudRenderer
from src.ui.game_over_screen import GameOverScreen
from src.ui.menu_screen import MenuScreen
from src.ui.pause_menu_screen import PauseMenuScreen
from src.ui.settings_screen import SettingsScreen
from src.ui.sound_manager import SoundManager
from src.ui.music_manager import MusicManager
from src.ui.sprite_manager import SpriteManager
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

    def __init__(self, session: GameSession, settings: Settings | None = None):
        """Создаёт окно и рендереры для заданной игровой сессии.
        Параметр settings позволяет тестам подставить свой объект настроек, не трогая
        settings.json в корне проекта."""
        self.session = session
        self.controller: GameController | None = None

        pygame.init()
        self.settings = settings if settings is not None else Settings.load()
        loc.set_language(self.settings.language)

        self.width, self.height = self.settings.resolution
        self.screen = None
        self._apply_display_mode()
        pygame.display.set_caption("Tower Defense - Camera & Zoom")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)
        self.small_font = pygame.font.SysFont("Arial", 14)
        self.title_font = pygame.font.SysFont("Arial", 40, bold=True)
        self.running = True

        self.menu_view = "main"
        self.pause_menu_open = False
        self.pause_view = "menu"
        self._pause_notice = ""
        self._pause_notice_timer = 0.0

        self.tower_options = [
            {"key": pygame.K_1, "type": "laser", "name": "Laser (50)", "color": (0, 255, 255)},
            {"key": pygame.K_2, "type": "bullet", "name": "Bullet (100)", "color": (255, 255, 0)},
            {"key": pygame.K_3, "type": "mortar", "name": "Mortar (200)", "color": (255, 100, 0)},
        ]

        self.hud_renderer = HudRenderer()
        self.game_over_screen = GameOverScreen()
        self.menu_screen = MenuScreen()
        self.settings_screen = SettingsScreen()
        self.pause_menu_screen = PauseMenuScreen()

        self._show_loading_screen("Loading sounds...")
        self.sound_manager = SoundManager(on_progress=self._on_sound_loading_progress)
        self.sound_manager.set_volume(self.settings.sfx_volume)
        self._show_loading_screen("Loading sprites...")
        self.sprite_manager = SpriteManager(on_progress=self._on_sprite_loading_progress)
        self._show_loading_screen("Loading music...")
        self.music_manager = MusicManager()
        self.music_manager.set_volume(self.settings.music_volume)
        self._menu_music_pending = True

        self.map_renderer = MapRenderer(self.sprite_manager)

    def _on_sound_loading_progress(self, done: int, total: int):
        """Перерисовывает экран загрузки и откачивает события после каждого загруженного звука —
        расчёт вариаций питча небыстрый, и без этого ОС считает окно зависшим на время загрузки."""
        percent = int(done / total * 100) if total else 100
        self._show_loading_screen(f"Loading sounds... {percent}%")

    def _on_sprite_loading_progress(self, done: int, total: int):
        """Перерисовывает экран загрузки и откачивает события после каждого загруженного спрайта."""
        percent = int(done / total * 100) if total else 100
        self._show_loading_screen(f"Loading sprites... {percent}%")

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
            self._pause_notice_timer = max(0.0, self._pause_notice_timer - dt)
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
            elif event.type == pygame.VIDEORESIZE and self.settings.display_mode == DISPLAY_MODE_WINDOWED:
                self._handle_resize(event.w, event.h)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._handle_escape()
            elif self.session.state == GameState.MENU:
                self._handle_menu_input(event)
            elif self.session.state == GameState.PAUSED and self.pause_menu_open:
                self._handle_pause_menu_input(event)
            elif self.controller:
                self.controller.handle_input(event)

    def _handle_escape(self):
        """ESC: из настроек — назад в меню; во время игры — открыть/закрыть меню паузы; иначе — выход."""
        state = self.session.state
        if state == GameState.MENU:
            if self.menu_view == "settings":
                self.menu_view = "main"
            else:
                self.running = False
        elif state in (GameState.PLAYING, GameState.PAUSED):
            self._toggle_pause_menu()
        else:
            self.running = False

    def _toggle_pause_menu(self):
        """Открывает меню паузы (ставя игру на паузу), возвращает из настроек в меню паузы,
        либо закрывает меню паузы и снимает игру с паузы."""
        if self.session.state == GameState.PLAYING:
            self.session.state = GameState.PAUSED
            self.pause_menu_open = True
            self.pause_view = "menu"
        elif self.pause_view == "settings":
            self.pause_view = "menu"
        elif self.pause_menu_open:
            self._resume_game()
        else:
            self.pause_menu_open = True
            self.pause_view = "menu"

    def _resume_game(self):
        """Закрывает меню паузы и снимает игру с паузы."""
        self.pause_menu_open = False
        self.pause_view = "menu"
        if self.session.state == GameState.PAUSED:
            self.session.state = GameState.PLAYING

    def _handle_pause_menu_input(self, event):
        """Обрабатывает клики по меню паузы (и по настройкам, открытым из него)."""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        if self.pause_view == "settings":
            action = self.settings_screen.handle_click(event.pos, self.width, self.height, self.settings)
            if action:
                self._apply_settings_action(action)
            return

        action = self.pause_menu_screen.handle_click(event.pos, self.width, self.height)
        self._apply_pause_action(action)

    def _apply_pause_action(self, action):
        """Применяет действие, полученное от PauseMenuScreen.handle_click."""
        if action == "resume":
            self._resume_game()
        elif action in ("save", "load"):
            self._show_pause_notice(loc.get("pause.not_implemented"))
        elif action == "settings":
            self.pause_view = "settings"
        elif action == "main_menu":
            self._exit_to_main_menu()
        elif action == "exit":
            self.running = False

    def _show_pause_notice(self, text: str):
        """Показывает временную подсказку в меню паузы (например, для заглушек сохранения/загрузки)."""
        self._pause_notice = text
        self._pause_notice_timer = 1.6

    def _exit_to_main_menu(self):
        """Прерывает текущую партию и возвращает в главное меню."""
        self.controller = None
        self.session.on_event = None
        self.session.state = GameState.MENU
        self.pause_menu_open = False
        self.pause_view = "menu"
        self.menu_view = "main"
        self.music_manager.play_category("menu")

    def _handle_resize(self, width, height):
        """Пересоздаёт поверхность экрана под новый размер окна, подстраивает камеру и сохраняет разрешение."""
        self.width = max(self.MIN_WIDTH, width)
        self.height = max(self.MIN_HEIGHT, height)
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.settings.resolution = (self.width, self.height)
        self.settings.save()
        if self.controller:
            self.controller.camera.resize(self.width, self.height)

    def _apply_display_mode(self):
        """Применяет текущий self.settings.display_mode/resolution к окну pygame."""
        if self.settings.display_mode == DISPLAY_MODE_FULLSCREEN:
            self.screen = pygame.display.set_mode(self.settings.resolution, pygame.FULLSCREEN)
        elif self.settings.display_mode == DISPLAY_MODE_BORDERLESS:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self.settings.resolution, pygame.RESIZABLE)
        self.width, self.height = self.screen.get_size()
        if self.controller:
            self.controller.camera.resize(self.width, self.height)

    def _apply_settings_action(self, action):
        """Применяет действие, полученное от SettingsScreen.handle_click, и сохраняет настройки."""
        kind, value = action
        if kind == "display_mode":
            self.settings.display_mode = value
            self._apply_display_mode()
        elif kind == "resolution":
            self._cycle_resolution(value)
            if self.settings.display_mode != DISPLAY_MODE_BORDERLESS:
                self._apply_display_mode()
        elif kind == "music_volume":
            self.settings.music_volume += value * VOLUME_STEP
            self.settings.clamp_volumes()
            self.music_manager.set_volume(self.settings.music_volume)
        elif kind == "sfx_volume":
            self.settings.sfx_volume += value * VOLUME_STEP
            self.settings.clamp_volumes()
            self.sound_manager.set_volume(self.settings.sfx_volume)
        elif kind == "language":
            self._cycle_language(value)
        elif kind == "back":
            self.menu_view = "main"
        self.settings.save()

    def _cycle_resolution(self, direction):
        """Переключает разрешение на следующее/предыдущее из списка поддерживаемых."""
        try:
            index = RESOLUTIONS.index(tuple(self.settings.resolution))
        except ValueError:
            index = -1
        self.settings.resolution = RESOLUTIONS[(index + direction) % len(RESOLUTIONS)]

    def _cycle_language(self, direction):
        """Переключает язык интерфейса на следующий/предыдущий из доступных locale-файлов."""
        languages = loc.available_languages()
        index = languages.index(self.settings.language) if self.settings.language in languages else -1
        self.settings.language = languages[(index + direction) % len(languages)]
        loc.set_language(self.settings.language)

    def _handle_menu_input(self, event):
        """Обрабатывает клики по кнопкам главного меню и экрана настроек."""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        if self.menu_view == "settings":
            action = self.settings_screen.handle_click(event.pos, self.width, self.height, self.settings)
            if action:
                self._apply_settings_action(action)
            return

        action = self.menu_screen.handle_click(event.pos, self.width, self.height)
        if action == "start":
            self._start_game()
        elif action == "settings":
            self.menu_view = "settings"
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
            if self.menu_view == "settings":
                self.settings_screen.render(self.screen, self.width, self.height,
                                             self.font, self.small_font, self.title_font, self.settings)
            else:
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

        if self.session.state == GameState.PAUSED and self.pause_menu_open:
            if self.pause_view == "settings":
                self.settings_screen.render(self.screen, self.width, self.height,
                                             self.font, self.small_font, self.title_font, self.settings)
            else:
                notice = self._pause_notice if self._pause_notice_timer > 0 else ""
                self.pause_menu_screen.render(self.screen, self.width, self.height,
                                               self.font, self.small_font, self.title_font, notice)
