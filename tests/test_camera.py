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


# --------------------------------------------------- min_zoom видит границы карты

def test_default_min_zoom_lets_the_whole_map_fit_on_screen():
    """Раньше min_zoom был захардкожен (0.3) и на карте 4000x4000 при экране
    900x600 нельзя было отзумиться так, чтобы видеть оба края карты сразу -
    камера всегда упиралась в границы раньше, чем показывала всю карту."""
    camera = Camera(screen_w=900, screen_h=600, map_w=4000, map_h=4000)

    vis_w = camera.screen_w / camera.min_zoom
    vis_h = camera.screen_h / camera.min_zoom

    assert vis_w >= camera.map_w - 1e-6
    assert vis_h >= camera.map_h - 1e-6


def test_zooming_out_to_min_zoom_reveals_map_border():
    """При максимальном отзуме камера должна упираться ровно в границы
    карты хотя бы по одной оси (той, что "теснее"), а не оставлять её
    края недостижимыми."""
    camera = Camera(screen_w=900, screen_h=600, map_w=4000, map_h=4000)
    camera.x, camera.y = 500.0, 500.0

    for _ in range(100):
        camera.zoom_at_mouse(450, 300, 0.5)

    assert camera.zoom == pytest.approx(camera.min_zoom)
    vis_w = camera.screen_w / camera.zoom
    vis_h = camera.screen_h / camera.zoom
    # по оси высоты 900x600 в карту 4000x4000 упирается ровно (600/4000 меньше 900/4000)
    assert vis_h == pytest.approx(camera.map_h, rel=0.01)
    assert camera.y == pytest.approx(0.0)


def test_extra_visible_space_beyond_map_is_centered_not_pinned_to_corner():
    """Раньше при несовпадении пропорций окна и карты (например, широкое
    окно на квадратной карте) лишнее пространство всегда прижималось к
    x=0 - граница карты повисала где-то посреди экрана, а не выглядела
    рамкой. Теперь она должна быть по центру."""
    camera = Camera(screen_w=1800, screen_h=600, map_w=4000, map_h=4000)
    camera.zoom = camera.min_zoom  # видимая ширина заведомо больше карты
    camera.move(0, 0)

    vis_w = camera.screen_w / camera.zoom
    expected_x = (camera.map_w - vis_w) / 2
    assert camera.x == pytest.approx(expected_x)
    assert camera.x < 0, "лишнее пространство должно быть поровну с обеих сторон карты"
