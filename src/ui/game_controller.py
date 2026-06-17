from typing import Optional
from src.core.game_session import GameSession
from src.entities.coordinate import Coordinate
from src.entities.turrets import LaserTurret, BulletTurret, MortarTurret

class GameController:
    def __init__(self, session: GameSession):
        self.session = session
        self.selected_tower_type = None
        self.selected_module = None

    def select_tower(self, tower_type: str) -> bool:
        tower_classes = {"laser": LaserTurret, "bullet": BulletTurret, "mortar": MortarTurret}
        if tower_type in tower_classes:
            self.selected_tower_type = tower_classes[tower_type]
            return True
        return False

    def handle_click(self, position: Coordinate) -> None:
        """Умная обработка клика: выбор башни или постройка новой"""
        for module in self.session.map.modules:
            if position.distance_to(module.position) < 16:
                self.selected_module = module
                return

        if self.selected_tower_type:
            self.place_tower(position)

    def place_tower(self, position: Coordinate) -> bool:
        if self.selected_tower_type is None:
            return False
        if not self._is_valid_position(position):
            return False

        success = self.session.place_turret(self.selected_tower_type, position)
        if success:
            self.selected_tower_type = None
        return success

    def upgrade_selected(self) -> bool:
        if not self.selected_module or not self.selected_module.can_upgrade():
            return False
        cost = self.selected_module.get_upgrade_cost()
        if cost and self.session.resources.spend(cost):
            self.selected_module.upgrade()
            return True
        return False

    def deselect(self):
        self.selected_module = None

    def start_next_wave(self) -> bool:
        if self.session.wave_protocol.is_active:
            return False
        self.session.wave_protocol.force_start_next_wave()
        return True

    def pause_game(self):
        from src.enums import GameState
        if self.session.state == GameState.PLAYING:
            self.session.state = GameState.PAUSED
        elif self.session.state == GameState.PAUSED:
            self.session.state = GameState.PLAYING

    def get_game_state(self) -> dict:
        return {
            "credits": self.session.resources.credits,
            "base_health": self.session.base_health,
            "max_base_health": self.session.max_base_health,
            "current_wave": self.session.wave_protocol.current_wave_idx + 1,
            "total_waves": len(self.session.wave_protocol.waves),
            "game_state": self.session.state,
            "is_wave_active": self.session.wave_protocol.is_active,
            "selected_tower": self.selected_tower_type.__name__ if self.selected_tower_type else None
        }

    def _is_valid_position(self, position: Coordinate) -> bool:
        for point in self.session.map.path:
            if position.distance_to(point) < 30:
                return False
        for module in self.session.map.modules:
            if position.distance_to(module.position) < 25:
                return False
        if position.x < 0 or position.x > 900 or position.y < 0 or position.y > 600:
            return False
        return True