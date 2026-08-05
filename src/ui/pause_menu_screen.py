"""Внутриигровое меню паузы, открывается по ESC во время игры."""
import pygame

from src.localization.loc import loc

BUTTON_WIDTH = 300
BUTTON_HEIGHT = 50
BUTTON_GAP = 14
BUTTON_KEYS = ("resume", "save", "load", "settings", "main_menu", "exit")
BUTTON_LABEL_KEYS = {
    "resume": "pause.resume",
    "save": "pause.save",
    "load": "pause.load",
    "settings": "menu.settings",
    "main_menu": "pause.main_menu",
    "exit": "menu.exit",
}
BUTTON_COLORS = {
    "resume": (60, 160, 90),
    "save": (70, 70, 80),
    "load": (70, 70, 80),
    "settings": (60, 100, 150),
    "main_menu": (170, 120, 40),
    "exit": (160, 60, 60),
}


class PauseMenuScreen:
    """Меню паузы: продолжить, сохранить/загрузить (заглушки), настройки, в главное меню, выйти."""

    def __init__(self):
        """Создаёт меню с пустой раскладкой кнопок."""
        self._rects = {}

    def _layout(self, width, height):
        """Рассчитывает положение кнопок под размер окна."""
        cx = width // 2
        total_height = BUTTON_HEIGHT * len(BUTTON_KEYS) + BUTTON_GAP * (len(BUTTON_KEYS) - 1)
        top = height // 2 - total_height // 2
        self._rects = {}
        y = top
        for key in BUTTON_KEYS:
            self._rects[key] = (cx - BUTTON_WIDTH // 2, y, BUTTON_WIDTH, BUTTON_HEIGHT)
            y += BUTTON_HEIGHT + BUTTON_GAP

    def render(self, screen, width, height, font, small_font, title_font, notice=""):
        """Рисует полупрозрачную подложку поверх замороженной игры и панель меню паузы."""
        self._layout(width, height)

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((10, 12, 15, 190))
        screen.blit(overlay, (0, 0))

        title = title_font.render(loc.get("pause.title"), True, (255, 255, 255))
        tw, _ = title.get_size()
        first_button_y = self._rects[BUTTON_KEYS[0]][1]
        screen.blit(title, ((width - tw) // 2, first_button_y - 90))

        for key in BUTTON_KEYS:
            self._draw_button(screen, self._rects[key], loc.get(BUTTON_LABEL_KEYS[key]), font, BUTTON_COLORS[key])

        if notice:
            notice_label = small_font.render(notice, True, (255, 210, 90))
            nw, _ = notice_label.get_size()
            last_button = self._rects[BUTTON_KEYS[-1]]
            screen.blit(notice_label, ((width - nw) // 2, last_button[1] + last_button[3] + 16))

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
        for key, rect in self._rects.items():
            if self._point_in(pos, rect):
                return key
        return None

    @staticmethod
    def _point_in(pos, rect) -> bool:
        """Проверяет, попадает ли точка в прямоугольник."""
        px, py = pos
        x, y, w, h = rect
        return x <= px <= x + w and y <= py <= y + h
