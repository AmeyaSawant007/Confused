"""Semantic field matching: map extracted page phrases to decision criteria.

Two implementations behind one interface::

    phrase "battery backup 14 hrs"  ~~>  criterion "Battery Life"   0.87

* ``NeuralFieldMatcher`` -- MiniLM transformer embeddings + cosine similarity.
  Lazy-loaded, so torch is only needed if you actually use it.
* ``KeywordFieldMatcher`` -- token overlap + unit hints. Zero dependencies,
  always available as the honest fallback.

``match()`` returns the FULL similarity matrix (rendered in the UI, so the
neural net's reasoning is visible) plus greedy best-criterion assignments
above threshold.
"""
from __future__ import annotations

import re
from typing import Dict, List

MODEL_NAME = "all-MiniLM-L6-v2"
NEURAL_THRESHOLD = 0.30
KEYWORD_THRESHOLD = 0.25
UNIT_BONUS = 0.20


def _tokens(s: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


UNIT_HINTS = {
    "INR": ["price", "cost", "budget", "fee", "fees", "stipend", "salary"],
    "USD": ["price", "cost", "budget", "fee", "fees", "stipend", "salary"],
    "kg": ["weight"],
    "hours": ["battery"],
    "GB": ["ram", "storage", "memory"],
    "TB": ["storage", "memory"],
    "inch": ["display", "screen"],
    "/5": ["rating", "review"],
    "%": ["rating", "placement", "chance", "ppo"],
    "months": ["time", "duration"],
    "min": ["commute", "time"],
}


def _unit_bonus(unit: str | None, criterion: str) -> float:
    if not unit:
        return 0.0
    hints = UNIT_HINTS.get(unit, [])
    ctoks = set(_tokens(criterion))
    return UNIT_BONUS if any(h in ctoks for h in hints) else 0.0


def _assignments(matrix: Dict[str, Dict[str, float]],
                 threshold: float) -> List[dict]:
    out = []
    for phrase, row in matrix.items():
        best_c, best_s = None, -1.0
        for c, s in row.items():
            if s > best_s:
                best_c, best_s = c, s
        out.append({"phrase": phrase,
                    "criterion": best_c if best_s >= threshold else None,
                    "score": round(best_s, 3)})
    return out


class KeywordFieldMatcher:
    """Token-overlap + unit-hint fallback. No dependencies."""

    name = "keyword"
    model_name: str | None = None

    def match(self, criteria: List[str], phrases: List[dict],
              threshold: float = KEYWORD_THRESHOLD) -> dict:
        matrix: Dict[str, Dict[str, float]] = {}
        for p in phrases:
            ptoks = set(_tokens(p["text"]))
            row: Dict[str, float] = {}
            for c in criteria:
                ctoks = set(_tokens(c))
                overlap = (len(ptoks & ctoks) / min(len(ptoks), len(ctoks))
                           if ptoks and ctoks else 0.0)
                score = min(1.0, overlap + _unit_bonus(p.get("unit"), c))
                row[c] = round(score, 3)
            matrix[p["text"]] = row
        return {"matcher": self.name, "model": self.model_name,
                "matrix": matrix,
                "assignments": _assignments(matrix, threshold)}


class NeuralFieldMatcher:
    """MiniLM transformer embeddings + cosine similarity (lazy torch)."""

    name = "neural"
    model_name: str | None = MODEL_NAME

    def __init__(self) -> None:
        self._model = None

    @staticmethod
    def available() -> bool:
        try:
            import sentence_transformers  # noqa: F401
            return True
        except ImportError:
            return False

    def _ensure(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model

    def match(self, criteria: List[str], phrases: List[dict],
              threshold: float = NEURAL_THRESHOLD) -> dict:
        import numpy as np
        if not phrases or not criteria:
            return {"matcher": self.name, "model": self.model_name,
                    "matrix": {}, "assignments": []}
        model = self._ensure()
        ce = np.asarray(model.encode(criteria, normalize_embeddings=True,
                                      show_progress_bar=False), dtype=float)
        pe = np.asarray(model.encode([p["text"] for p in phrases],
                                     normalize_embeddings=True,
                                     show_progress_bar=False), dtype=float)
        sims = pe @ ce.T
        matrix: Dict[str, Dict[str, float]] = {}
        for i, p in enumerate(phrases):
            matrix[p["text"]] = {c: round(float(sims[i][j]), 3)
                                 for j, c in enumerate(criteria)}
        return {"matcher": self.name, "model": self.model_name,
                "matrix": matrix,
                "assignments": _assignments(matrix, threshold)}


_singleton = None


def get_matcher():
    """Neural matcher when torch is installed, else the keyword fallback."""
    global _singleton
    if _singleton is None:
        _singleton = (NeuralFieldMatcher()
                      if NeuralFieldMatcher.available()
                      else KeywordFieldMatcher())
    return _singleton
