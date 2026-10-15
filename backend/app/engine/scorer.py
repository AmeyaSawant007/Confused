"""Scoring helpers: min-max normalization, weighted aggregation and
the incremental re-scoring formula used by "What If?" mode.

Incremental update
------------------
score_i = 100 * sum_j(norm_ij * w_j) / W,  W = sum_j w_j

When weights change from w to w' the engine does NOT rescan every
score. It reuses the cached numerator::

    num_i' = num_i + sum_j(norm_ij * (w'_j - w_j))
    score_i' = 100 * num_i' / W'

Only criteria whose weight changed contribute to the delta, and the
new total W' comes from the segment tree in O(log C).
"""
from __future__ import annotations

from typing import Dict, List, Tuple


def min_max_normalize(values: Dict[str, float], kind: str) -> Dict[str, float]:
    """Normalize option->raw maps to 0..1.

    kind "benefit": higher raw is better. kind "cost": lower raw is better.
    A single option, or all-equal values, maps to 1.0 (nothing to compare).
    """
    if not values:
        return {}
    xs = list(values.values())
    lo, hi = min(xs), max(xs)
    if hi - lo < 1e-12:
        return {k: 1.0 for k in values}
    out: Dict[str, float] = {}
    for k, v in values.items():
        if kind == "cost":
            out[k] = (hi - v) / (hi - lo)
        else:
            out[k] = (v - lo) / (hi - lo)
    return out


def weighted_scores(norm_matrix: Dict[str, Dict[str, float]],
                    weights: Dict[str, float]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Return (scores 0..100, numerators) for options x criteria."""
    total = sum(weights.values())
    scores: Dict[str, float] = {}
    numerators: Dict[str, float] = {}
    for opt_id, row in norm_matrix.items():
        num = sum(row.get(c, 0.0) * w for c, w in weights.items())
        numerators[opt_id] = num
        scores[opt_id] = (100.0 * num / total) if total > 0 else 0.0
    return scores, numerators


def incremental_rescore(norm_matrix: Dict[str, Dict[str, float]],
                        numerators: Dict[str, float],
                        old_total: float,
                        delta_weights: Dict[str, float],
                        new_total: float) -> Dict[str, float]:
    """Re-score after a weight change using cached numerators.

    Only the changed criteria (delta_weights) are touched per option.
    """
    out: Dict[str, float] = {}
    for opt_id, row in norm_matrix.items():
        num = numerators.get(opt_id, 0.0)
        for crit_id, dw in delta_weights.items():
            if dw:
                num += row.get(crit_id, 0.0) * dw
        out[opt_id] = (100.0 * num / new_total) if new_total > 0 else 0.0
    return out


def contributions_for_option(norm_row: Dict[str, float],
                             weights: Dict[str, float],
                             total: float) -> List[dict]:
    pts = []
    for crit_id, w in weights.items():
        n = norm_row.get(crit_id, 0.0)
        pts.append({"criterion_id": crit_id,
                    "points": round(100.0 * n * w / total, 2) if total > 0 else 0.0,
                    "norm": round(n, 4)})
    pts.sort(key=lambda d: d["points"], reverse=True)
    return pts
