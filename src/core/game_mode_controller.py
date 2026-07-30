from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.game_session import GameSession


class IGameModeController(ABC):
    """Управляет вводом, обновлением и камерой одного режима игры."""

    def __init__(self, session: "GameSession"):
        """Создаёт контроллер и его камеру для данной игровой сессии."""
        self.session = session
        self.camera = self._create_camera()

    @abstractmethod
    def _create_camera(self):
        """Создаёт камеру для этого режима."""
        pass

    @abstractmethod
    def update(self, delta_time: float):
        """Обновляет логику режима на один кадр."""
        pass

    @abstractmethod
    def handle_input(self, event) -> bool:
        """Обрабатывает событие ввода."""
        pass

    def on_enter(self):
        """Вызывается при активации режима."""
        pass

    def on_exit(self):
        """Вызывается при деактивации режима."""
        pass
