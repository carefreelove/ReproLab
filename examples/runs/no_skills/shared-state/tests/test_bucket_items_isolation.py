from source import Bucket


def test_instances_have_independent_items():
    b1 = Bucket()
    b2 = Bucket()

    b1.add(1)
    b2.add(2)

    assert b1.items == [1]
    assert b2.items == [2]


def test_new_instance_starts_empty_after_other_instance_add():
    b1 = Bucket()
    b1.add("x")

    b2 = Bucket()
    assert b2.items == []
