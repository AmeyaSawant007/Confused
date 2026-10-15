"""Educational hash table with separate chaining, djb2 hashing and
automatic resizing.

Genuinely used inside the engine for:

* option registry   (option id -> option record)      O(1) average lookup
* criterion registry (criterion id -> criterion)      O(1) average lookup
* result cache      (decision fingerprint -> scores)  memoization
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple


class HashTable:
    def __init__(self, capacity: int = 16, load_factor: float = 0.7) -> None:
        self.capacity = max(4, capacity)
        self.load_factor = load_factor
        self.buckets: List[List[Tuple[Any, Any]]] = [[] for _ in range(self.capacity)]
        self.size = 0
        self.collisions = 0
        self.resizes = 0

    @staticmethod
    def _hash(key: Any) -> int:
        h = 5381
        for ch in str(key):
            h = ((h << 5) + h + ord(ch)) & 0xFFFFFFFF
        return h

    def _index(self, key: Any) -> int:
        return self._hash(key) % self.capacity

    def put(self, key: Any, value: Any) -> None:
        idx = self._index(key)
        bucket = self.buckets[idx]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)
                return
        if bucket:
            self.collisions += 1
        bucket.append((key, value))
        self.size += 1
        if self.size / self.capacity > self.load_factor:
            self._resize(self.capacity * 2)

    def get(self, key: Any, default: Any = None) -> Any:
        bucket = self.buckets[self._index(key)]
        for k, v in bucket:
            if k == key:
                return v
        return default

    def delete(self, key: Any) -> bool:
        bucket = self.buckets[self._index(key)]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                del bucket[i]
                self.size -= 1
                return True
        return False

    def __contains__(self, key: Any) -> bool:
        return any(k == key for k, _ in self.buckets[self._index(key)])

    def keys(self) -> List[Any]:
        return [k for b in self.buckets for k, _ in b]

    def _resize(self, new_capacity: int) -> None:
        old = self.buckets
        self.capacity = new_capacity
        self.buckets = [[] for _ in range(new_capacity)]
        self.size = 0
        self.resizes += 1
        for bucket in old:
            for k, v in bucket:
                # re-insert without triggering another resize cascade
                idx = self._index(k)
                self.buckets[idx].append((k, v))
                self.size += 1

    def snapshot(self, max_buckets: Optional[int] = None) -> dict:
        buckets = self.buckets if max_buckets is None else self.buckets[:max_buckets]
        return {
            "capacity": self.capacity,
            "size": self.size,
            "load": round(self.size / self.capacity, 3) if self.capacity else 0,
            "collisions": self.collisions,
            "resizes": self.resizes,
            "buckets": [
                {"index": i, "keys": [str(k) for k, _ in b], "count": len(b)}
                for i, b in enumerate(buckets)
            ],
        }
