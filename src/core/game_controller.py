"""Контроллер — прослойка между Model (GameSession) и View (GameView).

Правило слоёв:
    View создаёт Controller(session)
    Controller дёргает публичные методы модели
    Модель ничего не знает ни о Controller, ни о View, ни о pygame

GameController — стабильная точка входа для View. Внутри он хранит
активный "режим" (IGameModeController) — сейчас единственная реализация
это OrbitalModeController, а когда появится Operator-режим (режим
"3rd персон шутера"), новый OperatorModeController будет подключаться
через set_mode().
"""
from src.core.game_session import GameSession
from src.core.game_mode_controller import IGameModeController
from src.core.orbital_mode_controller import OrbitalModeController
from src.core.coordinate import Coordinate


class GameController:
    def __init__(self, session: GameSession):
        self.session = session
        self.active_mode: IGameModeController = OrbitalModeController(session)

    # ------------------------------------------------------------------
    # Переключение активного режима (Orbital <-> Operator в будущем)
    # ------------------------------------------------------------------
    def set_mode(self, mode: IGameModeController):
        self.active_mode.on_exit()
        self.active_mode = mode
        self.active_mode.on_enter()

    # ------------------------------------------------------------------
    # Интерфейс, которым пользуется GameView
    # ------------------------------------------------------------------
    @property
    def camera(self):
        return self.active_mode.camera

    @property
    def selected_tower_type(self):
        """Нужно GameView для отрисовки превью размещения башни."""
        return getattr(self.active_mode, "selected_tower_type", None)

    @property
    def selected_module(self):
        """Нужно GameView для отрисовки выделения/панели улучшения."""
        return getattr(self.active_mode, "selected_module", None)

    def update(self, delta_time: float):
        self.active_mode.update(delta_time)

    def handle_input(self, event) -> bool:
        return self.active_mode.handle_input(event)

    def get_game_state(self) -> dict:
        return self.active_mode.get_game_state()

    def _is_valid_position(self, position: Coordinate) -> bool:
        return self.active_mode._is_valid_position(position)
