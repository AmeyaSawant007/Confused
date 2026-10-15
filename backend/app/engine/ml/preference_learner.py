"""Preference learning: infer criterion weights from pairwise duels.

Each answer "I prefer A over B" becomes one training sample::

    X = norm(A) - norm(B)     difference of normalized criterion vectors
    y = 1                     (first option chosen)

A from-scratch binary logistic regression (batch gradient descent, L2,
no intercept so P(A>B) = 1-P(B>A) by construction) learns one coefficient
per criterion; the positive part normalized to 100 becomes the suggested
weights. Normalization reuses the engine's min-max scaler, so learned
weights plug straight into the exact pipeline.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from ..decision_engine import EngineError, _normalize
from ..scorer import min_max_normalize, weighted_scores


class LogisticRegressionGD:
    """Binary logistic regression, batch gradient descent, L2. NumPy only."""

    def __init__(self, lr: float = 1.0, epochs: int = 2000, l2: float = 0.01,
                 seed: int = 0, fit_intercept: bool = True) -> None:
        self.lr = lr
        self.epochs = epochs
        self.l2 = l2
        self.seed = seed
        self.fit_intercept = fit_intercept
        self.coef_: np.ndarray | None = None
        self.intercept_: float = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> List[float]:
        n, d = X.shape
        rng = np.random.default_rng(self.seed)
        w = rng.normal(0, 0.1, d)
        b = 0.0
        losses: List[float] = []
        for _ in range(self.epochs):
            z = X @ w + b
            p = np.clip(1.0 / (1.0 + np.exp(-z)), 1e-12, 1 - 1e-12)
            losses.append(float(
                -(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()
                + 0.5 * self.l2 * float(w @ w)))
            err = (p - y) / n
            w -= self.lr * (X.T @ err + self.l2 * w)
            if self.fit_intercept:
                b -= self.lr * float(err.sum())
        self.coef_ = w
        self.intercept_ = b
        return losses

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        assert self.coef_ is not None
        return 1.0 / (1.0 + np.exp(-(X @ self.coef_ + self.intercept_)))

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X) >= 0.5).astype(int)

    def accuracy(self, X: np.ndarray, y: np.ndarray) -> float:
        return float((self.predict(X) == y).mean())


def _profiles(clean: dict) -> Dict[str, Dict[str, float]]:
    """Min-max normalized option vectors over ALL options (learning context)."""
    norms: Dict[str, Dict[str, float]] = {o["id"]: {} for o in clean["options"]}
    for c in clean["criteria"]:
        raw = {o["id"]: o["values"][c["id"]] for o in clean["options"]}
        for oid, v in min_max_normalize(raw, c["type"]).items():
            norms[oid][c["id"]] = v
    return norms


def _weights_or_uniform(clean: dict) -> Dict[str, float]:
    w = {c["id"]: c["weight"] for c in clean["criteria"]}
    if sum(w.values()) <= 0:
        w = {c["id"]: 1.0 for c in clean["criteria"]}
    return w


def select_duel_pairs(decision: dict, n: int = 6) -> dict:
    """Pick the n most informative pairs (closest races first, full coverage).

    Uncertainty sampling: pairs whose predicted scores are closest teach the
    model the most. Greedy coverage guarantees every option appears ASAP.
    """
    clean, warnings = _normalize(decision)
    opts = clean["options"]
    if len(opts) < 3:
        raise EngineError("Smart Weights needs at least 3 options to duel.")
    norms = _profiles(clean)
    scores, _ = weighted_scores(norms, _weights_or_uniform(clean))
    ids = [o["id"] for o in opts]
    name_of = {o["id"]: o["name"] for o in opts}
    ranked = sorted(
        ((a, b, abs(scores[a] - scores[b]))
         for i, a in enumerate(ids) for b in ids[i + 1:]),
        key=lambda t: t[2])
    picked, seen = [], set()
    for a, b, m in ranked:
        if len(picked) >= n:
            break
        if len(seen) == len(ids) or a not in seen or b not in seen:
            picked.append({"a": {"id": a, "name": name_of[a]},
                           "b": {"id": b, "name": name_of[b]},
                           "margin": round(m, 2)})
            seen.add(a)
            seen.add(b)
    return {"pairs": picked,
            "criteria": [c["name"] for c in clean["criteria"]],
            "weights": {c["name"]: c["weight"] for c in clean["criteria"]},
            "warnings": warnings}


def _coefs_to_weights(coef: np.ndarray, names: List[str]):
    pos = np.maximum(np.asarray(coef, dtype=float), 0.0)
    uniform = bool(pos.sum() <= 1e-12)
    if uniform:
        pos = np.ones_like(pos)
    w = pos / pos.sum() * 100.0
    rounded = [round(float(v), 1) for v in w]
    drift = round(100.0 - sum(rounded), 1)
    if rounded:
        rounded[int(np.argmax(w))] = round(rounded[int(np.argmax(w))] + drift, 1)
    return {nm: rounded[i] for i, nm in enumerate(names)}, uniform


def _loo_accuracy(X: np.ndarray, y: np.ndarray) -> float:
    n = len(X)
    if n < 2:
        return 0.0
    correct = 0
    for i in range(n):
        mask = np.array([j != i for j in range(n)])
        m = LogisticRegressionGD(fit_intercept=False)
        m.fit(X[mask], y[mask])
        correct += int(m.predict(X[i:i + 1])[0] == y[i])
    return round(correct / n, 3)


def learn_weights(decision: dict, answers: List[dict]) -> dict:
    """Train on duel answers; return suggested weights + training diagnostics."""
    if len(answers) < 2:
        raise EngineError("Answer at least 2 duels so the model has something to learn.")
    clean, _ = _normalize(decision)
    opt_ids = {o["id"] for o in clean["options"]}
    for a in answers:
        if a["a"] not in opt_ids or a["b"] not in opt_ids:
            raise EngineError("A duel references an unknown option.")
        if a["a"] == a["b"] or a["winner"] not in (a["a"], a["b"]):
            raise EngineError("Invalid duel answer.")
    order = [c["id"] for c in clean["criteria"]]
    names = [c["name"] for c in clean["criteria"]]
    norms = _profiles(clean)
    # x10 feature scaling (standard practice): direction-preserving, keeps the
    # L2 penalty honest relative to the tiny [-1, 1] difference features.
    X = np.array([[norms[a["winner"]][cid] -
                   norms[a["b"] if a["winner"] == a["a"] else a["a"]][cid]
                   for cid in order] for a in answers]) * 10.0
    y = np.ones(len(X))
    model = LogisticRegressionGD(fit_intercept=False)
    losses = model.fit(X, y)
    train_acc = round(model.accuracy(X, y), 3)
    loo_acc = _loo_accuracy(X, y)
    weights, uniform = _coefs_to_weights(model.coef_, names)
    step = max(1, len(losses) // 60)
    warnings = []
    if len(answers) < len(names):
        warnings.append(f"Only {len(answers)} answers for {len(names)} criteria — "
                        "more duels sharpen the weights.")
    if uniform:
        warnings.append("Answers were contradictory — fell back to uniform weights.")
    elif train_acc < 1.0:
        warnings.append("Some answers contradict each other — weights are a best-fit compromise.")
    return {
        "method": "logistic_regression",
        "method_detail": ("from-scratch NumPy: batch gradient descent, 2000 epochs, "
                          "L2=0.01, no intercept (antisymmetric pairs)"),
        "weights": weights,
        "coefficients": {nm: round(float(model.coef_[i]), 4)
                         for i, nm in enumerate(names)},
        "loss_curve": [round(v, 4) for v in losses[::step]],
        "train_acc": train_acc, "loo_acc": loo_acc,
        "n_samples": len(X), "n_criteria": len(names),
        "uniform_fallback": uniform, "warnings": warnings,
    }
