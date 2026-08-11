"""Отрисовка игрового поля: карта, башни, враги, снаряды."""
import pygame

from src.core.coordinate import Coordinate
from src.entities.defense_module import DefenseModule
from src.entities.projectile import HitscanBeam, MortarShell, ShrapnelPellet
from src.enums import Faction
from src.systems.threat_strategy import ShipLandingStrategy

ENEMY_COLORS = {
    "drone_walker": (220, 50, 50),
    "giant_roach": (120, 200, 60),
    "scout_drone": (80, 160, 255),
    "heavy_assault_drone": (150, 60, 200),
    "bio_titan": (40, 140, 40),
    "medic_drone": (80, 255, 220),
    "sniper_drone": (255, 210, 60),
}
DEFAULT_ENEMY_COLOR = (220, 50, 50)

# Множитель к обычному размеру спрайта врага (см. MapRenderer._enemy_screen_size) -
# "гигантский" таракан должен и выглядеть крупнее, а не только иметь больше HP (см.
# задачу пользователя на замедление + компенсацию здоровьем/бронёй).
ENEMY_SPRITE_SIZE_MULTIPLIERS = {
    "giant_roach": 1.4,
}

# Множитель ширины спрайта постройки (см. MapRenderer._blit_scaled) - генератор и
# пилон после автообрезки реально шире, чем выше (bbox ~1.39 и ~1.33 к высоте), но
# без этого сжимались в квадрат вместе со всеми остальными башнями (см. запрос
# пользователя увеличить их по ширине).
TOWER_SPRITE_WIDTH_MULTIPLIERS = {
    "generator": 1.4,
    "pylon": 1.35,
}

FACTION_SPAWN_COLORS = {
    Faction.CORPORATION: (80, 160, 255),
    Faction.FAUNA: (120, 200, 60),
}
DEFAULT_SPAWN_COLOR = (255, 140, 0)


class MapRenderer:
    """Рисует игровое поле."""

    BACKGROUND_TILE_WORLD_SIZE = 200
    BACKGROUND_FALLBACK_COLOR = (48, 50, 55)

    TOWER_SPRITE_FOOTPRINT_MARGIN = 8
    TOWER_SPRITE_MIN_SCREEN_SIZE = 30

    ENEMY_SPRITE_WORLD_SIZE = 20
    ENEMY_SPRITE_MIN_SCREEN_SIZE = 20

    BASE_SPRITE_WORLD_SIZE = 60
    BASE_SPRITE_MIN_SCREEN_SIZE = 50

    NEST_SPRITE_WORLD_SIZE = 34
    NEST_SPRITE_MIN_SCREEN_SIZE = 28

    LOCKED_SECTOR_OVERLAY_COLOR = (0, 0, 0)
    LOCKED_SECTOR_OVERLAY_ALPHA = 150
    SECTOR_BORDER_COLOR_LOCKED = (255, 90, 40)
    SECTOR_BORDER_COLOR_UNLOCKED = (90, 200, 255)
    SECTOR_BORDER_WIDTH = 2

    def __init__(self, sprite_manager=None):
        """Запоминает SpriteManager; без него (или без спрайта под ключ) рисует примитивами."""
        self.sprite_manager = sprite_manager
        self._range_overlay = None

    def _range_overlay_surface(self, size):
        """Возвращает переиспользуемую SRCALPHA-поверхность размером с экран для
        полупрозрачных колец радиуса (см. _draw_modules). pygame.draw.circle с
        альфа-цветом молча игнорирует альфу при рисовании прямо на обычный screen
        (у него нет по-пиксельного альфа-канала) - тем же способом уже обходили это
        для секторов, см. _draw_sector_overlay. Держим одну поверхность на кадр
        вместо новой на каждую башню - иначе при постоянном показе радиусов у
        десятков построек будет создаваться и уничтожаться десяток поверхностей
        каждый кадр."""
        if self._range_overlay is None or self._range_overlay.get_size() != size:
            self._range_overlay = pygame.Surface(size, pygame.SRCALPHA)
        else:
            self._range_overlay.fill((0, 0, 0, 0))
        return self._range_overlay

    def _sprite_for(self, key, elapsed_time):
        """Возвращает текущий кадр спрайта для ключа, или None, если спрайтов нет/не подключены."""
        if not self.sprite_manager:
            return None
        return self.sprite_manager.get_frame(key, elapsed_time)

    def _sprite_for_angle(self, key, angle_degrees):
        """Возвращает кадр, ближайший к азимуту (для направленных спрайтов вроде поворота
        башни), или None, если спрайтов нет/не подключены."""
        if not self.sprite_manager:
            return None
        return self.sprite_manager.get_frame_for_angle(key, angle_degrees)

    def _blit_scaled(self, screen, sprite, sx, sy, target_size, width_multiplier=1.0):
        """Масштабирует спрайт под target_size (диаметр в пикселях, высота) и рисует
        центром в (sx, sy). width_multiplier растягивает только ширину - нужно
        генератору/пилону, чьи спрайты после автообрезки реально шире, чем выше, но
        раньше сжимались в квадрат вместе со всеми остальными постройками (см.
        TOWER_SPRITE_WIDTH_MULTIPLIERS, запрос пользователя)."""
        target_size = max(1, int(target_size))
        target_width = max(1, int(target_size * width_multiplier))
        scaled = pygame.transform.smoothscale(sprite, (target_width, target_size))
        rect = scaled.get_rect(center=(int(sx), int(sy)))
        screen.blit(scaled, rect)

    def _tower_screen_size(self, camera, cell_size):
        """Диаметр спрайта башни в пикселях: занимает почти весь footprint в
        DefenseModule.FOOTPRINT_CELLS клеток (с небольшим отступом, чтобы соседние башни не
        сливались друг с другом на глаз), но не мельче TOWER_SPRITE_MIN_SCREEN_SIZE при отдалении камеры."""
        world_size = DefenseModule.FOOTPRINT_CELLS * cell_size - self.TOWER_SPRITE_FOOTPRINT_MARGIN
        return max(world_size * camera.zoom, self.TOWER_SPRITE_MIN_SCREEN_SIZE)

    def _enemy_screen_size(self, camera, type_name=None):
        """Диаметр спрайта врага в пикселях: растёт вместе с зумом камеры (раньше был жёстко
        зафиксирован, из-за чего при приближении враг визуально становился мельче на фоне
        выросшей остальной карты), но не мельче ENEMY_SPRITE_MIN_SCREEN_SIZE при отдалении.
        type_name умножает итоговый размер по ENEMY_SPRITE_SIZE_MULTIPLIERS (например,
        giant_roach крупнее остальных)."""
        base = max(self.ENEMY_SPRITE_WORLD_SIZE * camera.zoom, self.ENEMY_SPRITE_MIN_SCREEN_SIZE)
        return base * ENEMY_SPRITE_SIZE_MULTIPLIERS.get(type_name, 1.0)

    def _base_screen_size(self, camera):
        """Диаметр спрайта базы в пикселях: растёт вместе с зумом камеры, как башни и враги -
        раньше был жёстко зафиксирован в 50px на экране и при приближении визуально "терялся"
        на фоне выросших построек и карты, но не мельче BASE_SPRITE_MIN_SCREEN_SIZE при отдалении."""
        return max(self.BASE_SPRITE_WORLD_SIZE * camera.zoom, self.BASE_SPRITE_MIN_SCREEN_SIZE)

    def _nest_screen_size(self, camera):
        """Диаметр спрайта гнезда фауны в пикселях - растёт вместе с зумом камеры, как база и
        враги, но не мельче NEST_SPRITE_MIN_SCREEN_SIZE при отдалении."""
        return max(self.NEST_SPRITE_WORLD_SIZE * camera.zoom, self.NEST_SPRITE_MIN_SCREEN_SIZE)

    def _draw_background(self, screen, camera, width, height):
        """Рисует фон карты под всеми объектами: тайлит спрайт грунта, иначе — заливка цветом,
        достаточно светлым, чтобы тёмные спрайты башен/врагов не сливались с фоном."""
        sprite = self._sprite_for("map_background", 0.0)
        if not sprite:
            screen.fill(self.BACKGROUND_FALLBACK_COLOR)
            return

        tile_size = max(1, int(self.BACKGROUND_TILE_WORLD_SIZE * camera.zoom))
        tile = pygame.transform.smoothscale(sprite, (tile_size, tile_size))
        start_x = (int(-camera.x * camera.zoom) % tile_size) - tile_size
        start_y = (int(-camera.y * camera.zoom) % tile_size) - tile_size

        y = start_y
        while y < height:
            x = start_x
            while x < width:
                screen.blit(tile, (x, y))
                x += tile_size
            y += tile_size

    def render(self, screen, camera, session, controller, tower_options, width, height):
        """Рисует все элементы карты за один кадр."""
        keys = pygame.key.get_pressed()
        alt_held = bool(keys[pygame.K_LALT] or keys[pygame.K_RALT])
        show_tower_ranges = getattr(controller, "show_tower_ranges", False)
        show_power_radii = getattr(controller, "show_power_radii", False)

        self._draw_background(screen, camera, width, height)
        self._draw_sector_overlay(screen, camera, session, width, height)
        self._draw_placement_grid(screen, camera, session, controller, width, height)
        self._draw_base(screen, camera, session, show_power_radii)
        self._draw_spawn_points(screen, camera, session)
        self._draw_pending_landings(screen, camera, session)
        self._draw_power_links(screen, camera, session)
        self._draw_modules(screen, camera, session, controller, tower_options, alt_held,
                            show_tower_ranges, show_power_radii)
        self._draw_enemies(screen, camera, session, controller, width, height)
        self._draw_projectiles(screen, camera, session)
        self._draw_placement_preview(screen, camera, session, controller, tower_options)

    def _draw_sector_overlay(self, screen, camera, session, width, height):
        """Затемняет ещё не открытые секторы карты (см. src/systems/sector.py и
        GameSession.unlock_sector_at) полупрозрачным тёмным прямоугольником и рисует
        цветную границу вокруг КАЖДОГО сектора - не только закрытого, но и уже
        открытого - чтобы сетка секторов оставалась видна и после открытия (иначе
        по клику Ctrl+ЛКМ было не понять, где именно проходит граница следующего
        сектора на продажу). Карты без секторов (session.map.sectors пуст - старые/
        тестовые карты) не затрагиваются."""
        sectors = getattr(session.map, "sectors", None)
        if not sectors:
            return
        screen_rect = pygame.Rect(0, 0, width, height)
        visible = []
        for sector in sectors:
            x_min, y_min, x_max, y_max = sector.bounds
            sx1, sy1 = camera.world_to_screen(x_min, y_min)
            sx2, sy2 = camera.world_to_screen(x_max, y_max)
            # int() каждого угла ОТДЕЛЬНО, а не int(sx2 - sx1) для ширины: соседний
            # сектор считает свою левую границу как int() от ТОЙ ЖЕ мировой координаты
            # (общая граница x_max этого сектора == x_min соседнего), так что квадраты
            # обязаны сходиться день в день. int(sx2 - sx1) же округляет разность
            # независимо от округления самих углов и мог отличаться от соседского
            # int() на 1px - отсюда тонкая мерцающая при зуме щель между секторами.
            left, top = int(sx1), int(sy1)
            right, bottom = int(sx2), int(sy2)
            rect = pygame.Rect(left, top, right - left, bottom - top)
            if not rect.colliderect(screen_rect):
                continue
            visible.append((rect, sector))

            if sector.unlocked:
                continue
            clipped = rect.clip(screen_rect)
            if clipped.width <= 0 or clipped.height <= 0:
                continue
            overlay = pygame.Surface((clipped.width, clipped.height), pygame.SRCALPHA)
            overlay.fill((*self.LOCKED_SECTOR_OVERLAY_COLOR, self.LOCKED_SECTOR_OVERLAY_ALPHA))
            screen.blit(overlay, (clipped.x, clipped.y))

        # Границы - отдельным проходом поверх всех затемнений: сначала открытые
        # (тихий цвет), потом закрытые (яркий) - на общей границе открытого и
        # закрытого сектора должен победить более заметный "закрыто" цвет.
        for rect, sector in visible:
            if sector.unlocked:
                pygame.draw.rect(screen, self.SECTOR_BORDER_COLOR_UNLOCKED, rect, self.SECTOR_BORDER_WIDTH)
        for rect, sector in visible:
            if not sector.unlocked:
                pygame.draw.rect(screen, self.SECTOR_BORDER_COLOR_LOCKED, rect, self.SECTOR_BORDER_WIDTH)

    def _draw_placement_grid(self, screen, camera, session, controller, width, height):
        """Рисует сетку построек, пока выбрана башня для постройки."""
        if not getattr(controller, "selected_tower_type", None):
            return

        cell = session.map.nav_grid.cell_size
        step = cell * camera.zoom
        if step < 4:
            return

        start_col = int(camera.x // cell)
        start_row = int(camera.y // cell)
        end_col = int((camera.x + width / camera.zoom) // cell) + 1
        end_row = int((camera.y + height / camera.zoom) // cell) + 1

        color = (90, 90, 90)
        for col in range(start_col, end_col + 1):
            sx, _ = camera.world_to_screen(col * cell, 0)
            if 0 <= sx <= width:
                pygame.draw.line(screen, color, (sx, 0), (sx, height))
        for row in range(start_row, end_row + 1):
            _, sy = camera.world_to_screen(0, row * cell)
            if 0 <= sy <= height:
                pygame.draw.line(screen, color, (0, sy), (width, sy))

    def _draw_spawn_points(self, screen, camera, session):
        """Рисует точки спавна врагов по фракциям, кроме высаживающихся кораблями и
        гнёзд фауны (у них своя отрисовка с полоской здоровья - см. _draw_fauna_nests)."""
        fauna_nests = getattr(session.map, "fauna_nests", None)
        if fauna_nests:
            self._draw_fauna_nests(screen, camera, fauna_nests, getattr(session, "elapsed_time", 0.0))

        by_faction = getattr(session.map, "spawn_points_by_faction", {}) or {}
        threat_strategies = getattr(session, "threat_strategies", {}) or {}
        if by_faction:
            for faction, points in by_faction.items():
                if isinstance(threat_strategies.get(faction), ShipLandingStrategy):
                    continue
                if faction == Faction.FAUNA and fauna_nests:
                    continue
                color = FACTION_SPAWN_COLORS.get(faction, DEFAULT_SPAWN_COLOR)
                for point in points:
                    self._draw_spawn_marker(screen, camera, point, color)
        else:
            for point in getattr(session.map, "spawn_points", []):
                self._draw_spawn_marker(screen, camera, point, DEFAULT_SPAWN_COLOR)

    def _draw_spawn_marker(self, screen, camera, point, color):
        """Рисует один маркер точки спавна."""
        sx, sy = camera.world_to_screen(point.x, point.y)
        size = max(12, int(14 * camera.zoom))
        triangle = [
            (sx, sy - size),
            (sx - size, sy + size),
            (sx + size, sy + size),
        ]
        pygame.draw.polygon(screen, color, triangle)
        pygame.draw.polygon(screen, (255, 255, 255), triangle, 2)

    def _draw_fauna_nests(self, screen, camera, nests, elapsed_time=0.0):
        """Рисует гнёзда фауны спрайтом (если он есть - см. assets/sprites/fauna_nest/) или,
        пока его нет, маркером точки спавна, и полоской здоровья - в отличие от обычных точек
        спавна, гнёзда можно уничтожить (см. FaunaNest, Map.update)."""
        color = FACTION_SPAWN_COLORS.get(Faction.FAUNA, DEFAULT_SPAWN_COLOR)
        for nest in nests:
            if not nest.is_alive():
                continue
            sx, sy = camera.world_to_screen(nest.position.x, nest.position.y)
            sprite = self._sprite_for("fauna_nest", elapsed_time)
            if sprite:
                self._blit_scaled(screen, sprite, sx, sy, target_size=self._nest_screen_size(camera))
            else:
                self._draw_spawn_marker(screen, camera, nest.position, color)

            hp_ratio = max(0.0, nest.health / nest.max_health)
            bar_y = int(sy) - int(14 * camera.zoom) - 10
            pygame.draw.rect(screen, (50, 50, 50), (int(sx) - 16, bar_y, 32, 5))
            pygame.draw.rect(screen, (0, 255, 0) if hp_ratio > 0.5 else (255, 50, 50),
                              (int(sx) - 16, bar_y, int(32 * hp_ratio), 5))

    LANDING_WARNING_MAX_RADIUS = 55.0

    def _draw_pending_landings(self, screen, camera, session):
        """Рисует маркеры высадки Corporation - место на границе карты, где через
        time_remaining секунд материализуется отряд (ShipLandingStrategy.pending_landings).
        Раньше нигде не отображались, хотя предупреждение по игровой логике уже было."""
        threat_strategies = getattr(session, "threat_strategies", {}) or {}
        for faction, strategy in threat_strategies.items():
            if not isinstance(strategy, ShipLandingStrategy):
                continue
            color = FACTION_SPAWN_COLORS.get(faction, DEFAULT_SPAWN_COLOR)
            for landing in strategy.pending_landings:
                self._draw_pending_landing_marker(screen, camera, landing, strategy.warning_time, color)

    def _draw_pending_landing_marker(self, screen, camera, landing, warning_time, color):
        """Рисует одну точку высадки: внешнее кольцо цвета фракции и стягивающееся к
        центру белое кольцо-обратный отсчёт, наглядно показывающее, сколько времени
        осталось до появления отряда."""
        sx, sy = camera.world_to_screen(landing.position.x, landing.position.y)
        progress = 1.0 - max(0.0, landing.time_remaining) / warning_time if warning_time > 0 else 1.0
        progress = min(1.0, max(0.0, progress))

        outer_radius = max(10, int(self.LANDING_WARNING_MAX_RADIUS * camera.zoom))
        inner_radius = max(4, int(outer_radius * (1.0 - progress)))

        pygame.draw.line(screen, color, (sx - outer_radius, sy), (sx + outer_radius, sy), 1)
        pygame.draw.line(screen, color, (sx, sy - outer_radius), (sx, sy + outer_radius), 1)
        pygame.draw.circle(screen, color, (int(sx), int(sy)), outer_radius, 2)
        pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), inner_radius, 3)

    BASE_POWER_RADIUS_RING_COLOR = (255, 215, 0)

    def _draw_base(self, screen, camera, session, show_power_radii=False):
        """Рисует базу и полоску её здоровья."""
        if session.base_position is None:
            return
        sx, sy = camera.world_to_screen(session.base_position.x, session.base_position.y)

        if show_power_radii:
            self._draw_base_power_radius(screen, camera, session, sx, sy)

        sprite = self._sprite_for("base", getattr(session, "elapsed_time", 0.0))
        if sprite:
            self._blit_scaled(screen, sprite, sx, sy, target_size=self._base_screen_size(camera))
        else:
            pygame.draw.circle(screen, (255, 50, 50), (int(sx), int(sy)), 25)
            pygame.draw.circle(screen, (255, 200, 200), (int(sx), int(sy)), 30, 3)
        hp_ratio = session.base_health / session.max_base_health
        pygame.draw.rect(screen, (50, 50, 50), (int(sx) - 20, int(sy) - 40, 40, 6))
        pygame.draw.rect(screen, (0, 255, 0) if hp_ratio > 0.5 else (255, 50, 50),
                          (int(sx) - 20, int(sy) - 40, int(40 * hp_ratio), 6))

    def _draw_base_power_radius(self, screen, camera, session, sx, sy):
        """Рисует радиус бесплатного питания от базы (Map.BASE_POWER_RADIUS) - в его
        пределах боевые башни и узлы энергосети запитаны без генератора/пилона (см.
        Map._update_power_grid). Раньше кнопка/хоткей G показывала радиусы только у
        пилонов/генераторов, но не у самой базы (см. запрос пользователя). Радиус
        читается прямо с session.map.BASE_POWER_RADIUS, а не дублируется константой
        здесь - иначе отрисовка могла бы разойтись с реальной механикой."""
        if not getattr(session.map, "power_grid_enabled", False):
            return
        radius = getattr(session.map, "BASE_POWER_RADIUS", None)
        if not radius:
            return
        screen_radius = int(radius * camera.zoom)
        if screen_radius <= 0:
            return
        size = screen_radius * 2
        overlay = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(overlay, (*self.BASE_POWER_RADIUS_RING_COLOR, 90),
                            (screen_radius, screen_radius), screen_radius, 2)
        screen.blit(overlay, (int(sx) - screen_radius, int(sy) - screen_radius))

    def _draw_power_links(self, screen, camera, session):
        """Рисует линии энергосети между запитанными узлами (и от базы к ним) - чисто
        информативно, чтобы игрок видел, что от чего получает питание."""
        for start, end in getattr(session.map, "power_links", []):
            sx, sy = camera.world_to_screen(start.x, start.y)
            ex, ey = camera.world_to_screen(end.x, end.y)
            pygame.draw.line(screen, (255, 215, 0), (sx, sy), (ex, ey), 1)

    def _draw_modules(self, screen, camera, session, controller, tower_options, alt_held=False,
                       show_tower_ranges=False, show_power_radii=False):
        """Рисует все башни, их уровень и радиус атаки при необходимости. Радиус
        показывается: у выделенной постройки - всегда, у всех построек разом - пока
        держишь ALT, а также постоянно у своей категории отдельно от ALT - у боевых
        башен при show_tower_ranges, у энергосети (пилоны/генераторы, IS_COMBAT_TOWER=False -
        см. power_infrastructure.py) при show_power_radii (кнопки/хоткеи T и G в HUD).
        Полупрозрачные кольца копятся на отдельной overlay-поверхности и блитятся одним
        куском в конце (см. _range_overlay_surface) - иначе альфа молча игнорируется."""
        range_overlay = self._range_overlay_surface(screen.get_size())
        any_ring_drawn = False
        for module in session.map.modules:
            color = (100, 100, 100)
            is_selected = (module == controller.selected_module)
            opt = next((o for o in tower_options
                        if o["type"] == getattr(module, "type_name", None)), None)
            if opt:
                color = opt["color"]

            is_powered = getattr(module, "is_powered", True)
            if not is_powered:
                color = tuple((c + 90) // 3 for c in color)

            cell_size = getattr(getattr(session.map, "nav_grid", None), "cell_size", 32)

            if module.is_landing:
                self._draw_landing_module(screen, camera, module, color, cell_size)
                continue

            sx, sy = camera.world_to_screen(module.position.x, module.position.y)

            is_combat_tower = getattr(module, "IS_COMBAT_TOWER", True)
            persistent_range = show_tower_ranges if is_combat_tower else show_power_radii

            if is_selected:
                pygame.draw.circle(screen, (255, 255, 255),
                                   (int(sx), int(sy)), int(module.range_radius * camera.zoom) + 5, 2)

            if is_selected or alt_held or persistent_range:
                pygame.draw.circle(range_overlay, (*color[:3], 90),
                                   (int(sx), int(sy)), int(module.range_radius * camera.zoom), 2)
                any_ring_drawn = True

            type_name = getattr(module, "type_name", "")
            tower_size = self._tower_screen_size(camera, cell_size)
            sprite = self._sprite_for_angle(f"tower_{type_name}", getattr(module, "facing_angle", 0.0))
            if sprite:
                width_mult = TOWER_SPRITE_WIDTH_MULTIPLIERS.get(type_name, 1.0)
                self._blit_scaled(screen, sprite, sx, sy, target_size=tower_size, width_multiplier=width_mult)
            else:
                pygame.draw.circle(screen, color, (int(sx), int(sy)), int(tower_size / 2))

            if not is_powered:
                pygame.draw.circle(screen, (255, 60, 60), (int(sx), int(sy)), int(tower_size / 2) + 3, 2)

            if module.health < module.max_health:
                hp_ratio = max(0.0, module.health / module.max_health)
                pygame.draw.rect(screen, (50, 50, 50), (int(sx) - 16, int(sy) - 28, 32, 5))
                pygame.draw.rect(screen, (0, 255, 0) if hp_ratio > 0.5 else (255, 50, 50),
                                  (int(sx) - 16, int(sy) - 28, int(32 * hp_ratio), 5))

        if any_ring_drawn:
            screen.blit(range_overlay, (0, 0))

    def _draw_landing_module(self, screen, camera, module, color, cell_size):
        """Рисует падающую с орбиты башню: тень на земле, зону удара и опускающийся спрайт."""
        sx, sy = camera.world_to_screen(module.position.x, module.position.y)
        impact_radius = int(module.LANDING_IMPACT_RADIUS * camera.zoom)
        pygame.draw.circle(screen, (255, 120, 0, 60), (int(sx), int(sy)), impact_radius, 1)
        shadow_scale = max(0.3, 1.0 - module.landing_progress * 0.5)
        pygame.draw.circle(screen, (20, 20, 20), (int(sx), int(sy)), int(10 * camera.zoom * shadow_scale))

        pod_y = sy - module.landing_height * camera.zoom
        pod_size = self._tower_screen_size(camera, cell_size)
        sprite = self._sprite_for("landing_pod", module.landing_elapsed)
        if sprite:
            self._blit_scaled(screen, sprite, sx, pod_y, target_size=pod_size)
        else:
            pygame.draw.circle(screen, color, (int(sx), int(pod_y)), int(pod_size / 2))
            pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(pod_y)), int(pod_size / 2), 2)

    def _draw_enemies(self, screen, camera, session, controller, width, height):
        """Рисует врагов, их полоски здоровья и линии эскорта к лидеру."""
        selected_enemy = getattr(controller, "selected_enemy", None)
        for enemy in session.map.enemies:
            leader = getattr(enemy, "group_leader", None)
            if leader is not None:
                ex, ey = camera.world_to_screen(enemy.position.x, enemy.position.y)
                lx, ly = camera.world_to_screen(leader.position.x, leader.position.y)
                pygame.draw.line(screen, (150, 150, 60), (ex, ey), (lx, ly), 1)

        for enemy in session.map.enemies:
            sx, sy = camera.world_to_screen(enemy.position.x, enemy.position.y)
            if -50 < sx < width + 50 and -50 < sy < height + 50:
                if enemy is selected_enemy:
                    pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), 16, 2)

                if getattr(enemy, "is_patrolling", False):
                    pygame.draw.circle(screen, (255, 220, 0), (int(sx), int(sy)), 14, 2)

                if getattr(enemy, "is_group_leader", False):
                    pygame.draw.circle(screen, (255, 200, 0), (int(sx), int(sy)), 13, 2)

                hp_ratio = enemy.health / enemy.max_health
                pygame.draw.rect(screen, (50, 50, 50),
                                 (int(sx) - 12, int(sy) - 18, 24, 4))
                pygame.draw.rect(screen, (0, 255, 0) if hp_ratio > 0.5 else (255, 50, 50),
                                 (int(sx) - 12, int(sy) - 18, int(24 * hp_ratio), 4))

                type_name = getattr(enemy, "type_name", None)
                enemy_size = self._enemy_screen_size(camera, type_name)
                sprite = self._sprite_for(f"enemy_{type_name}", getattr(session, "elapsed_time", 0.0))
                if sprite:
                    self._blit_scaled(screen, sprite, sx, sy, target_size=enemy_size)
                else:
                    color = ENEMY_COLORS.get(type_name, DEFAULT_ENEMY_COLOR)
                    pygame.draw.circle(screen, color, (int(sx), int(sy)), int(enemy_size / 2))

    def _draw_projectiles(self, screen, camera, session):
        """Рисует все снаряды на карте, каждый тип по-своему."""
        for proj in session.map.projectiles:
            if isinstance(proj, HitscanBeam):
                self._draw_beam(screen, camera, proj)
            elif isinstance(proj, MortarShell):
                self._draw_mortar_shell(screen, camera, proj)
            elif isinstance(proj, ShrapnelPellet):
                self._draw_shrapnel(screen, camera, proj)
            else:
                self._draw_bullet(screen, camera, proj)

    def _draw_beam(self, screen, camera, beam):
        """Рисует лазерный луч."""
        ox, oy = camera.world_to_screen(beam.origin.x, beam.origin.y)
        ex, ey = camera.world_to_screen(beam.end.x, beam.end.y)
        pygame.draw.line(screen, (120, 220, 255), (ox, oy), (ex, ey), 2)
        pygame.draw.circle(screen, (200, 240, 255), (int(ex), int(ey)), 4)

    def _draw_bullet(self, screen, camera, bullet):
        """Рисует пулю."""
        sx, sy = camera.world_to_screen(bullet.position.x, bullet.position.y)
        pygame.draw.circle(screen, (255, 255, 150), (int(sx), int(sy)), 3)

    def _draw_shrapnel(self, screen, camera, pellet):
        """Рисует осколок шрапнели."""
        sx, sy = camera.world_to_screen(pellet.position.x, pellet.position.y)
        pygame.draw.circle(screen, (255, 150, 60), (int(sx), int(sy)), 2)

    def _draw_mortar_shell(self, screen, camera, shell):
        """Рисует миномётный снаряд с тенью на земле."""
        sx, sy = camera.world_to_screen(shell.position.x, shell.position.y)
        pygame.draw.circle(screen, (35, 35, 35), (int(sx), int(sy)), 5)
        shell_y = sy - shell.height * camera.zoom
        pygame.draw.circle(screen, (90, 90, 90), (int(sx), int(shell_y)), 5)

    def _draw_placement_preview(self, screen, camera, session, controller, tower_options):
        """Показывает радиус башни под курсором при выборе."""
        selected_type = controller.selected_tower_type
        if not selected_type:
            return

        mouse_x, mouse_y = pygame.mouse.get_pos()
        wx, wy = camera.screen_to_world(mouse_x, mouse_y)
        pos = session.map.snap_to_grid(Coordinate(wx, wy))
        snap_x, snap_y = camera.world_to_screen(pos.x, pos.y)

        preview_tower = session.tower_factory.create(selected_type, pos)
        tower_range = preview_tower.range_radius if preview_tower else 100
        opt = next((o for o in tower_options if o["type"] == selected_type), None)
        tower_color = opt["color"] if opt else (255, 255, 255)

        valid = controller._is_valid_position(pos)

        screen_radius = int(tower_range * camera.zoom)
        alpha_color = (*tower_color, 60 if valid else 30)

        preview_surf = pygame.Surface((screen_radius * 2, screen_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(preview_surf, alpha_color, (screen_radius, screen_radius), screen_radius, 2)
        screen.blit(preview_surf, (snap_x - screen_radius, snap_y - screen_radius))

        marker_color = (0, 255, 0) if valid else (255, 0, 0)

        footprint_size = DefenseModule.FOOTPRINT_CELLS * session.map.nav_grid.cell_size * camera.zoom
        footprint_rect = pygame.Rect(0, 0, int(footprint_size), int(footprint_size))
        footprint_rect.center = (int(snap_x), int(snap_y))
        pygame.draw.rect(screen, marker_color, footprint_rect, 2)

        pygame.draw.circle(screen, marker_color, (int(snap_x), int(snap_y)), 6)
        pygame.draw.circle(screen, (255, 255, 255), (int(snap_x), int(snap_y)), 6, 2)
