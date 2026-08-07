"""Дерево технологий башен - экран-заготовка (см. запрос пользователя): выбор
типа башни сверху, три ветки-заглушки (радиус/урон/скорострельность) по центру.
Содержимое веток пока ни к чему не подключено - это каркас под будущее
наполнение, отдельный от ИИ-модулей за scrap (см. DefenseModule.AI_MODULE_COSTS)."""
import pygame

from src.localization.loc import loc

TOWER_BUTTON_WIDTH = 180
TOWER_BUTTON_HEIGHT = 50
TOWER_BUTTON_GAP = 20

BRANCH_WIDTH = 220
BRANCH_HEIGHT = 260
BRANCH_GAP = 40

BACK_BUTTON_WIDTH = 200
BACK_BUTTON_HEIGHT = 50


class TechTreeScreen:
    """Экран дерева технологий (см. GameView.tech_tree_open)."""

    BRANCHES = ["radius", "damage", "attack_speed"]

    def __init__(self):
        """Создаёт экран с пустой раскладкой и первой башней по умолчанию."""
        self._tower_rects: dict[str, tuple] = {}
        self._branch_rects: dict[str, tuple] = {}
        self._back_rect = (0, 0, 0, 0)
        self.selected_type = "laser"
        # Выбранная ветка запоминается отдельно на каждый тип башни - чисто
        # визуальная подсветка, ни на что в игре пока не влияет.
        self._selected_branch: dict[str, str | None] = {}

    def _layout(self, width, height, tower_options):
        """Рассчитывает положение кнопок-башен сверху и веток-заглушек по центру."""
        cx = width // 2
        n = len(tower_options)
        total_w = n * TOWER_BUTTON_WIDTH + (n - 1) * TOWER_BUTTON_GAP
        start_x = cx - total_w // 2
        top_y = 90

        self._tower_rects = {}
        x = start_x
        for opt in tower_options:
            self._tower_rects[opt["type"]] = (x, top_y, TOWER_BUTTON_WIDTH, TOWER_BUTTON_HEIGHT)
            x += TOWER_BUTTON_WIDTH + TOWER_BUTTON_GAP

        branch_top = top_y + TOWER_BUTTON_HEIGHT + 80
        total_branch_w = len(self.BRANCHES) * BRANCH_WIDTH + (len(self.BRANCHES) - 1) * BRANCH_GAP
        branch_start_x = cx - total_branch_w // 2

        self._branch_rects = {}
        x = branch_start_x
        for key in self.BRANCHES:
            self._branch_rects[key] = (x, branch_top, BRANCH_WIDTH, BRANCH_HEIGHT)
            x += BRANCH_WIDTH + BRANCH_GAP

        self._back_rect = (cx - BACK_BUTTON_WIDTH // 2, height - 90, BACK_BUTTON_WIDTH, BACK_BUTTON_HEIGHT)

    def render(self, screen, width, height, font, small_font, title_font, tower_options):
        """Рисует экран дерева технологий для tower_options (только боевые башни)."""
        self._layout(width, height, tower_options)
        screen.fill((16, 18, 22))

        title = title_font.render(loc.get("tech_tree.title"), True, (255, 255, 255))
        screen.blit(title, ((width - title.get_width()) // 2, 24))

        for opt in tower_options:
            rect = self._tower_rects[opt["type"]]
            is_selected = opt["type"] == self.selected_type
            color = (60, 100, 150) if is_selected else (45, 48, 55)
            self._draw_button(screen, rect, opt["name"], font, color, highlighted=is_selected)

        selected_branch = self._selected_branch.get(self.selected_type)
        for key in self.BRANCHES:
            rect = self._branch_rects[key]
            self._draw_branch(screen, rect, key, font, small_font, key == selected_branch)

        self._draw_button(screen, self._back_rect, loc.get("menu.back"), font, (100, 100, 100))

    def _draw_button(self, screen, rect, text, font, color, highlighted=False):
        """Рисует прямоугольную кнопку с подписью."""
        x, y, w, h = rect
        pygame.draw.rect(screen, color, (x, y, w, h))
        border_color = (255, 215, 0) if highlighted else (255, 255, 255)
        pygame.draw.rect(screen, border_color, (x, y, w, h), 3 if highlighted else 2)
        label = font.render(text, True, (255, 255, 255))
        lw, lh = label.get_size()
        screen.blit(label, (x + (w - lw) // 2, y + (h - lh) // 2))

    def _draw_branch(self, screen, rect, key, font, small_font, is_selected):
        """Рисует одну ветку-заглушку дерева."""
        x, y, w, h = rect
        pygame.draw.rect(screen, (32, 36, 44), (x, y, w, h))
        border_color = (255, 215, 0) if is_selected else (120, 120, 130)
        pygame.draw.rect(screen, border_color, (x, y, w, h), 3 if is_selected else 2)

        label = font.render(loc.get(f"tech_tree.branch_{key}"), True, (255, 255, 255))
        screen.blit(label, (x + (w - label.get_width()) // 2, y + 20))

        hint = small_font.render(loc.get("tech_tree.stub_hint"), True, (150, 150, 150))
        screen.blit(hint, (x + (w - hint.get_width()) // 2, y + h // 2))

    def handle_click(self, pos, width, height, tower_options) -> tuple | None:
        """Определяет, по чему кликнули: ('select_tower', type), ('select_branch',
        key) или ('back', None). Раскладка та же, что и при отрисовке (_layout)."""
        self._layout(width, height, tower_options)

        for tower_type, rect in self._tower_rects.items():
            if self._point_in(pos, rect):
                self.selected_type = tower_type
                return ("select_tower", tower_type)

        for key, rect in self._branch_rects.items():
            if self._point_in(pos, rect):
                self._selected_branch[self.selected_type] = key
                return ("select_branch", key)

        if self._point_in(pos, self._back_rect):
            return ("back", None)
        return None

    @staticmethod
    def _point_in(pos, rect) -> bool:
        """Проверяет, попадает ли точка в прямоугольник."""
        px, py = pos
        x, y, w, h = rect
        return x <= px <= x + w and y <= py <= y + h
