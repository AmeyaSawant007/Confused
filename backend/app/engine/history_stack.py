"""Decision history stack: every mutation pushes a snapshot so the
user can undo changes (weight edits, added/removed options, criteria
or constraints) in LIFO order. push/pop/peek are O(1)."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, List, Optional


class HistoryStack:
    def __init__(self, capacity: int = 50) -> None:
        self._items: List[dict] = []
        self.capacity = capacity

    def push(self, label: str, state: Any) -> int:
        self._items.append({
            "label": label,
            "state": copy.deepcopy(state),
            "at": datetime.now(timezone.utc).isoformat(),
        })
        while len(self._items) > self.capacity:
            self._items.pop(0)
        return len(self._items)

    def pop(self) -> Optional[dict]:
        if not self._items:
            return None
        return self._items.pop()

    def peek(self) -> Optional[dict]:
        return self._items[-1] if self._items else None

    def __len__(self) -> int:
        return len(self._items)

    def is_empty(self) -> bool:
        return not self._items

    def clear(self) -> None:
        self._items.clear()

    def labels(self) -> List[str]:
        """Top-of-stack first."""
        return [it["label"] for it in reversed(self._items)]

    def snapshot(self) -> dict:
        return {"depth": len(self._items), "capacity": self.capacity,
                "labels_top_first": self.labels()}
