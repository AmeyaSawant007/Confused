import math

from app.engine.graph import Graph


def sample() -> Graph:
    g = Graph()
    for a, b, w in [("A", "B", 4), ("A", "C", 2), ("C", "B", 1),
                    ("B", "D", 5), ("C", "D", 8), ("D", "E", 2)]:
        g.add_edge(a, b, weight=w)
    return g


def test_bfs_order():
    g = sample()
    assert g.bfs("A") == ["A", "B", "C", "D", "E"]


def test_bfs_unknown_start():
    assert sample().bfs("ZZZ") == []


def test_dfs_visits_all_starting_first():
    order = sample().dfs("A")
    assert order[0] == "A"
    assert sorted(order) == ["A", "B", "C", "D", "E"]


def test_dijkstra_distances():
    dist, _ = sample().dijkstra("A")
    assert dist["A"] == 0
    assert dist["B"] == 3  # A -> C -> B
    assert dist["C"] == 2
    assert dist["D"] == 8  # A -> C -> B -> D
    assert dist["E"] == 10  # ... -> D -> E


def test_dijkstra_path():
    g = sample()
    _, prev = g.dijkstra("A")
    assert g.shortest_path(prev, "B") == ["A", "C", "B"]
    assert g.shortest_path(prev, "E") == ["A", "C", "B", "D", "E"]


def test_dijkstra_unreachable_is_inf():
    g = sample()
    g.add_node("LONELY")
    dist, _ = g.dijkstra("A")
    assert math.isinf(dist["LONELY"])


def test_snapshot_counts():
    s = sample().snapshot()
    assert s["num_vertices"] == 5
    assert s["num_edges"] == 6
    assert set(s["adjacency"]["A"][0].keys()) == {"to", "w"}
