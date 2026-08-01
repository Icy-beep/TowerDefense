"""Ресемплинг для вариации питча (высоты тона) звука."""
import array

from src.systems.pitch_shift import resample_pitch


def test_resample_pitch_returns_unchanged_copy_when_factor_is_one():
    samples = array.array("h", [0, 100, 200, 300, 400, 500])

    result = resample_pitch(samples, channels=1, pitch_factor=1.0)

    assert list(result) == list(samples)


def test_resample_pitch_higher_factor_produces_fewer_frames():
    samples = array.array("h", range(0, 200, 10))

    result = resample_pitch(samples, channels=1, pitch_factor=2.0)

    assert len(result) < len(samples)


def test_resample_pitch_lower_factor_produces_more_frames():
    samples = array.array("h", range(0, 200, 10))

    result = resample_pitch(samples, channels=1, pitch_factor=0.5)

    assert len(result) > len(samples)


def test_resample_pitch_keeps_channels_interleaved_and_independent():
    samples = array.array("h", [0, 300, 100, 200, 200, 100, 300, 0])

    result = resample_pitch(samples, channels=2, pitch_factor=1.0)

    left = list(result)[0::2]
    right = list(result)[1::2]
    assert left == [0, 100, 200, 300]
    assert right == [300, 200, 100, 0]


def test_resample_pitch_interpolates_between_samples():
    samples = array.array("h", [0, 100])

    result = resample_pitch(samples, channels=1, pitch_factor=0.5)

    assert result[0] == 0
    assert 0 < result[1] < 100


def test_resample_pitch_returns_copy_for_degenerate_input():
    samples = array.array("h", [42])

    assert list(resample_pitch(samples, channels=1, pitch_factor=1.2)) == [42]
    assert list(resample_pitch(array.array("h", [1, 2]), channels=1, pitch_factor=0.0)) == [1, 2]
