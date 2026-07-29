"""Случайная генерация волн (GameSession._generate_random_waves):
каждый запуск игры даёт разное число волн и разный состав врагов,
но всегда в допустимых границах и только из зарегистрированных типов."""
import random
import pytest
from src.core.game_session import GameSession


@pytest.fixture
def session():
    s = GameSession()
    s.setup_game()
    return s


def test_generated_waves_count_within_bounds(session):
    waves = session._generate_random_waves(rng=random.Random(1))
    assert 4 <= len(waves) <= 7


def test_generated_waves_use_only_registered_enemy_types(session):
    available = set(session.enemy_factory.available_types())
    waves = session._generate_random_waves(rng=random.Random(2))

    for wave in waves:
        assert set(wave.enemy_types).issubset(available)
        assert len(wave.enemy_types) >= 1


def test_generated_waves_have_positive_count_and_interval(session):
    waves = session._generate_random_waves(rng=random.Random(3))
    for wave in waves:
        assert wave.count > 0
        assert wave.interval > 0


def test_same_seed_produces_same_waves(session):
    waves_a = session._generate_random_waves(rng=random.Random(42))
    waves_b = session._generate_random_waves(rng=random.Random(42))

    assert len(waves_a) == len(waves_b)
    for a, b in zip(waves_a, waves_b):
        assert a.enemy_types == b.enemy_types
        assert a.count == b.count
        assert a.interval == pytest.approx(b.interval)


def test_different_seeds_can_produce_different_wave_counts_or_composition():
    """Не строгий инвариант (рандом иногда совпадает), но по 30 запускам
    хотя бы что-то должно отличаться — иначе рандомизация не работает."""
    session = GameSession()
    session.setup_game()
    results = {
        tuple((tuple(w.enemy_types), w.count) for w in session._generate_random_waves(rng=random.Random(seed)))
        for seed in range(30)
    }
    assert len(results) > 1


def test_setup_game_uses_random_waves_by_default(session):
    assert len(session.wave_protocol.waves) >= 4
