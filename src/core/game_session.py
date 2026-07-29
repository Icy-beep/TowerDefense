from src.core.map import Map
from src.core.game_state import GameStateManager
from src.systems.resource_bank import ResourceBank
from src.systems.wave_protocol import WaveProtocol, WaveConfig
from src.factories.tower_factory import TowerFactory
from src.factories.enemy_factory import EnemyFactory
from src.enums import GameState
from src.entities.hostile_entity import HostileEntity
from src.core.coordinate import Coordinate


class GameSession:
    """Модель. Ничего не знает ни о pygame, ни о контроллере, ни о режимах
    ввода — только правила игры. Camera/OrbitalModeController и всё, что
    связано с вводом и отрисовкой, находится строго в контроллере (ui-слой),
    который создаёт View, а не сессия.

    Фабрики (TowerFactory/EnemyFactory) тоже живут здесь, а не в
    контроллере: "создать башню/врага определённого типа" — это правило
    игры (нужны деньги, нужно валидное место, враг должен получить путь),
    а не забота UI-слоя."""

    def __init__(self):
        self.map = None
        self.resources = ResourceBank()
        self.wave_protocol = WaveProtocol()
        self.tower_factory = TowerFactory()
        self.enemy_factory = EnemyFactory()
        self.state_manager = GameStateManager(GameState.MENU)
        self.base_health = 100
        self.max_base_health = 100

    @property
    def state(self) -> GameState:
        """Мост к GameStateManager.current_state — сохраняет прежний
        публичный API (session.state читают GameView/OrbitalModeController),
        но единственным источником истины по переходам состояния
        является GameStateManager, а не разбросанные присваивания."""
        return self.state_manager.current_state

    @state.setter
    def state(self, new_state: GameState):
        self.state_manager.change_state(new_state)

    def setup_game(self):
        self.state = GameState.PLAYING
        self.base_health = self.max_base_health
        self.resources = ResourceBank(start_credits=300)

        self.map = Map(width=4000, height=4000)
        self.base_position = Coordinate(2000, 2000)
        self.map.nav_grid.set_blocked(self.base_position.x, self.base_position.y, blocked=True)
        self.map.spawn_points = [
            Coordinate(200, 200),
            Coordinate(3800, 200),
            Coordinate(200, 3800),
            Coordinate(3800, 3800)
        ]

        print(f"Карта инициализирована")
        print(f"База: {self.base_position}")
        waves = [
            WaveConfig(["drone_walker"], 5, 1.5),
            WaveConfig(["drone_walker", "giant_roach"], 8, 1.2),
        ]
        self.wave_protocol.set_waves(waves)
        self.wave_protocol.start_next_wave()

    def update(self, delta_time: float):
        if self.state != GameState.PLAYING:
            return

        self.wave_protocol.update(delta_time, self.map, self._spawn_enemy_factory)
        reached_base, killed_enemies = self.map.update(delta_time)
        for enemy in killed_enemies:
            self.resources.add_reward(enemy.reward)

        for _ in reached_base:
            self.base_health -= 10

        if self.state_manager.check_defeat(self.base_health):
            self.state = GameState.GAME_OVER
            return

        if self.state_manager.check_victory(self.map, self.wave_protocol):
            self.state = GameState.VICTORY

    def place_turret(self, tower_type: str, position: Coordinate) -> bool:
        """tower_type — строка ("laser"/"bullet"/"mortar"), а не класс."""
        if not self.map.can_place_module(position):
            return False
        turret = self.tower_factory.create(tower_type, position)
        if turret is None:
            return False
        if self.resources.spend(turret.cost):
            self.map.add_module(turret)
            return True
        return False

    def _spawn_enemy_factory(self, enemy_type: str, pos: Coordinate) -> HostileEntity:
        enemy = self.enemy_factory.create(enemy_type, pos)
        if enemy is None:
            raise ValueError(f"Неизвестный тип врага в WaveConfig: '{enemy_type}'")

        path = self.map.nav_grid.find_path(pos, self.base_position)
        if path:
            enemy.set_path(path)
        else:
            print(f"Ошибка пути! Враг застрянет.")

        return enemy
