class Camera:
    """Камера с поддержкой зума к курсору.
    Не зависит ни от game_view, ни от game_controller — общий, независимый модуль."""

    def __init__(self, screen_w, screen_h, map_w=4000, map_h=4000):
        self.x = 0.0
        self.y = 0.0
        self.screen_w, self.screen_h = screen_w, screen_h
        self.map_w, self.map_h = map_w, map_h
        self.zoom = 1.0
        self.min_zoom, self.max_zoom = 0.3, 2.5
        self.speed = 400.0

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        vis_w = self.screen_w / self.zoom
        vis_h = self.screen_h / self.zoom
        self.x = max(0, min(self.x, self.map_w - vis_w))
        self.y = max(0, min(self.y, self.map_h - vis_h))

    def zoom_at_mouse(self, mx, my, factor):
        """Зумит так, чтобы мировая точка под курсором осталась под курсором."""
        new_zoom = max(self.min_zoom, min(self.max_zoom, self.zoom * factor))
        if abs(new_zoom - self.zoom) < 0.001:
            return
        wx, wy = self.screen_to_world(mx, my)
        self.zoom = new_zoom
        self.x = wx - mx / new_zoom
        self.y = wy - my / new_zoom
        self.move(0, 0)

    def world_to_screen(self, wx, wy):
        return (wx - self.x) * self.zoom, (wy - self.y) * self.zoom

    def screen_to_world(self, sx, sy):
        return sx / self.zoom + self.x, sy / self.zoom + self.y

    def center_on(self, position):
        """position — объект с полями .x и .y (Coordinate)"""
        self.x = position.x - self.screen_w / (2 * self.zoom)
        self.y = position.y - self.screen_h / (2 * self.zoom)
        self.move(0, 0)

    def follow(self, position):
        """Жёсткое следование за целью — для будущего Operator-режима"""
        self.center_on(position)

    def update(self, dt, keys):
        """Непрерывное движение камеры по WASD/стрелкам"""
        import pygame
        dx = dy = 0.0
        speed = self.speed * dt
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy = -speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy = speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx = -speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx = speed
        if dx or dy:
            self.move(dx, dy)
