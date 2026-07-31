"""Прослойка между GameSession и View."""
from src.core.game_session import GameSession
from src.core.game_mode_controller import IGameModeController
from src.core.orbital_mode_controller import OrbitalModeController
from src.core.coordinate import Coordinate


class GameController:
    """Точка входа для View, хранит активный режим игры."""

    def __init__(self, session: GameSession):
        """Создаёт контроллер с орбитальным режимом(rts) по умолчанию."""
        self.session = session
        self.active_mode: IGameModeController = OrbitalModeController(session)

    def set_mode(self, mode: IGameModeController):
        """Переключает активный режим игры."""
        self.active_mode.on_exit()
        self.active_mode = mode
        self.active_mode.on_enter()

    @property
    def camera(self):
        """Камера активного режима."""
        return self.active_mode.camera

    @property
    def selected_tower_type(self):
        """Тип строящейся башни."""
        return getattr(self.active_mode, "selected_tower_type", None)

    @property
    def selected_module(self):
        """Выбранная башня."""
        return getattr(self.active_mode, "selected_module", None)

    @property
    def selected_enemy(self):
        """Выбранный враг."""
        return getattr(self.active_mode, "selected_enemy", None)

    def update(self, delta_time: float):
        """Обновляет активный режим на один кадр."""
        self.active_mode.update(delta_time)

    def handle_input(self, event) -> bool:
        """Передаёт событие ввода активному режиму."""
        return self.active_mode.handle_input(event)

    def get_game_state(self) -> dict:
        """Возвращает состояние игры для HUD."""
        return self.active_mode.get_game_state()

    def _is_valid_position(self, position: Coordinate) -> bool:
        """Проверяет, можно ли поставить башню в этой точке."""
        return self.active_mode._is_valid_position(position)
