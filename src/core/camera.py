import pygame


class Camera:
    """Камера с зумом к курсору и перемещением по карте."""

    def __init__(self, screen_w, screen_h, map_w=4000, map_h=4000):
        """Создаёт камеру для экрана и карты заданного размера."""
        self.x = 0.0
        self.y = 0.0
        self.screen_w, self.screen_h = screen_w, screen_h
        self.map_w, self.map_h = map_w, map_h
        self.zoom = 1.0
        self.min_zoom = self._min_zoom_for_screen()
        self.max_zoom = 2.5
        self.speed = 400.0
        self.boost_multiplier = 2.5

    def _min_zoom_for_screen(self) -> float:
        """Зум до границ экрана"""
        return min(self.screen_w / self.map_w, self.screen_h / self.map_h)

    def resize(self, screen_w, screen_h):
        """Обновляет видимую область при изменении размера окна."""
        self.screen_w, self.screen_h = screen_w, screen_h
        self.min_zoom = self._min_zoom_for_screen()
        self.zoom = max(self.min_zoom, min(self.max_zoom, self.zoom))
        self.move(0, 0)

    def move(self, dx, dy):
        """Должен смещать камеру не давая выйти за пределы экрана."""
        self.x += dx
        self.y += dy
        vis_w = self.screen_w / self.zoom
        vis_h = self.screen_h / self.zoom
        if vis_w >= self.map_w:
            self.x = (self.map_w - vis_w) / 2
        else:
            self.x = max(0, min(self.x, self.map_w - vis_w))
        if vis_h >= self.map_h:
            self.y = (self.map_h - vis_h) / 2
        else:
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
        """Переводит мировые координаты в экранные."""
        return (wx - self.x) * self.zoom, (wy - self.y) * self.zoom

    def screen_to_world(self, sx, sy):
        """Переводит экранные координаты в мировые."""
        return sx / self.zoom + self.x, sy / self.zoom + self.y

    def center_on(self, position):
        """Центрирует камеру на заданной точке."""
        self.x = position.x - self.screen_w / (2 * self.zoom)
        self.y = position.y - self.screen_h / (2 * self.zoom)
        self.move(0, 0)

    def follow(self, position):
        """Мгновенно следует за целью."""
        self.center_on(position)

    def update(self, dt, keys):
        """Двигает камеру по нажатым клавишам WASD/стрелок с ускорением по Shift."""
        dx = dy = 0.0
        speed = self.speed * dt
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            speed *= self.boost_multiplier
        if keys[pygame.K_w] or keys[pygame.K_UP]: dy = -speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy = speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx = -speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx = speed
        if dx or dy:
            self.move(dx, dy)
