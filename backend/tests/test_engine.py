import copy

import pytest

from app.engine.decision_engine import EngineError, analyze, what_if
from app.engine.history_stack import HistoryStack
from app.seed_data import TEMPLATE_INDEX


def laptop():
    return copy.deepcopy(TEMPLATE_INDEX["laptop"])


# -- realistic scenarios ------------------------------------------------------
def test_laptop_scenario():
    r = analyze(laptop())
    assert r["winner"]["name"] == "EcoLite 13"
    assert [x["name"] for x in r["ranked"]] == ["EcoLite 13", "AeroBook 14"]
    assert r["ranked"][0]["score"] == pytest.approx(65.0)
    assert [e["name"] for e in r["eliminated"]] == ["Titan Gaming 15"]
    assert any("Weight" in reason for reason in r["eliminated"][0]["reasons"])


def test_internship_scenario():
    r = analyze(copy.deepcopy(TEMPLATE_INDEX["internship"]))
    assert r["winner"]["name"] == "Startup SDE Intern"
    assert [e["name"] for e in r["eliminated"]] == ["Bank IT Intern"]


def test_project_scenario():
    r = analyze(copy.deepcopy(TEMPLATE_INDEX["project"]))
    assert r["winner"]["name"] == "Confused? Decision Platform"
    assert [e["name"] for e in r["eliminated"]] == ["IoT Smart Irrigation"]


def test_tech_scenario_has_four_options_one_eliminated():
    r = analyze(copy.deepcopy(TEMPLATE_INDEX["tech"]))
    assert len(r["ranked"]) == 3
    assert [e["name"] for e in r["eliminated"]] == ["ML & Deep Learning"]
    assert r["winner"]["name"] == "React & Frontend"


# -- engine internals are real -------------------------------------------------
def test_ranking_comes_from_heap_ops():
    r = analyze(laptop())
    assert r["heap"]["mode"] == "max"
    assert len(r["heap"]["array"]) == 2  # two feasible options in the heap
    assert any("extract" in op for op in r["heap"]["ops"])


def test_dijkstra_shortest_path_is_winner():
    r = analyze(laptop())
    dist = r["graph"]["dijkstra"]["dist"]
    opt_dists = {k: v for k, v in dist.items() if k.startswith("o:") and v is not None}
    best_node = min(opt_dists, key=opt_dists.get)
    assert best_node == f"o:{r['winner']['option_id']}"


def test_graph_traversals_cover_nodes():
    r = analyze(laptop())
    n = len(r["graph"]["nodes"])
    assert len(r["graph"]["bfs"]) == n
    assert len(r["graph"]["dfs"]) == n
    assert r["graph"]["bfs"][0] == "decision"


def test_contributions_add_up_to_score():
    r = analyze(laptop())
    for row in r["ranked"]:
        total = sum(c["points"] for c in row["contributions"])
        assert total == pytest.approx(row["score"], abs=0.05)


# -- edge cases -----------------------------------------------------------------
def test_no_options_is_error():
    d = laptop()
    d["options"] = []
    with pytest.raises(EngineError):
        analyze(d)


def test_single_option_scores_100():
    d = laptop()
    d["options"] = [d["options"][0]]
    d["constraints"] = []
    r = analyze(d)
    assert len(r["ranked"]) == 1
    assert r["ranked"][0]["score"] == pytest.approx(100.0)


def test_equal_scores_tie_is_deterministic():
    d = laptop()
    d["constraints"] = []
    for o in d["options"]:
        o["scores"] = {"Price": 100, "Performance": 5, "Battery Life": 10, "Weight": 1.0}
    r = analyze(d)
    scores = [x["score"] for x in r["ranked"]]
    assert scores == [100.0, 100.0, 100.0]
    # stable insertion order from the heap
    assert [x["name"] for x in r["ranked"]] == [
        "AeroBook 14", "Titan Gaming 15", "EcoLite 13"]


def test_weights_not_100_get_normalized():
    d = laptop()
    for c in d["criteria"]:
        c["weight"] = 10  # sums to 40
    r = analyze(d)
    assert any("normalized" in w for w in r["warnings"])
    assert sum(c["weight_pct"] for c in r["criteria"]) == pytest.approx(100.0)
    assert r["winner"]["name"] == "EcoLite 13"  # proportions unchanged


def test_negative_weight_is_error():
    d = laptop()
    d["criteria"][0]["weight"] = -5
    with pytest.raises(EngineError):
        analyze(d)


def test_all_zero_weights_is_error():
    d = laptop()
    for c in d["criteria"]:
        c["weight"] = 0
    with pytest.raises(EngineError):
        analyze(d)


def test_all_options_infeasible():
    d = laptop()
    d["constraints"] = [{"name": "impossible", "target": "Price",
                         "operator": "<=", "value": 1, "hard": True, "enabled": True}]
    r = analyze(d)
    assert r["ranked"] == []
    assert r["winner"] is None
    assert len(r["eliminated"]) == 3
    assert r["confidence"] is None


def test_duplicate_option_names_warn_but_work():
    d = laptop()
    d["constraints"] = []
    d["options"][1]["name"] = "AeroBook 14"
    r = analyze(d)
    assert any("Duplicate option" in w for w in r["warnings"])
    assert len(r["ranked"]) == 3


def test_missing_score_is_error():
    d = laptop()
    del d["options"][0]["scores"]["Price"]
    with pytest.raises(EngineError):
        analyze(d)


def test_unknown_constraint_target_skipped_with_warning():
    d = laptop()
    d["constraints"].append({"name": "x", "target": "Nope", "operator": "<=",
                             "value": 5, "hard": True, "enabled": True})
    r = analyze(d)
    assert any("Nope" in w for w in r["warnings"])


def test_soft_constraint_does_not_eliminate():
    d = laptop()
    d["constraints"] = [{"name": "soft", "target": "Price", "operator": "<=",
                         "value": 60000, "hard": False, "enabled": True}]
    r = analyze(d)
    assert len(r["ranked"]) == 3


# -- what-if + history ------------------------------------------------------------
def test_whatif_weight_change_flips_winner_incrementally():
    base = laptop()
    base["constraints"] = []  # keep Titan feasible
    out = what_if(base, {"Performance": 80})
    assert out["incremental_used"] is True
    assert out["incremental_verified"] is True
    assert out["before"]["winner"]["name"] == "EcoLite 13"
    assert out["after"]["winner"]["name"] == "Titan Gaming 15"
    assert out["segment_trace"]["affected_union"]  # touched nodes recorded
    moves = {m["name"]: m for m in out["movements"]}
    assert moves["Titan Gaming 15"]["status"] == "moved_up"
    assert out["causes"][0]["criterion"] == "Performance"


def test_whatif_disabling_constraint_adds_option():
    out = what_if(laptop(), disable_constraints=["Weight ≤ 2 kg"])
    assert out["incremental_used"] is False  # structural change -> full recompute
    assert len(out["after"]["ranked"]) == 3
    moves = {m["name"]: m for m in out["movements"]}
    assert moves["Titan Gaming 15"]["status"] == "new"


def test_whatif_repeated_changes_stay_consistent():
    base = laptop()
    w1 = what_if(base, {"Performance": 50})
    again = what_if(base, {"Performance": 50})
    assert w1["after"]["winner"] == again["after"]["winner"]
    w2 = what_if(base, {"Performance": 50, "Price": 60, "Battery Life": 5, "Weight": 5})
    assert w2["incremental_verified"] is True


def test_undo_stack_roundtrip():
    h = HistoryStack()
    v1, v2 = {"w": 1}, {"w": 2}
    h.push("change weight", v1)
    h.push("add constraint", v2)
    assert h.pop()["state"] == v2
    assert h.pop()["state"] == v1
    assert h.pop() is None
