"""Confused? API -- decision engine, persistence, search and DS playground."""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .engine import (BinaryHeap, Graph, HashTable, HistoryStack, SegmentTree, Trie)
from .engine.decision_engine import (EngineError, analyze, rank_with_heap, what_if)
from .engine.ml.semantic import get_matcher
from .engine.ml.preference_learner import learn_weights, select_duel_pairs
from .engine.scorer import weighted_scores
from .importer import SAMPLES, import_from_urls, import_samples
from .models import (CheckpointIn, DecisionIn, DuelsIn, ImportIn, LearnIn,
                     MatchIn, PlayIn, ProfileIn, WhatIfIn)
from .seed_data import CATEGORIES, TEMPLATE_INDEX, TEMPLATES
from .store import (delete_decision, delete_profile, get_decision, get_profile,
                    init_db, list_decisions, list_profiles, save_decision,
                    save_profile)

TRIE: Trie = Trie()
INDEX_REFS: dict = {}   # decision/template id -> list[(word, ref)]
HISTORIES: dict = {}    # decision id -> HistoryStack


# --------------------------------------------------------------------------- #
# search index (trie)
# --------------------------------------------------------------------------- #
_STOPWORDS = {"which", "what", "should", "could", "would", "the", "a", "an",
              "to", "for", "of", "in", "is", "are", "i", "my", "me", "and",
              "or", "vs", "do", "does", "next", "in", "on"}


def _keywords(text: str) -> List[str]:
    import re
    return [w for w in re.findall(r"[a-z0-9]+", text.lower())
            if len(w) >= 3 and w not in _STOPWORDS]


def _index_payload(payload: dict, kind: str) -> None:
    pid = payload.get("id")
    title = str(payload.get("title", ""))
    refs: List[tuple] = []
    items = [(title, {"kind": kind, "id": pid, "label": title, "match": "title"})]
    for o in payload.get("options", []) or []:
        oname = str(o.get("name", ""))
        if oname:
            items.append((oname, {"kind": kind, "id": pid,
                                  "label": f"{oname} — in {title}",
                                  "match": f"option: {oname}"}))
    seen_kw = set()
    for text in [title] + [str(o.get("name", "")) for o in payload.get("options", []) or []]:
        for kw in _keywords(text):
            if kw not in seen_kw:
                seen_kw.add(kw)
                items.append((kw, {"kind": kind, "id": pid, "label": title,
                                   "match": f"keyword: {kw}"}))
    for word, ref in items:
        TRIE.insert(word, ref)
        refs.append((word, ref))
    INDEX_REFS[f"{kind}:{pid}"] = refs


def _deindex(kind: str, pid: str) -> None:
    for word, ref in INDEX_REFS.pop(f"{kind}:{pid}", []):
        TRIE.delete(word, ref)


def _history(decision_id: str) -> HistoryStack:
    return HISTORIES.setdefault(decision_id, HistoryStack())


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    for cat in CATEGORIES:
        TRIE.insert(cat["label"], {"kind": "category", "id": cat["id"],
                                   "label": f"{cat['label']} decisions",
                                   "match": "category"})
    for t in TEMPLATES:
        _index_payload(t, "template")
    for row in list_decisions(limit=200):
        payload = get_decision(row["id"])
        if payload:
            payload["id"] = row["id"]
            _index_payload(payload, "decision")
    yield


app = FastAPI(title="Confused? API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(EngineError)
async def engine_error_handler(_, exc: EngineError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# --------------------------------------------------------------------------- #
# basics
# --------------------------------------------------------------------------- #
@app.get("/")
def root():
    return {"app": "Confused?", "version": "1.0.0",
            "docs": "/docs", "health": "/api/health"}


@app.get("/api/health")
def health():
    return {"status": "ok", "trie_words": TRIE.size}


@app.get("/api/categories")
def categories():
    return {"categories": CATEGORIES}


@app.get("/api/templates")
def templates():
    return {"templates": [
        {"id": t["id"], "title": t["title"], "category": t["category"],
         "options": len(t["options"]), "criteria": len(t["criteria"])}
        for t in TEMPLATES]}


@app.get("/api/templates/{tid}")
def template_detail(tid: str):
    if tid not in TEMPLATE_INDEX:
        raise HTTPException(404, "Unknown template")
    import copy
    return copy.deepcopy(TEMPLATE_INDEX[tid])


# --------------------------------------------------------------------------- #
# engine
# --------------------------------------------------------------------------- #
@app.post("/api/analyze")
def api_analyze(decision: DecisionIn):
    return analyze(decision.model_dump())


@app.post("/api/whatif")
def api_whatif(payload: WhatIfIn):
    return what_if(payload.baseline.model_dump(), payload.weights,
                   payload.disable_constraints, payload.disable_options)


# --------------------------------------------------------------------------- #
# persistence + undo history
# --------------------------------------------------------------------------- #
@app.get("/api/decisions")
def api_list_decisions(limit: int = Query(20, le=100)):
    return {"decisions": list_decisions(limit)}


@app.post("/api/decisions")
def api_create_decision(decision: DecisionIn):
    payload = decision.model_dump()
    payload["id"] = payload.get("id") or uuid.uuid4().hex[:8]
    meta = save_decision(payload["id"], payload)
    _deindex("decision", payload["id"])
    _index_payload(payload, "decision")
    return {**meta, "data": payload}


@app.get("/api/decisions/{did}")
def api_get_decision(did: str):
    payload = get_decision(did)
    if payload is None:
        raise HTTPException(404, "Decision not found")
    payload["id"] = did
    return payload


@app.put("/api/decisions/{did}")
def api_update_decision(did: str, decision: DecisionIn):
    if get_decision(did) is None:
        raise HTTPException(404, "Decision not found")
    payload = decision.model_dump()
    payload["id"] = did
    meta = save_decision(did, payload)
    _deindex("decision", did)
    _index_payload(payload, "decision")
    return {**meta, "data": payload}


@app.delete("/api/decisions/{did}")
def api_delete_decision(did: str):
    if not delete_decision(did):
        raise HTTPException(404, "Decision not found")
    _deindex("decision", did)
    HISTORIES.pop(did, None)
    return {"deleted": did}


@app.post("/api/decisions/{did}/checkpoint")
def api_checkpoint(did: str, body: CheckpointIn):
    current = get_decision(did)
    if current is None:
        raise HTTPException(404, "Decision not found")
    current["id"] = did
    _history(did).push(body.label, current)
    payload = body.state.model_dump()
    payload["id"] = did
    save_decision(did, payload)
    _deindex("decision", did)
    _index_payload(payload, "decision")
    return {"saved": did, "history": _history(did).snapshot()}


@app.post("/api/decisions/{did}/undo")
def api_undo(did: str):
    entry = _history(did).pop()
    if entry is None:
        raise HTTPException(400, "Nothing to undo — history is empty.")
    state = entry["state"]
    state["id"] = did
    save_decision(did, state)
    _deindex("decision", did)
    _index_payload(state, "decision")
    return {"restored": state, "undone": entry["label"],
            "history": _history(did).snapshot()}


@app.get("/api/decisions/{did}/history")
def api_history(did: str):
    return _history(did).snapshot()


# --------------------------------------------------------------------------- #
# trie search
# --------------------------------------------------------------------------- #
@app.get("/api/search")
def api_search(q: str = Query(..., min_length=1), limit: int = Query(8, le=20)):
    matches = TRIE.starts_with(q, limit=limit)
    flat = []
    for m in matches:
        for ref in m["refs"]:
            flat.append({"word": m["word"], **ref})
    return {"query": q, "results": flat[:limit]}


@app.get("/api/trie")
def api_trie():
    return TRIE.snapshot()


# --------------------------------------------------------------------------- #
# smart import (neural field matching) + preference profiles
# --------------------------------------------------------------------------- #
@app.get("/api/import/samples")
def api_import_samples():
    return {"samples": SAMPLES}


@app.post("/api/import")
def api_import(body: ImportIn):
    if body.mode == "samples":
        return import_samples(body.criteria)
    return import_from_urls(body.urls, body.criteria)


@app.post("/api/match")
def api_match(body: MatchIn):
    if not body.criteria:
        raise EngineError("Provide at least one criterion.")
    if not body.phrases:
        raise EngineError("Provide at least one phrase.")
    matcher = get_matcher()
    return matcher.match(body.criteria, [{"text": p} for p in body.phrases[:40]])


@app.get("/api/profiles")
def api_list_profiles():
    return {"profiles": list_profiles()}


@app.post("/api/profiles")
def api_save_profile(body: ProfileIn):
    if not body.category:
        raise EngineError("Profile needs a category.")
    return save_profile(body.category, body.weights, body.criteria)


@app.get("/api/profiles/{category}")
def api_get_profile(category: str):
    prof = get_profile(category)
    if prof is None:
        raise HTTPException(404, "No saved profile for this category")
    return prof


@app.delete("/api/profiles/{category}")
def api_delete_profile(category: str):
    if not delete_profile(category):
        raise HTTPException(404, "No saved profile for this category")
    return {"deleted": category}


# --------------------------------------------------------------------------- #
# smart weights (preference learning from duels)
# --------------------------------------------------------------------------- #
@app.post("/api/duels")
def api_duels(body: DuelsIn):
    return select_duel_pairs(body.decision.model_dump(),
                             n=max(1, min(body.n, 12)))


@app.post("/api/learn")
def api_learn(body: LearnIn):
    return learn_weights(body.decision.model_dump(),
                         [a.model_dump() for a in body.answers])


# --------------------------------------------------------------------------- #
# DS playground (real implementations, ephemeral instances)
# --------------------------------------------------------------------------- #
@app.post("/api/play/heap")
def play_heap(body: PlayIn):
    heap = BinaryHeap(is_max=(body.mode != "min"))
    steps = []
    for op in body.ops:
        name = str(op.get("op", ""))
        try:
            if name == "push":
                heap.push(str(op["key"]), float(op["priority"]))
                res = f"pushed {op['key']}"
            elif name == "pop":
                k, p, _ = heap.pop()
                res = {"key": k, "priority": round(p, 3)}
            elif name == "peek":
                top = heap.peek()
                res = {"key": top[0], "priority": round(top[1], 3)} if top else None
            elif name == "update":
                heap.update(str(op["key"]), float(op["priority"]))
                res = f"updated {op['key']}"
            elif name == "remove":
                heap.remove(str(op["key"]))
                res = f"removed {op['key']}"
            elif name == "topk":
                res = [{"key": k, "priority": round(p, 3)}
                       for k, p, _ in heap.topk(int(op.get("k", 3)))]
            else:
                raise ValueError(f"unknown heap op: {name}")
            steps.append({"op": op, "ok": True, "result": res,
                          "array": heap.to_array()})
        except (KeyError, ValueError, IndexError) as e:
            steps.append({"op": op, "ok": False, "error": str(e),
                          "array": heap.to_array()})
    return {"mode": body.mode, "steps": steps, "final": heap.to_array(),
            "ops": heap.ops_log}


@app.post("/api/play/trie")
def play_trie(body: PlayIn):
    trie = Trie()
    steps = []
    for op in body.ops:
        name = str(op.get("op", ""))
        try:
            if name == "insert":
                trie.insert(str(op.get("word", "")),
                            {"note": str(op.get("note", "playground"))})
                res = f"inserted {op.get('word', '')!r}"
            elif name == "search":
                res = {"matches": len(trie.search(str(op.get("word", ""))))}
            elif name == "prefix":
                res = {"words": [m["word"] for m in trie.starts_with(
                    str(op.get("prefix", "")), limit=int(op.get("limit", 8)))]}
            elif name == "delete":
                res = {"deleted": trie.delete(str(op.get("word", "")))}
            else:
                raise ValueError(f"unknown trie op: {name}")
            steps.append({"op": op, "ok": True, "result": res, "size": trie.size})
        except (KeyError, ValueError) as e:
            steps.append({"op": op, "ok": False, "error": str(e), "size": trie.size})
    return {"steps": steps, "snapshot": trie.snapshot()}


@app.post("/api/play/graph")
def play_graph(body: PlayIn):
    g = Graph()
    if body.nodes or body.edges:
        for n in body.nodes or []:
            g.add_node(str(n), label=str(n))
        for e in body.edges or []:
            g.add_edge(str(e["from"]), str(e["to"]),
                       weight=float(e.get("weight", 1.0)),
                       label=str(e.get("label", "")))
    else:
        for a, b, w in [("A", "B", 4), ("A", "C", 2), ("C", "B", 1),
                        ("B", "D", 5), ("C", "D", 8), ("C", "E", 10),
                        ("D", "E", 2), ("B", "E", 6)]:
            g.add_node(a, label=a)
            g.add_node(b, label=b)
            g.add_edge(a, b, weight=w)
    steps = []
    for op in body.ops:
        name = str(op.get("op", ""))
        try:
            if name == "bfs":
                res = {"order": g.bfs(str(op.get("start", "A")))}
            elif name == "dfs":
                res = {"order": g.dfs(str(op.get("start", "A")))}
            elif name == "dijkstra":
                dist, prev = g.dijkstra(str(op.get("start", "A")))
                res = {"dist": {k: (None if v == float("inf") else round(v, 2))
                                for k, v in dist.items()},
                       "prev": prev}
            elif name == "path":
                _, prev = g.dijkstra(str(op["start"]))
                res = {"path": g.shortest_path(prev, str(op["target"]))}
            else:
                raise ValueError(f"unknown graph op: {name}")
            steps.append({"op": op, "ok": True, "result": res})
        except (KeyError, ValueError) as e:
            steps.append({"op": op, "ok": False, "error": str(e)})
    return {"steps": steps, "snapshot": g.snapshot()}


@app.post("/api/play/segment")
def play_segment(body: PlayIn):
    values = body.values if body.values else [30, 35, 20, 15]
    labels = body.labels if body.labels else [f"x{i}" for i in range(len(values))]
    seg = SegmentTree(values, labels)
    steps = []
    for op in body.ops:
        name = str(op.get("op", ""))
        try:
            if name == "update":
                touched = seg.point_update(int(op["index"]), float(op["value"]))
                res = {"touched_nodes": touched, "total": round(seg.total(), 3)}
            elif name == "query":
                res = {"sum": round(seg.range_query(int(op.get("l", 0)),
                                                   int(op.get("r", len(values) - 1))), 3)}
            elif name == "total":
                res = {"total": round(seg.total(), 3)}
            else:
                raise ValueError(f"unknown segment op: {name}")
            steps.append({"op": op, "ok": True, "result": res})
        except (KeyError, ValueError, IndexError) as e:
            steps.append({"op": op, "ok": False, "error": str(e)})
    return {"steps": steps, "snapshot": seg.snapshot()}


@app.post("/api/play/hash")
def play_hash(body: PlayIn):
    ht = HashTable(capacity=max(4, body.capacity))
    steps = []
    for op in body.ops:
        name = str(op.get("op", ""))
        try:
            if name == "put":
                ht.put(str(op["key"]), op.get("value", op["key"]))
                res = f"stored {op['key']}"
            elif name == "get":
                res = {"value": ht.get(str(op["key"]), None)}
            elif name == "delete":
                res = {"deleted": ht.delete(str(op["key"]))}
            else:
                raise ValueError(f"unknown hash op: {name}")
            steps.append({"op": op, "ok": True, "result": res,
                          "size": ht.size, "load": round(ht.size / ht.capacity, 3),
                          "collisions": ht.collisions})
        except (KeyError, ValueError) as e:
            steps.append({"op": op, "ok": False, "error": str(e)})
    return {"steps": steps, "snapshot": ht.snapshot()}


@app.post("/api/play/stack")
def play_stack(body: PlayIn):
    st = HistoryStack()
    steps = []
    for op in body.ops:
        name = str(op.get("op", ""))
        try:
            if name == "push":
                depth = st.push(str(op.get("label", "state")),
                                op.get("state", op.get("label", "state")))
                res = {"depth": depth}
            elif name == "pop":
                entry = st.pop()
                res = {"popped": entry["label"] if entry else None}
            elif name == "peek":
                top = st.peek()
                res = {"top": top["label"] if top else None}
            else:
                raise ValueError(f"unknown stack op: {name}")
            steps.append({"op": op, "ok": True, "result": res,
                          "labels": st.labels()})
        except (KeyError, ValueError) as e:
            steps.append({"op": op, "ok": False, "error": str(e)})
    return {"steps": steps, "snapshot": st.snapshot()}
