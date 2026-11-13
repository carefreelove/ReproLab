import pytest

from source import mean


def test_mean_empty_list_returns_zero():
    """契约：空输入应返回 0，而不是抛异常。"""
    assert mean([]) == 0


@pytest.mark.parametrize(
    "values, expected",
    [
        ([5], 5),
        ([1, 2, 3], 2),
        ([0, 0], 0),
        ([-1, 1], 0),
        ([-2, -4], -3),
        ([1.5, 2.5], 2.0),
    ],
)
def test_mean_non_empty_returns_arithmetic_mean(values, expected):
    """正常值校验：非空输入返回算术平均值。"""
    assert mean(values) == pytest.approx(expected)
