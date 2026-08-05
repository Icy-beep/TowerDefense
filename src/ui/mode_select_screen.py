"""Экран выбора режима после кнопки "Новая игра" в главном меню."""
import pygame

from src.localization.loc import loc

BUTTON_WIDTH = 260
BUTTON_HEIGHT = 60
BUTTON_GAP = 20


class ModeSelectScreen:
    """Выбор режима новой игры: бесконечный (играбелен) или сюжетный (заглушка,
    пока не реализован - см. ответ пользователя на уточняющий вопрос при
    добавлении этого экрана: серая неактивная кнопка с подписью "Скоро")."""

    def __init__(self):
        """Создаёт экран с пустой раскладкой кнопок."""
        self._endless_rect = (0, 0, 0, 0)
        self._story_rect = (0, 0, 0, 0)
        self._back_rect = (0, 0, 0, 0)

    def _layout(self, width, height):
        """Рассчитывает положение кнопок под размер окна."""
        cx = width // 2
        top = height // 2 - (BUTTON_HEIGHT * 3 + BUTTON_GAP * 2) // 2
        self._endless_rect = (cx - BUTTON_WIDTH // 2, top, BUTTON_WIDTH, BUTTON_HEIGHT)
        self._story_rect = (cx - BUTTON_WIDTH // 2, top + BUTTON_HEIGHT + BUTTON_GAP,
                             BUTTON_WIDTH, BUTTON_HEIGHT)
        self._back_rect = (cx - BUTTON_WIDTH // 2, top + (BUTTON_HEIGHT + BUTTON_GAP) * 2,
                            BUTTON_WIDTH, BUTTON_HEIGHT)

    def render(self, screen, width, height, font, title_font):
        """Рисует экран выбора режима."""
        self._layout(width, height)
        screen.fill((20, 24, 28))

        title = title_font.render(loc.get("menu.mode_select_title"), True, (255, 255, 255))
        tw, th = title.get_size()
        screen.blit(title, ((width - tw) // 2, height // 2 - 160))

        self._draw_button(screen, self._endless_rect, loc.get("menu.mode_endless"), font, (60, 160, 90))
        self._draw_button(screen, self._story_rect, loc.get("menu.mode_story"), font, (70, 70, 75))
        self._draw_button(screen, self._back_rect, loc.get("menu.back"), font, (100, 100, 100))

    def _draw_button(self, screen, rect, text, font, color):
        """Рисует одну кнопку с подписью."""
        x, y, w, h = rect
        pygame.draw.rect(screen, color, (x, y, w, h))
        pygame.draw.rect(screen, (255, 255, 255), (x, y, w, h), 2)
        label = font.render(text, True, (255, 255, 255))
        lw, lh = label.get_size()
        screen.blit(label, (x + (w - lw) // 2, y + (h - lh) // 2))

    def handle_click(self, pos, width, height) -> str | None:
        """Определяет, по какой кнопке кликнули. Кнопка "Сюжет" намеренно не
        обрабатывается - она неактивна и не должна возвращать действие."""
        self._layout(width, height)
        if self._point_in(pos, self._endless_rect):
            return "endless"
        if self._point_in(pos, self._back_rect):
            return "back"
        return None

    @staticmethod
    def _point_in(pos, rect) -> bool:
        """Проверяет, попадает ли точка в прямоугольник."""
        px, py = pos
        x, y, w, h = rect
        return x <= px <= x + w and y <= py <= y + h
