import math
import random
from typing import Callable, Dict, List, Optional

from src.core.map import Map
from src.core.game_state import GameStateManager
from src.systems.resource_bank import ResourceBank
from src.systems.threat_strategy import ThreatStrategy, ShipLandingStrategy, NestSpawnStrategy
from src.factories.tower_factory import TowerFactory
from src.factories.enemy_factory import EnemyFactory
from src.enums import Faction, GameState
from src.entities.hostile_entity import HostileEntity
from src.entities.fauna_nest import FaunaNest
from src.core.coordinate import Coordinate
from src.systems.mission import Objective, SurviveDurationObjective, ProtectTowersObjective


class GameSession:
    """Модель игры: правила, состояние, фабрики башен и врагов."""

    NEST_COUNT_MIN = 6
    NEST_COUNT_MAX = 10
    NEST_MIN_DISTANCE_FROM_BASE = 800.0
    NEST_MAX_DISTANCE_FROM_BASE = 2600.0
    NEST_MIN_SPACING = 500.0
    NEST_PLACEMENT_ATTEMPTS_PER_NEST = 200

    def __init__(self):
        """Создаёт пустую игровую сессию в главном меню."""
        self.map = None
        self.resources = ResourceBank()
        self.threat_strategies: Dict[Faction, ThreatStrategy] = {}
        self.tower_factory = TowerFactory()
        self.enemy_factory = EnemyFactory()
        self.state_manager = GameStateManager(GameState.MENU)
        self.base_health = 100
        self.max_base_health = 100
        self.elapsed_time = 0.0
        self.survive_duration_target = 180.0
        self.objectives: List[Objective] = []
        self.endless = False
        self.on_event: Optional[Callable[..., None]] = None

    def _emit(self, event_name: str, **data):
        """Уведомляет подписчика (например, звуковую систему) об игровом событии."""
        if self.on_event:
            self.on_event(event_name, **data)

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

    def setup_game(self, endless: bool = False):
        """Готовит новую игру: карту, базу, ресурсы, источники угроз и задания.
        endless=True - режим без ограничения по времени и без заданий (см. update):
        победы по таймеру не будет, база остаётся уязвимой, поражение по-прежнему
        возможно."""
        self.state = GameState.PLAYING
        self.endless = endless
        self.base_health = self.max_base_health
        self.resources = ResourceBank(start_credits=1000)

        self.map = Map(on_event=self._emit)
        self.map.power_grid_enabled = True
        self.base_position = Coordinate(self.map.width / 2, self.map.height / 2)
        self.map.nav_grid.set_blocked(self.base_position.x, self.base_position.y, blocked=True)

        margin = 200
        near_edge, far_edge_x, far_edge_y = margin, self.map.width - margin, self.map.height - margin
        self.map.spawn_points = [
            Coordinate(near_edge, near_edge),
            Coordinate(far_edge_x, near_edge),
            Coordinate(near_edge, far_edge_y),
            Coordinate(far_edge_x, far_edge_y),
        ]

        fauna_nests = self._generate_fauna_nests()
        self.map.fauna_nests = fauna_nests
        self.map.spawn_points_by_faction = {
            Faction.CORPORATION: [],
            Faction.FAUNA: [nest.position for nest in fauna_nests],
        }

        print(f"Карта инициализирована")
        print(f"База: {self.base_position}")

        corp_types = self._enemy_types_for_faction(Faction.CORPORATION)
        fauna_types = self._enemy_types_for_faction(Faction.FAUNA)
        self.threat_strategies = {
            Faction.CORPORATION: ShipLandingStrategy(enemy_types=corp_types),
            Faction.FAUNA: NestSpawnStrategy(enemy_types=fauna_types),
        }

        self.elapsed_time = 0.0
        self.objectives = [] if endless else [
            SurviveDurationObjective(target_seconds=self.survive_duration_target),
            ProtectTowersObjective(),
        ]

    def _generate_fauna_nests(self, rng: Optional[random.Random] = None) -> List[FaunaNest]:
        """Расставляет гнёзда фауны один раз при старте игры (новые не появляются, а
        уничтоженные исчезают навсегда - см. Map.update). Случайное число гнёзд в
        диапазоне [NEST_COUNT_MIN, NEST_COUNT_MAX], каждое не дальше
        NEST_MAX_DISTANCE_FROM_BASE и не ближе NEST_MIN_DISTANCE_FROM_BASE от базы
        игрока, и не ближе NEST_MIN_SPACING к уже поставленным гнёздам."""
        rng = rng or random
        count = rng.randint(self.NEST_COUNT_MIN, self.NEST_COUNT_MAX)
        nests: List[FaunaNest] = []
        max_attempts = count * self.NEST_PLACEMENT_ATTEMPTS_PER_NEST
        attempts = 0
        while len(nests) < count and attempts < max_attempts:
            attempts += 1
            angle = rng.uniform(0, 2 * math.pi)
            distance = rng.uniform(self.NEST_MIN_DISTANCE_FROM_BASE, self.NEST_MAX_DISTANCE_FROM_BASE)
            x = self.base_position.x + math.cos(angle) * distance
            y = self.base_position.y + math.sin(angle) * distance
            if not (0 <= x <= self.map.width and 0 <= y <= self.map.height):
                continue
            candidate = Coordinate(x, y)
            if any(candidate.distance_to(nest.position) < self.NEST_MIN_SPACING for nest in nests):
                continue
            nests.append(FaunaNest(candidate))
        return nests

    def _enemy_types_for_faction(self, faction: Faction) -> List[str]:
        """Возвращает зарегистрированные типы врагов, принадлежащие фракции."""
        return [t for t in self.enemy_factory.available_types()
                if self.enemy_factory.faction_for(t) == faction]

    def update(self, delta_time: float):
        """Обновляет игру на один кадр: угрозы, карту, здоровье базы, состояние, задания."""
        if self.state != GameState.PLAYING:
            return

        self.elapsed_time += delta_time
        for strategy in self.threat_strategies.values():
            strategy.update(delta_time, self.map, self._spawn_enemy_factory)

        reached_base, killed_enemies, destroyed_nests = self.map.update(delta_time)
        for enemy in killed_enemies:
            self.resources.add_reward(enemy.reward)
            self._emit("enemy_died", enemy_type=getattr(enemy, "type_name", None), position=enemy.position)

        for nest in destroyed_nests:
            self.resources.add_reward(nest.reward)

        for _ in reached_base:
            self.base_health -= 10
            self._emit("base_hit", position=self.base_position)

        if self.state_manager.check_defeat(self.base_health):
            self.state = GameState.GAME_OVER
            self._emit("defeat")

        if (not self.endless and self.state == GameState.PLAYING
                and self.state_manager.check_victory(self.elapsed_time, self.survive_duration_target)):
            self.state = GameState.VICTORY
            self._emit("victory")

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
            turret.start_landing()
            self.map.add_module(turret)
            self.map.replan_enemy_paths()
            return True
        return False

    def _spawn_enemy_factory(self, enemy_type: str, position: Optional[Coordinate] = None) -> Optional[HostileEntity]:
        """Создаёт врага и прокладывает путь к базе, при необходимости выбирая точку спавна фракции."""
        faction = self.enemy_factory.faction_for(enemy_type)
        if position is None:
            spawn_points = self.map.spawn_points_for(faction)
            if not spawn_points:
                print(f"Ошибка: нет точек спавна для фракции {faction}!")
                return None
            position = random.choice(spawn_points)

        pos = Coordinate(position.x, position.y)

        enemy = self.enemy_factory.create(enemy_type, pos)
        if enemy is None:
            raise ValueError(f"Неизвестный тип врага: '{enemy_type}'")

        if enemy.stages_before_attacking():
            # Отложенная атака: враг сначала кружит у точки появления, дожидаясь
            # сбора группы (см. Map._update_staging_groups), и получает маршрут
            # к базе только когда группа наберётся и атакует всей массой.
            enemy.is_staging = True
        else:
            path = self.map.path_to_base_within_budget(pos, enemy.faction, avoid_danger=enemy.avoids_danger())
            if path:
                enemy.set_path(path)
            elif not enemy.avoids_danger():
                print(f"Ошибка пути! Враг застрянет.")

        return enemy
