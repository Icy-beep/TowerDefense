"""HUD-панели поверх игрового поля: единый RTS-стиль - панель ресурсов сверху,
командная панель (выбор/постройки/подсказки) снизу (см. обсуждение с пользователем:
раньше HUD был чисто текстовым, без кликабельных иконок построек)."""
import logging

import pygame

from src.enums import ArmorType, Faction
from src.localization.loc import loc

logger = logging.getLogger(__name__)

ENEMY_DISPLAY_KEYS = {
    "drone_walker": "enemy.drone_walker",
    "giant_roach": "enemy.giant_roach",
    "scout_drone": "enemy.scout_drone",
    "heavy_assault_drone": "enemy.heavy_assault_drone",
    "bio_titan": "enemy.bio_titan",
    "medic_drone": "enemy.medic_drone",
}

ARMOR_LABEL_KEYS = {
    ArmorType.LIGHT: "armor.light",
    ArmorType.HEAVY: "armor.heavy",
    ArmorType.ENERGY_SHIELDED: "armor.energy_shielded",
    ArmorType.ORGANIC: "armor.organic",
}

FACTION_LABEL_KEYS = {
    Faction.CORPORATION: "faction.corporation",
    Faction.FAUNA: "faction.fauna",
}


class HudRenderer:
    """Рисует HUD-панели поверх игрового поля."""

    # Общая палитра - одна и та же для всех панелей, чтобы HUD выглядел как единый
    # набор, а не набор случайно раскрашенных прямоугольников.
    PANEL_BG = (18, 22, 30, 210)
    BORDER_COLOR = (90, 140, 190)
    BORDER_WIDTH = 2
    HIGHLIGHT_COLOR = (255, 215, 0)
    TEXT_COLOR = (230, 230, 230)
    DIM_TEXT_COLOR = (140, 140, 145)

    TOP_BAR_HEIGHT = 60
    BOTTOM_BAR_HEIGHT = 130

    BUILD_ICON_SIZE = 64
    BUILD_ICON_GAP = 12

    TOGGLE_BUTTON_SIZE = 40
    TOGGLE_BUTTON_GAP = 8
    # (ключ состояния, хоткей) - порядок и есть порядок отрисовки слева направо.
    TOGGLE_BUTTONS = [("power_radii", "G"), ("tower_ranges", "T")]

    TECH_TREE_HOTKEY = "K"

    HELP_BUTTON_SIZE = 28
    HELP_POPUP_WIDTH = 380
    HELP_POPUP_LINE_HEIGHT = 18
    HELP_POPUP_PADDING = 10

    def __init__(self, sprite_manager=None):
        """Запоминает SpriteManager; без него (или без спрайта под ключ) иконки
        построек рисуются цветными плашками вместо картинки."""
        self.sprite_manager = sprite_manager
        # Раньше подсказки по управлению висели статичным текстом в правом нижнем
        # углу и при добавлении новой строки (см. hud.controls_ranges) стали вылезать
        # за пределы экрана - теперь это всплывающая панель по кнопке "?" (см.
        # запрос пользователя), состояние открытия - чисто UI, к сессии не относится.
        self.show_help = False

    def _sprite_for(self, key, elapsed_time=0.0):
        """Возвращает статичный (первый) кадр спрайта для ключа, или None, если
        спрайтов нет/не подключены - иконкам не нужна анимация/поворот."""
        if not self.sprite_manager:
            return None
        return self.sprite_manager.get_frame(key, elapsed_time)

    def render(self, screen, camera, session, controller, tower_options, width, height, font, small_font,
               tech_tree_open=False):
        """Рисует все панели HUD."""
        state = controller.get_game_state()

        self._draw_top_bar(screen, state, font, width)
        self._draw_toggle_buttons(screen, state, width, small_font)
        self._draw_tech_tree_button(screen, width, small_font, tech_tree_open)
        self._draw_missions_panel(screen, session, small_font, width)
        self._draw_bottom_bar(screen, state, controller, tower_options, camera, small_font, width, height)

    # ------------------------------------------------------------------
    # Верхняя панель: ресурсы, здоровье базы, таймер/бесконечный режим
    # ------------------------------------------------------------------

    def _draw_top_bar(self, screen, state, font, width):
        """Рисует полосу ресурсов во всю ширину экрана: деньги и здоровье базы
        слева, таймер выживания (или ничего - в бесконечном режиме нет таймера,
        см. GameSession.setup_game) справа."""
        surf = pygame.Surface((width, self.TOP_BAR_HEIGHT), pygame.SRCALPHA)
        surf.fill(self.PANEL_BG)
        screen.blit(surf, (0, 0))
        pygame.draw.line(screen, self.BORDER_COLOR, (0, self.TOP_BAR_HEIGHT), (width, self.TOP_BAR_HEIGHT),
                          self.BORDER_WIDTH)

        cy = self.TOP_BAR_HEIGHT // 2
        x = 16
        x = self._draw_coin_icon(screen, x, cy) + 8

        credits_text = loc.get("hud.money", credits=state['credits'])
        x = self._draw_label(screen, font, credits_text, x, cy, (255, 215, 0)) + 28

        x = self._draw_heart_icon(screen, x, cy) + 8
        hp_text = loc.get("hud.base_health", hp=state['base_health'], max_hp=state['max_base_health'])
        x = self._draw_label(screen, font, hp_text, x, cy, (255, 100, 100)) + 12

        hp_ratio = max(0.0, min(1.0, state['base_health'] / state['max_base_health'])) \
            if state['max_base_health'] else 0.0
        self._draw_mini_bar(screen, x, cy, 70, 10, hp_ratio)

        if state.get('endless', False):
            return

        target = state['survive_duration_target']
        current = min(state['elapsed_time'], target)
        remaining = max(0.0, target - state['elapsed_time'])
        remaining_color = (150, 255, 150) if remaining <= 0 else (200, 200, 100)

        remaining_text = loc.get("hud.survive_remaining", seconds=remaining)
        progress_text = loc.get("hud.survive_progress", current=int(current), target=int(target))

        rw, _ = font.size(remaining_text)
        pw, _ = font.size(progress_text)
        rx = width - 16 - rw
        self._draw_label(screen, font, remaining_text, rx, cy, remaining_color)
        px = rx - 24 - pw
        self._draw_label(screen, font, progress_text, px, cy, (100, 200, 255))
        self._draw_clock_icon(screen, px - 24, cy)

    def _draw_label(self, screen, font, text, x, cy, color):
        """Рисует строку с вертикальным центрированием по cy, возвращает x после текста."""
        surf = font.render(text, True, color)
        rect = surf.get_rect(midleft=(x, cy))
        screen.blit(surf, rect)
        return rect.right

    def _draw_mini_bar(self, screen, x, cy, w, h, ratio):
        """Рисует небольшую полоску прогресса (для здоровья базы в верхней панели)."""
        y = cy - h // 2
        pygame.draw.rect(screen, (50, 50, 55), (x, y, w, h))
        fill_color = (0, 220, 0) if ratio > 0.5 else (220, 60, 60)
        pygame.draw.rect(screen, fill_color, (x, y, int(w * ratio), h))
        pygame.draw.rect(screen, (10, 10, 12), (x, y, w, h), 1)

    def _draw_coin_icon(self, screen, x, cy):
        """Рисует иконку-монету (кредиты). Возвращает x после иконки."""
        r = 10
        pygame.draw.circle(screen, (255, 215, 0), (x + r, cy), r)
        pygame.draw.circle(screen, (150, 110, 0), (x + r, cy), r, 2)
        return x + r * 2

    def _draw_heart_icon(self, screen, x, cy):
        """Рисует иконку-крест (здоровье базы). Возвращает x после иконки."""
        size = 20
        rect = pygame.Rect(x, cy - size // 2, size, size)
        pygame.draw.rect(screen, (120, 30, 30), rect)
        pygame.draw.rect(screen, (220, 90, 90), rect, 2)
        cx, cy2 = rect.center
        pygame.draw.line(screen, (255, 210, 210), (cx - 5, cy2), (cx + 5, cy2), 3)
        pygame.draw.line(screen, (255, 210, 210), (cx, cy2 - 5), (cx, cy2 + 5), 3)
        return x + size

    def _draw_clock_icon(self, screen, x, cy):
        """Рисует иконку-часы (таймер выживания)."""
        r = 9
        pygame.draw.circle(screen, (40, 45, 55), (x + r, cy), r)
        pygame.draw.circle(screen, (150, 190, 220), (x + r, cy), r, 2)
        pygame.draw.line(screen, (150, 190, 220), (x + r, cy), (x + r, cy - r + 2), 2)
        pygame.draw.line(screen, (150, 190, 220), (x + r, cy), (x + r + r - 3, cy), 2)
        return x + r * 2

    # ------------------------------------------------------------------
    # Кнопки-переключатели постоянного показа радиусов (энергосеть/атака башен) -
    # см. запрос пользователя: не хватало способа держать радиусы включёнными без
    # ALT, отдельно для энергосети и для боевых башен. Центр верхней панели между
    # деньгами/здоровьем базы слева и таймером выживания справа обычно пустует.
    # ------------------------------------------------------------------

    def _layout_toggle_buttons(self, width):
        """Считает прямоугольники кнопок-переключателей - используется и при
        отрисовке, и при обработке клика (handle_toggle_click), чтобы раскладка
        совпадала (тот же приём, что и в _layout_build_panel)."""
        n = len(self.TOGGLE_BUTTONS)
        total_w = n * self.TOGGLE_BUTTON_SIZE + (n - 1) * self.TOGGLE_BUTTON_GAP
        start_x = (width - total_w) // 2
        y = (self.TOP_BAR_HEIGHT - self.TOGGLE_BUTTON_SIZE) // 2

        slots = []
        x = start_x
        for key, hotkey in self.TOGGLE_BUTTONS:
            rect = pygame.Rect(x, y, self.TOGGLE_BUTTON_SIZE, self.TOGGLE_BUTTON_SIZE)
            slots.append((rect, key, hotkey))
            x += self.TOGGLE_BUTTON_SIZE + self.TOGGLE_BUTTON_GAP
        return slots

    def handle_toggle_click(self, pos, width) -> "str | None":
        """Определяет, по какой кнопке-переключателю кликнули ('power_radii' /
        'tower_ranges'), или None, если клик мимо. Раскладка та же, что и при
        отрисовке (_layout_toggle_buttons)."""
        for rect, key, _hotkey in self._layout_toggle_buttons(width):
            if rect.collidepoint(pos):
                return key
        return None

    def _draw_toggle_buttons(self, screen, state, width, small_font):
        """Рисует кнопки постоянного показа радиусов: золотая рамка и зеленоватый фон,
        когда включено, иначе - обычный вид иконки построек."""
        active = {
            "power_radii": state.get("show_power_radii", False),
            "tower_ranges": state.get("show_tower_ranges", False),
        }
        for rect, key, hotkey in self._layout_toggle_buttons(width):
            is_on = active.get(key, False)
            bg_color = (55, 75, 40) if is_on else (34, 38, 48)
            pygame.draw.rect(screen, bg_color, rect)

            if key == "power_radii":
                self._draw_power_toggle_icon(screen, rect)
            else:
                self._draw_range_toggle_icon(screen, rect)

            border_color = self.HIGHLIGHT_COLOR if is_on else self.BORDER_COLOR
            border_width = 3 if is_on else self.BORDER_WIDTH
            pygame.draw.rect(screen, border_color, rect, border_width)

            badge = small_font.render(hotkey, True, (255, 255, 255))
            screen.blit(badge, (rect.x + 3, rect.y + 1))

    def _layout_tech_tree_button(self, width):
        """Прямоугольник кнопки дерева технологий - сразу справа от переключателей
        радиусов в верхней панели. Используется и при отрисовке, и при обработке
        клика (handle_tech_tree_click), чтобы раскладка совпадала."""
        last_toggle_rect = self._layout_toggle_buttons(width)[-1][0]
        size = self.TOGGLE_BUTTON_SIZE
        y = (self.TOP_BAR_HEIGHT - size) // 2
        x = last_toggle_rect.right + self.TOGGLE_BUTTON_GAP * 3
        return pygame.Rect(x, y, size, size)

    def handle_tech_tree_click(self, pos, width) -> bool:
        """True, если клик пришёлся на кнопку дерева технологий (см.
        GameView._handle_tech_tree_button_click)."""
        return self._layout_tech_tree_button(width).collidepoint(pos)

    def _draw_tech_tree_button(self, screen, width, small_font, is_open):
        """Рисует кнопку дерева технологий - золотая рамка, пока экран открыт."""
        rect = self._layout_tech_tree_button(width)
        bg_color = (55, 75, 40) if is_open else (34, 38, 48)
        pygame.draw.rect(screen, bg_color, rect)
        border_color = self.HIGHLIGHT_COLOR if is_open else self.BORDER_COLOR
        border_width = 3 if is_open else self.BORDER_WIDTH
        pygame.draw.rect(screen, border_color, rect, border_width)
        label = small_font.render(self.TECH_TREE_HOTKEY, True, (255, 255, 255))
        screen.blit(label, label.get_rect(center=rect.center))

    def _draw_power_toggle_icon(self, screen, rect):
        """Иконка кнопки радиусов энергосети - молния."""
        cx, cy = rect.center
        points = [(cx - 4, cy - 12), (cx + 4, cy - 2), (cx - 1, cy - 2),
                  (cx + 5, cy + 12), (cx - 5, cy + 2), (cx, cy + 2)]
        pygame.draw.polygon(screen, (255, 215, 0), points)

    def _draw_range_toggle_icon(self, screen, rect):
        """Иконка кнопки радиусов атаки башен - прицел."""
        cx, cy = rect.center
        r = 10
        pygame.draw.circle(screen, (220, 90, 90), (cx, cy), r, 2)
        pygame.draw.line(screen, (220, 90, 90), (cx - r - 3, cy), (cx + r + 3, cy), 2)
        pygame.draw.line(screen, (220, 90, 90), (cx, cy - r - 3), (cx, cy + r + 3), 2)

    # ------------------------------------------------------------------
    # Панель заданий (справа сверху, под верхней панелью ресурсов)
    # ------------------------------------------------------------------

    def _draw_missions_panel(self, screen, session, small_font, width):
        """Рисует панель заданий в правом верхнем углу, под панелью ресурсов."""
        objectives = getattr(session, "objectives", [])
        if not objectives:
            return

        pad = 10
        line_height = 22
        w = 340
        h = len(objectives) * line_height + 35
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill(self.PANEL_BG)
        x = width - w - pad
        y = self.TOP_BAR_HEIGHT + 8
        screen.blit(surf, (x, y))
        pygame.draw.rect(screen, self.BORDER_COLOR, (x, y, w, h), self.BORDER_WIDTH)

        screen.blit(small_font.render(loc.get("mission.title"), True, (200, 200, 255)),
                    (x + 10, y + 8))

        for i, objective in enumerate(objectives):
            text = objective.describe(session)
            if objective.completed:
                color = (100, 255, 100)
                text += f" — {loc.get('mission.status_completed')}"
            elif objective.failed:
                color = (255, 100, 100)
                text += f" — {loc.get('mission.status_failed')}"
            else:
                color = (230, 230, 230)
            screen.blit(small_font.render(text, True, color), (x + 10, y + 32 + i * line_height))

    # ------------------------------------------------------------------
    # Нижняя командная панель: инфо о выборе | иконки построек | подсказки
    # ------------------------------------------------------------------

    def _draw_bottom_bar(self, screen, state, controller, tower_options, camera, small_font, width, height):
        """Рисует единую нижнюю панель во всю ширину экрана, поделённую на три зоны:
        слева - информация о текущем выборе, по центру - кликабельные иконки построек,
        справа - подсказки по управлению."""
        bar_y = height - self.BOTTOM_BAR_HEIGHT
        surf = pygame.Surface((width, self.BOTTOM_BAR_HEIGHT), pygame.SRCALPHA)
        surf.fill(self.PANEL_BG)
        screen.blit(surf, (0, bar_y))
        pygame.draw.line(screen, self.BORDER_COLOR, (0, bar_y), (width, bar_y), self.BORDER_WIDTH)

        slots = self._layout_build_panel(tower_options, width, height)
        build_left = slots[0][0].left if slots else width // 2
        build_right = slots[-1][0].right if slots else width // 2

        self._draw_selection_zone(screen, state, controller, tower_options, small_font,
                                   16, bar_y + 10, build_left - 26, self.BOTTOM_BAR_HEIGHT - 20)
        self._draw_build_icons(screen, state, controller, slots, small_font)
        self._draw_controls_zone(screen, camera, small_font,
                                  build_right + 16, bar_y + 10, width - 16, self.BOTTOM_BAR_HEIGHT - 20,
                                  width, height)

    def _layout_build_panel(self, tower_options, width, height):
        """Считает прямоугольники иконок построек - используется и при отрисовке, и
        при обработке клика (handle_build_click), чтобы раскладка совпадала."""
        n = len(tower_options)
        if n == 0:
            return []
        total_w = n * self.BUILD_ICON_SIZE + (n - 1) * self.BUILD_ICON_GAP
        start_x = (width - total_w) // 2
        icon_y = height - self.BOTTOM_BAR_HEIGHT + (self.BOTTOM_BAR_HEIGHT - self.BUILD_ICON_SIZE - 22) // 2

        slots = []
        x = start_x
        for opt in tower_options:
            rect = pygame.Rect(x, icon_y, self.BUILD_ICON_SIZE, self.BUILD_ICON_SIZE)
            slots.append((rect, opt))
            x += self.BUILD_ICON_SIZE + self.BUILD_ICON_GAP
        return slots

    def handle_build_click(self, pos, tower_options, width, height) -> "str | None":
        """Определяет, по какой иконке постройки кликнули - или None, если клик мимо
        панели. Раскладка та же, что и при отрисовке (_layout_build_panel)."""
        for rect, opt in self._layout_build_panel(tower_options, width, height):
            if rect.collidepoint(pos):
                return opt["type"]
        return None

    def _draw_build_icons(self, screen, state, controller, slots, small_font):
        """Рисует иконки построек: спрайт (если есть) или цветную плашку, значок
        хоткея, цену (тусклую и красную, если не хватает денег) и золотую рамку
        у текущего выбранного типа."""
        credits = state.get('credits', 0)
        selected_type = state.get('selected_tower')
        tower_factory = getattr(controller.session, "tower_factory", None)

        for rect, opt in slots:
            cost = tower_factory.get_cost(opt["type"]) if tower_factory else None
            affordable = cost is None or credits >= cost
            is_selected = opt["type"] == selected_type

            bg_color = (34, 38, 48) if affordable else (22, 22, 26)
            pygame.draw.rect(screen, bg_color, rect)

            sprite = self._sprite_for(f"tower_{opt['type']}")
            if sprite:
                self._blit_icon_sprite(screen, sprite, rect)
            else:
                swatch = opt.get("color", (150, 150, 150))
                if not affordable:
                    swatch = tuple(c // 3 for c in swatch)
                inner = rect.inflate(-14, -14)
                pygame.draw.rect(screen, swatch, inner)

            border_color = self.HIGHLIGHT_COLOR if is_selected else self.BORDER_COLOR
            border_width = 3 if is_selected else self.BORDER_WIDTH
            pygame.draw.rect(screen, border_color, rect, border_width)

            hotkey_label = self._hotkey_label(opt.get("key"))
            if hotkey_label:
                badge = small_font.render(hotkey_label, True, (255, 255, 255))
                screen.blit(badge, (rect.x + 3, rect.y + 1))

            if cost is not None:
                cost_color = (255, 215, 0) if affordable else (220, 80, 80)
                cost_surf = small_font.render(str(cost), True, cost_color)
                crect = cost_surf.get_rect(midtop=(rect.centerx, rect.bottom + 2))
                screen.blit(cost_surf, crect)

    def _blit_icon_sprite(self, screen, sprite, rect):
        """Масштабирует спрайт под размер иконки (с небольшим отступом от рамки)."""
        target = rect.inflate(-8, -8)
        scaled = pygame.transform.smoothscale(sprite, (target.width, target.height))
        screen.blit(scaled, target)

    @staticmethod
    def _hotkey_label(key) -> "str | None":
        """Возвращает подпись хоткея для иконки постройки (например, "1" для K_1)."""
        if key is None:
            return None
        try:
            return pygame.key.name(key).upper()
        except Exception:
            logger.warning("Не удалось получить имя клавиши для хоткея %r", key, exc_info=True)
            return None

    def _build_selection_info(self, state, controller, tower_options):
        """Собирает строки текста для панели выбора."""
        info_lines = []
        if state['selected_tower']:
            opt = next((o for o in tower_options if o["type"] == state['selected_tower']), None)
            label = opt["name"] if opt else state['selected_tower']
            info_lines.append(loc.get("hud.build_label", name=label))
            info_lines.append(loc.get("hud.build_hint"))
        elif controller.selected_module:
            mod = controller.selected_module
            info_lines.append(loc.get("hud.tower_level", level=mod.level, max_level=mod.max_level))
            if mod.can_upgrade():
                cost = mod.get_upgrade_cost()
                can_afford = state['credits'] >= cost
                status = loc.get("hud.upgrade_yes") if can_afford else loc.get("hud.upgrade_no")
                info_lines.append(loc.get("hud.upgrade_cost", cost=cost, status=status))
            else:
                info_lines.append(loc.get("hud.max_level"))
        elif controller.selected_enemy:
            enemy = controller.selected_enemy
            name_key = ENEMY_DISPLAY_KEYS.get(getattr(enemy, "type_name", None))
            name = loc.get(name_key) if name_key else type(enemy).__name__
            armor_key = ARMOR_LABEL_KEYS.get(enemy.armor)
            armor_label = loc.get(armor_key) if armor_key else str(enemy.armor)
            faction_key = FACTION_LABEL_KEYS.get(getattr(enemy, "faction", None))
            faction_label = loc.get(faction_key) if faction_key else None
            info_lines.append(loc.get("hud.enemy_label", name=name))
            if faction_label:
                info_lines.append(loc.get("hud.enemy_faction", faction=faction_label))
            info_lines.append(loc.get("hud.enemy_hp", hp=int(enemy.health), max_hp=int(enemy.max_health)))
            info_lines.append(loc.get("hud.enemy_stats", armor=armor_label, speed=int(enemy.speed)))
            info_lines.append(loc.get("hud.enemy_reward", reward=enemy.reward))
        else:
            info_lines.append(loc.get("hud.nothing_selected"))
        return info_lines

    def _draw_selection_zone(self, screen, state, controller, tower_options, small_font, x, y, right, h):
        """Рисует информацию о текущем выборе в левой зоне нижней панели."""
        info_lines = self._build_selection_info(state, controller, tower_options)
        line_height = 17
        for i, line in enumerate(info_lines):
            col = self.TEXT_COLOR
            if "НЕТ" in line:
                col = (255, 100, 100)
            elif "ДА" in line:
                col = (100, 255, 100)
            elif "МАКСИМУМ" in line:
                col = self.HIGHLIGHT_COLOR
            screen.blit(small_font.render(line, True, col), (x, y + i * line_height))

    def _draw_controls_zone(self, screen, camera, small_font, left, y, right, h, width, height):
        """Рисует позицию камеры (живая информация) и кнопку '?' в правой зоне нижней
        панели. Полный список подсказок по управлению раньше был статичным текстом
        здесь же, но при добавлении новой строки стал вылезать за пределы экрана -
        теперь это всплывающая панель по клику на кнопку (см. handle_help_click)."""
        camera_text = loc.get("hud.camera_info", x=int(camera.x), y=int(camera.y), zoom=int(camera.zoom * 100))
        surf = small_font.render(camera_text, True, (180, 180, 180))
        rect = surf.get_rect(topright=(right, y))
        screen.blit(surf, rect)

        self._draw_help_button(screen, width, height, small_font)
        if self.show_help:
            self._draw_help_popup(screen, width, height, small_font)

    def _help_lines(self):
        """Полный список строк подсказок по управлению для всплывающей панели."""
        return [
            loc.get("hud.controls_move"),
            loc.get("hud.controls_drag"),
            loc.get("hud.controls_build"),
            loc.get("hud.controls_select"),
            loc.get("hud.controls_misc"),
            loc.get("hud.controls_alt"),
            loc.get("hud.controls_ranges"),
            loc.get("hud.controls_tech_tree"),
        ]

    def _layout_help_button(self, width, height):
        """Прямоугольник кнопки '?' - нижний правый угол экрана. Используется и при
        отрисовке, и при обработке клика (handle_help_click)."""
        size = self.HELP_BUTTON_SIZE
        return pygame.Rect(width - 16 - size, height - 16 - size, size, size)

    def handle_help_click(self, pos, width, height) -> bool:
        """Переключает показ всплывающей подсказки по управлению, если клик пришёлся
        на кнопку '?'. Возвращает True, если клик был обработан (нужно
        GameView._handle_help_click, чтобы клик не долетал до карты под кнопкой)."""
        if self._layout_help_button(width, height).collidepoint(pos):
            self.show_help = not self.show_help
            return True
        return False

    def _draw_help_button(self, screen, width, height, small_font):
        """Рисует саму кнопку '?': золотая рамка, пока подсказка открыта."""
        rect = self._layout_help_button(width, height)
        bg_color = (55, 75, 40) if self.show_help else (34, 38, 48)
        pygame.draw.rect(screen, bg_color, rect)
        border_color = self.HIGHLIGHT_COLOR if self.show_help else self.BORDER_COLOR
        border_width = 3 if self.show_help else self.BORDER_WIDTH
        pygame.draw.rect(screen, border_color, rect, border_width)
        label = small_font.render("?", True, (255, 255, 255))
        screen.blit(label, label.get_rect(center=rect.center))

    def _draw_help_popup(self, screen, width, height, small_font):
        """Рисует панель с подсказками по управлению над кнопкой '?' - растёт вверх от
        кнопки, поэтому не может вылезти ни за низ, ни за правый край экрана."""
        lines = self._help_lines()
        line_height = self.HELP_POPUP_LINE_HEIGHT
        pad = self.HELP_POPUP_PADDING
        w = self.HELP_POPUP_WIDTH
        h = len(lines) * line_height + pad * 2
        button_rect = self._layout_help_button(width, height)
        x = width - 16 - w
        y = button_rect.top - 8 - h

        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill(self.PANEL_BG)
        screen.blit(surf, (x, y))
        pygame.draw.rect(screen, self.BORDER_COLOR, (x, y, w, h), self.BORDER_WIDTH)

        for i, line in enumerate(lines):
            text_surf = small_font.render(line, True, self.TEXT_COLOR)
            screen.blit(text_surf, (x + pad, y + pad + i * line_height))
