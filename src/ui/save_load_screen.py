"""Экран сохранения/загрузки, открывается из меню паузы кнопками "Сохранить"
("save") и "Загрузить" ("load"). Слоты приходят снаружи (GameView собирает их
через SaveManager) - экран сам ничего не знает про диск, только рисует список и
сообщает о клике."""
import pygame

from src.localization.loc import loc

ROW_WIDTH = 460
ROW_HEIGHT = 46
ROW_GAP = 10
MAX_VISIBLE_SLOTS = 6
BACK_BUTTON_WIDTH = 220
BACK_BUTTON_HEIGHT = 50


class SaveLoadScreen:
    """Список слотов сохранения: в режиме "save" есть кнопка "Новое сохранение" и
    клик по существующему слоту его перезаписывает; в режиме "load" клик по слоту
    загружает его. Показывает не больше MAX_VISIBLE_SLOTS слотов (без прокрутки -
    достаточно для курсового проекта, самые новые сохранения всегда видны, т.к.
    список уже отсортирован по свежести вызывающей стороной)."""

    def __init__(self):
        """Создаёт экран с пустой раскладкой (заполняется в _layout)."""
        self._new_save_rect = (0, 0, 0, 0)
        self._slot_rects = []
        self._back_rect = (0, 0, 0, 0)

    def _layout(self, width, height, mode, slots):
        """Рассчитывает положение кнопки "Новое сохранение" (только в режиме save),
        строк слотов и кнопки "Назад" под размер окна и число слотов."""
        cx = width // 2
        rows = list(slots[:MAX_VISIBLE_SLOTS])
        n_extra = 1 if mode == "save" else 0
        total_rows = n_extra + len(rows)
        content_height = total_rows * ROW_HEIGHT + max(0, total_rows - 1) * ROW_GAP
        top = height // 2 - content_height // 2 - 60

        y = top
        if mode == "save":
            self._new_save_rect = (cx - ROW_WIDTH // 2, y, ROW_WIDTH, ROW_HEIGHT)
            y += ROW_HEIGHT + ROW_GAP
        else:
            self._new_save_rect = (0, 0, 0, 0)

        self._slot_rects = []
        for info in rows:
            rect = (cx - ROW_WIDTH // 2, y, ROW_WIDTH, ROW_HEIGHT)
            self._slot_rects.append((rect, info["slot_id"]))
            y += ROW_HEIGHT + ROW_GAP

        y += ROW_GAP
        self._back_rect = (cx - BACK_BUTTON_WIDTH // 2, y, BACK_BUTTON_WIDTH, BACK_BUTTON_HEIGHT)

    def render(self, screen, width, height, font, small_font, title_font, mode, slots):
        """Рисует полупрозрачную подложку, заголовок, список слотов и кнопку "Назад"."""
        self._layout(width, height, mode, slots)

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((10, 12, 15, 200))
        screen.blit(overlay, (0, 0))

        title_key = "save_load.title_save" if mode == "save" else "save_load.title_load"
        title = title_font.render(loc.get(title_key), True, (255, 255, 255))
        tw, _ = title.get_size()
        first_row_y = self._new_save_rect[1] if mode == "save" else \
            (self._slot_rects[0][0][1] if self._slot_rects else self._back_rect[1])
        screen.blit(title, ((width - tw) // 2, first_row_y - 90))

        if mode == "save":
            self._draw_button(screen, self._new_save_rect, loc.get("save_load.new_save"), font, (60, 160, 90))

        visible = slots[:MAX_VISIBLE_SLOTS]
        if not visible:
            empty_label = small_font.render(loc.get("save_load.empty"), True, (170, 170, 170))
            ew, _ = empty_label.get_size()
            y = self._slot_rects[0][0][1] if self._slot_rects else \
                (self._new_save_rect[1] + ROW_HEIGHT + ROW_GAP if mode == "save" else self._back_rect[1] - ROW_HEIGHT)
            screen.blit(empty_label, ((width - ew) // 2, y))

        for (rect, _slot_id), info in zip(self._slot_rects, visible):
            color = (70, 105, 150) if info.get("is_quicksave") else (55, 55, 60)
            self._draw_button(screen, rect, self._slot_label(info), small_font, color)

        self._draw_button(screen, self._back_rect, loc.get("menu.back"), font, (100, 100, 100))

    def _slot_label(self, info: dict) -> str:
        """Формирует подпись строки слота: время сохранения и сколько было сыграно."""
        saved_at = info.get("saved_at") or "?"
        display_time = saved_at.replace("T", " ")
        played = self._format_duration(info.get("elapsed_time", 0.0))
        if info.get("is_quicksave"):
            return f"{loc.get('save_load.quicksave')} — {display_time} ({played})"
        return f"{display_time} ({played})"

    @staticmethod
    def _format_duration(seconds) -> str:
        """Форматирует секунды как m:ss для подписи слота."""
        total = int(max(0.0, seconds))
        return f"{total // 60}:{total % 60:02d}"

    def _draw_button(self, screen, rect, text, font, color):
        """Рисует одну кнопку/строку с подписью."""
        x, y, w, h = rect
        pygame.draw.rect(screen, color, (x, y, w, h))
        pygame.draw.rect(screen, (255, 255, 255), (x, y, w, h), 2)
        label = font.render(text, True, (255, 255, 255))
        lw, lh = label.get_size()
        screen.blit(label, (x + (w - lw) // 2, y + (h - lh) // 2))

    def handle_click(self, pos, width, height, mode, slots) -> "tuple | None":
        """Определяет действие по клику: ("back", None), ("new_save", None) (только
        save), ("save_slot", slot_id) или ("load_slot", slot_id)."""
        self._layout(width, height, mode, slots)

        if self._point_in(pos, self._back_rect):
            return ("back", None)
        if mode == "save" and self._point_in(pos, self._new_save_rect):
            return ("new_save", None)
        for rect, slot_id in self._slot_rects:
            if self._point_in(pos, rect):
                return ("save_slot" if mode == "save" else "load_slot", slot_id)
        return None

    @staticmethod
    def _point_in(pos, rect) -> bool:
        """Проверяет, попадает ли точка в прямоугольник."""
        px, py = pos
        x, y, w, h = rect
        return x <= px <= x + w and y <= py <= y + h
