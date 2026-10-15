"""Segment tree over the criterion-weight array.

The engine keeps criterion weights in this tree so that:

* changing one weight is a point update:            O(log C)
* the weight total / any range sum is a range query: O(log C)

Together with per-option cached numerators this makes "What If?"
weight changes cost O(n + log C) instead of O(n * C).
The tree records exactly which segment nodes were touched so the UI
can highlight the dynamic update path.
"""
from __future__ import annotations

from typing import List, Optional, Tuple


class SegmentTree:
    def __init__(self, values: Optional[List[float]] = None,
                 labels: Optional[List[str]] = None) -> None:
        self.n = 0
        self.tree: List[float] = []
        self.labels: List[str] = []
        self.last_affected: List[int] = []
        if values:
            self.build(values, labels)

    def build(self, values: List[float],
              labels: Optional[List[str]] = None) -> None:
        self.n = len(values)
        self.labels = list(labels) if labels else [f"[{i}]" for i in range(self.n)]
        self.tree = [0.0] * (4 * self.n + 5)
        self._build(1, 0, self.n - 1, values)
        self.last_affected = []

    def _build(self, node: int, l: int, r: int, values: List[float]) -> None:
        if l == r:
            self.tree[node] = float(values[l])
            return
        m = (l + r) // 2
        self._build(node * 2, l, m, values)
        self._build(node * 2 + 1, m + 1, r, values)
        self.tree[node] = self.tree[node * 2] + self.tree[node * 2 + 1]

    def point_update(self, index: int, value: float) -> List[int]:
        """Set position ``index`` to ``value``. Returns touched node ids. O(log n)."""
        if not 0 <= index < self.n:
            raise IndexError("segment index out of range")
        touched: List[int] = []
        self._update(1, 0, self.n - 1, index, float(value), touched)
        self.last_affected = touched
        return touched

    def _update(self, node: int, l: int, r: int, idx: int,
                value: float, touched: List[int]) -> None:
        touched.append(node)
        if l == r:
            self.tree[node] = value
            return
        m = (l + r) // 2
        if idx <= m:
            self._update(node * 2, l, m, idx, value, touched)
        else:
            self._update(node * 2 + 1, m + 1, r, idx, value, touched)
        self.tree[node] = self.tree[node * 2] + self.tree[node * 2 + 1]

    def range_query(self, ql: int, qr: int) -> float:
        """Sum over [ql, qr]. O(log n)."""
        if self.n == 0:
            return 0.0
        ql, qr = max(0, ql), min(self.n - 1, qr)
        if ql > qr:
            return 0.0
        return self._query(1, 0, self.n - 1, ql, qr)

    def _query(self, node: int, l: int, r: int, ql: int, qr: int) -> float:
        if ql <= l and r <= qr:
            return self.tree[node]
        if r < ql or l > qr:
            return 0.0
        m = (l + r) // 2
        return (self._query(node * 2, l, m, ql, qr) +
                self._query(node * 2 + 1, m + 1, r, ql, qr))

    def total(self) -> float:
        return self.tree[1] if self.n else 0.0

    def leaves(self) -> List[float]:
        return [self.range_query(i, i) for i in range(self.n)]

    def snapshot(self) -> dict:
        nodes = []
        if self.n:
            # 1-indexed heap-style layout of the segment tree
            def walk(node: int, l: int, r: int) -> None:
                rng = f"{l}-{r}" if l != r else self.labels[l]
                nodes.append({"id": node, "range": rng,
                              "value": round(self.tree[node], 3),
                              "touched": node in self.last_affected,
                              "is_leaf": l == r})
                if l != r:
                    m = (l + r) // 2
                    walk(node * 2, l, m)
                    walk(node * 2 + 1, m + 1, r)
            walk(1, 0, self.n - 1)
        return {"n": self.n, "labels": self.labels,
                "total": round(self.total(), 3), "nodes": nodes,
                "affected": self.last_affected}
