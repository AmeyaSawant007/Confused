import pytest

from app.engine.heap import BinaryHeap


def test_max_order():
    h = BinaryHeap(is_max=True)
    for k, p in [("a", 1), ("b", 5), ("c", 3)]:
        h.push(k, p)
    assert [k for k, _, _ in h.drain_sorted()] == ["b", "c", "a"]


def test_min_order():
    h = BinaryHeap(is_max=False)
    for k, p in [("a", 1), ("b", 5), ("c", 3)]:
        h.push(k, p)
    assert [k for k, _, _ in h.drain_sorted()] == ["a", "c", "b"]


def test_peek_update_remove():
    h = BinaryHeap()
    h.push("a", 10)
    h.push("b", 20)
    assert h.peek()[0] == "b"
    h.update("a", 30)
    assert h.peek()[0] == "a"
    h.remove("a")
    assert h.peek()[0] == "b"
    assert len(h) == 1


def test_topk_is_nondestructive():
    h = BinaryHeap()
    for i in range(10):
        h.push(f"o{i}", i)
    top3 = h.topk(3)
    assert [k for k, _, _ in top3] == ["o9", "o8", "o7"]
    assert len(h) == 10


def test_ties_are_stable_fifo():
    h = BinaryHeap()
    h.push("first", 5)
    h.push("second", 5)
    h.push("third", 5)
    assert [k for k, _, _ in h.drain_sorted()] == ["first", "second", "third"]


def test_push_same_key_replaces():
    h = BinaryHeap()
    h.push("a", 1)
    h.push("a", 99)
    assert len(h) == 1
    assert h.peek() == ("a", 99, None)


def test_errors():
    h = BinaryHeap()
    with pytest.raises(IndexError):
        h.pop()
    with pytest.raises(KeyError):
        h.update("nope", 1)
    with pytest.raises(KeyError):
        h.remove("nope")


def test_array_snapshot_and_log():
    h = BinaryHeap()
    h.push("a", 2)
    h.push("b", 9)
    arr = h.to_array()
    assert arr[0]["key"] == "b"  # root is the max
    assert any("insert" in line for line in h.ops_log)
