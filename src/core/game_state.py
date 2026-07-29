from src.enums import GameState


class GameStateManager:
    """
    Единая точка истины для переходов состояния игры.
    """

    def __init__(self, initial_state: GameState = GameState.MENU):
        self.current_state = initial_state

    def change_state(self, new_state: GameState):
        self.current_state = new_state

    def check_defeat(self, base_health: float) -> bool:
        """
        Поражение: прочность базы упала до нуля
        """
        return base_health <= 0

    def check_victory(self, game_map, wave_protocol) -> bool:
        """
        Победа: все волны отражены и на поле не осталось противников.
        """
        return wave_protocol.is_all_waves_complete() and not game_map.enemies
