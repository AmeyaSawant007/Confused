"""Trie (prefix tree) for instant search over decision titles,
categories, templates and option names.

* insert / search / prefix search: O(L) where L = key length.
* Each terminal node stores reference payloads (what matched and where).
"""
from __future__ import annotations

from typing import Dict, List, Optional


class TrieNode:
    __slots__ = ("children", "is_end", "refs", "word")

    def __init__(self) -> None:
        self.children: Dict[str, "TrieNode"] = {}
        self.is_end: bool = False
        self.refs: List[dict] = []
        self.word: str = ""


class Trie:
    def __init__(self) -> None:
        self.root = TrieNode()
        self.size = 0  # number of distinct words

    @staticmethod
    def _norm(text: str) -> str:
        return " ".join(text.strip().lower().split())

    def insert(self, word: str, ref: Optional[dict] = None) -> None:
        """Insert a word with an optional reference payload. O(L)."""
        w = self._norm(word)
        if not w:
            return
        node = self.root
        for ch in w:
            node = node.children.setdefault(ch, TrieNode())
        if not node.is_end:
            node.is_end = True
            node.word = word.strip()
            self.size += 1
        if ref is not None and ref not in node.refs:
            node.refs.append(ref)

    def search(self, word: str) -> List[dict]:
        """Exact search. O(L). Returns refs or []."""
        node = self._find(self._norm(word))
        return list(node.refs) if node and node.is_end else []

    def starts_with(self, prefix: str, limit: int = 10) -> List[dict]:
        """Prefix search. O(P + M) for prefix length P and M matches.

        Returns [{word, refs}] sorted with exact/prefix-shortest first.
        """
        node = self._find(self._norm(prefix))
        if node is None:
            return []
        out: List[dict] = []
        stack = [node]
        while stack and len(out) < limit * 4:
            cur = stack.pop()
            if cur.is_end:
                out.append({"word": cur.word, "refs": list(cur.refs)})
            for ch in sorted(cur.children.keys(), reverse=True):
                stack.append(cur.children[ch])
        out.sort(key=lambda d: (len(d["word"]), d["word"].lower()))
        return out[:limit]

    def delete(self, word: str, ref: Optional[dict] = None) -> bool:
        """Delete a word (or one ref). Returns True if something was removed."""
        w = self._norm(word)
        if not w:
            return False

        removed = False

        def _rec(node: TrieNode, depth: int) -> bool:
            nonlocal removed
            if depth == len(w):
                if not node.is_end:
                    return False
                if ref is None:
                    node.refs.clear()
                    node.is_end = False
                    removed = True
                elif ref in node.refs:
                    node.refs.remove(ref)
                    removed = True
                    if not node.refs:
                        node.is_end = False
                return len(node.children) == 0 and not node.is_end
            ch = w[depth]
            child = node.children.get(ch)
            if child is None:
                return False
            prune = _rec(child, depth + 1)
            if prune:
                del node.children[ch]
            return len(node.children) == 0 and not node.is_end

        _rec(self.root, 0)
        if removed and ref is None:
            self.size = max(0, self.size - 1)
        return removed

    def _find(self, w: str) -> Optional[TrieNode]:
        node = self.root
        for ch in w:
            node = node.children.get(ch)
            if node is None:
                return None
        return node

    def snapshot(self, max_nodes: int = 120) -> dict:
        """Nested snapshot for visualization (breadth-capped)."""

        nodes = [{"id": 0, "char": "root", "is_end": False, "words": []}]
        edges: List[dict] = []
        counter = [1]
        queue = [(self.root, 0)]
        while queue and len(nodes) < max_nodes:
            node, pid = queue.pop(0)
            for ch in sorted(node.children.keys()):
                if len(nodes) >= max_nodes:
                    break
                child = node.children[ch]
                nid = counter[0]
                counter[0] += 1
                nodes.append({"id": nid, "char": ch, "is_end": child.is_end,
                              "words": [child.word] if child.is_end else []})
                edges.append({"from": pid, "to": nid, "char": ch})
                queue.append((child, nid))
        return {"nodes": nodes, "edges": edges, "total_words": self.size,
                "truncated": len(nodes) >= max_nodes}
