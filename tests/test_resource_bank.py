"""Списание ресурсов и запрет постройки при недостатке средств (юнит-уровень)."""
from src.systems.resource_bank import ResourceBank


def test_spend_succeeds_when_enough_credits():
    bank = ResourceBank(start_credits=100)

    result = bank.spend(60)

    assert result is True
    assert bank.credits == 40


def test_spend_fails_when_not_enough_credits():
    bank = ResourceBank(start_credits=50)

    result = bank.spend(100)

    assert result is False
    assert bank.credits == 50, "кредиты не должны списываться при неудачной попытке"


def test_spend_exact_amount_leaves_zero_balance():
    bank = ResourceBank(start_credits=50)

    assert bank.spend(50) is True
    assert bank.credits == 0


def test_spend_zero_amount_always_succeeds():
    bank = ResourceBank(start_credits=10)

    assert bank.spend(0) is True
    assert bank.credits == 10


def test_add_reward_increases_credits():
    bank = ResourceBank(start_credits=0)

    bank.add_reward(15)
    bank.add_reward(40)

    assert bank.credits == 55
