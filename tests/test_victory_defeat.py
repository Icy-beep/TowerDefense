"""
- корректность уменьшения прочности базы при достижении её противником
- корректность определения состояний победы и поражения
"""
from src.core.game_state import GameStateManager
from src.core.game_session import GameSession
from src.core.coordinate import Coordinate
from src.entities.enemies import DroneWalker
from src.enums import GameState


# ---------------------------------------------------------------------
# Урон базе при достижении противником конца маршрута
# ---------------------------------------------------------------------

def _enemy_that_reached_base():
    enemy = DroneWalker(Coordinate(0, 0))
    enemy.set_path([Coordinate(0, 0)])
    enemy.path_index = 1  # индекс уже за пределами пути — противник "дошёл"
    return enemy


def test_base_health_decreases_when_enemy_reaches_base():
    session = GameSession()
    session.setup_game()
    session.base_health = 100
    session.map.enemies = [_enemy_that_reached_base()]

    session.update(delta_time=0.016)

    assert session.base_health == 90
    assert session.map.enemies == [], "дошедший до базы противник должен покидать поле"


def test_multiple_enemies_reaching_base_stack_damage():
    session = GameSession()
    session.setup_game()
    session.base_health = 100
    session.map.enemies = [_enemy_that_reached_base() for _ in range(3)]

    session.update(delta_time=0.016)

    assert session.base_health == 70


# ---------------------------------------------------------------------
# GameStateManager — правила определения победы/поражения
# ---------------------------------------------------------------------

def test_check_defeat_true_when_base_health_zero_or_below():
    gsm = GameStateManager()

    assert gsm.check_defeat(base_health=0) is True
    assert gsm.check_defeat(base_health=-5) is True
    assert gsm.check_defeat(base_health=1) is False


class _FakeWaveProtocol:
    def __init__(self, complete):
        self._complete = complete

    def is_all_waves_complete(self):
        return self._complete


class _FakeMap:
    def __init__(self, enemies):
        self.enemies = enemies


def test_check_victory_requires_both_conditions_simultaneously():
    gsm = GameStateManager()

    assert gsm.check_victory(_FakeMap([]), _FakeWaveProtocol(True)) is True
    assert gsm.check_victory(_FakeMap(["enemy"]), _FakeWaveProtocol(True)) is False, \
        "победа не должна засчитываться, пока на поле остаются противники"
    assert gsm.check_victory(_FakeMap([]), _FakeWaveProtocol(False)) is False, \
        "победа не должна засчитываться, пока не пройдены все волны"


# ---------------------------------------------------------------------
# Полный переход состояния через GameSession
# ---------------------------------------------------------------------

def test_game_session_transitions_to_game_over_on_defeat():
    session = GameSession()
    session.setup_game()
    session.base_health = 5
    session.map.enemies = [_enemy_that_reached_base()]

    session.update(delta_time=0.016)

    assert session.state == GameState.GAME_OVER


def test_game_session_transitions_to_victory_when_all_waves_cleared():
    session = GameSession()
    session.setup_game()
    session.wave_protocol.finished = True
    session.wave_protocol.is_active = False
    session.map.enemies = []

    session.update(delta_time=0.016)

    assert session.state == GameState.VICTORY


def test_game_session_stays_in_playing_state_during_normal_gameplay():
    session = GameSession()
    session.setup_game()

    session.update(delta_time=0.016)

    assert session.state == GameState.PLAYING


def test_defeat_takes_priority_when_both_conditions_true_simultaneously():
    """Если база уже разрушена в тот же тик, когда волны закончились —
    поражение должно иметь приоритет (игрок не успел выиграть)."""
    session = GameSession()
    session.setup_game()
    session.base_health = 5
    session.wave_protocol.finished = True
    session.wave_protocol.is_active = False
    session.map.enemies = [_enemy_that_reached_base()]  # снимет ещё 10 хп -> уйдёт в минус

    session.update(delta_time=0.016)

    assert session.state == GameState.GAME_OVER
