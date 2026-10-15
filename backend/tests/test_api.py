import copy

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed_data import TEMPLATE_INDEX

client = TestClient(app)


def setup_module():
    client.__enter__()  # run lifespan: seed DB + trie index


def teardown_module():
    client.__exit__(None, None, None)


def test_health_and_meta():
    assert client.get("/api/health").json()["status"] == "ok"
    assert len(client.get("/api/categories").json()["categories"]) == 8
    assert len(client.get("/api/templates").json()["templates"]) == 4
    assert client.get("/api/templates/laptop").json()["title"].startswith("Which laptop")


def test_analyze_endpoint():
    r = client.post("/api/analyze", json=TEMPLATE_INDEX["laptop"])
    assert r.status_code == 200
    body = r.json()
    assert body["winner"]["name"] == "EcoLite 13"
    assert "heap" in body and "segment" in body and "graph" in body


def test_analyze_validation_error():
    bad = copy.deepcopy(TEMPLATE_INDEX["laptop"])
    bad["options"] = []
    r = client.post("/api/analyze", json=bad)
    assert r.status_code == 400
    assert "detail" in r.json()


def test_whatif_endpoint():
    r = client.post("/api/whatif", json={
        "baseline": TEMPLATE_INDEX["laptop"],
        "weights": {"Performance": 60}})
    assert r.status_code == 200
    body = r.json()
    assert body["incremental_used"] is True
    assert body["incremental_verified"] is True
    assert body["before"]["winner"]["name"] == "EcoLite 13"


def test_save_checkpoint_undo_flow():
    payload = copy.deepcopy(TEMPLATE_INDEX["tech"])
    created = client.post("/api/decisions", json=payload).json()
    did = created["id"]
    try:
        edited = copy.deepcopy(payload)
        edited["criteria"][0]["weight"] = 99
        cp = client.post(f"/api/decisions/{did}/checkpoint",
                         json={"label": "Boost Job Demand", "state": edited}).json()
        assert cp["history"]["depth"] == 1
        undone = client.post(f"/api/decisions/{did}/undo").json()
        assert undone["undone"] == "Boost Job Demand"
        assert undone["restored"]["criteria"][0]["weight"] == 25
        assert undone["history"]["depth"] == 0
        # second undo fails honestly
        assert client.post(f"/api/decisions/{did}/undo").status_code == 400
    finally:
        client.delete(f"/api/decisions/{did}")


def test_search_uses_trie():
    r = client.get("/api/search", params={"q": "lap"})
    assert r.status_code == 200
    words = [x["word"].lower() for x in r.json()["results"]]
    assert any("laptop" in w for w in words)


def test_playgrounds():
    h = client.post("/api/play/heap", json={"mode": "max", "ops": [
        {"op": "push", "key": "a", "priority": 3},
        {"op": "push", "key": "b", "priority": 9},
        {"op": "pop"}]}).json()
    assert h["steps"][-1]["result"]["key"] == "b"

    t = client.post("/api/play/trie", json={"ops": [
        {"op": "insert", "word": "laptop"},
        {"op": "insert", "word": "lamp"},
        {"op": "prefix", "prefix": "la"}]}).json()
    assert sorted(t["steps"][-1]["result"]["words"]) == ["lamp", "laptop"]

    g = client.post("/api/play/graph", json={"ops": [
        {"op": "bfs", "start": "A"},
        {"op": "dijkstra", "start": "A"}]}).json()
    assert g["steps"][0]["result"]["order"][0] == "A"
    assert g["steps"][1]["result"]["dist"]["E"] == 9  # A-C-B-E: 2+1+6

    s = client.post("/api/play/segment", json={
        "values": [30, 35, 20, 15], "labels": ["a", "b", "c", "d"],
        "ops": [{"op": "update", "index": 1, "value": 50},
                {"op": "total"}]}).json()
    assert s["steps"][1]["result"]["total"] == 115

    hh = client.post("/api/play/hash", json={"capacity": 4, "ops": [
        {"op": "put", "key": "k1", "value": 1},
        {"op": "get", "key": "k1"}]}).json()
    assert hh["steps"][1]["result"] == {"value": 1}

    st = client.post("/api/play/stack", json={"ops": [
        {"op": "push", "label": "v1"},
        {"op": "push", "label": "v2"},
        {"op": "pop"}]}).json()
    assert st["steps"][-1]["result"] == {"popped": "v2"}


def test_import_samples_endpoint():
    crits = ["Price", "Performance", "Battery Life", "Weight"]
    samples = client.get("/api/import/samples").json()["samples"]
    assert len(samples) == 3
    r = client.post("/api/import", json={"mode": "samples", "criteria": crits})
    assert r.status_code == 200
    body = r.json()
    assert body["matcher"] in ("neural", "keyword")
    assert len(body["options"]) == 3
    assert body["options"][0]["sources"]


def test_match_endpoint():
    r = client.post("/api/match", json={
        "criteria": ["Price", "Weight"],
        "phrases": ["Price", "Weight", "totally unrelated xyz"]})
    assert r.status_code == 200
    body = r.json()
    assert body["matrix"]["Price"]["Price"] >= 0.9
    got = {a["phrase"]: a["criterion"] for a in body["assignments"]}
    assert got["Price"] == "Price"
    assert got["Weight"] == "Weight"


def test_profiles_crud():
    saved = client.post("/api/profiles", json={
        "category": "gadgets",
        "weights": {"Price": 40, "Performance": 60},
        "criteria": [{"name": "Price", "type": "cost"}]}).json()
    assert saved["weights"]["Price"] == 40
    assert client.get("/api/profiles/gadgets").json()["weights"]["Performance"] == 60
    assert any(p["category"] == "gadgets"
               for p in client.get("/api/profiles").json()["profiles"])
    assert client.delete("/api/profiles/gadgets").json() == {"deleted": "gadgets"}
    assert client.get("/api/profiles/gadgets").status_code == 404


def test_duels_endpoint():
    r = client.post("/api/duels",
                    json={"decision": TEMPLATE_INDEX["laptop"], "n": 4})
    assert r.status_code == 200
    body = r.json()
    assert len(body["pairs"]) == 3
    assert set(body["pairs"][0].keys()) == {"a", "b", "margin"}


def test_learn_endpoint_and_validation():
    pairs = client.post(
        "/api/duels", json={"decision": TEMPLATE_INDEX["laptop"]}).json()["pairs"]
    answers = [{"a": p["a"]["id"], "b": p["b"]["id"], "winner": p["a"]["id"]}
               for p in pairs]
    r = client.post("/api/learn",
                    json={"decision": TEMPLATE_INDEX["laptop"], "answers": answers})
    assert r.status_code == 200
    body = r.json()
    assert body["method"] == "logistic_regression"
    assert sum(body["weights"].values()) == pytest.approx(100.0)
    assert body["loss_curve"][0] > body["loss_curve"][-1]
    bad = client.post("/api/learn", json={
        "decision": TEMPLATE_INDEX["laptop"],
        "answers": [{"a": pairs[0]["a"]["id"], "b": pairs[0]["b"]["id"],
                     "winner": "ghost"}]})
    assert bad.status_code == 400
