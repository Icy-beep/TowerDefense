"""Затухание громкости звука по положению относительно вида камеры."""
import types

import pytest

from src.core.coordinate import Coordinate
from src.systems.spatial_audio import (
    ZOOM_FALLOFF_MIN_VOLUME,
    ZOOM_FALLOFF_START,
    volume_for_distance,
    volume_for_position,
    volume_for_zoom,
)


def test_volume_for_distance_is_full_at_zero_and_zero_beyond_falloff():
    assert volume_for_distance(0.0, 100.0) == pytest.approx(1.0)
    assert volume_for_distance(100.0, 100.0) == pytest.approx(0.0)
    assert volume_for_distance(200.0, 100.0) == pytest.approx(0.0)


def test_volume_for_distance_falls_off_linearly_between():
    assert volume_for_distance(50.0, 100.0) == pytest.approx(0.5)


def test_volume_for_distance_is_zero_for_non_positive_falloff():
    assert volume_for_distance(10.0, 0.0) == 0.0


def _fake_camera(x=0.0, y=0.0, screen_w=900, screen_h=600, zoom=1.0):
    return types.SimpleNamespace(x=x, y=y, screen_w=screen_w, screen_h=screen_h, zoom=zoom)


def test_volume_for_position_is_full_at_camera_center():
    camera = _fake_camera(x=0.0, y=0.0)
    center = Coordinate(450, 300)

    assert volume_for_position(camera, center) == pytest.approx(1.0)


def test_volume_for_position_is_full_anywhere_inside_the_visible_rectangle():
    camera = _fake_camera(x=0.0, y=0.0)
    near_edge = Coordinate(890, 10)

    assert volume_for_position(camera, near_edge) == pytest.approx(1.0)


def test_volume_for_position_fades_out_just_beyond_the_edge():
    camera = _fake_camera(x=0.0, y=0.0)
    just_outside = Coordinate(950, 300)

    volume = volume_for_position(camera, just_outside)

    assert 0.0 < volume < 1.0


def test_volume_for_position_is_silent_far_outside_the_view():
    camera = _fake_camera(x=0.0, y=0.0)
    far_away = Coordinate(5000, 5000)

    assert volume_for_position(camera, far_away) == 0.0


def test_volume_for_position_falloff_margin_shrinks_in_world_units_when_zoomed_in():
    zoomed_out = _fake_camera(x=0.0, y=0.0, zoom=1.0)
    zoomed_in = _fake_camera(x=0.0, y=0.0, zoom=2.0)
    point_past_edge = Coordinate(950, 300)

    assert volume_for_position(zoomed_in, point_past_edge) < volume_for_position(zoomed_out, point_past_edge)


# ---------------------------------------------------------------------------
# volume_for_zoom - громкость снижается на сильном отдалении камеры (см. запрос
# пользователя: от 45% зума до ~5% на максимальном отдалении).
# ---------------------------------------------------------------------------

def _zoom_camera(zoom, min_zoom=0.1):
    return types.SimpleNamespace(zoom=zoom, min_zoom=min_zoom)


def test_volume_for_zoom_is_full_at_100_percent():
    assert volume_for_zoom(_zoom_camera(zoom=1.0)) == pytest.approx(1.0)


def test_volume_for_zoom_is_full_anywhere_at_or_above_the_falloff_start():
    assert volume_for_zoom(_zoom_camera(zoom=ZOOM_FALLOFF_START)) == pytest.approx(1.0)
    assert volume_for_zoom(_zoom_camera(zoom=0.9)) == pytest.approx(1.0)


def test_volume_for_zoom_reaches_minimum_at_max_zoom_out():
    camera = _zoom_camera(zoom=0.1, min_zoom=0.1)
    assert volume_for_zoom(camera) == pytest.approx(ZOOM_FALLOFF_MIN_VOLUME)


def test_volume_for_zoom_falls_off_linearly_between_start_and_min_zoom():
    camera = _zoom_camera(zoom=0.275, min_zoom=0.1)  # ровно посередине между 0.45 и 0.1
    volume = volume_for_zoom(camera)

    expected_midpoint = (1.0 + ZOOM_FALLOFF_MIN_VOLUME) / 2
    assert volume == pytest.approx(expected_midpoint, abs=0.01)


def test_volume_for_zoom_never_drops_below_the_configured_minimum_even_past_min_zoom():
    """Защита от рассинхрона, если zoom когда-то окажется чуть ниже min_zoom камеры
    (например, только что уменьшили окно) - не должно уйти в отрицательную/безумную
    громкость."""
    camera = _zoom_camera(zoom=0.05, min_zoom=0.1)
    volume = volume_for_zoom(camera)

    assert volume == pytest.approx(ZOOM_FALLOFF_MIN_VOLUME)


def test_volume_for_zoom_stays_full_when_min_zoom_is_not_below_falloff_start():
    """На маленькой карте/большом окне min_zoom может оказаться >= 0.45 - отдалиться
    дальше физически нельзя, поэтому и снижать громкость не на чем."""
    camera = _zoom_camera(zoom=0.5, min_zoom=0.5)
    assert volume_for_zoom(camera) == pytest.approx(1.0)


def test_volume_for_zoom_defaults_min_zoom_gracefully_when_missing():
    """Фейковая камера без min_zoom (как в некоторых старых тестах/двойниках) не
    должна ронять функцию - трактуем как min_zoom=0.0."""
    camera = types.SimpleNamespace(zoom=0.2)
    volume = volume_for_zoom(camera)

    assert 0.0 <= volume <= 1.0
