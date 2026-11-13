import pytest

from source import chunks


def test_chunks_normal():
    assert chunks([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunks_zero_returns_empty_list():
    # 契约：n=0 返回空列表
    assert chunks([1, 2, 3], 0) == []


def test_chunks_zero_on_empty_input():
    assert chunks([], 0) == []


@pytest.mark.parametrize("n", [-1, -3])
def test_chunks_negative_raises_value_error(n):
    # 契约：n<0 抛出 ValueError
    with pytest.raises(ValueError):
        chunks([1, 2, 3], n)
