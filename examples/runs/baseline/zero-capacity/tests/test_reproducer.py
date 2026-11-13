import pytest

from source import chunks


def test_chunks_zero_returns_empty_list():
    # 约定：n=0 应返回空列表，而不是抛出异常
    assert chunks([1, 2, 3], 0) == []


def test_chunks_negative_raises_value_error():
    # 约定：n<0 应抛出 ValueError
    with pytest.raises(ValueError):
        chunks([1, 2, 3], -1)
