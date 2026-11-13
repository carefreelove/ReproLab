from decimal import Decimal

import pytest

from source import money


@pytest.mark.parametrize(
    "amount, expected",
    [
        # 正常值：非临界舍入
        ("1.234", Decimal("1.23")),
        ("1.236", Decimal("1.24")),
        ("0.00", Decimal("0.00")),
        # 临界值：ROUND_HALF_UP 的 .xx5 边界
        ("1.235", Decimal("1.24")),
        ("2.675", Decimal("2.68")),
        ("-2.675", Decimal("-2.68")),
    ],
)
def test_money_rounds_half_up_to_two_places(amount, expected):
    result = money(amount)
    assert isinstance(result, Decimal)
    assert result == expected
