import pytest

from source import paginate


def test_paginate_rejects_negative_offset():
    items = [1, 2, 3, 4, 5]
    with pytest.raises(ValueError):
        paginate(items, -1, 2)
