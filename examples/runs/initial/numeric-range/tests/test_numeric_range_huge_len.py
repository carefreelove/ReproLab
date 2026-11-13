"""numeric_range 的等值比较与哈希应支持元素数量超过 sys.maxsize 的范围。

内置 range(10**30) 可以正常比较与哈希（只有 len() 抛 OverflowError），
numeric_range 应保持一致。
"""

import pytest

from more_itertools.more import numeric_range

HUGE = 10**30


def test_huge_numeric_range_equality_does_not_overflow():
    a = numeric_range(HUGE)
    b = numeric_range(HUGE)
    assert a == b
    assert not (a != b)


def test_huge_numeric_range_equality_with_different_step():
    assert numeric_range(HUGE) != numeric_range(0, HUGE, 2)


def test_huge_numeric_range_hash_matches_builtin_range():
    assert hash(numeric_range(HUGE)) == hash(range(HUGE))


def test_huge_numeric_range_hash_usable_in_set_and_dict():
    assert len({numeric_range(HUGE), numeric_range(HUGE)}) == 1
    assert {numeric_range(HUGE): 'x'}[numeric_range(HUGE)] == 'x'


def test_huge_numeric_range_len_still_overflows():
    with pytest.raises(OverflowError):
        len(numeric_range(HUGE))


@pytest.mark.parametrize('stop', [0, 1, 2, 10, 2**62])
def test_normal_sized_numeric_range_still_consistent(stop):
    """正常值校验：小范围行为不变。"""
    assert numeric_range(stop) == numeric_range(stop)
    assert hash(numeric_range(stop)) == hash(range(stop))
    assert len(numeric_range(stop)) == stop
