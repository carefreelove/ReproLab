import pytest

from source import in_window


def test_in_window_includes_end_boundary():
    # 时间窗口应包含两个端点：start 和 end 都应被视为在窗口内
    assert in_window(5, 5, 10) is True, "start 端点应包含在窗口内"
    assert in_window(10, 5, 10) is True, "end 端点应包含在窗口内"


def test_in_window_interior_and_outside():
    assert in_window(7, 5, 10) is True
    assert in_window(4, 5, 10) is False
    assert in_window(11, 5, 10) is False
