"""MapRenderer — отрисовка игрового поля: граница карты, база, башни,
противники, снаряды и превью размещения выбранной башни.

Выделено из game_view.py, чтобы у "рисования мира" и "рисования HUD"
(hud_renderer.py) были разные файлы: одна ответственность на
модуль, как и у остальных слоёв проекта (Model/Controller/View)."""
import pygame

from src.core.coordinate import Coordinate

MAP_WIDTH = 4000
MAP_HEIGHT = 4000


class MapRenderer:
    def render(self, screen, camera, session, controller, tower_options, width, height):
        self._draw_border(screen, camera)
        self._draw_placement_grid(screen, camera, session, controller, width, height)
        self._draw_base(screen, camera, session)
        self._draw_spawn_points(screen, camera, session)
        self._draw_modules(screen, camera, session, controller, tower_options)
        self._draw_enemies(screen, camera, session, controller, width, height)
        self._draw_projectiles(screen, camera, session)
        self._draw_placement_preview(screen, camera, session, controller, tower_options)

    def _draw_border(self, screen, camera):
        border_rect = pygame.Rect(
            -camera.x * camera.zoom,
            -camera.y * camera.zoom,
            MAP_WIDTH * camera.zoom,
            MAP_HEIGHT * camera.zoom
        )
        pygame.draw.rect(screen, (50, 50, 50), border_rect, 3)

    def _draw_placement_grid(self, screen, camera, session, controller, width, height):
        """Лёгкая сетка построек — видна только пока выбрана башня для
        постройки, чтобы не захламлять экран в остальное время. Шаг сетки
        берётся из session.map.nav_grid.cell_size — это та же сетка, к
        которой привязывается позиция при постройке (Map.snap_to_grid)."""
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
        """Точки спавна противников — оранжевые маркеры-треугольники,
        чтобы игрок видел, откуда придут волны, ещё до их начала."""
        spawn_points = getattr(session.map, "spawn_points", [])
        for point in spawn_points:
            sx, sy = camera.world_to_screen(point.x, point.y)
            size = max(12, int(14 * camera.zoom))
            triangle = [
                (sx, sy - size),
                (sx - size, sy + size),
                (sx + size, sy + size),
            ]
            pygame.draw.polygon(screen, (255, 140, 0), triangle)
            pygame.draw.polygon(screen, (255, 220, 150), triangle, 2)

    def _draw_base(self, screen, camera, session):
        if not hasattr(session, 'base_position'):
            return
        sx, sy = camera.world_to_screen(session.base_position.x, session.base_position.y)
        pygame.draw.circle(screen, (255, 50, 50), (int(sx), int(sy)), 25)
        pygame.draw.circle(screen, (255, 200, 200), (int(sx), int(sy)), 30, 3)
        hp_ratio = session.base_health / session.max_base_health
        pygame.draw.rect(screen, (50, 50, 50), (int(sx) - 20, int(sy) - 40, 40, 6))
        pygame.draw.rect(screen, (0, 255, 0) if hp_ratio > 0.5 else (255, 50, 50),
                          (int(sx) - 20, int(sy) - 40, int(40 * hp_ratio), 6))

    def _draw_modules(self, screen, camera, session, controller, tower_options):
        for module in session.map.modules:
            color = (100, 100, 100)
            is_selected = (module == controller.selected_module)
            opt = next((o for o in tower_options
                        if o["type"] == getattr(module, "type_name", None)), None)
            if opt:
                color = opt["color"]

            sx, sy = camera.world_to_screen(module.position.x, module.position.y)

            if is_selected:
                pygame.draw.circle(screen, (255, 255, 255),
                                   (int(sx), int(sy)), int(module.range_radius * camera.zoom) + 5, 2)

            pygame.draw.circle(screen, (*color[:3], 40),
                               (int(sx), int(sy)), int(module.range_radius * camera.zoom), 1)
            pygame.draw.circle(screen, color, (int(sx), int(sy)), int(14 * camera.zoom))

            for i in range(module.level):
                pygame.draw.circle(screen, (255, 215, 0),
                                   (int(sx) - 6 + i * 6, int(sy) - 20), 3)

    def _draw_enemies(self, screen, camera, session, controller, width, height):
        selected_enemy = getattr(controller, "selected_enemy", None)
        for enemy in session.map.enemies:
            sx, sy = camera.world_to_screen(enemy.position.x, enemy.position.y)
            if -50 < sx < width + 50 and -50 < sy < height + 50:
                if enemy is selected_enemy:
                    pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), 16, 2)
                hp_ratio = enemy.health / enemy.max_health
                pygame.draw.rect(screen, (50, 50, 50),
                                 (int(sx) - 12, int(sy) - 18, 24, 4))
                pygame.draw.rect(screen, (0, 255, 0) if hp_ratio > 0.5 else (255, 50, 50),
                                 (int(sx) - 12, int(sy) - 18, int(24 * hp_ratio), 4))
                pygame.draw.circle(screen, (220, 50, 50), (int(sx), int(sy)), 10)

    def _draw_projectiles(self, screen, camera, session):
        for proj in session.map.projectiles:
            sx, sy = camera.world_to_screen(proj.position.x, proj.position.y)
            pygame.draw.circle(screen, (255, 255, 200), (int(sx), int(sy)), 3)

    def _draw_placement_preview(self, screen, camera, session, controller, tower_options):
        """Показывает радиус башни под курсором при выборе"""
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
        pygame.draw.circle(screen, marker_color, (int(snap_x), int(snap_y)), 6)
        pygame.draw.circle(screen, (255, 255, 255), (int(snap_x), int(snap_y)), 6, 2)
