"""Затухание громкости звука по положению относительно вида камеры."""
import types

import pytest

from src.core.coordinate import Coordinate
from src.systems.spatial_audio import volume_for_distance, volume_for_position


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
