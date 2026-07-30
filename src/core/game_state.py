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

    def check_victory(self, game_map, wave_protocol) -> bool:
        """Проверяет, наступила ли победа."""
        return wave_protocol.is_all_waves_complete() and not game_map.enemies
