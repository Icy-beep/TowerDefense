"""Задания (src/systems/mission.py) - слой целей поверх victory/defeat, не блокирует их."""
import types

from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.core.map import Map
from src.entities.turrets import LaserTurret
from src.enums import GameState
from src.systems.mission import Objective, ProtectTowersObjective, SurviveDurationObjective


def _fake_session(state=GameState.PLAYING, elapsed_time=0.0, towers_lost=0):
    return types.SimpleNamespace(
        state=state,
        elapsed_time=elapsed_time,
        map=types.SimpleNamespace(towers_lost_count=towers_lost),
    )



def test_objective_is_active_until_completed_or_failed():
    session = _fake_session()
    objective = SurviveDurationObjective(target_seconds=60)

    assert objective.is_active() is True

    objective.completed = True
    assert objective.is_active() is False



def test_survive_duration_completes_once_target_reached():
    objective = SurviveDurationObjective(target_seconds=60)
    session = _fake_session(elapsed_time=60)

    objective.update(session)

    assert objective.completed is True
    assert objective.failed is False


def test_survive_duration_not_yet_completed_before_target():
    objective = SurviveDurationObjective(target_seconds=60)
    session = _fake_session(elapsed_time=30)

    objective.update(session)

    assert objective.completed is False


def test_survive_duration_fails_on_game_over():
    objective = SurviveDurationObjective(target_seconds=60)
    session = _fake_session(state=GameState.GAME_OVER, elapsed_time=10)

    objective.update(session)

    assert objective.failed is True
    assert objective.completed is False


def test_survive_duration_describe_reports_progress():
    objective = SurviveDurationObjective(target_seconds=50)
    session = _fake_session(elapsed_time=20)

    text = objective.describe(session)

    assert "20" in text and "50" in text



def test_protect_towers_fails_as_soon_as_one_tower_is_lost():
    objective = ProtectTowersObjective()
    session = _fake_session(towers_lost=1)

    objective.update(session)

    assert objective.failed is True
    assert objective.completed is False


def test_protect_towers_completes_when_session_reaches_victory():
    objective = ProtectTowersObjective()
    session = _fake_session(towers_lost=0, state=GameState.VICTORY)

    objective.update(session)

    assert objective.completed is True


def test_protect_towers_neither_completed_nor_failed_mid_game():
    objective = ProtectTowersObjective()
    session = _fake_session(towers_lost=0, state=GameState.PLAYING)

    objective.update(session)

    assert objective.completed is False
    assert objective.failed is False



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



def test_setup_game_creates_default_objectives():
    session = GameSession()
    session.setup_game()

    assert len(session.objectives) == 2
    assert any(isinstance(o, SurviveDurationObjective) for o in session.objectives)
    assert any(isinstance(o, ProtectTowersObjective) for o in session.objectives)


def test_game_session_update_ticks_active_objectives():
    session = GameSession()
    session.setup_game()
    objective = session.objectives[0]
    assert objective.is_active() is True

    session.update(delta_time=0.016)

    assert isinstance(objective, Objective)


def test_game_session_survive_duration_completes_via_real_gameplay_progression():
    session = GameSession()
    session.setup_game()
    duration_objective = next(o for o in session.objectives if isinstance(o, SurviveDurationObjective))

    session.elapsed_time = duration_objective.target_seconds

    session.update(delta_time=0.016)

    assert duration_objective.completed is True


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

    assert protect_objective.failed is True
    assert protect_objective.completed is False
