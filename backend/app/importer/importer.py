"""Build decision options from imported pages.

Pipeline per page::

    HTML -> extract facts -> candidates -> neural field matching
        -> best fact per criterion -> option values + confidence + sources
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ..engine.decision_engine import EngineError
from ..engine.ml.semantic import get_matcher
from .extractor import FetchError, extract_facts, fetch_html

FIXTURES = Path(__file__).parent / "fixtures"

SAMPLES = [
    {"id": "aerobook", "label": "AeroBook 14 — ShopKart (offline sample)",
     "url": "https://shopkart.example/p/aerobook-14"},
    {"id": "titan", "label": "Titan Gaming 15 — ShopKart (offline sample)",
     "url": "https://shopkart.example/p/titan-gaming-15"},
    {"id": "ecolite", "label": "EcoLite 13 — ShopKart (offline sample)",
     "url": "https://shopkart.example/p/ecolite-13"},
]


def load_sample(sample_id: str) -> str:
    path = (FIXTURES / f"{sample_id}.html").resolve()
    if FIXTURES.resolve() not in path.parents:
        raise EngineError("Unknown sample.")
    if not path.exists():
        raise EngineError(f"Unknown sample: {sample_id}")
    return path.read_text(encoding="utf-8")


def _candidates(facts: dict) -> List[dict]:
    cands: List[dict] = []
    if facts.get("price"):
        p = facts["price"]
        cands.append({"text": "Price", "number": p["number"], "unit": p["unit"],
                      "kind": "price", "raw": p["text"]})
    if facts.get("rating"):
        rt = facts["rating"]
        cands.append({"text": "Customer Rating", "number": rt["number"],
                      "unit": rt["unit"], "kind": "rating", "raw": rt["text"]})
    for s in facts.get("numeric_specs", []):
        cands.append({"text": s["label"], "number": s["number"], "unit": s["unit"],
                      "kind": "spec", "raw": s["text"]})
    return cands


def _build_option(url: str, facts: dict, criteria: List[str], matcher) -> tuple:
    cands = _candidates(facts)
    match = matcher.match(criteria, cands) if cands else {
        "matcher": matcher.name, "model": matcher.model_name,
        "matrix": {}, "assignments": []}
    by_criterion: Dict[str, list] = {}
    for a, c in zip(match["assignments"], cands):
        if a["criterion"] is not None:
            by_criterion.setdefault(a["criterion"], []).append((a["score"], c))
    scores, confidence, sources = {}, {}, []
    for crit, pairs in by_criterion.items():
        pairs.sort(key=lambda pc: pc[0], reverse=True)
        score, cand = pairs[0]
        scores[crit] = cand["number"]
        confidence[crit] = score
        sources.append({"criterion": crit, "phrase": cand["text"],
                        "score": score, "text": cand["raw"]})
    sources.sort(key=lambda s: s["score"], reverse=True)
    filled = sorted(scores)
    missing = [c for c in criteria if c not in scores]
    option = {"name": facts["name"], "url": url, "scores": scores,
              "filled": filled, "missing": missing, "confidence": confidence,
              "sources": sources}
    table = {"url": url, "title": facts["title"],
             "candidates": [{"text": c["text"], "number": c["number"],
                             "unit": c["unit"]} for c in cands],
             "matrix": match["matrix"], "assignments": match["assignments"],
             "unmatched": [a["phrase"] for a in match["assignments"]
                            if a["criterion"] is None]}
    return option, table


def import_from_pages(pages: List[dict], criteria: List[str],
                      mode: str = "urls") -> dict:
    if not criteria:
        raise EngineError("Add criteria first — Smart Import matches page facts to your criteria.")
    matcher = get_matcher()
    options, tables, warnings = [], [], []
    for page in pages:
        try:
            facts = page.get("facts") or extract_facts(page["html"], page.get("url", ""))
            option, table = _build_option(page.get("url", ""), facts, criteria, matcher)
            options.append(option)
            tables.append(table)
            if not option["filled"]:
                warnings.append(f"{option['name']}: no page facts matched your criteria.")
            elif option["missing"]:
                warnings.append(f"{option['name']}: fill manually: {', '.join(option['missing'])}.")
        except (FetchError, EngineError) as e:
            warnings.append(str(e))
        except Exception as e:  # never let one bad page kill the batch
            warnings.append(f"{page.get('url', 'page')}: could not parse ({e}).")
    if not options:
        raise EngineError("Nothing could be imported. " + " ".join(warnings))
    return {"mode": mode, "matcher": matcher.name, "model": matcher.model_name,
            "options": options, "match_tables": tables, "warnings": warnings}


def import_from_urls(urls: List[str], criteria: List[str]) -> dict:
    urls = [u.strip() for u in urls if u.strip()][:6]
    if not urls:
        raise EngineError("Paste at least one URL.")
    pages = []
    for u in urls:
        if not u.lower().startswith(("http://", "https://")):
            u = "https://" + u
        try:
            pages.append({"url": u, "html": fetch_html(u)})
        except FetchError as e:
            pages.append({"url": u, "facts": {"title": u, "name": u[:48],
                                              "price": None, "rating": None,
                                              "specs": [], "numeric_specs": [],
                                              "skipped_non_numeric": 0,
                                              "_error": str(e)}})
    # surface fetch errors as warnings attached to placeholder facts
    for p in pages:
        err = (p.get("facts") or {}).pop("_error", None)
        if err:
            p["facts"] = None
            p["_fetch_error"] = err
    real_pages = [p for p in pages if p.get("html")]
    result = import_from_pages(real_pages, criteria, mode="urls") if real_pages else {
        "mode": "urls", "matcher": get_matcher().name,
        "model": get_matcher().model_name, "options": [],
        "match_tables": [], "warnings": []}
    for p in pages:
        if p.get("_fetch_error"):
            result["warnings"].append(p["_fetch_error"])
    if not result["options"]:
        raise EngineError("Nothing could be imported. " + " ".join(result["warnings"]))
    return result


def import_samples(criteria: List[str]) -> dict:
    pages = [{"url": s["url"], "html": load_sample(s["id"])} for s in SAMPLES]
    return import_from_pages(pages, criteria, mode="samples")
