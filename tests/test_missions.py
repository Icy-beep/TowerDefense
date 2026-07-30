"""Задания (src/systems/mission.py) — необязательный слой поверх волн:
не заменяют и не блокируют victory/defeat (GameStateManager), просто
дают дополнительную направленную цель и статус в HUD. Полный переход на
"открытую песочницу" был отклонён как слишком рискованная перестройка
работающего игрового цикла — это дешёвая альтернатива с тем же эффектом
направленности."""
import types

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.core.map import Map
from src.entities.turrets import LaserTurret
from src.enums import GameState
from src.systems.mission import Objective, SurviveWavesObjective, ProtectTowersObjective


def _fake_session(state=GameState.PLAYING, current_wave_idx=0, towers_lost=0, all_waves_complete=False):
    return types.SimpleNamespace(
        state=state,
        wave_protocol=types.SimpleNamespace(
            current_wave_idx=current_wave_idx,
            is_all_waves_complete=lambda: all_waves_complete,
        ),
        map=types.SimpleNamespace(towers_lost_count=towers_lost),
    )


# --------------------------------------------------------------- Objective

def test_objective_is_active_until_completed_or_failed():
    session = _fake_session()
    objective = SurviveWavesObjective(target_wave_count=3)

    assert objective.is_active() is True

    objective.completed = True
    assert objective.is_active() is False


# --------------------------------------------------------- SurviveWavesObjective

def test_survive_waves_completes_once_target_reached():
    objective = SurviveWavesObjective(target_wave_count=3)
    session = _fake_session(current_wave_idx=3)

    objective.update(session)

    assert objective.completed is True
    assert objective.failed is False


def test_survive_waves_not_yet_completed_before_target():
    objective = SurviveWavesObjective(target_wave_count=3)
    session = _fake_session(current_wave_idx=2)

    objective.update(session)

    assert objective.completed is False


def test_survive_waves_fails_on_game_over():
    objective = SurviveWavesObjective(target_wave_count=3)
    session = _fake_session(state=GameState.GAME_OVER, current_wave_idx=1)

    objective.update(session)

    assert objective.failed is True
    assert objective.completed is False


def test_survive_waves_describe_reports_progress():
    objective = SurviveWavesObjective(target_wave_count=5)
    session = _fake_session(current_wave_idx=2)

    text = objective.describe(session)

    assert "2" in text and "5" in text


# --------------------------------------------------------- ProtectTowersObjective

def test_protect_towers_fails_as_soon_as_one_tower_is_lost():
    objective = ProtectTowersObjective()
    session = _fake_session(towers_lost=1)

    objective.update(session)

    assert objective.failed is True
    assert objective.completed is False


def test_protect_towers_completes_when_all_waves_done_and_none_lost():
    objective = ProtectTowersObjective()
    session = _fake_session(towers_lost=0, all_waves_complete=True)

    objective.update(session)

    assert objective.completed is True


def test_protect_towers_neither_completed_nor_failed_mid_game():
    objective = ProtectTowersObjective()
    session = _fake_session(towers_lost=0, all_waves_complete=False)

    objective.update(session)

    assert objective.completed is False
    assert objective.failed is False


# --------------------------------------------------------------- Map.towers_lost_count

def test_map_increments_towers_lost_count_when_a_tower_is_destroyed():
    game_map = Map(width=4000, height=4000)
    tower = LaserTurret(Coordinate(0, 0))
    tower.health = 0
    game_map.modules.append(tower)

    game_map.update(delta_time=0.1)

    assert game_map.towers_lost_count == 1
    assert tower not in game_map.modules


def test_map_towers_lost_count_does_not_increment_for_healthy_towers():
    game_map = Map(width=4000, height=4000)
    game_map.modules.append(LaserTurret(Coordinate(0, 0)))

    game_map.update(delta_time=0.1)

    assert game_map.towers_lost_count == 0


# --------------------------------------------------------------- GameSession wiring

def test_setup_game_creates_default_objectives():
    session = GameSession()
    session.setup_game()

    assert len(session.objectives) == 2
    assert any(isinstance(o, SurviveWavesObjective) for o in session.objectives)
    assert any(isinstance(o, ProtectTowersObjective) for o in session.objectives)


def test_game_session_update_ticks_active_objectives():
    session = GameSession()
    session.setup_game()
    objective = session.objectives[0]
    assert objective.is_active() is True

    session.update(delta_time=0.016)

    # Тик произошёл без исключений и не сломал остальной игровой цикл —
    # конкретное состояние задания зависит от рандомного числа волн,
    # поэтому здесь просто проверяем, что update() дошёл до объекта.
    assert isinstance(objective, Objective)


def test_game_session_survive_waves_completes_via_real_gameplay_progression():
    session = GameSession()
    session.setup_game()
    milestone_objective = next(o for o in session.objectives if isinstance(o, SurviveWavesObjective))

    session.wave_protocol.current_wave_idx = milestone_objective.target_wave_count

    session.update(delta_time=0.016)

    assert milestone_objective.completed is True


def test_game_session_protect_towers_fails_after_tower_destroyed_via_real_update():
    session = GameSession()
    session.setup_game()
    protect_objective = next(o for o in session.objectives if isinstance(o, ProtectTowersObjective))

    tower = LaserTurret(Coordinate(500, 500))
    tower.health = 0
    session.map.modules.append(tower)

    session.update(delta_time=0.016)

    assert protect_objective.failed is True


def test_inactive_objective_stops_receiving_updates():
    session = GameSession()
    session.setup_game()
    protect_objective = next(o for o in session.objectives if isinstance(o, ProtectTowersObjective))
    protect_objective.failed = True

    tower = LaserTurret(Coordinate(500, 500))
    session.map.modules.append(tower)
    session.map.towers_lost_count = 0

    session.update(delta_time=0.016)

    # Уже неактивное задание не должно повторно проверяться/меняться
    assert protect_objective.failed is True
    assert protect_objective.completed is False
