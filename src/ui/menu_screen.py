"""Экран главного меню."""
import pygame

from src.localization.loc import loc

BUTTON_WIDTH = 260
BUTTON_HEIGHT = 60


class MenuScreen:
    """Главное меню с кнопками "Начать игру" и "Выйти"."""

    def __init__(self):
        """Создаёт меню с пустой раскладкой кнопок."""
        self._start_rect = (0, 0, 0, 0)
        self._exit_rect = (0, 0, 0, 0)

    def _layout(self, width, height):
        """Рассчитывает положение кнопок под размер окна."""
        cx = width // 2
        self._start_rect = (cx - BUTTON_WIDTH // 2, height // 2 - BUTTON_HEIGHT - 10,
                             BUTTON_WIDTH, BUTTON_HEIGHT)
        self._exit_rect = (cx - BUTTON_WIDTH // 2, height // 2 + 10,
                            BUTTON_WIDTH, BUTTON_HEIGHT)

    def render(self, screen, width, height, font, title_font):
        """Рисует экран меню."""
        self._layout(width, height)
        screen.fill((20, 24, 28))

        title = title_font.render(loc.get("menu.title"), True, (255, 255, 255))
        tw, th = title.get_size()
        screen.blit(title, ((width - tw) // 2, height // 2 - 160))

        self._draw_button(screen, self._start_rect, loc.get("menu.start"), font, (60, 160, 90))
        self._draw_button(screen, self._exit_rect, loc.get("menu.exit"), font, (160, 60, 60))

    def _draw_button(self, screen, rect, text, font, color):
        """Рисует одну кнопку с подписью."""
        x, y, w, h = rect
        pygame.draw.rect(screen, color, (x, y, w, h))
        pygame.draw.rect(screen, (255, 255, 255), (x, y, w, h), 2)
        label = font.render(text, True, (255, 255, 255))
        lw, lh = label.get_size()
        screen.blit(label, (x + (w - lw) // 2, y + (h - lh) // 2))

    def handle_click(self, pos, width, height) -> str | None:
        """Определяет, по какой кнопке кликнули."""
        self._layout(width, height)
        if self._point_in(pos, self._start_rect):
            return "start"
        if self._point_in(pos, self._exit_rect):
            return "exit"
        return None

    @staticmethod
    def _point_in(pos, rect) -> bool:
        """Проверяет, попадает ли точка в прямоугольник."""
        px, py = pos
        x, y, w, h = rect
        return x <= px <= x + w and y <= py <= y + h
