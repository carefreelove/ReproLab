"""chunked_even 边界复现：n=0 与 n<0 的行为及输入迭代器消耗状态。"""

import pytest

import more_itertools as mi


class TracingIterator:
    """记录被消耗元素个数的迭代器。"""

    def __init__(self, values):
        self.source = iter(values)
        self.consumed = 0

    def __iter__(self):
        return self

    def __next__(self):
        value = next(self.source)
        self.consumed += 1
        return value


def test_normal_value_still_works():
    """正常值校验：n=3 时分组长度差不超过 1，且元素完整。"""
    assert list(mi.chunked_even([1, 2, 3, 4, 5, 6, 7], 3)) == [
        [1, 2, 3],
        [4, 5],
        [6, 7],
    ]


def test_n_zero_returns_empty_and_does_not_consume():
    """n=0 应得到空结果，且不消耗输入迭代器。"""
    it = TracingIterator([1, 2, 3, 4, 5])
    result = list(mi.chunked_even(it, 0))
    assert result == []
    assert it.consumed == 0


@pytest.mark.parametrize("n", [-1, -2, -5])
def test_n_negative_raises_value_error_without_consuming(n):
    """n<0 应抛出 ValueError，且不消耗输入迭代器。"""
    it = TracingIterator([1, 2, 3, 4, 5])
    with pytest.raises(ValueError):
        list(mi.chunked_even(it, n))
    assert it.consumed == 0
