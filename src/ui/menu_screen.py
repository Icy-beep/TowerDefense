"""MenuScreen — экран главного меню (заготовка). Сейчас только две
кнопки: "Начать игру" и "Выйти" — точка расширения под будущие пункты
(настройки, выбор режима игры и т.п.), когда они появятся.

Раскладка кнопок (_layout) отделена от отрисовки, чтобы клики можно было
проверять юнит-тестами без реального pygame-окна."""
import pygame

BUTTON_WIDTH = 260
BUTTON_HEIGHT = 60


class MenuScreen:
    def __init__(self):
        self._start_rect = (0, 0, 0, 0)
        self._exit_rect = (0, 0, 0, 0)

    def _layout(self, width, height):
        cx = width // 2
        self._start_rect = (cx - BUTTON_WIDTH // 2, height // 2 - BUTTON_HEIGHT - 10,
                             BUTTON_WIDTH, BUTTON_HEIGHT)
        self._exit_rect = (cx - BUTTON_WIDTH // 2, height // 2 + 10,
                            BUTTON_WIDTH, BUTTON_HEIGHT)

    def render(self, screen, width, height, font, title_font):
        self._layout(width, height)
        screen.fill((20, 24, 28))

        title = title_font.render("Tower Defense", True, (255, 255, 255))
        tw, th = title.get_size()
        screen.blit(title, ((width - tw) // 2, height // 2 - 160))

        self._draw_button(screen, self._start_rect, "Начать игру", font, (60, 160, 90))
        self._draw_button(screen, self._exit_rect, "Выйти", font, (160, 60, 60))

    def _draw_button(self, screen, rect, text, font, color):
        x, y, w, h = rect
        pygame.draw.rect(screen, color, (x, y, w, h))
        pygame.draw.rect(screen, (255, 255, 255), (x, y, w, h), 2)
        label = font.render(text, True, (255, 255, 255))
        lw, lh = label.get_size()
        screen.blit(label, (x + (w - lw) // 2, y + (h - lh) // 2))

    def handle_click(self, pos, width, height) -> str | None:
        """Пересчитывает раскладку под текущий размер окна и возвращает
        'start' / 'exit' / None. Ничего не хранит между кадрами кроме
        последней раскладки — безопасно для юнит-тестов."""
        self._layout(width, height)
        if self._point_in(pos, self._start_rect):
            return "start"
        if self._point_in(pos, self._exit_rect):
            return "exit"
        return None

    @staticmethod
    def _point_in(pos, rect) -> bool:
        px, py = pos
        x, y, w, h = rect
        return x <= px <= x + w and y <= py <= y + h
