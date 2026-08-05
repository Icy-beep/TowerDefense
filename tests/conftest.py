import random
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _seed_random():
    """Фиксирует состояние глобального random перед каждым тестом, чтобы тесты были
    воспроизводимыми - без этого случайные механики (например, расстановка гнёзд
    фауны в GameSession._generate_fauna_nests) могли бы изредка и непредсказуемо
    сталкиваться с зашитыми в тестах координатами, делая падения тестов "плавающими"
    в зависимости от порядка запуска и состояния ОС-энтропии."""
    random.seed(12345)
