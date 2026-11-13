import pytest

from more_itertools import chunked_even


class TrackingIterator:
    """Iterator that records how many items have been consumed."""

    def __init__(self, data):
        self._data = list(data)
        self._index = 0
        self.consumed = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._data):
            raise StopIteration
        item = self._data[self._index]
        self._index += 1
        self.consumed += 1
        return item


def test_chunked_even_n_zero_returns_empty_without_consuming():
    it = TrackingIterator([1, 2, 3, 4, 5])
    result = list(chunked_even(it, 0))
    assert result == []
    assert it.consumed == 0


def test_chunked_even_n_negative_raises_without_consuming():
    it = TrackingIterator([1, 2, 3, 4, 5])
    with pytest.raises(ValueError):
        list(chunked_even(it, -1))
    assert it.consumed == 0
