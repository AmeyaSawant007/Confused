from app.engine.hash_table import HashTable


def test_put_get_update_delete():
    h = HashTable(capacity=4)
    h.put("o1", "Laptop A")
    assert h.get("o1") == "Laptop A"
    assert "o1" in h
    h.put("o1", "Laptop A2")
    assert h.get("o1") == "Laptop A2"
    assert h.delete("o1") is True
    assert h.get("o1") is None
    assert h.delete("o1") is False


def test_missing_key_default():
    assert HashTable().get("x", "dflt") == "dflt"


def test_resize_keeps_entries():
    h = HashTable(capacity=4, load_factor=0.7)
    for i in range(20):
        h.put(f"k{i}", i)
    assert h.capacity > 4
    assert h.resizes >= 1
    for i in range(20):
        assert h.get(f"k{i}") == i


def test_snapshot_shape():
    h = HashTable(capacity=8)
    h.put("a", 1)
    h.put("b", 2)
    s = h.snapshot()
    assert s["capacity"] == 8
    assert s["size"] == 2
    assert len(s["buckets"]) == 8
    assert abs(s["load"] - 0.25) < 1e-9
