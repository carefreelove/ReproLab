from source import Bucket


def test_new_instance_starts_with_empty_items():
    """新建实例的 items 应为空，不受其他实例 add 影响。"""
    a = Bucket()
    a.add(1)

    b = Bucket()
    assert a.items == [1]
    assert b.items == []


def test_two_instances_keep_independent_items():
    """两个实例各自 add 后，items 应互不干扰。"""
    a = Bucket()
    b = Bucket()

    a.add("x")
    b.add("y")

    assert a.items == ["x"]
    assert b.items == ["y"]
