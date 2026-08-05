"""Затухание громкости звука по положению относительно вида камеры."""
import math

EDGE_FALLOFF_SCREEN_PIXELS = 250.0


def volume_for_distance(distance: float, falloff_distance: float) -> float:
    """Линейно затухает от 1.0 при distance=0 до 0.0 на falloff_distance."""
    if falloff_distance <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - distance / falloff_distance))


def volume_for_position(camera, position) -> float:
    """Громкость для точки: 1.0 в кадре камеры, затухает за его границами."""
    left, top = camera.x, camera.y
    right = camera.x + camera.screen_w / camera.zoom
    bottom = camera.y + camera.screen_h / camera.zoom

    dx = max(left - position.x, 0.0, position.x - right)
    dy = max(top - position.y, 0.0, position.y - bottom)
    outside_distance = math.hypot(dx, dy)

    falloff_distance = EDGE_FALLOFF_SCREEN_PIXELS / camera.zoom
    return volume_for_distance(outside_distance, falloff_distance)
