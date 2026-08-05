"""Экран главного меню."""
import pygame

from src.localization.loc import loc

BUTTON_WIDTH = 260
BUTTON_HEIGHT = 60
BUTTON_GAP = 20


class MenuScreen:
    """Главное меню с кнопками "Продолжить" (если есть сохранение), "Начать игру",
    "Настройки" и "Выйти"."""

    def __init__(self):
        """Создаёт меню с пустой раскладкой кнопок."""
        self._continue_rect = (0, 0, 0, 0)
        self._start_rect = (0, 0, 0, 0)
        self._settings_rect = (0, 0, 0, 0)
        self._exit_rect = (0, 0, 0, 0)

    def _layout(self, width, height, has_continue=False):
        """Рассчитывает положение кнопок под размер окна. Кнопка "Продолжить"
        появляется первой, только если есть хоть одно сохранение (см.
        SaveManager.has_any_save)."""
        cx = width // 2
        button_count = 4 if has_continue else 3
        total_height = BUTTON_HEIGHT * button_count + BUTTON_GAP * (button_count - 1)
        top = height // 2 - total_height // 2

        y = top
        if has_continue:
            self._continue_rect = (cx - BUTTON_WIDTH // 2, y, BUTTON_WIDTH, BUTTON_HEIGHT)
            y += BUTTON_HEIGHT + BUTTON_GAP
        else:
            self._continue_rect = (0, 0, 0, 0)

        self._start_rect = (cx - BUTTON_WIDTH // 2, y, BUTTON_WIDTH, BUTTON_HEIGHT)
        y += BUTTON_HEIGHT + BUTTON_GAP
        self._settings_rect = (cx - BUTTON_WIDTH // 2, y, BUTTON_WIDTH, BUTTON_HEIGHT)
        y += BUTTON_HEIGHT + BUTTON_GAP
        self._exit_rect = (cx - BUTTON_WIDTH // 2, y, BUTTON_WIDTH, BUTTON_HEIGHT)

    def render(self, screen, width, height, font, title_font, has_continue=False):
        """Рисует экран меню."""
        self._layout(width, height, has_continue)
        screen.fill((20, 24, 28))

        title = title_font.render(loc.get("menu.title"), True, (255, 255, 255))
        tw, th = title.get_size()
        screen.blit(title, ((width - tw) // 2, height // 2 - 160))

        if has_continue:
            self._draw_button(screen, self._continue_rect, loc.get("menu.continue"), font, (60, 130, 160))
        self._draw_button(screen, self._start_rect, loc.get("menu.start"), font, (60, 160, 90))
        self._draw_button(screen, self._settings_rect, loc.get("menu.settings"), font, (60, 100, 150))
        self._draw_button(screen, self._exit_rect, loc.get("menu.exit"), font, (160, 60, 60))

    def _draw_button(self, screen, rect, text, font, color):
        """Рисует одну кнопку с подписью."""
        x, y, w, h = rect
        pygame.draw.rect(screen, color, (x, y, w, h))
        pygame.draw.rect(screen, (255, 255, 255), (x, y, w, h), 2)
        label = font.render(text, True, (255, 255, 255))
        lw, lh = label.get_size()
        screen.blit(label, (x + (w - lw) // 2, y + (h - lh) // 2))

    def handle_click(self, pos, width, height, has_continue=False) -> "str | None":
        """Определяет, по какой кнопке кликнули."""
        self._layout(width, height, has_continue)
        if has_continue and self._point_in(pos, self._continue_rect):
            return "continue"
        if self._point_in(pos, self._start_rect):
            return "start"
        if self._point_in(pos, self._settings_rect):
            return "settings"
        if self._point_in(pos, self._exit_rect):
            return "exit"
        return None

    @staticmethod
    def _point_in(pos, rect) -> bool:
        """Проверяет, попадает ли точка в прямоугольник."""
        px, py = pos
        x, y, w, h = rect
        return x <= px <= x + w and y <= py <= y + h
