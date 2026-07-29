"""Регрессионный тест на баг зума: zoom_at_mouse раньше использовал
формулу со смещением на screen_w/2 (как будто экран центрирован в (0,0)),
а world_to_screen/screen_to_world работают без такого смещения (верхний
левый угол экрана — (0,0)). Из-за рассинхрона мировая точка под курсором
"уплывала" при зуме везде, кроме курсора ровно в центре экрана."""
import pytest
from src.core.camera import Camera


@pytest.mark.parametrize("mx, my", [
    (450, 300),  # центр экрана — раньше единственная рабочая точка
    (0, 0),      # угол экрана
    (900, 600),  # противоположный угол
    (200, 500),  # произвольная точка
])
def test_zoom_at_mouse_keeps_world_point_under_cursor(mx, my):
    camera = Camera(screen_w=900, screen_h=600, map_w=4000, map_h=4000)
    camera.x, camera.y = 500.0, 500.0  # не в углу карты, чтобы move() не подрезал границами

    world_before = camera.screen_to_world(mx, my)
    camera.zoom_at_mouse(mx, my, 1.5)
    world_after = camera.screen_to_world(mx, my)

    assert world_after == pytest.approx(world_before, abs=0.5)


def test_zoom_at_mouse_changes_zoom_level():
    camera = Camera(screen_w=900, screen_h=600)
    camera.zoom_at_mouse(300, 200, 1.2)
    assert camera.zoom == pytest.approx(1.2)


def test_zoom_at_mouse_respects_min_max_bounds():
    camera = Camera(screen_w=900, screen_h=600)
    camera.min_zoom, camera.max_zoom = 0.3, 2.5

    for _ in range(50):
        camera.zoom_at_mouse(100, 100, 0.5)
    assert camera.zoom == pytest.approx(camera.min_zoom)

    for _ in range(50):
        camera.zoom_at_mouse(100, 100, 2.0)
    assert camera.zoom == pytest.approx(camera.max_zoom)
