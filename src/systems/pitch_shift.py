"""Ресемплинг сэмплов для случайной вариации питча (высоты тона) звука."""
import array
from typing import Sequence


def resample_pitch(samples: Sequence[int], channels: int, pitch_factor: float) -> array.array:
    """Ресемплирует interleaved 16-битные сэмплы линейной интерполяцией, меняя длительность и высоту тона."""
    frame_count = len(samples) // channels
    if frame_count <= 1 or pitch_factor <= 0:
        return array.array("h", samples)

    new_frame_count = max(1, round(frame_count / pitch_factor))
    result = array.array("h", bytes(new_frame_count * channels * 2))

    for new_frame in range(new_frame_count):
        source_pos = new_frame * pitch_factor
        left_frame = min(int(source_pos), frame_count - 1)
        right_frame = min(left_frame + 1, frame_count - 1)
        blend = source_pos - left_frame

        for channel in range(channels):
            left_sample = samples[left_frame * channels + channel]
            right_sample = samples[right_frame * channels + channel]
            result[new_frame * channels + channel] = round(left_sample + (right_sample - left_sample) * blend)

    return result
