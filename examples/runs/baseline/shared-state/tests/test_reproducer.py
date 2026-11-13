from source import Bucket


def test_bucket_instances_have_independent_items():
    a = Bucket()
    b = Bucket()

    a.add("x")

    assert a.items == ["x"]
    assert b.items == [], "Bucket instances must not share the class-level items list"
