import pytest

from app.engine.decision_engine import analyze
from app.engine.ml.semantic import KeywordFieldMatcher
from app.importer.extractor import extract_facts, standalone_number
from app.importer.importer import SAMPLES, import_samples, load_sample

CRIT = ["Price", "Performance", "Battery Life", "Weight"]


def test_standalone_number_guards():
    assert standalone_number("Intel Core i7 13th Gen") == (None, None)
    assert standalone_number("Up to 14 hours") == (14.0, "hours")
    assert standalone_number("1.4 kg") == (1.4, "kg")
    assert standalone_number("₹72,000")[0] == 72000.0
    assert standalone_number("no digits here") == (None, None)


def test_fixture_extraction():
    facts = extract_facts(load_sample("aerobook"))
    assert facts["name"] == "AeroBook 14"
    assert facts["price"]["number"] == 72000
    assert facts["rating"]["number"] == 4.3
    by_label = {s["label"]: s for s in facts["specs"]}
    assert by_label["Battery Backup"]["number"] == 14
    assert by_label["Battery Backup"]["unit"] == "hours"
    assert by_label["Weight"]["number"] == 1.4
    assert by_label["Performance Score"]["number"] == 7200
    assert by_label["Processor"]["number"] is None  # i7/13th guarded
    assert by_label["RAM"]["number"] == 16


def test_samples_catalog():
    assert len(SAMPLES) == 3
    assert all("offline sample" in s["label"] for s in SAMPLES)


def test_keyword_matcher_assignments():
    m = KeywordFieldMatcher()
    out = m.match(CRIT, [{"text": t} for t in
                         ["Price", "Battery Backup", "Weight", "Performance Score",
                          "Customer Rating", "RAM", "Processor"]])
    got = {a["phrase"]: a["criterion"] for a in out["assignments"]}
    assert got["Price"] == "Price"
    assert got["Battery Backup"] == "Battery Life"
    assert got["Weight"] == "Weight"
    assert got["Performance Score"] == "Performance"
    assert got["Customer Rating"] is None
    assert got["RAM"] is None
    assert out["matrix"]["Price"]["Price"] == 1.0


def test_sample_import_fills_all_criteria():
    res = import_samples(CRIT)
    assert res["matcher"] in ("neural", "keyword")
    assert len(res["options"]) == 3
    eco = next(o for o in res["options"] if "EcoLite" in o["name"])
    assert eco["scores"] == {"Price": 55000, "Performance": 5100,
                             "Battery Life": 18, "Weight": 1.2}
    assert eco["missing"] == []
    assert all(o["filled"] for o in res["options"])
    assert len(res["match_tables"]) == 3


def test_imported_options_analyze_to_ecolite():
    res = import_samples(CRIT)
    decision = {
        "title": "Which laptop should I buy?",
        "category": "gadgets",
        "criteria": [
            {"name": "Price", "weight": 30, "type": "cost"},
            {"name": "Performance", "weight": 35, "type": "benefit"},
            {"name": "Battery Life", "weight": 20, "type": "benefit"},
            {"name": "Weight", "weight": 15, "type": "cost"},
        ],
        "options": [{"name": o["name"], "description": "",
                     "scores": o["scores"]} for o in res["options"]],
        "constraints": [
            {"name": "Budget", "target": "Price", "operator": "<=",
             "value": 80000, "hard": True, "enabled": True},
            {"name": "Light", "target": "Weight", "operator": "<=",
             "value": 2.0, "hard": True, "enabled": True},
        ],
    }
    r = analyze(decision)
    assert r["winner"]["name"] == "EcoLite 13"
    assert [e["name"] for e in r["eliminated"]] == ["Titan Gaming 15"]


def test_neural_matcher_semantics():
    pytest.importorskip("sentence_transformers")
    from app.engine.ml.semantic import NeuralFieldMatcher
    m = NeuralFieldMatcher()
    out = m.match(["Price", "Battery Life"],
                  [{"text": "battery backup 14 hrs"},
                   {"text": "how much does it cost"}])
    mx = out["matrix"]
    assert out["matcher"] == "neural"
    assert mx["battery backup 14 hrs"]["Battery Life"] > 0.5
    assert (mx["battery backup 14 hrs"]["Battery Life"] >
            mx["battery backup 14 hrs"]["Price"] + 0.2)
    # zero token overlap with "Price" -- purely semantic
    assert mx["how much does it cost"]["Price"] > mx["how much does it cost"]["Battery Life"]
