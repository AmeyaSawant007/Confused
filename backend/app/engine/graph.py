"""Weighted graph with adjacency-list representation, BFS, DFS and Dijkstra.

Central representation of a decision problem::

    [decision] --cost--> [option] --contribution--> [criterion]
                    |                         \
                    +--similarity--> [option]   +--> [constraint]

* ``decision -> option`` edge weight = ``100 - score`` (a *cost*: lower is better).
* ``option -> criterion`` edge weight = weighted points contributed by that criterion.
* ``option <-> option`` edges = Euclidean distance between normalized profiles
  (used to find the closest alternative to the winner with Dijkstra).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .heap import BinaryHeap


@dataclass
class Edge:
    to: str
    weight: float = 1.0
    label: str = ""


class Graph:
    """Directed weighted graph backed by an adjacency list."""

    def __init__(self) -> None:
        self.nodes: Dict[str, dict] = {}
        self.adj: Dict[str, List[Edge]] = {}

    # -- construction -----------------------------------------------------
    def add_node(self, node_id: str, kind: str = "node", label: str = "",
                 meta: Optional[dict] = None) -> None:
        if node_id not in self.nodes:
            self.nodes[node_id] = {"id": node_id, "kind": kind,
                                   "label": label or node_id,
                                   "meta": meta or {}}
            self.adj[node_id] = []

    def add_edge(self, frm: str, to: str, weight: float = 1.0,
                 label: str = "") -> None:
        if frm not in self.nodes:
            self.add_node(frm)
        if to not in self.nodes:
            self.add_node(to)
        self.adj[frm].append(Edge(to=to, weight=weight, label=label))

    def add_undirected_edge(self, a: str, b: str, weight: float = 1.0,
                            label: str = "") -> None:
        self.add_edge(a, b, weight, label)
        self.add_edge(b, a, weight, label)

    @property
    def num_edges(self) -> int:
        return sum(len(v) for v in self.adj.values())

    # -- traversals --------------------------------------------------------
    def bfs(self, start: str) -> List[str]:
        """Breadth-first traversal. O(V + E)."""
        if start not in self.nodes:
            return []
        order: List[str] = []
        seen = {start}
        q: deque = deque([start])
        while q:
            u = q.popleft()
            order.append(u)
            for e in self.adj.get(u, []):
                if e.to not in seen:
                    seen.add(e.to)
                    q.append(e.to)
        return order

    def dfs(self, start: str) -> List[str]:
        """Depth-first traversal (iterative). O(V + E)."""
        if start not in self.nodes:
            return []
        order: List[str] = []
        seen = set()
        stack = [start]
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            order.append(u)
            for e in reversed(self.adj.get(u, [])):
                if e.to not in seen:
                    stack.append(e.to)
        return order

    # -- shortest paths ----------------------------------------------------
    def dijkstra(self, start: str) -> Tuple[Dict[str, float], Dict[str, Optional[str]]]:
        """Single-source shortest paths using our own binary min-heap.

        O((V + E) log V). Returns (dist, prev) maps.
        """
        import math
        dist: Dict[str, float] = {nid: math.inf for nid in self.nodes}
        prev: Dict[str, Optional[str]] = {nid: None for nid in self.nodes}
        if start not in self.nodes:
            return dist, prev
        dist[start] = 0.0
        pq: BinaryHeap = BinaryHeap(is_max=False)
        pq.push(start, 0.0)
        settled = set()
        while len(pq):
            u, du, _ = pq.pop()
            if u in settled:
                continue
            settled.add(u)
            for e in self.adj.get(u, []):
                nd = du + e.weight
                if nd < dist[e.to] - 1e-12:
                    dist[e.to] = nd
                    prev[e.to] = u
                    if e.to in pq:
                        pq.update(e.to, nd)
                    else:
                        pq.push(e.to, nd)
        return dist, prev

    def shortest_path(self, prev: Dict[str, Optional[str]], target: str) -> List[str]:
        path: List[str] = []
        cur: Optional[str] = target
        while cur is not None:
            path.append(cur)
            cur = prev.get(cur)
        path.reverse()
        return path

    # -- export ------------------------------------------------------------
    def snapshot(self) -> dict:
        edges = []
        for frm, lst in self.adj.items():
            for e in lst:
                edges.append({"from": frm, "to": e.to,
                              "weight": round(e.weight, 3), "label": e.label})
        adjacency = {nid: [{"to": e.to, "w": round(e.weight, 3)}
                           for e in lst] for nid, lst in self.adj.items()}
        return {
            "nodes": list(self.nodes.values()),
            "edges": edges,
            "adjacency": adjacency,
            "num_vertices": len(self.nodes),
            "num_edges": self.num_edges,
        }
