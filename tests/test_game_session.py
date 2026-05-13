import pytest
from src.core.game_session import GameSession
from src.entities.coordinate import Coordinate
from src.entities.turrets import LaserTurret
from src.enums.enums import GameState


class TestGameSession:
    """Тесты игровой сессии"""

    def test_base_health_initial(self):
        """Проверка начального здоровья базы"""
        session = GameSession()
        assert session.base_health == 100

    def test_place_turret_success(self):
        """Интеграционный тест: размещение башни при достаточном количестве ресурсов"""
        session = GameSession()
        session.setup_game()

        success = session.place_turret(LaserTurret, Coordinate(50, 50))

        assert success is True
        assert len(session.map.modules) == 1

    def test_place_turret_insufficient_funds(self):
        """Интеграционный тест: запрет размещения при недостатке ресурсов"""
        session = GameSession()
        session.setup_game()
        session.resources.credits = 10

        success = session.place_turret(LaserTurret, Coordinate(50, 50))

        assert success is False
        assert len(session.map.modules) == 0

    def test_enemy_reaches_base(self):
        """Тест 8: Корректность уменьшения прочности базы при достижении ее противником"""
        session = GameSession()
        session.setup_game()

        initial_health = session.base_health

        from src.entities.enemies import DroneWalker
        enemy = DroneWalker(session.map.path[-1])
        enemy.path_index = len(session.map.path)
        session.map.enemies.append(enemy)

        session.update(delta_time=0.1)

        assert session.base_health < initial_health

    def test_victory_condition(self):
        """Тест 9: Корректность определения состояния победы"""
        session = GameSession()
        session.setup_game()

        session.wave_protocol.finished = True
        session.map.enemies = []

        session.update(delta_time=0.1)

        assert session.state == GameState.VICTORY

    def test_defeat_condition(self):
        """Тест 9: Корректность определения состояния поражения"""
        session = GameSession()
        session.setup_game()
        session.base_health = 0

        session.update(delta_time=0.1)

        assert session.state == GameState.GAME_OVER