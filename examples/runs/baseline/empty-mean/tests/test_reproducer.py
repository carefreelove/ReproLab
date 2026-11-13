import pytest

from source import mean


def test_mean_empty_list_returns_zero():
    assert mean([]) == 0


def test_mean_non_empty_list_returns_arithmetic_mean():
    assert mean([1, 2, 3, 4]) == pytest.approx(2.5)
    assert mean([10]) == pytest.approx(10)
