"""Decision engine: the pipeline that turns a decision problem into an
explainable ranking.

Pipeline (every stage genuinely uses its data structure)::

    validate -> hash registries -> constraint filter -> min-max normalize
      -> segment-tree weights -> weighted scores -> decision graph
      -> BFS / DFS / Dijkstra -> max-heap ranking -> explained result

No ``list.sort()`` is used for ranking anywhere: order always comes out
of the binary heap (drain / top-K).
"""
from __future__ import annotations

import copy
import json
import math
import re
import time
from typing import Dict, List, Optional, Tuple

from .graph import Graph
from .hash_table import HashTable
from .heap import BinaryHeap
from .segment_tree import SegmentTree
from .scorer import (contributions_for_option, incremental_rescore,
                     min_max_normalize, weighted_scores)

INF = 1e9
EPS = 1e-9

COMPLEXITIES = [
    {"operation": "BFS traversal", "complexity": "O(V + E)"},
    {"operation": "DFS traversal", "complexity": "O(V + E)"},
    {"operation": "Dijkstra (own binary heap)", "complexity": "O((V + E) log V)"},
    {"operation": "Heap insert / update / remove", "complexity": "O(log n)"},
    {"operation": "Heap extract-max", "complexity": "O(log n)"},
    {"operation": "Top-K ranking", "complexity": "O(k log n)"},
    {"operation": "Trie prefix search", "complexity": "O(P + M)"},
    {"operation": "Hash-table lookup", "complexity": "O(1) average"},
    {"operation": "Segment-tree point update", "complexity": "O(log C)"},
    {"operation": "Segment-tree range sum", "complexity": "O(log C)"},
    {"operation": "History push / pop (undo)", "complexity": "O(1)"},
    {"operation": "Incremental re-score on weight change", "complexity": "O(n + log C)"},
]

DISCLAIMER = ("Ranking reflects only the criteria, weights, scores and constraints "
              "you supplied. It is not an objectively 'correct' decision.")


class EngineError(Exception):
    """Fatal, user-facing validation failure."""


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)


def _slug(text: str, prefix: str, idx: int) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or prefix
    return f"{s[:24]}-{idx}"


def _check_op(op: str, actual: float, expected: float) -> bool:
    if op in ("<=", "≤"):
        return actual <= expected + EPS
    if op in ("<",):
        return actual < expected - EPS
    if op in (">=", "≥"):
        return actual >= expected - EPS
    if op in (">",):
        return actual > expected + EPS
    if op in ("==", "=", "==="):
        return abs(actual - expected) <= EPS
    if op in ("!=", "≠"):
        return abs(actual - expected) > EPS
    raise EngineError(f"Unknown constraint operator: {op!r}")


# --------------------------------------------------------------------------- #
# validation / normalization of raw input
# --------------------------------------------------------------------------- #
def _normalize(decision: dict) -> Tuple[dict, List[str]]:
    d = copy.deepcopy(decision)
    warnings: List[str] = []
    title = str(d.get("title", "")).strip()
    if not title:
        raise EngineError("Please provide a decision question/title.")
    category = str(d.get("category", "custom") or "custom")

    raw_crits = d.get("criteria") or []
    if not raw_crits:
        raise EngineError("Add at least one evaluation criterion.")
    crits: List[dict] = []
    seen_names = set()
    for i, c in enumerate(raw_crits):
        name = str(c.get("name", "")).strip()
        if not name:
            raise EngineError(f"Criterion #{i + 1} needs a name.")
        if name.lower() in seen_names:
            raise EngineError(f"Duplicate criterion name: {name!r}.")
        seen_names.add(name.lower())
        ctype = str(c.get("type", "benefit")).lower()
        if ctype not in ("benefit", "cost"):
            raise EngineError(f"Criterion {name!r}: type must be benefit/cost.")
        w = c.get("weight", 0)
        if not _is_num(w):
            raise EngineError(f"Criterion {name!r}: weight must be a number.")
        if w < 0:
            raise EngineError(f"Criterion {name!r}: weight cannot be negative.")
        crits.append({"id": str(c.get("id") or _slug(name, "c", i + 1)),
                      "name": name, "type": ctype, "weight": float(w)})
    if all(c["weight"] <= 0 for c in crits):
        raise EngineError("At least one criterion needs a positive weight.")
    wsum = sum(c["weight"] for c in crits)
    if abs(wsum - 100.0) > 1e-9:
        warnings.append(f"Weights sum to {wsum:g}, not 100 — normalized proportionally.")

    name_to_crit = {c["name"].lower(): c for c in crits}

    raw_opts = d.get("options") or []
    if not raw_opts:
        raise EngineError("Add at least one option to compare.")
    opts: List[dict] = []
    seen_opt_names = set()
    for i, o in enumerate(raw_opts):
        name = str(o.get("name", "")).strip()
        if not name:
            raise EngineError(f"Option #{i + 1} needs a name.")
        if name.lower() in seen_opt_names:
            warnings.append(f"Duplicate option name: {name!r} — kept as separate entries.")
        seen_opt_names.add(name.lower())
        scores = o.get("scores") or {}
        if not isinstance(scores, dict):
            raise EngineError(f"Option {name!r}: scores must be a name->value map.")
        lowered = {str(k).lower(): v for k, v in scores.items()}
        values: Dict[str, float] = {}
        for c in crits:
            if c["name"].lower() not in lowered:
                raise EngineError(f"Option {name!r} is missing a value for {c['name']!r}.")
            v = lowered[c["name"].lower()]
            if not _is_num(v):
                raise EngineError(f"Option {name!r}, {c['name']!r}: value must be numeric.")
            values[c["id"]] = float(v)
        opts.append({"id": str(o.get("id") or _slug(name, "o", i + 1)),
                     "name": name,
                     "description": str(o.get("description", "") or ""),
                     "values": values})

    raw_cons = d.get("constraints") or []
    cons: List[dict] = []
    for i, k in enumerate(raw_cons):
        target = str(k.get("target", "")).strip()
        if not target:
            raise EngineError(f"Constraint #{i + 1} needs a target criterion.")
        op = str(k.get("operator", "<=")).strip()
        if op not in ("<=", "<", ">=", ">", "==", "=", "!=", "≤", "≥", "≠"):
            raise EngineError(f"Constraint on {target!r}: bad operator {op!r}.")
        val = k.get("value", 0)
        if not _is_num(val):
            raise EngineError(f"Constraint on {target!r}: value must be numeric.")
        crit = name_to_crit.get(target.lower())
        skipped = crit is None
        if skipped:
            warnings.append(f"Constraint target {target!r} matches no criterion — skipped.")
        cons.append({"id": str(k.get("id") or _slug(target + op, "k", i + 1)),
                     "name": str(k.get("name", "") or f"{target} {op} {val:g}"),
                     "target": target, "operator": op, "value": float(val),
                     "hard": bool(k.get("hard", True)),
                     "enabled": bool(k.get("enabled", True)),
                     "crit_id": crit["id"] if crit else None,
                     "skipped": skipped})
    clean = {"id": d.get("id"), "title": title, "category": category,
             "criteria": crits, "options": opts, "constraints": cons}
    return clean, warnings


# --------------------------------------------------------------------------- #
# ranking helper (heap only -- never sort())
# --------------------------------------------------------------------------- #
def rank_with_heap(scores: Dict[str, float],
                   names: Dict[str, str]) -> Tuple[List[Tuple[str, float]], dict, List[str]]:
    heap: BinaryHeap = BinaryHeap(is_max=True)
    for oid, s in scores.items():
        heap.push(oid, s, names.get(oid, oid))
    array_snapshot = heap.to_array()
    ordered = [(oid, s) for oid, s, _ in heap.drain_sorted()]
    return ordered, {"mode": "max", "array": array_snapshot,
                     "size": len(array_snapshot)}, list(heap.ops_log)


# --------------------------------------------------------------------------- #
# main analysis
# --------------------------------------------------------------------------- #
def analyze(decision: dict) -> dict:
    t0 = time.perf_counter()
    timings: Dict[str, float] = {}

    def mark(stage: str, start: float) -> None:
        timings[stage] = round((time.perf_counter() - start) * 1000, 2)

    # ---- 1. validate ------------------------------------------------------
    t = time.perf_counter()
    clean, warnings = _normalize(decision)
    crits, opts, cons = clean["criteria"], clean["options"], clean["constraints"]
    crit_by_id = {c["id"]: c for c in crits}
    opt_by_id = {o["id"]: o for o in opts}
    mark("validate", t)

    explanations = [f"Validated {len(opts)} option(s) x {len(crits)} criteria. "
                    f"Weights normalized to 100%."]

    # ---- 2. hash registries + result cache --------------------------------
    t = time.perf_counter()
    opt_reg: HashTable = HashTable(capacity=16)
    crit_reg: HashTable = HashTable(capacity=16)
    for o in opts:
        opt_reg.put(o["id"], o["name"])
    for c in crits:
        crit_reg.put(c["id"], c["name"])
    fp_payload = json.dumps(
        {"t": clean["title"], "c": [(c["name"], c["weight"], c["type"]) for c in crits],
         "o": sorted((o["name"], sorted(o["values"].items())) for o in opts),
         "k": [(k["target"], k["operator"], k["value"], k["hard"], k["enabled"])
               for k in cons]})
    fingerprint = format(HashTable._hash(fp_payload), "x")
    mark("hash_registries", t)

    # ---- 3. hard constraints ----------------------------------------------
    t = time.perf_counter()
    feasible: List[str] = []
    eliminated: List[dict] = []
    con_status: Dict[str, Dict[str, bool]] = {}  # opt -> con -> satisfied
    for o in opts:
        reasons: List[str] = []
        status: Dict[str, bool] = {}
        for k in cons:
            if k["skipped"] or not k["enabled"]:
                continue
            actual = o["values"][k["crit_id"]]
            ok = _check_op(k["operator"], actual, k["value"])
            status[k["id"]] = ok
            if not ok:
                msg = (f"{k['target']} = {actual:g} violates "
                       f"{k['target']} {k['operator']} {k['value']:g}")
                if k["hard"]:
                    reasons.append(msg)
        con_status[o["id"]] = status
        if reasons:
            eliminated.append({"option_id": o["id"], "name": o["name"], "reasons": reasons})
        else:
            feasible.append(o["id"])
    soft_flags = [o["name"] for o in opts if o["id"] in feasible
                  for k in cons if (not k["skipped"] and k["enabled"] and not k["hard"]
                                    and not con_status[o["id"]].get(k["id"], True))]
    if soft_flags:
        warnings.append("Soft-preference miss (non-eliminating): " + ", ".join(sorted(set(soft_flags))))
    mark("constraints", t)
    if eliminated:
        explanations.append("Constraints eliminated "
                            + ", ".join(e["name"] for e in eliminated) + ".")
    else:
        explanations.append("All options satisfy the hard constraints.")

    # ---- 4. normalize + 5. segment-tree weights + scores ------------------
    t = time.perf_counter()
    norm_matrix: Dict[str, Dict[str, float]] = {oid: {} for oid in feasible}
    for c in crits:
        raw = {oid: opt_by_id[oid]["values"][c["id"]] for oid in feasible}
        normed = min_max_normalize(raw, c["type"])
        for oid, v in normed.items():
            norm_matrix[oid][c["id"]] = v
    mark("normalize", t)

    t = time.perf_counter()
    seg = SegmentTree([c["weight"] for c in crits],
                      [c["name"] for c in crits])
    w_total = seg.total()
    weights = {c["id"]: c["weight"] for c in crits}
    scores, numerators = weighted_scores(norm_matrix, weights)
    mark("score", t)
    explanations.append(
        f"Min-max normalized each criterion (benefit: higher better, cost: lower better); "
        f"score = 100 x sum(norm x weight) / {w_total:g} (segment-tree total).")

    # ---- 6. decision graph -------------------------------------------------
    t = time.perf_counter()
    g = Graph()
    g.add_node("decision", kind="decision", label=clean["title"][:42])
    for c in crits:
        g.add_node(f"c:{c['id']}", kind="criterion", label=c["name"])
    for k in cons:
        if k["skipped"] or not k["enabled"]:
            continue
        g.add_node(f"k:{k['id']}", kind="constraint",
                   label=f"{k['target']} {k['operator']} {k['value']:g}")
    for o in opts:
        oid = o["id"]
        node = f"o:{oid}"
        feas = oid in feasible
        sc = round(scores.get(oid, 0.0), 2)
        g.add_node(node, kind="option", label=o["name"],
                   meta={"feasible": feas, "score": sc if feas else None})
        g.add_edge("decision", node,
                   weight=round(100.0 - sc, 2) if feas else INF,
                   label=f"{sc:.1f}" if feas else "out")
        if feas:
            contribs = contributions_for_option(norm_matrix[oid], weights, w_total)
            for cp in contribs:
                g.add_edge(node, f"c:{cp['criterion_id']}",
                           weight=cp["points"], label=f"+{cp['points']:.1f}")
        for k in cons:
            if k["skipped"] or not k["enabled"]:
                continue
            ok = con_status[oid].get(k["id"], True)
            g.add_edge(node, f"k:{k['id']}", weight=0.0 if ok else INF,
                       label="ok" if ok else "violated")
    # option <-> option similarity (for closest-alternative search)
    order = [c["id"] for c in crits]
    denom = math.sqrt(len(order)) or 1.0
    for i in range(len(feasible)):
        for j in range(i + 1, len(feasible)):
            a, b = feasible[i], feasible[j]
            d = math.sqrt(sum((norm_matrix[a][cid] - norm_matrix[b][cid]) ** 2
                                for cid in order)) / denom * 100.0
            g.add_undirected_edge(f"o:{a}", f"o:{b}", weight=round(d, 2),
                                  label=f"~{d:.0f}")
    mark("graph_build", t)

    # ---- 7. traversals + Dijkstra ------------------------------------------
    t = time.perf_counter()
    bfs_order = g.bfs("decision")
    dfs_order = g.dfs("decision")
    dist, prev = g.dijkstra("decision")
    paths = {f"o:{oid}": g.shortest_path(prev, f"o:{oid}") for oid in opt_by_id}
    dist_out = {nid: (None if d >= INF / 2 else round(d, 2)) for nid, d in dist.items()}
    mark("traverse", t)

    # ---- 8. heap ranking ----------------------------------------------------
    t = time.perf_counter()
    ordered, heap_snap, heap_ops = rank_with_heap(
        scores, {oid: opt_by_id[oid]["name"] for oid in feasible})
    mark("rank", t)

    ranked: List[dict] = []
    for rank, (oid, sc) in enumerate(ordered, start=1):
        o = opt_by_id[oid]
        contribs = []
        for cp in contributions_for_option(norm_matrix[oid], weights, w_total):
            c = crit_by_id[cp["criterion_id"]]
            contribs.append({
                "criterion_id": c["id"], "criterion": c["name"],
                "type": c["type"], "raw": o["values"][c["id"]],
                "norm": cp["norm"],
                "weight_pct": round(100.0 * c["weight"] / w_total, 2),
                "points": cp["points"]})
        ranked.append({"rank": rank, "option_id": oid, "name": o["name"],
                       "description": o["description"], "score": round(sc, 2),
                       "contributions": contribs})
    winner = ranked[0] if ranked else None

    # closest alternative to the winner (Dijkstra over similarity edges)
    nearest_alt = None
    if winner and len(ranked) >= 2:
        wnode = f"o:{winner['option_id']}"
        d2, p2 = g.dijkstra(wnode)
        best, best_d = None, INF
        for r in ranked[1:]:
            dd = d2.get(f"o:{r['option_id']}", INF)
            if dd < best_d:
                best, best_d = r, dd
        if best and best_d < INF / 2:
            nearest_alt = {"option_id": best["option_id"], "name": best["name"],
                           "distance": round(best_d, 2),
                           "path": g.shortest_path(p2, f"o:{best['option_id']}")}
    explanations.append(
        f"Ranked {len(ranked)} feasible option(s) with a max-heap "
        f"({len(heap_ops)} heap ops, top-K without sorting).")
    explanations.append(
        f"BFS/DFS covered {len(g.nodes)} nodes, {g.num_edges} edges; Dijkstra "
        f"decision-path cost = 100 - score, so the shortest path is the winner.")

    # ---- 9. confidence (heuristic, documented) ------------------------------
    if not ranked:
        confidence, conf_note = None, "No feasible option — relax a constraint."
    elif len(ranked) == 1:
        confidence, conf_note = 90.0, "Only one option satisfies all hard constraints."
    else:
        gap = ranked[0]["score"] - ranked[1]["score"]
        confidence = round(min(97.0, max(50.0, 55.0 + gap * 1.5)), 1)
        conf_note = (f"Heuristic from the top-2 gap ({gap:.1f} pts): a bigger gap "
                     f"means a less ambiguous winner.")

    # result cache (hash table in action)
    cache: HashTable = HashTable(capacity=8)
    if winner:
        cache.put(fingerprint, {"winner": winner["option_id"],
                                "score": winner["score"]})

    mark("total", t0)
    result = {
        "title": clean["title"], "category": clean["category"],
        "warnings": warnings, "explanations": explanations,
        "timings": timings, "complexities": COMPLEXITIES,
        "disclaimer": DISCLAIMER,
        "criteria": [{"id": c["id"], "name": c["name"], "type": c["type"],
                      "weight": c["weight"],
                      "weight_pct": round(100.0 * c["weight"] / w_total, 2)}
                     for c in crits],
        "options": [{"id": o["id"], "name": o["name"],
                     "description": o["description"],
                     "values": {crit_by_id[cid]["name"]: o["values"][cid]
                                for cid in o["values"]}} for o in opts],
        "ranked": ranked, "eliminated": eliminated, "winner": winner,
        "confidence": confidence, "confidence_note": conf_note,
        "nearest_alternative": nearest_alt,
        "graph": {**g.snapshot(), "bfs": bfs_order, "dfs": dfs_order,
                  "dijkstra": {"dist": dist_out, "paths": paths}},
        "heap": {**heap_snap, "ops": heap_ops},
        "segment": seg.snapshot(),
        "hash": {"options_registry": opt_reg.snapshot(),
                 "criteria_registry": crit_reg.snapshot(),
                 "result_cache": cache.snapshot(),
                 "fingerprint": fingerprint},
        "score_table": {oid: {crit_by_id[cid]["name"]: round(v, 4)
                              for cid, v in row.items()}
                        for oid, row in norm_matrix.items()},
        "weight_vector": {c["id"]: c["weight"] for c in crits},
        "weight_total": w_total,
        "numerators": numerators,
    }
    return result


# --------------------------------------------------------------------------- #
# what-if comparison
# --------------------------------------------------------------------------- #
def _match_criterion(crits: List[dict], key: str) -> Optional[dict]:
    kl = str(key).lower()
    for c in crits:
        if c["id"] == key or c["name"].lower() == kl:
            return c
    return None


def _match_option(opts: List[dict], key: str) -> Optional[dict]:
    kl = str(key).lower()
    for o in opts:
        if o.get("id") == key or str(o.get("name", "")).lower() == kl:
            return o
    return None


def _match_constraint(cons: List[dict], key: str) -> Optional[dict]:
    kl = str(key).lower()
    for k in cons:
        if (k.get("id") == key or str(k.get("name", "")).lower() == kl
                or str(k.get("target", "")).lower() == kl):
            return k
    return None


def what_if(baseline: dict,
            weight_overrides: Optional[Dict[str, float]] = None,
            disable_constraints: Optional[List[str]] = None,
            disable_options: Optional[List[str]] = None) -> dict:
    t0 = time.perf_counter()
    weight_overrides = weight_overrides or {}
    disable_constraints = disable_constraints or []
    disable_options = disable_options or []

    before = analyze(baseline)
    patched = copy.deepcopy(baseline)
    patch_warnings: List[str] = []

    # apply weight overrides (resolve against canonical analyzed criteria
    # so `changed` is keyed by criterion id for the segment tree path)
    pcrits = patched.get("criteria") or []
    changed: Dict[str, Tuple[float, float]] = {}  # canonical crit_id -> (old, new)
    for key, new_w in weight_overrides.items():
        if not _is_num(new_w) or new_w < 0:
            raise EngineError(f"What-if weight for {key!r} must be >= 0.")
        entry = None
        for c in before["criteria"]:
            if c["id"] == key or c["name"].lower() == str(key).lower():
                entry = c
                break
        if entry is None:
            patch_warnings.append(f"What-if: unknown criterion {key!r} — ignored.")
            continue
        for c in pcrits:
            if str(c.get("name", "")).lower() == entry["name"].lower():
                old_w = float(c.get("weight", 0))
                c["weight"] = float(new_w)
                if abs(old_w - float(new_w)) > 1e-12:
                    changed[entry["id"]] = (old_w, float(new_w))

    structural = False
    for key in disable_constraints:
        hit = _match_constraint(patched.get("constraints") or [], key)
        if hit is None:
            patch_warnings.append(f"What-if: unknown constraint {key!r} — ignored.")
        else:
            hit["enabled"] = False
            structural = True
    for key in disable_options:
        hit = _match_option(patched.get("options") or [], key)
        if hit is None:
            patch_warnings.append(f"What-if: unknown option {key!r} — ignored.")
        else:
            hit["_disabled"] = True
            structural = True
    if structural:
        patched["options"] = [o for o in patched.get("options", [])
                              if not o.get("_disabled")]

    after = analyze(patched)

    # ---- incremental dynamic update (the O(n + log C) path) ----------------
    seg_trace: dict = {"updates": [], "affected_union": [],
                       "old_total": before["weight_total"], "new_total": after["weight_total"]}
    incremental_used = bool(changed) and not structural
    incremental_verified: Optional[bool] = None
    incr_scores: Optional[Dict[str, float]] = None
    if incremental_used:
        seg = SegmentTree([c["weight"] for c in before["criteria"]],
                          [c["name"] for c in before["criteria"]])
        delta: Dict[str, float] = {}
        id_order = [c["id"] for c in before["criteria"]]
        idx_of = {cid: i for i, cid in enumerate(id_order)}
        for cid, (old_w, new_w) in changed.items():
            if cid in idx_of:
                touched = seg.point_update(idx_of[cid], new_w)
                seg_trace["updates"].append(
                    {"criterion_id": cid, "old": old_w, "new": new_w,
                     "touched_nodes": touched})
                delta[cid] = new_w - old_w
        union: List[int] = []
        for u in seg_trace["updates"]:
            for nid in u["touched_nodes"]:
                if nid not in union:
                    union.append(nid)
        seg_trace["affected_union"] = union
        seg_trace["new_total"] = seg.total()
        # norms keyed by criterion NAME in score_table; map back to ids
        name_to_id = {c["name"]: c["id"] for c in before["criteria"]}
        norm_by_id = {oid: {name_to_id[nm]: v for nm, v in row.items()}
                      for oid, row in before["score_table"].items()}
        incr_scores = incremental_rescore(
            norm_by_id, before["numerators"], before["weight_total"],
            delta, seg.total())
        full_scores = {r["option_id"]: r["score"] for r in after["ranked"]}
        incremental_verified = all(
            abs(round(incr_scores.get(oid, -1), 2) - full_scores.get(oid, -2)) < 1e-9
            for oid in full_scores) and set(incr_scores) == set(full_scores)

    # ---- movements ---------------------------------------------------------
    b_rank = {r["option_id"]: (r["rank"], r["score"], r["name"]) for r in before["ranked"]}
    a_rank = {r["option_id"]: (r["rank"], r["score"], r["name"]) for r in after["ranked"]}
    b_elim = {e["option_id"]: e["name"] for e in before["eliminated"]}
    a_elim = {e["option_id"]: e["name"] for e in after["eliminated"]}
    movements = []
    for oid in list(b_rank) + [x for x in a_rank if x not in b_rank]:
        br, bs, nm = b_rank.get(oid, (None, None, a_rank.get(oid, (None, None, "?"))[2]))
        ar, as_, _ = a_rank.get(oid, (None, None, nm))
        if br is None:
            status = "new"
        elif ar is None:
            status = "eliminated"
        elif ar < br:
            status = "moved_up"
        elif ar > br:
            status = "moved_down"
        else:
            status = "same"
        movements.append({
            "option_id": oid, "name": nm, "status": status,
            "before_rank": br, "after_rank": ar,
            "before_score": round(bs, 2) if bs is not None else None,
            "after_score": round(as_, 2) if as_ is not None else None,
            "delta_rank": (br - ar) if br and ar else None,
            "delta_score": round(as_ - bs, 2) if bs is not None and as_ is not None else None,
        })
    for oid, nm in a_elim.items():
        if oid not in b_rank and oid not in a_rank:
            movements.append({"option_id": oid, "name": nm, "status": "eliminated",
                              "before_rank": None, "after_rank": None,
                              "before_score": None, "after_score": None,
                              "delta_rank": None, "delta_score": None})

    # ---- causes ------------------------------------------------------------
    causes = []
    id_to_name = {c["id"]: c["name"] for c in before["criteria"]}
    for cid, (old_w, new_w) in sorted(changed.items(),
                                      key=lambda kv: abs(kv[1][1] - kv[1][0]),
                                      reverse=True):
        nm = id_to_name.get(cid, cid)
        beneficiary, best = None, -1.0
        for r in after["ranked"]:
            for cp in r["contributions"]:
                if cp["criterion_id"] == cid and cp["norm"] > best:
                    best, beneficiary = cp["norm"], r["name"]
        causes.append({"criterion": nm, "old_weight": old_w, "new_weight": new_w,
                       "delta": round(new_w - old_w, 2),
                       "top_beneficiary": beneficiary,
                       "note": (f"{beneficiary or '—'} is strongest on {nm} "
                                f"(norm {best:.2f}), so raising it helps "
                                f"{beneficiary or 'nobody'}.")})

    total_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {"before": before, "after": after, "movements": movements,
            "causes": causes, "segment_trace": seg_trace,
            "incremental_used": incremental_used,
            "incremental_verified": incremental_verified,
            "incremental_scores": ({k: round(v, 2) for k, v in incr_scores.items()}
                                   if incr_scores else None),
            "patch_warnings": patch_warnings + after.get("warnings", []),
            "total_ms": total_ms}
