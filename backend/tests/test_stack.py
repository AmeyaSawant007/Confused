from app.engine.history_stack import HistoryStack


def test_push_pop_peek():
    h = HistoryStack()
    assert h.is_empty()
    h.push("change weight", {"w": 1})
    h.push("add constraint", {"w": 2})
    assert len(h) == 2
    assert h.peek()["label"] == "add constraint"
    entry = h.pop()
    assert entry["label"] == "add constraint"
    assert entry["state"] == {"w": 2}
    assert len(h) == 1


def test_pop_empty_returns_none():
    assert HistoryStack().pop() is None
    assert HistoryStack().peek() is None


def test_labels_top_first_and_snapshot():
    h = HistoryStack()
    h.push("first", 1)
    h.push("second", 2)
    assert h.labels() == ["second", "first"]
    assert h.snapshot()["depth"] == 2


def test_capacity_evicts_oldest():
    h = HistoryStack(capacity=2)
    h.push("a", 1)
    h.push("b", 2)
    h.push("c", 3)
    assert h.labels() == ["c", "b"]


def test_state_is_deep_copied():
    h = HistoryStack()
    state = {"nested": [1]}
    h.push("x", state)
    state["nested"].append(999)
    assert h.peek()["state"] == {"nested": [1]}
