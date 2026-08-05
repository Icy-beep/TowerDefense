import random
import sys
from pathlib import Path

import pygame
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def pytest_configure(config):
    """Инициализирует pygame один раз перед всей сессией тестов. Без этого тесты,
    которым нужна видеоподсистема (например, OrbitalModeController.update() дергает
    pygame.key.get_pressed() - см. test_enemy_selection.py), падают с
    'video system not initialized', если случайно выполняются раньше любого теста,
    который сам вызывает pygame.init() - раньше такой глобальной инициализации не
    было, и тест зависел от порядка запуска файлов."""
    pygame.init()


@pytest.fixture(autouse=True)
def _seed_random():
    """Фиксирует состояние глобального random перед каждым тестом, чтобы тесты были
    воспроизводимыми - без этого случайные механики (например, расстановка гнёзд
    фауны в GameSession._generate_fauna_nests) могли бы изредка и непредсказуемо
    сталкиваться с зашитыми в тестах координатами, делая падения тестов "плавающими"
    в зависимости от порядка запуска и состояния ОС-энтропии."""
    random.seed(12345)
