"""Reproduce chunked_even boundary handling for n <= 0.

Expected (per issue):
  * n == 0 -> empty result, input iterator not consumed
  * n < 0  -> ValueError, input iterator not consumed
"""

import pytest

import more_itertools as mi


class CountingIterator:
    """Iterator that records how many items were pulled from it."""

    def __init__(self, data):
        self._data = iter(data)
        self.items_seen = 0

    def __iter__(self):
        return self

    def __next__(self):
        item = next(self._data)
        self.items_seen += 1
        return item


def test_chunked_even_zero_returns_empty_without_consuming():
    it = CountingIterator([1, 2, 3, 4, 5])
    assert list(mi.chunked_even(it, 0)) == []
    assert it.items_seen == 0


def test_chunked_even_negative_raises_value_error_without_consuming():
    it = CountingIterator([1, 2, 3, 4, 5])
    with pytest.raises(ValueError):
        list(mi.chunked_even(it, -1))
    assert it.items_seen == 0


def test_chunked_even_negative_two_raises_value_error_without_consuming():
    it = CountingIterator([1, 2, 3, 4, 5])
    with pytest.raises(ValueError):
        list(mi.chunked_even(it, -2))
    assert it.items_seen == 0
