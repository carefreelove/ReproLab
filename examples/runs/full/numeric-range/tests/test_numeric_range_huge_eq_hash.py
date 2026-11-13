"""numeric_range 在元素数量超过 sys.maxsize 时的等值比较与哈希。

内置 range 的 == 与 hash 不依赖 len()，因此 range(10**30) 可以正常比较与哈希；
numeric_range 的 __eq__/__hash__ 却直接调用 len(self)，在 _len > sys.maxsize 时
触发 OverflowError: cannot fit 'int' into an index-sized integer。

注意：numeric_range 只接受位置参数（__init__(self, *args)），step 必须作为第三个
位置参数传入。
"""

import sys

import pytest

from more_itertools import numeric_range

HUGE = 10**30
assert HUGE > sys.maxsize


def test_small_range_baseline():
    """正常值校验：小范围行为不受影响。"""
    a = numeric_range(0, 10, 2)
    b = numeric_range(0, 10, 2)
    assert len(a) == 5
    assert a == b
    assert hash(a) == hash(b)
    assert a != numeric_range(0, 10, 3)


def test_huge_range_equality_does_not_overflow():
    a = numeric_range(HUGE)
    b = numeric_range(HUGE)
    # 与内置 range 一致：等值比较不应抛 OverflowError
    assert a == b
    assert not (a != b)


def test_huge_range_inequality_does_not_overflow():
    a = numeric_range(HUGE)
    assert a != numeric_range(HUGE, 2 * HUGE)
    assert a != numeric_range(HUGE, 2 * HUGE, 2)


def test_huge_range_hash_does_not_overflow():
    a = numeric_range(HUGE)
    b = numeric_range(HUGE)
    h = hash(a)
    assert isinstance(h, int)
    # 等值对象必须哈希一致
    assert h == hash(b)


def test_huge_range_usable_as_dict_key():
    d = {numeric_range(HUGE): 'value'}
    assert d[numeric_range(HUGE)] == 'value'


def test_huge_range_len_still_overflows():
    """显式 len() 仍可抛 OverflowError（与内置 range 一致）。"""
    with pytest.raises(OverflowError):
        len(numeric_range(HUGE))
    with pytest.raises(OverflowError):
        len(range(HUGE))
