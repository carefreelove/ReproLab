import pytest


# 替换为真实目标导入与用户契约的预期值。
@pytest.mark.parametrize("value, expected", [(0, 0)])
def test_contract(value, expected):
    assert value == expected
