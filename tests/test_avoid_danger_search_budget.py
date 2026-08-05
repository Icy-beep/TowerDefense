"""Регрессия фриза: дорогой поиск пути avoid_danger=True не должен пересчитываться
каждый кадр для застрявшего врага, а число таких поисков в кадре должно быть ограничено."""
import math

import pytest

from src.core.coordinate import Coordinate
from src.core.map import Map
from src.entities.enemies import ScoutDrone
from src.entities.turrets import LaserTurret
from src.enums import Faction


def _fully_boxed_in_map():
    """Карта, где база окружена кольцом башен без разрывов - честного пути в обход всех
    сразу не существует, но сам разведчик у своей точки спавна ничем не накрыт (иначе
    он просто убегает и никогда не доходит до _advance_honestly_or_give_up)."""
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 2000)
    for i in range(8):
        angle = i * (2 * math.pi / 8)
        pos = Coordinate(2000 + 500 * math.cos(angle), 2000 + 500 * math.sin(angle))
        tower = LaserTurret(pos, range_radius=400)
        game_map.modules.append(tower)
        game_map.faction_intel[Faction.CORPORATION].reveal(tower)
    return game_map


def test_stuck_scout_backs_off_instead_of_retrying_every_frame():
    game_map = _fully_boxed_in_map()
    scout = ScoutDrone(Coordinate(500, 500))
    scout.set_path([Coordinate(2000, 2000)])
    game_map.spawn_enemy(scout)

    for _ in range(600):
        game_map.update(0.1)

    assert scout.replan_failure_streak >= 1
    assert scout.replan_retry_cooldown > 0.0, \
        "после неудачного поиска враг должен ждать кулдаун, а не пробовать каждый кадр"


def test_avoid_danger_search_budget_limits_searches_per_frame():
    """Несколько застрявших врагов не должны все пересчитывать дорогой путь в один
    кадр - иначе это даёт заметный фриз (см. path_to_base_within_budget)."""
    game_map = _fully_boxed_in_map()
    scouts = [ScoutDrone(Coordinate(500 + i * 10, 500)) for i in range(5)]
    for s in scouts:
        game_map.spawn_enemy(s)

    game_map.update(0.1)

    attempted = sum(1 for s in scouts if s.replan_failure_streak > 0)
    assert attempted <= Map.MAX_AVOID_DANGER_SEARCHES_PER_FRAME, \
        f"число дорогих avoid_danger-поисков в один кадр должно быть ограничено бюджетом (было {attempted})"


def test_replan_cooldown_grows_exponentially_and_caps():
    """Кулдаун повторной попытки должен расти 2с, 4с, 8с, 16с... и упираться в потолок."""
    class _ZeroRng:
        def random(self):
            return 0.0

    game_map = _fully_boxed_in_map()
    game_map._rng = _ZeroRng()

    scout = ScoutDrone(Coordinate(500, 500))

    expected_cooldowns = [2.0, 4.0, 8.0, 16.0, 16.0]
    for expected in expected_cooldowns:
        game_map._avoid_danger_searches_this_frame = 0
        game_map._advance_honestly_or_give_up(scout, 0.0)
        assert scout.replan_retry_cooldown == pytest.approx(expected)
        scout.replan_retry_cooldown = 0.0


def test_successful_replan_resets_the_failure_streak():
    game_map = Map(width=4000, height=4000)
    game_map.base_position = Coordinate(2000, 200)
    tower = LaserTurret(Coordinate(2000, 1000), range_radius=300)
    game_map.modules.append(tower)
    game_map.faction_intel[Faction.CORPORATION].reveal(tower)

    scout = ScoutDrone(Coordinate(2000, 1800))
    scout.set_path([Coordinate(2000, 200)])
    game_map.spawn_enemy(scout)

    for _ in range(200):
        game_map.update(0.05)

    assert scout.replan_failure_streak == 0, \
        "как только честный путь нашёлся, счётчик неудач должен сброситься"
