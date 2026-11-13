from source import Bucket


def test_instances_have_independent_items():
    b1 = Bucket()
    b2 = Bucket()

    b1.add("a")

    assert b1.items == ["a"]
    assert b2.items == [], f"b2.items 被 b1.add 污染: {b2.items!r}"


def test_second_instance_add_does_not_affect_first():
    b1 = Bucket()
    b2 = Bucket()

    b2.add(1)
    b2.add(2)

    assert b2.items == [1, 2]
    assert b1.items == [], f"b1.items 被 b2.add 污染: {b1.items!r}"
