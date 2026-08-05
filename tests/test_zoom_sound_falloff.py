"""GameView._handle_game_event: звуки должны становиться тише на сильном отдалении
камеры (см. spatial_audio.volume_for_zoom и запрос пользователя), но не для
ALWAYS_AUDIBLE_EVENTS (например base_hit - тревога о базе обязана быть слышна
всегда) и не для событий без позиции (victory/defeat - глобальные, не привязаны к
месту на карте). Тестируем через несвязанный метод на лёгком фейковом self, чтобы не
поднимать полноценный GameView (звук/спрайты/музыка/окно pygame)."""
import types

from src.core.coordinate import Coordinate
from src.ui.game_window import GameView


class _FakeCamera:
    """Камера в состоянии покоя в мировых координатах (0,0) - позиция события внутри
    видимой области, чтобы volume_for_position не вмешивалась в результат (=1.0),
    и единственным переменным фактором оставался зум."""

    def __init__(self, zoom=1.0, min_zoom=0.1):
        self.x = 0.0
        self.y = 0.0
        self.screen_w = 900
        self.screen_h = 600
        self.zoom = zoom
        self.min_zoom = min_zoom


def _fake_view(zoom=1.0, min_zoom=0.1):
    """Минимальный дублёр GameView с ровно тем набором атрибутов, которые читает
    _handle_game_event - без реального pygame.init()/загрузки ассетов."""
    calls = []
    view = types.SimpleNamespace()
    view.controller = types.SimpleNamespace(camera=_FakeCamera(zoom=zoom, min_zoom=min_zoom))
    view.camera = view.controller.camera
    view.sound_manager = types.SimpleNamespace(
        play=lambda event, volume, cooldown=0.0: calls.append((event, volume, cooldown))
    )
    view.ALWAYS_AUDIBLE_EVENTS = GameView.ALWAYS_AUDIBLE_EVENTS
    view.SOUND_EVENTS = GameView.SOUND_EVENTS
    view.SOUND_COOLDOWNS = GameView.SOUND_COOLDOWNS
    view.SOUND_VOLUME_MULTIPLIERS = GameView.SOUND_VOLUME_MULTIPLIERS
    return view, calls


def test_positional_sound_is_full_volume_at_100_percent_zoom():
    view, calls = _fake_view(zoom=1.0)

    GameView._handle_game_event(view, "mortar_explosion", position=Coordinate(400, 300))

    assert len(calls) == 1
    _event, volume, _cooldown = calls[0]
    assert volume > 0.8  # почти полная (с учётом собственного множителя взрыва 0.85)


def test_positional_sound_gets_quieter_as_camera_zooms_out_past_45_percent():
    view_close, calls_close = _fake_view(zoom=1.0)
    view_far, calls_far = _fake_view(zoom=0.2, min_zoom=0.1)

    GameView._handle_game_event(view_close, "mortar_explosion", position=Coordinate(400, 300))
    GameView._handle_game_event(view_far, "mortar_explosion", position=Coordinate(400, 300))

    volume_close = calls_close[0][1]
    volume_far = calls_far[0][1]
    assert volume_far < volume_close, "на сильном отдалении звук должен быть заметно тише"


def test_positional_sound_reaches_roughly_5_percent_at_maximum_zoom_out():
    view, calls = _fake_view(zoom=0.1, min_zoom=0.1)

    GameView._handle_game_event(view, "laser_hit", position=Coordinate(400, 300))

    _event, volume, _cooldown = calls[0]
    # laser_hit имеет собственный множитель 0.6 (SOUND_VOLUME_MULTIPLIERS) - на
    # максимальном отдалении итоговая громкость должна быть около 5% от него.
    assert volume < 0.6 * 0.10, "должно быть заметно ближе к 5%, а не к полной громкости"


def test_base_hit_stays_full_volume_regardless_of_zoom():
    """base_hit - тревога о базе, ALWAYS_AUDIBLE_EVENTS - обязана быть слышна всегда,
    зум-затухание её не должно касаться."""
    view, calls = _fake_view(zoom=0.1, min_zoom=0.1)

    GameView._handle_game_event(view, "base_hit", position=Coordinate(999999, 999999))

    assert len(calls) == 1
    _event, volume, _cooldown = calls[0]
    assert volume == 1.0


def test_positionless_global_event_stays_unaffected_by_zoom():
    """victory/defeat - без position, глобальные стингеры, не про "насколько видно
    на экране" - зум-затухание к ним не применяется (см. докстринг _handle_game_event)."""
    view, calls = _fake_view(zoom=0.1, min_zoom=0.1)

    GameView._handle_game_event(view, "victory")

    assert len(calls) == 1
    _event, volume, _cooldown = calls[0]
    assert volume == 1.0
