from app.engine.trie import Trie


def test_insert_search_case_insensitive():
    t = Trie()
    t.insert("Laptop", {"id": 1})
    assert t.search("laptop") == [{"id": 1}]
    assert t.search("LAPTOP") == [{"id": 1}]
    assert t.search("lap") == []


def test_prefix_search():
    t = Trie()
    for w in ["laptop", "laptop purchase", "laptop comparison", "lamp", "phone"]:
        t.insert(w)
    words = [m["word"] for m in t.starts_with("lap")]
    assert words == ["laptop", "laptop purchase", "laptop comparison"]
    assert [m["word"] for m in t.starts_with("la")] == [
        "lamp", "laptop", "laptop purchase", "laptop comparison"]
    assert t.starts_with("zzz") == []


def test_prefix_limit():
    t = Trie()
    for i in range(20):
        t.insert(f"opt{i}")
    assert len(t.starts_with("opt", limit=5)) == 5


def test_delete_word_and_ref():
    t = Trie()
    t.insert("laptop", {"a": 1})
    t.insert("laptop", {"a": 2})
    assert t.delete("laptop", {"a": 1}) is True
    assert t.search("laptop") == [{"a": 2}]
    assert t.delete("laptop") is True
    assert t.search("laptop") == []
    assert t.delete("laptop") is False


def test_delete_keeps_shared_prefix():
    t = Trie()
    t.insert("car")
    t.insert("card")
    t.delete("card")
    assert [m["word"] for m in t.starts_with("car")] == ["car"]


def test_snapshot_shape():
    t = Trie()
    t.insert("ab")
    t.insert("ac")
    s = t.snapshot()
    assert s["total_words"] == 2
    assert s["nodes"][0]["char"] == "root"
    assert len(s["edges"]) == len(s["nodes"]) - 1
