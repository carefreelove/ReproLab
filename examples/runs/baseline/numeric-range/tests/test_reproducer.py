import sys

import pytest

from more_itertools import numeric_range


def test_numeric_range_eq_and_hash_beyond_maxsize():
    # A range whose length exceeds sys.maxsize is still a valid range.
    # Equality and hashing must work like the built-in range, which does not
    # raise OverflowError for such ranges.
    big = 10**30
    a = numeric_range(big)
    b = numeric_range(big)

    # Equality should not raise and should report equal ranges as equal.
    assert a == b

    # Hashing should not raise and equal ranges should hash equally.
    assert hash(a) == hash(b)

    # Sanity: explicit len() is still allowed to raise OverflowError.
    with pytest.raises(OverflowError):
        len(a)
