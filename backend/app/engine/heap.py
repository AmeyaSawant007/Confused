"""Self-implemented binary heap (min or max) with index map.

Used as the priority queue that maintains ranked decision alternatives.
Supports insert, peek, extract, priority update and removal -- all in
O(log n) -- plus non-destructive top-K extraction.

Ties are broken by insertion order (stable) so equal scores produce a
deterministic, explainable ranking.
"""
from __future__ import annotations

from itertools import count
from typing import Any, Dict, List, Optional, Tuple


class BinaryHeap:
    def __init__(self, is_max: bool = True) -> None:
        self.is_max = is_max
        # entries: [priority, -counter, key, payload]; counter keeps FIFO on ties
        self._a: List[list] = []
        self._pos: Dict[Any, int] = {}
        self._ctr = count()
        self.ops_log: List[str] = []

    # -- helpers -----------------------------------------------------------
    def __len__(self) -> int:
        return len(self._a)

    def __contains__(self, key: Any) -> bool:
        return key in self._pos

    def _better(self, i: int, j: int) -> bool:
        a, b = self._a[i], self._a[j]
        if a[0] != b[0]:
            return a[0] > b[0] if self.is_max else a[0] < b[0]
        return a[1] > b[1]  # larger -counter == inserted earlier

    def _swap(self, i: int, j: int) -> None:
        self._a[i], self._a[j] = self._a[j], self._a[i]
        self._pos[self._a[i][2]] = i
        self._pos[self._a[j][2]] = j

    def _sift_up(self, i: int) -> None:
        while i > 0:
            p = (i - 1) // 2
            if self._better(i, p):
                self._swap(i, p)
                i = p
            else:
                break

    def _sift_down(self, i: int) -> None:
        n = len(self._a)
        while True:
            l, r, best = 2 * i + 1, 2 * i + 2, i
            if l < n and self._better(l, best):
                best = l
            if r < n and self._better(r, best):
                best = r
            if best == i:
                break
            self._swap(i, best)
            i = best

    # -- public API --------------------------------------------------------
    def push(self, key: Any, priority: float, payload: Any = None) -> None:
        """Insert (or replace) ``key`` with ``priority``. O(log n)."""
        if key in self._pos:
            self.update(key, priority, payload)
            return
        entry = [priority, -next(self._ctr), key, payload]
        self._a.append(entry)
        self._pos[key] = len(self._a) - 1
        self._sift_up(len(self._a) - 1)
        self.ops_log.append(f"insert {key} (priority={priority:.2f})")

    def peek(self) -> Optional[Tuple[Any, float, Any]]:
        if not self._a:
            return None
        e = self._a[0]
        return (e[2], e[0], e[3])

    def pop(self) -> Tuple[Any, float, Any]:
        """Extract the best element. O(log n)."""
        if not self._a:
            raise IndexError("pop from empty heap")
        top = self._a[0]
        last = self._a.pop()
        del self._pos[top[2]]
        if self._a:
            self._a[0] = last
            self._pos[last[2]] = 0
            self._sift_down(0)
        self.ops_log.append(f"extract {top[2]} (priority={top[0]:.2f})")
        return (top[2], top[0], top[3])

    def update(self, key: Any, new_priority: float, payload: Any = None) -> None:
        """Change a key's priority. O(log n)."""
        if key not in self._pos:
            raise KeyError(f"key not in heap: {key}")
        i = self._pos[key]
        old = self._a[i][0]
        self._a[i][0] = new_priority
        if payload is not None:
            self._a[i][3] = payload
        if (new_priority > old) == self.is_max:
            self._sift_up(i)
        else:
            self._sift_down(i)
        self.ops_log.append(f"update {key} ({old:.2f} -> {new_priority:.2f})")

    def remove(self, key: Any) -> Tuple[Any, float, Any]:
        """Remove an arbitrary key. O(log n)."""
        if key not in self._pos:
            raise KeyError(f"key not in heap: {key}")
        i = self._pos[key]
        entry = self._a[i]
        last = self._a.pop()
        del self._pos[key]
        if i < len(self._a):
            self._a[i] = last
            self._pos[last[2]] = i
            self._sift_up(i)
            self._sift_down(self._pos[last[2]])
        self.ops_log.append(f"remove {key} (priority={entry[0]:.2f})")
        return (entry[2], entry[0], entry[3])

    def topk(self, k: int) -> List[Tuple[Any, float, Any]]:
        """Non-destructive top-K. O(k log n). No Array.sort anywhere."""
        clone = self.clone()
        out = []
        for _ in range(min(k, len(clone))):
            out.append(clone.pop())
        return out

    def drain_sorted(self) -> List[Tuple[Any, float, Any]]:
        """Extract everything in rank order. O(n log n)."""
        out = []
        while len(self):
            out.append(self.pop())
        return out

    def clone(self) -> "BinaryHeap":
        c = BinaryHeap(self.is_max)
        c._a = [list(e) for e in self._a]
        c._pos = dict(self._pos)
        c._ctr = count(len(self._a))
        return c

    def to_array(self) -> List[dict]:
        """Level-order array snapshot for visualization."""
        return [{"index": i, "key": e[2],
                 "priority": round(e[0], 3)} for i, e in enumerate(self._a)]
