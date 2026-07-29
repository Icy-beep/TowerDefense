from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.game_session import GameSession


class IGameModeController(ABC):
    """Стратегия: инкапсулирует ввод, апдейт и камеру одного режима игры.

    GameSession не знает деталей ни одного режима — только вызывает
    update()/handle_input() у текущего активного контроллера.
    """

    def __init__(self, session: "GameSession"):
        self.session = session
        self.camera = self._create_camera()

    @abstractmethod
    def _create_camera(self):
        """Создаёт камеру, подходящую для этого режима"""
        pass

    @abstractmethod
    def update(self, delta_time: float):
        """Логика режима, вызывается каждый кадр из GameSession.update()"""
        pass

    @abstractmethod
    def handle_input(self, event) -> bool:
        """Возвращает True, если событие обработано и не должно идти дальше"""
        pass

    def on_enter(self):
        """Хук при активации режима (например, центрирование камеры)"""
        pass

    def on_exit(self):
        """Хук при деактивации (например, сброс выделения башни)"""
        pass
