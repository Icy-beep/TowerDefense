"""Прослойка между GameSession и View."""
from src.core.coordinate import Coordinate
from src.core.game_mode_controller import IGameModeController
from src.core.game_session import GameSession
from src.core.orbital_mode_controller import OrbitalModeController


class GameController:
    """Точка входа для View, хранит активный режим игры."""

    def __init__(self, session: GameSession, screen_w: int = 900, screen_h: int = 600):
        """Создаёт контроллер с орбитальным режимом(rts) по умолчанию, под
        текущий размер окна."""
        self.session = session
        self.active_mode: IGameModeController = OrbitalModeController(session, screen_w, screen_h)

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

    @property
    def show_power_radii(self):
        """Включён ли постоянный показ радиусов энергосети - нужно MapRenderer.render,
        который читает это прямо с controller, а не через get_game_state()."""
        return getattr(self.active_mode, "show_power_radii", False)

    @property
    def show_tower_ranges(self):
        """Включён ли постоянный показ радиусов атаки боевых башен - нужно
        MapRenderer.render по той же причине, что и show_power_radii выше."""
        return getattr(self.active_mode, "show_tower_ranges", False)

    def update(self, delta_time: float):
        """Обновляет активный режим на один кадр."""
        self.active_mode.update(delta_time)

    def handle_input(self, event) -> bool:
        """Передаёт событие ввода активному режиму."""
        return self.active_mode.handle_input(event)

    def select_tower(self, tower_type: str) -> bool:
        """Выбирает тип постройки для размещения в активном режиме, если тот это
        поддерживает (см. OrbitalModeController.select_tower) - нужно HUD-панели
        построек, чтобы клик по иконке работал так же, как хоткей 1-5."""
        select = getattr(self.active_mode, "select_tower", None)
        if select is None:
            return False
        return select(tower_type)

    def toggle_power_radii(self) -> bool:
        """Переключает постоянный показ радиусов энергосети в активном режиме (если тот
        это поддерживает - см. OrbitalModeController.toggle_power_radii). Нужно
        HUD-кнопке, чтобы клик работал так же, как хоткей G."""
        toggle = getattr(self.active_mode, "toggle_power_radii", None)
        if toggle is None:
            return False
        return toggle()

    def toggle_tower_ranges(self) -> bool:
        """Переключает постоянный показ радиусов атаки башен в активном режиме - клик
        по HUD-кнопке работает так же, как хоткей T."""
        toggle = getattr(self.active_mode, "toggle_tower_ranges", None)
        if toggle is None:
            return False
        return toggle()

    def get_game_state(self) -> dict:
        """Возвращает состояние игры для HUD."""
        return self.active_mode.get_game_state()

    def _is_valid_position(self, position: Coordinate) -> bool:
        """Проверяет, можно ли поставить башню в этой точке."""
        return self.active_mode._is_valid_position(position)
