from src.enums import GameState


class GameStateManager:
    """Хранит и меняет текущее состояние игры."""

    def __init__(self, initial_state: GameState = GameState.MENU):
        """Создаёт менеджер с начальным состоянием."""
        self.current_state = initial_state

    def change_state(self, new_state: GameState):
        """Меняет текущее состояние игры."""
        self.current_state = new_state

    def check_defeat(self, base_health: float) -> bool:
        """Проверяет, наступило ли поражение."""
        return base_health <= 0

    def check_victory(self, elapsed_time: float, target_duration: float) -> bool:
        """Проверяет, наступила ли победа - продержаться заданное время под
        непрерывным давлением угроз. Временное условие на этап 1 перехода на
        RTS-модель угроз (docs/DESIGN_RTS_TRANSITION.md, раздел 4);
        полноценные Objective-условия победы - отдельный этап (5) плана."""
        return elapsed_time >= target_duration
