"""Затухание громкости звука по положению относительно вида камеры и по зуму."""
import math

EDGE_FALLOFF_SCREEN_PIXELS = 250.0

# На сильном отдалении камеры (см. Camera.min_zoom - зависит от размера карты и
# окна, поэтому не общая константа) бой уже трудно разглядеть в деталях, и звуки на
# полной громкости ощущаются неуместно резкими - см. запрос пользователя. От 100% до
# ZOOM_FALLOFF_START громкость не меняется, дальше линейно снижается до
# ZOOM_FALLOFF_MIN_VOLUME на самом сильном отдалении (camera.min_zoom).
ZOOM_FALLOFF_START = 0.45
ZOOM_FALLOFF_MIN_VOLUME = 0.05


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


def volume_for_zoom(camera) -> float:
    """Множитель громкости по текущему зуму камеры: 1.0 при zoom >= ZOOM_FALLOFF_START
    (то есть от 100% до 45% громкость не трогаем), дальше линейно снижается до
    ZOOM_FALLOFF_MIN_VOLUME на camera.min_zoom (максимальное отдаление - зависит от
    карты/окна, см. Camera._min_zoom_for_screen). Если min_zoom камеры сам оказался
    >= ZOOM_FALLOFF_START (крошечная карта/большое окно - отдалиться дальше 45%
    физически нельзя), затухать некуда - возвращаем 1.0."""
    if camera.zoom >= ZOOM_FALLOFF_START:
        return 1.0
    min_zoom = getattr(camera, "min_zoom", 0.0)
    span = ZOOM_FALLOFF_START - min_zoom
    if span <= 0:
        return 1.0
    t = max(0.0, min(1.0, (camera.zoom - min_zoom) / span))
    return ZOOM_FALLOFF_MIN_VOLUME + t * (1.0 - ZOOM_FALLOFF_MIN_VOLUME)
