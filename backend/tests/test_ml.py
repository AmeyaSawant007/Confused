import copy

import numpy as np
import pytest

from app.engine.decision_engine import EngineError
from app.engine.ml.preference_learner import learn_weights, select_duel_pairs
from app.engine.scorer import min_max_normalize
from app.seed_data import TEMPLATE_INDEX


def _synthetic(seed=7, n_opts=6):
    rng = np.random.default_rng(seed)
    names = ["C1", "C2", "C3"]
    true_w = np.array([50.0, 30.0, 20.0])
    opts = []
    for i in range(n_opts):
        vals = rng.uniform(1, 10, 3)
        opts.append({"name": f"O{i}",
                     "scores": {n: float(v) for n, v in zip(names, vals)}})
    decision = {"title": "synthetic", "category": "custom",
                "criteria": [{"name": n, "weight": 10, "type": "benefit"}
                             for n in names],
                "options": opts, "constraints": []}
    norms = {n: min_max_normalize({o["name"]: o["scores"][n] for o in opts},
                                  "benefit") for n in names}
    scores = {o["name"]: sum(norms[n][o["name"]] * true_w[i]
                             for i, n in enumerate(names)) for o in opts}
    return decision, names, true_w, scores


def _answers_from_scores(decision, scores):
    names = [o["name"] for o in decision["options"]]
    out = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if abs(scores[a] - scores[b]) < 1e-9:
                continue
            out.append({"a": a, "b": b,
                        "winner": a if scores[a] > scores[b] else b})
    return out


def test_duel_pairs_closest_first_with_coverage():
    out = select_duel_pairs(copy.deepcopy(TEMPLATE_INDEX["laptop"]), n=6)
    assert len(out["pairs"]) == 3  # C(3,2)
    margins = [p["margin"] for p in out["pairs"]]
    assert margins == sorted(margins)
    seen = {o for p in out["pairs"] for o in (p["a"]["id"], p["b"]["id"])}
    assert len(seen) == 3


def test_duels_need_three_options():
    d = copy.deepcopy(TEMPLATE_INDEX["laptop"])
    d["options"] = d["options"][:2]
    with pytest.raises(EngineError):
        select_duel_pairs(d)


def test_synthetic_user_recovery():
    decision, names, true_w, scores = _synthetic()
    # answers use engine-style ids; rebuild via slug mapping names->ids
    out = select_duel_pairs(decision, n=20)
    id_of = {}
    for p in out["pairs"]:
        id_of[p["a"]["name"]] = p["a"]["id"]
        id_of[p["b"]["name"]] = p["b"]["id"]
    answers = [{"a": id_of[a["a"]], "b": id_of[a["b"]], "winner": id_of[a["winner"]]}
               for a in _answers_from_scores(decision, scores)]
    learned = learn_weights(decision, answers)
    got = np.array([learned["weights"][n] for n in names])
    assert learned["train_acc"] == 1.0
    assert float(np.corrcoef(got, true_w)[0, 1]) > 0.85
    assert names[int(np.argmax(got))] == names[int(np.argmax(true_w))]
    assert learned["loo_acc"] >= 0.7
    assert learned["n_samples"] == len(answers)
    assert sum(learned["weights"].values()) == pytest.approx(100.0)
    assert learned["loss_curve"][0] > learned["loss_curve"][-1]  # learning!


def test_contradictory_answers_still_valid():
    decision, _, _, _ = _synthetic()
    out = select_duel_pairs(decision, n=4)
    p = out["pairs"][0]
    answers = [{"a": p["a"]["id"], "b": p["b"]["id"], "winner": p["a"]["id"]},
               {"a": p["a"]["id"], "b": p["b"]["id"], "winner": p["b"]["id"]}]
    learned = learn_weights(decision, answers)
    assert sum(learned["weights"].values()) == pytest.approx(100.0)
    assert all(v >= 0 for v in learned["weights"].values())


def test_min_answers_and_invalid_winner_errors():
    decision, _, _, _ = _synthetic()
    out = select_duel_pairs(decision, n=4)
    p = out["pairs"][0]
    with pytest.raises(EngineError):
        learn_weights(decision, [{"a": p["a"]["id"], "b": p["b"]["id"],
                                  "winner": p["a"]["id"]}])
    with pytest.raises(EngineError):
        learn_weights(decision, [{"a": p["a"]["id"], "b": p["b"]["id"],
                                  "winner": p["a"]["id"]},
                                 {"a": p["a"]["id"], "b": p["b"]["id"],
                                  "winner": "ghost"}])
