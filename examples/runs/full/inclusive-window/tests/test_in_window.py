import pytest

from source import in_window


@pytest.mark.parametrize(
    "value, start, end, expected",
    [
        # 正常值：窗口内部
        (5, 0, 10, True),
        (1, 0, 10, True),
        (9, 0, 10, True),
        # 临界值：两个端点都应包含
        (0, 0, 10, True),
        (10, 0, 10, True),
        # 相邻值：窗口外
        (-1, 0, 10, False),
        (11, 0, 10, False),
        # 负时间戳窗口
        (-10, -10, -5, True),
        (-5, -10, -5, True),
        (-11, -10, -5, False),
        (-4, -10, -5, False),
        # 单点窗口（start == end）应包含该点
        (7, 7, 7, True),
        (6, 7, 7, False),
        (8, 7, 7, False),
        # 大整数时间戳
        (2**40, 2**40, 2**40 + 100, True),
        (2**40 + 100, 2**40, 2**40 + 100, True),
        (2**40 + 101, 2**40, 2**40 + 100, False),
    ],
)
def test_in_window_includes_both_endpoints(value, start, end, expected):
    assert in_window(value, start, end) is expected


def test_in_window_end_boundary_explicit():
    """结束时刻的记录必须被包含在窗口内。"""
    start, end = 1_700_000_000, 1_700_000_600
    assert in_window(end, start, end) is True
