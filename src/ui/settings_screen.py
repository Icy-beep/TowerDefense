"""Экран настроек, открывается из главного меню: экран, звук, язык."""
import pygame

from src.core.settings import DISPLAY_MODE_BORDERLESS, DISPLAY_MODES
from src.localization.loc import loc

PANEL_WIDTH = 560
LABEL_WIDTH = 170
ROW_HEIGHT = 44
ROW_GAP = 16
STEPPER_ARROW_SIZE = 36
SEGMENT_GAP = 8
BACK_BUTTON_WIDTH = 220
BACK_BUTTON_HEIGHT = 54

DISPLAY_MODE_LABEL_KEYS = {
    "windowed": "settings.display_windowed",
    "borderless": "settings.display_borderless",
    "fullscreen": "settings.display_fullscreen",
}


class SettingsScreen:
    """Настройки: режим экрана, разрешение, громкость музыки/звуков, язык, кнопка "Назад"."""

    def __init__(self):
        """Создаёт экран с пустой раскладкой (заполняется в _layout)."""
        self._display_mode_rects = {}
        self._resolution_prev_rect = (0, 0, 0, 0)
        self._resolution_next_rect = (0, 0, 0, 0)
        self._music_down_rect = (0, 0, 0, 0)
        self._music_up_rect = (0, 0, 0, 0)
        self._sfx_down_rect = (0, 0, 0, 0)
        self._sfx_up_rect = (0, 0, 0, 0)
        self._language_prev_rect = (0, 0, 0, 0)
        self._language_next_rect = (0, 0, 0, 0)
        self._back_rect = (0, 0, 0, 0)

    def _layout(self, width, height):
        """Рассчитывает положение всех элементов управления под размер окна."""
        cx = width // 2
        panel_left = cx - PANEL_WIDTH // 2
        controls_left = panel_left + LABEL_WIDTH
        controls_width = PANEL_WIDTH - LABEL_WIDTH

        row_count = 5
        total_height = ROW_HEIGHT * row_count + ROW_GAP * (row_count - 1)
        y = height // 2 - total_height // 2 - 30

        segment_width = (controls_width - SEGMENT_GAP * (len(DISPLAY_MODES) - 1)) // len(DISPLAY_MODES)
        self._display_mode_rects = {}
        x = controls_left
        for mode in DISPLAY_MODES:
            self._display_mode_rects[mode] = (x, y, segment_width, ROW_HEIGHT)
            x += segment_width + SEGMENT_GAP

        y += ROW_HEIGHT + ROW_GAP
        self._resolution_prev_rect = (controls_left, y, STEPPER_ARROW_SIZE, ROW_HEIGHT)
        self._resolution_next_rect = (controls_left + controls_width - STEPPER_ARROW_SIZE, y,
                                       STEPPER_ARROW_SIZE, ROW_HEIGHT)

        y += ROW_HEIGHT + ROW_GAP
        self._music_down_rect = (controls_left, y, STEPPER_ARROW_SIZE, ROW_HEIGHT)
        self._music_up_rect = (controls_left + controls_width - STEPPER_ARROW_SIZE, y,
                                STEPPER_ARROW_SIZE, ROW_HEIGHT)

        y += ROW_HEIGHT + ROW_GAP
        self._sfx_down_rect = (controls_left, y, STEPPER_ARROW_SIZE, ROW_HEIGHT)
        self._sfx_up_rect = (controls_left + controls_width - STEPPER_ARROW_SIZE, y,
                              STEPPER_ARROW_SIZE, ROW_HEIGHT)

        y += ROW_HEIGHT + ROW_GAP
        self._language_prev_rect = (controls_left, y, STEPPER_ARROW_SIZE, ROW_HEIGHT)
        self._language_next_rect = (controls_left + controls_width - STEPPER_ARROW_SIZE, y,
                                     STEPPER_ARROW_SIZE, ROW_HEIGHT)

        y += ROW_HEIGHT + ROW_GAP * 2
        self._back_rect = (cx - BACK_BUTTON_WIDTH // 2, y, BACK_BUTTON_WIDTH, BACK_BUTTON_HEIGHT)

    def render(self, screen, width, height, font, small_font, title_font, settings):
        """Рисует экран настроек по текущему объекту Settings."""
        self._layout(width, height)
        screen.fill((20, 24, 28))

        title = title_font.render(loc.get("settings.title"), True, (255, 255, 255))
        tw, _ = title.get_size()
        screen.blit(title, ((width - tw) // 2, height // 2 - 260))

        panel_left = width // 2 - PANEL_WIDTH // 2
        first_row_y = self._display_mode_rects[DISPLAY_MODES[0]][1]
        self._draw_row_label(screen, panel_left, first_row_y, loc.get("settings.display_mode"), small_font)
        for mode, rect in self._display_mode_rects.items():
            active = settings.display_mode == mode
            color = (60, 140, 90) if active else (55, 55, 60)
            self._draw_button(screen, rect, loc.get(DISPLAY_MODE_LABEL_KEYS[mode]), small_font, color)

        resolution_disabled = settings.display_mode == DISPLAY_MODE_BORDERLESS
        res_text = f"{settings.resolution[0]}x{settings.resolution[1]}"
        self._draw_stepper_row(screen, panel_left, self._resolution_prev_rect, self._resolution_next_rect,
                                loc.get("settings.resolution"), res_text, font, small_font,
                                disabled=resolution_disabled)

        self._draw_stepper_row(screen, panel_left, self._music_down_rect, self._music_up_rect,
                                loc.get("settings.music_volume"), f"{round(settings.music_volume * 100)}%",
                                font, small_font)

        self._draw_stepper_row(screen, panel_left, self._sfx_down_rect, self._sfx_up_rect,
                                loc.get("settings.sfx_volume"), f"{round(settings.sfx_volume * 100)}%",
                                font, small_font)

        self._draw_stepper_row(screen, panel_left, self._language_prev_rect, self._language_next_rect,
                                loc.get("settings.language"), loc.language_name(settings.language),
                                font, small_font)

        self._draw_button(screen, self._back_rect, loc.get("settings.back"), font, (100, 100, 100))

    def _draw_row_label(self, screen, x, y, text, font):
        """Рисует подпись строки настройки слева от элементов управления."""
        label = font.render(text, True, (200, 200, 200))
        _, lh = label.get_size()
        screen.blit(label, (x, y + (ROW_HEIGHT - lh) // 2))

    def _draw_stepper_row(self, screen, panel_left, minus_rect, plus_rect, label_text, value_text,
                           font, small_font, disabled=False):
        """Рисует строку "подпись [-] значение [+]"."""
        mx, my, mw, mh = minus_rect
        self._draw_row_label(screen, panel_left, my, label_text, small_font)

        arrow_color = (55, 55, 60) if disabled else (60, 100, 150)
        self._draw_button(screen, minus_rect, "-", font, arrow_color)
        self._draw_button(screen, plus_rect, "+", font, arrow_color)

        px = plus_rect[0]
        value_x, value_w = mx + mw, px - (mx + mw)
        text_color = (110, 110, 110) if disabled else (255, 255, 255)
        value_label = font.render(value_text, True, text_color)
        lw, lh = value_label.get_size()
        screen.blit(value_label, (value_x + (value_w - lw) // 2, my + (mh - lh) // 2))

    def _draw_button(self, screen, rect, text, font, color):
        """Рисует одну кнопку с подписью."""
        x, y, w, h = rect
        pygame.draw.rect(screen, color, (x, y, w, h))
        pygame.draw.rect(screen, (255, 255, 255), (x, y, w, h), 2)
        label = font.render(text, True, (255, 255, 255))
        lw, lh = label.get_size()
        screen.blit(label, (x + (w - lw) // 2, y + (h - lh) // 2))

    def handle_click(self, pos, width, height, settings) -> tuple | None:
        """Определяет действие по клику: (тип, значение) или None, если мимо элементов управления."""
        self._layout(width, height)

        for mode, rect in self._display_mode_rects.items():
            if self._point_in(pos, rect):
                return ("display_mode", mode)

        if settings.display_mode != DISPLAY_MODE_BORDERLESS:
            if self._point_in(pos, self._resolution_prev_rect):
                return ("resolution", -1)
            if self._point_in(pos, self._resolution_next_rect):
                return ("resolution", 1)

        if self._point_in(pos, self._music_down_rect):
            return ("music_volume", -1)
        if self._point_in(pos, self._music_up_rect):
            return ("music_volume", 1)
        if self._point_in(pos, self._sfx_down_rect):
            return ("sfx_volume", -1)
        if self._point_in(pos, self._sfx_up_rect):
            return ("sfx_volume", 1)
        if self._point_in(pos, self._language_prev_rect):
            return ("language", -1)
        if self._point_in(pos, self._language_next_rect):
            return ("language", 1)
        if self._point_in(pos, self._back_rect):
            return ("back", None)
        return None

    @staticmethod
    def _point_in(pos, rect) -> bool:
        """Проверяет, попадает ли точка в прямоугольник."""
        px, py = pos
        x, y, w, h = rect
        return x <= px <= x + w and y <= py <= y + h
