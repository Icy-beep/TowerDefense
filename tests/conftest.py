import random
from functools import partial
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


@pytest.fixture(autouse=True)
def _lightweight_view_assets(monkeypatch, tmp_path, request):
    """UI-тесты используют настоящие менеджеры с пустой папкой ресурсов.

    Меняем только конструкторы в GameView: прямые тесты SoundManager,
    SpriteManager и MusicManager по-прежнему проверяют загрузку ресурсов.
    Маркер real_assets позволяет проверить и полное окно с ресурсами.
    """
    if request.node.get_closest_marker("real_assets"):
        return
    from src.ui import game_window
    from src.ui.music_manager import MusicManager
    from src.ui.sound_manager import SoundManager
    from src.ui.sprite_manager import SpriteManager

    root = str(tmp_path / "empty_assets")
    monkeypatch.setattr(game_window, "SoundManager", partial(SoundManager, sounds_root=root))
    monkeypatch.setattr(game_window, "SpriteManager", partial(SpriteManager, sprites_root=root))
    monkeypatch.setattr(game_window, "MusicManager", partial(MusicManager, music_root=root))
