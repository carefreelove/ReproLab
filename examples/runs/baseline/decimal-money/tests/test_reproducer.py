from decimal import Decimal

from source import money


def test_money_rounds_half_up():
    # 2.675 按 ROUND_HALF_UP 保留两位应为 2.68
    assert money("2.675") == Decimal("2.68")
