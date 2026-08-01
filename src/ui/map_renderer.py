"""Отрисовка игрового поля: карта, башни, враги, снаряды."""
import pygame

from src.core.coordinate import Coordinate
from src.entities.projectile import HitscanBeam, MortarShell, ShrapnelPellet
from src.enums import Faction
from src.systems.threat_strategy import ShipLandingStrategy

MAP_WIDTH = 4000
MAP_HEIGHT = 4000

ENEMY_COLORS = {
    "drone_walker": (220, 50, 50),
    "giant_roach": (120, 200, 60),
    "scout_drone": (80, 160, 255),
    "heavy_assault_drone": (150, 60, 200),
    "bio_titan": (40, 140, 40),
    "medic_drone": (80, 255, 220),
}
DEFAULT_ENEMY_COLOR = (220, 50, 50)

FACTION_SPAWN_COLORS = {
    Faction.CORPORATION: (80, 160, 255),
    Faction.FAUNA: (120, 200, 60),
}
DEFAULT_SPAWN_COLOR = (255, 140, 0)


class MapRenderer:
    """Рисует игровое поле."""

    def render(self, screen, camera, session, controller, tower_options, width, height):
        """Рисует все элементы карты за один кадр."""
        keys = pygame.key.get_pressed()
        alt_held = bool(keys[pygame.K_LALT] or keys[pygame.K_RALT])

        self._draw_border(screen, camera)
        self._draw_placement_grid(screen, camera, session, controller, width, height)
        self._draw_base(screen, camera, session)
        self._draw_spawn_points(screen, camera, session)
        self._draw_modules(screen, camera, session, controller, tower_options, alt_held)
        self._draw_enemies(screen, camera, session, controller, width, height)
        self._draw_projectiles(screen, camera, session)
        self._draw_placement_preview(screen, camera, session, controller, tower_options)

    def _draw_border(self, screen, camera):
        """Рисует границу карты."""
        border_rect = pygame.Rect(
            -camera.x * camera.zoom,
            -camera.y * camera.zoom,
            MAP_WIDTH * camera.zoom,
            MAP_HEIGHT * camera.zoom
        )
        pygame.draw.rect(screen, (50, 50, 50), border_rect, 3)

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
        """Рисует точки спавна врагов по фракциям, кроме высаживающихся кораблями."""
        by_faction = getattr(session.map, "spawn_points_by_faction", {}) or {}
        threat_strategies = getattr(session, "threat_strategies", {}) or {}
        if by_faction:
            for faction, points in by_faction.items():
                if isinstance(threat_strategies.get(faction), ShipLandingStrategy):
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

    def _draw_base(self, screen, camera, session):
        """Рисует базу и полоску её здоровья."""
        if session.base_position is None:
            return
        sx, sy = camera.world_to_screen(session.base_position.x, session.base_position.y)
        pygame.draw.circle(screen, (255, 50, 50), (int(sx), int(sy)), 25)
        pygame.draw.circle(screen, (255, 200, 200), (int(sx), int(sy)), 30, 3)
        hp_ratio = session.base_health / session.max_base_health
        pygame.draw.rect(screen, (50, 50, 50), (int(sx) - 20, int(sy) - 40, 40, 6))
        pygame.draw.rect(screen, (0, 255, 0) if hp_ratio > 0.5 else (255, 50, 50),
                          (int(sx) - 20, int(sy) - 40, int(40 * hp_ratio), 6))

    def _draw_modules(self, screen, camera, session, controller, tower_options, alt_held=False):
        """Рисует все башни, их уровень и радиус атаки при необходимости."""
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

            if is_selected or alt_held:
                pygame.draw.circle(screen, (*color[:3], 40),
                                   (int(sx), int(sy)), int(module.range_radius * camera.zoom), 1)
            pygame.draw.circle(screen, color, (int(sx), int(sy)), int(14 * camera.zoom))

            for i in range(module.level):
                pygame.draw.circle(screen, (255, 215, 0),
                                   (int(sx) - 6 + i * 6, int(sy) - 20), 3)

            if module.health < module.max_health:
                hp_ratio = max(0.0, module.health / module.max_health)
                pygame.draw.rect(screen, (50, 50, 50), (int(sx) - 16, int(sy) - 28, 32, 5))
                pygame.draw.rect(screen, (0, 255, 0) if hp_ratio > 0.5 else (255, 50, 50),
                                  (int(sx) - 16, int(sy) - 28, int(32 * hp_ratio), 5))

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
                color = ENEMY_COLORS.get(getattr(enemy, "type_name", None), DEFAULT_ENEMY_COLOR)
                pygame.draw.circle(screen, color, (int(sx), int(sy)), 10)

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
        pygame.draw.circle(screen, marker_color, (int(snap_x), int(snap_y)), 6)
        pygame.draw.circle(screen, (255, 255, 255), (int(snap_x), int(snap_y)), 6, 2)
