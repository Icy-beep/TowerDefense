"""Дерево технологий башен: выбор типа башни сверху, три покупаемые за scrap ветки
(радиус/урон/скорострельность) по центру. Апгрейд ветки действует на ВЕСЬ ТИП
башни сразу (все текущие и будущие), а не на одну конкретную постройку - см.
src/systems/tech_tree.py, GameSession.upgrade_tech_branch. Отдельная система от
ИИ-модулей, которые достаются случайным дропом (DefenseModule.AI_MODULE_KEYS,
GameSession.ai_module_stock)."""
import pygame

from src.localization.loc import loc
from src.systems.tech_tree import BRANCHES

TOWER_BUTTON_WIDTH = 180
TOWER_BUTTON_HEIGHT = 50
TOWER_BUTTON_GAP = 20

BRANCH_WIDTH = 220
BRANCH_HEIGHT = 260
BRANCH_GAP = 40

BACK_BUTTON_WIDTH = 200
BACK_BUTTON_HEIGHT = 50

AFFORDABLE_COLOR = (100, 255, 100)
UNAFFORDABLE_COLOR = (220, 90, 90)
MAXED_COLOR = (255, 215, 0)


class TechTreeScreen:
    """Экран дерева технологий (см. GameView.tech_tree_open)."""

    def __init__(self):
        """Создаёт экран с пустой раскладкой и первой башней по умолчанию."""
        self._tower_rects: dict[str, tuple] = {}
        self._branch_rects: dict[str, tuple] = {}
        self._back_rect = (0, 0, 0, 0)
        self.selected_type = "laser"

    def _layout(self, width, height, tower_options):
        """Рассчитывает положение кнопок-башен сверху и веток по центру."""
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
        total_branch_w = len(BRANCHES) * BRANCH_WIDTH + (len(BRANCHES) - 1) * BRANCH_GAP
        branch_start_x = cx - total_branch_w // 2

        self._branch_rects = {}
        x = branch_start_x
        for key in BRANCHES:
            self._branch_rects[key] = (x, branch_top, BRANCH_WIDTH, BRANCH_HEIGHT)
            x += BRANCH_WIDTH + BRANCH_GAP

        self._back_rect = (cx - BACK_BUTTON_WIDTH // 2, height - 90, BACK_BUTTON_WIDTH, BACK_BUTTON_HEIGHT)

    def render(self, screen, width, height, font, small_font, title_font, tower_options, session):
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

        upgrade_costs = session.tower_factory.get_upgrade_costs(self.selected_type)
        scrap = session.resources.scrap
        for key in BRANCHES:
            rect = self._branch_rects[key]
            level = session.tech_tree.level_for(self.selected_type, key)
            cost = session.tech_tree.upgrade_cost(self.selected_type, key, upgrade_costs)
            self._draw_branch(screen, rect, key, font, small_font, level, len(upgrade_costs), cost, scrap)

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

    def _draw_branch(self, screen, rect, key, font, small_font, level, max_level, cost, scrap):
        """Рисует одну ветку: название, текущий уровень и цену следующего (или
        МАКС, если уже максимальна)."""
        x, y, w, h = rect
        maxed = cost is None
        border_color = MAXED_COLOR if maxed else (120, 120, 130)
        pygame.draw.rect(screen, (32, 36, 44), (x, y, w, h))
        pygame.draw.rect(screen, border_color, (x, y, w, h), 3 if maxed else 2)

        label = font.render(loc.get(f"tech_tree.branch_{key}"), True, (255, 255, 255))
        screen.blit(label, (x + (w - label.get_width()) // 2, y + 20))

        level_text = small_font.render(loc.get("tech_tree.level", level=level, max_level=max_level),
                                        True, (200, 200, 200))
        screen.blit(level_text, (x + (w - level_text.get_width()) // 2, y + 60))

        if maxed:
            status = small_font.render(loc.get("tech_tree.maxed"), True, MAXED_COLOR)
        else:
            can_afford = scrap >= cost
            color = AFFORDABLE_COLOR if can_afford else UNAFFORDABLE_COLOR
            status = small_font.render(loc.get("tech_tree.cost", cost=cost), True, color)
        screen.blit(status, (x + (w - status.get_width()) // 2, y + h // 2))

    def handle_click(self, pos, width, height, tower_options, session) -> str | None:
        """Обрабатывает клик: выбор типа башни и покупка ветки применяются сразу
        через session, наружу возвращается только 'back' (закрыть экран) или None."""
        self._layout(width, height, tower_options)

        for tower_type, rect in self._tower_rects.items():
            if self._point_in(pos, rect):
                self.selected_type = tower_type
                return None

        for key, rect in self._branch_rects.items():
            if self._point_in(pos, rect):
                session.upgrade_tech_branch(self.selected_type, key)
                return None

        if self._point_in(pos, self._back_rect):
            return "back"
        return None

    @staticmethod
    def _point_in(pos, rect) -> bool:
        """Проверяет, попадает ли точка в прямоугольник."""
        px, py = pos
        x, y, w, h = rect
        return x <= px <= x + w and y <= py <= y + h
