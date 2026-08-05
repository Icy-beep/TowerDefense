"""Уменьшение прочности базы врагами и определение состояний победы/поражения."""
from src.core.game_state import GameStateManager
from src.core.game_session import GameSession
from src.core.coordinate import Coordinate
from src.entities.enemies import DroneWalker
from src.enums import GameState



def _enemy_that_reached_base():
    enemy = DroneWalker(Coordinate(0, 0))
    enemy.set_path([Coordinate(0, 0)])
    enemy.path_index = 1
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



def test_check_defeat_true_when_base_health_zero_or_below():
    gsm = GameStateManager()

    assert gsm.check_defeat(base_health=0) is True
    assert gsm.check_defeat(base_health=-5) is True
    assert gsm.check_defeat(base_health=1) is False


def test_check_victory_true_once_target_duration_reached():
    gsm = GameStateManager()

    assert gsm.check_victory(elapsed_time=180.0, target_duration=180.0) is True
    assert gsm.check_victory(elapsed_time=200.0, target_duration=180.0) is True
    assert gsm.check_victory(elapsed_time=179.9, target_duration=180.0) is False, \
        "победа не должна засчитываться раньше целевого времени"



def test_game_session_transitions_to_game_over_on_defeat():
    session = GameSession()
    session.setup_game()
    session.base_health = 5
    session.map.enemies = [_enemy_that_reached_base()]

    session.update(delta_time=0.016)

    assert session.state == GameState.GAME_OVER


def test_game_session_transitions_to_victory_when_duration_target_reached():
    session = GameSession()
    session.setup_game()
    session.elapsed_time = session.survive_duration_target
    session.map.enemies = []

    session.update(delta_time=0.016)

    assert session.state == GameState.VICTORY


def test_game_session_stays_in_playing_state_during_normal_gameplay():
    session = GameSession()
    session.setup_game()

    session.update(delta_time=0.016)

    assert session.state == GameState.PLAYING


def test_setup_game_defaults_to_not_endless():
    session = GameSession()
    session.setup_game()

    assert session.endless is False
    assert len(session.objectives) == 2


def test_endless_mode_has_no_objectives():
    session = GameSession()
    session.setup_game(endless=True)

    assert session.endless is True
    assert session.objectives == []


def test_endless_mode_never_triggers_victory_by_time():
    session = GameSession()
    session.setup_game(endless=True)
    session.elapsed_time = session.survive_duration_target * 10
    session.map.enemies = []

    session.update(delta_time=0.016)

    assert session.state == GameState.PLAYING, "в бесконечном режиме не должно быть победы по таймеру"


def test_endless_mode_base_can_still_be_destroyed():
    session = GameSession()
    session.setup_game(endless=True)
    session.base_health = 5
    session.map.enemies = [_enemy_that_reached_base()]

    session.update(delta_time=0.016)

    assert session.state == GameState.GAME_OVER, "база должна оставаться уязвимой и в бесконечном режиме"


def test_defeat_takes_priority_when_both_conditions_true_simultaneously():
    """Если база уже разрушена в тот же тик, когда целевое время достигнуто —
    поражение должно иметь приоритет (игрок не успел выиграть)."""
    session = GameSession()
    session.setup_game()
    session.base_health = 5
    session.elapsed_time = session.survive_duration_target
    session.map.enemies = [_enemy_that_reached_base()]

    session.update(delta_time=0.016)

    assert session.state == GameState.GAME_OVER
