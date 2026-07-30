import random
from typing import List, Optional

from src.core.map import Map
from src.core.game_state import GameStateManager
from src.systems.resource_bank import ResourceBank
from src.systems.wave_protocol import WaveProtocol, WaveConfig
from src.factories.tower_factory import TowerFactory
from src.factories.enemy_factory import EnemyFactory
from src.enums import Faction, GameState
from src.entities.hostile_entity import HostileEntity
from src.core.coordinate import Coordinate
from src.systems.mission import Objective, SurviveWavesObjective, ProtectTowersObjective


class GameSession:
    """Модель игры: правила, состояние, фабрики башен и врагов."""

    def __init__(self):
        """Создаёт пустую игровую сессию в главном меню."""
        self.map = None
        self.resources = ResourceBank()
        self.wave_protocol = WaveProtocol()
        self.tower_factory = TowerFactory()
        self.enemy_factory = EnemyFactory()
        self.state_manager = GameStateManager(GameState.MENU)
        self.base_health = 100
        self.max_base_health = 100
        self.objectives: List[Objective] = []

    @property
    def base_position(self) -> Optional[Coordinate]:
        """Позиция базы."""
        return self.map.base_position if self.map else None

    @base_position.setter
    def base_position(self, position: Coordinate):
        """Задаёт позицию базы."""
        self.map.base_position = position

    @property
    def state(self) -> GameState:
        """Текущее состояние игры."""
        return self.state_manager.current_state

    @state.setter
    def state(self, new_state: GameState):
        """Меняет состояние игры."""
        self.state_manager.change_state(new_state)

    def setup_game(self):
        """Готовит новую игру: карту, базу, ресурсы, волны и задания."""
        self.state = GameState.PLAYING
        self.base_health = self.max_base_health
        self.resources = ResourceBank(start_credits=1000)

        self.map = Map(width=4000, height=4000)
        self.base_position = Coordinate(2000, 2000)
        self.map.nav_grid.set_blocked(self.base_position.x, self.base_position.y, blocked=True)
        self.map.spawn_points = [
            Coordinate(200, 200),
            Coordinate(3800, 200),
            Coordinate(200, 3800),
            Coordinate(3800, 3800)
        ]
        self.map.spawn_points_by_faction = {
            Faction.CORPORATION: [Coordinate(200, 200), Coordinate(3800, 3800)],
            Faction.FAUNA: [Coordinate(3800, 200), Coordinate(200, 3800)],
        }

        print(f"Карта инициализирована")
        print(f"База: {self.base_position}")
        waves = self._generate_random_waves()
        self.wave_protocol.set_waves(waves)
        self.wave_protocol.start_next_wave()

        milestone = max(1, len(waves) // 2)
        self.objectives = [
            SurviveWavesObjective(target_wave_count=milestone),
            ProtectTowersObjective(),
        ]

    def _generate_random_waves(self, rng: Optional[random.Random] = None) -> List[WaveConfig]:
        """Генерирует случайный набор волн врагов."""
        rng = rng or random
        available_types = self.enemy_factory.available_types()

        wave_count = rng.randint(4, 7)
        waves = []
        for i in range(wave_count):
            type_count = rng.randint(1, min(3, len(available_types)))
            enemy_types = rng.sample(available_types, type_count)
            count = rng.randint(18 + i, 22 + i * 2)
            interval = rng.uniform(0.7, 1.5)
            waves.append(WaveConfig(enemy_types, count, interval))
        return waves

    def update(self, delta_time: float):
        """Обновляет игру на один кадр: волны, карту, здоровье базы, состояние, задания."""
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

        if self.state == GameState.PLAYING and self.state_manager.check_victory(self.map, self.wave_protocol):
            self.state = GameState.VICTORY

        for objective in self.objectives:
            if objective.is_active():
                objective.update(self)

    def place_turret(self, tower_type: str, position: Coordinate) -> bool:
        """Строит башню заданного типа в указанной точке."""
        position = self.map.snap_to_grid(position)
        if not self.map.can_place_module(position):
            return False
        turret = self.tower_factory.create(tower_type, position)
        if turret is None:
            return False
        if self.resources.spend(turret.cost):
            self.map.add_module(turret)
            self.map.replan_enemy_paths()
            return True
        return False

    def _spawn_enemy_factory(self, enemy_type: str) -> Optional[HostileEntity]:
        """Создаёт врага заданного типа в точке спавна его фракции и прокладывает путь к базе."""
        faction = self.enemy_factory.faction_for(enemy_type)
        spawn_points = self.map.spawn_points_for(faction)
        if not spawn_points:
            print(f"Ошибка: нет точек спавна для фракции {faction}!")
            return None
        spawn_point = random.choice(spawn_points)
        pos = Coordinate(spawn_point.x, spawn_point.y)  # копия — враг не должен владеть точкой спавна

        enemy = self.enemy_factory.create(enemy_type, pos)
        if enemy is None:
            raise ValueError(f"Неизвестный тип врага в WaveConfig: '{enemy_type}'")

        path = self.map.path_to_base(pos, enemy.faction)
        if path:
            enemy.set_path(path)
        else:
            print(f"Ошибка пути! Враг застрянет.")

        return enemy
