import pytest

from source import paginate


@pytest.mark.parametrize("offset", [-1, -2, -3, -100])
def test_paginate_rejects_negative_offset(offset):
    """契约：负 offset 非法，必须抛 ValueError，而不是按切片规则返回元素。"""
    with pytest.raises(ValueError):
        paginate([1, 2, 3], offset, 2)


def test_paginate_zero_offset_is_valid():
    """正常值校验：offset=0 是合法边界，返回开头 limit 个元素。"""
    assert paginate([1, 2, 3], 0, 2) == [1, 2]


def test_paginate_positive_offset_is_valid():
    assert paginate([1, 2, 3, 4], 2, 2) == [3, 4]
