"""ConfigLoader и применение параметров башен/врагов из data/config/*.json."""
import json

import pytest

from src.config.config_loader import ConfigLoader
from src.core.coordinate import Coordinate
from src.enums import ArmorType
from src.factories.enemy_factory import EnemyFactory
from src.factories.tower_factory import TowerFactory


def test_config_loader_reads_real_tower_config():
    loader = ConfigLoader()
    config = loader.get_tower_config("laser")

    assert config["range_radius"] == 400
    assert config["damage"] == 15
    assert config["cost"] == 50
    assert config["upgrade_costs"] == [80, 120]


def test_config_loader_reads_real_enemy_config():
    loader = ConfigLoader()
    config = loader.get_enemy_config("drone_walker")

    assert config["max_health"] == 60
    assert config["armor"] == "Light"
    assert config["reward"] == 15


def test_config_loader_returns_empty_dict_for_unknown_type():
    loader = ConfigLoader()
    assert loader.get_tower_config("unknown_tower") == {}
    assert loader.get_enemy_config("unknown_enemy") == {}


def test_config_loader_returns_empty_dict_when_config_dir_missing(tmp_path):
    loader = ConfigLoader(config_dir=tmp_path / "does_not_exist")
    assert loader.get_tower_config("laser") == {}
    assert loader.get_enemy_config("drone_walker") == {}


@pytest.fixture
def custom_config_dir(tmp_path):
    (tmp_path / "towers.json").write_text(json.dumps({
        "laser": {"range_radius": 999, "damage": 1, "cost": 5, "attack_speed": 3.0, "upgrade_costs": [10, 20]}
    }), encoding="utf-8")
    (tmp_path / "enemies.json").write_text(json.dumps({
        "drone_walker": {"max_health": 12345, "speed": 1, "armor": "Heavy", "reward": 999}
    }), encoding="utf-8")
    return tmp_path


def test_tower_factory_applies_custom_config_values(custom_config_dir):
    factory = TowerFactory(config_loader=ConfigLoader(config_dir=custom_config_dir))

    turret = factory.create("laser", Coordinate(0, 0))

    assert turret.range_radius == 999
    assert turret.cost == 5
    assert turret.upgrade_costs == [10, 20]


def test_enemy_factory_applies_custom_config_values_and_converts_armor(custom_config_dir):
    factory = EnemyFactory(config_loader=ConfigLoader(config_dir=custom_config_dir))

    enemy = factory.create("drone_walker", Coordinate(0, 0))

    assert enemy.max_health == 12345
    assert enemy.reward == 999
    assert enemy.armor == ArmorType.HEAVY


def test_tower_factory_falls_back_to_class_defaults_without_config(tmp_path):
    factory = TowerFactory(config_loader=ConfigLoader(config_dir=tmp_path / "missing"))

    turret = factory.create("laser", Coordinate(0, 0))

    assert turret.range_radius == 120
    assert turret.cost == 50
