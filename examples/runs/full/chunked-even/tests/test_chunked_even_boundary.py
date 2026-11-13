"""Reproduce boundary/iterator-state defects of more_itertools.chunked_even.

Contract under test (per user report):
  * n == 0  -> empty result, input iterator must not be consumed
  * n <  0  -> ValueError, input iterator must not be consumed
"""

import pytest

import more_itertools as mi


class TracingIterator:
    """Iterator that records how many items were pulled from the source."""

    def __init__(self, values):
        self.source = iter(values)
        self.consumed = 0

    def __iter__(self):
        return self

    def __next__(self):
        value = next(self.source)
        self.consumed += 1
        return value


DATA = [1, 2, 3, 4, 5, 6, 7]


def test_sanity_normal_n():
    """Baseline: normal n keeps working (guards against unrelated breakage)."""
    assert list(mi.chunked_even(iter(DATA), 3)) == [[1, 2, 3], [4, 5], [6, 7]]


def test_n_zero_returns_empty_and_does_not_consume():
    it = TracingIterator(DATA)
    result = list(mi.chunked_even(it, 0))
    assert result == []
    assert it.consumed == 0, f"n=0 consumed {it.consumed} item(s) from the input"


@pytest.mark.parametrize("n", [-1, -2, -5])
def test_negative_n_raises_value_error_and_does_not_consume(n):
    it = TracingIterator(DATA)
    with pytest.raises(ValueError):
        list(mi.chunked_even(it, n))
    assert it.consumed == 0, f"n={n} consumed {it.consumed} item(s) from the input"
