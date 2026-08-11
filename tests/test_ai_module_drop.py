"""Редкий случайный дроп ИИ-модуля с убитых врагов Corporation (см.
GameSession.AI_MODULE_DROP_CHANCE, GameSession.ai_module_stock)."""
from src.core.coordinate import Coordinate
from src.core.game_session import GameSession
from src.entities.defense_module import DefenseModule
from src.entities.enemies import DroneWalker, GiantRoach


def _kill_corporation_enemy(session):
    enemy = DroneWalker(Coordinate(100, 100))
    enemy.set_path([Coordinate(200, 100)])
    session.map.spawn_enemy(enemy)
    enemy.health = 0
    session.update(delta_time=0.01)


def test_guaranteed_roll_adds_a_module_to_stock(monkeypatch):
    session = GameSession()
    session.setup_game()
    monkeypatch.setattr("random.random", lambda: 0.0)
    monkeypatch.setattr("random.choice", lambda seq: "hunt_leaders")

    _kill_corporation_enemy(session)

    assert session.ai_module_stock.get("hunt_leaders") == 1


def test_failed_roll_does_not_add_a_module(monkeypatch):
    session = GameSession()
    session.setup_game()
    monkeypatch.setattr("random.random", lambda: 1.0)

    _kill_corporation_enemy(session)

    assert session.ai_module_stock == {}


def test_dropped_module_is_always_a_valid_key(monkeypatch):
    session = GameSession()
    session.setup_game()
    monkeypatch.setattr("random.random", lambda: 0.0)

    _kill_corporation_enemy(session)

    dropped_keys = set(session.ai_module_stock.keys())
    assert dropped_keys <= set(DefenseModule.AI_MODULE_KEYS)


def test_fauna_kill_never_drops_a_module_even_on_guaranteed_roll(monkeypatch):
    session = GameSession()
    session.setup_game()
    monkeypatch.setattr("random.random", lambda: 0.0)
    monkeypatch.setattr("random.choice", lambda seq: "hunt_leaders")

    enemy = GiantRoach(Coordinate(100, 100))
    enemy.set_path([Coordinate(200, 100)])
    session.map.spawn_enemy(enemy)
    enemy.health = 0
    session.update(delta_time=0.01)

    assert session.ai_module_stock == {}


def test_stock_accumulates_across_multiple_drops(monkeypatch):
    session = GameSession()
    session.setup_game()
    monkeypatch.setattr("random.random", lambda: 0.0)
    monkeypatch.setattr("random.choice", lambda seq: "finish_wounded")

    _kill_corporation_enemy(session)
    _kill_corporation_enemy(session)

    assert session.ai_module_stock["finish_wounded"] == 2
