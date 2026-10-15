"""Fetch pages and extract candidate facts (title, price, rating, specs).

Only stdlib + requests + BeautifulSoup. Numbers use standalone matching so
model codes like "i7" or ordinals like "13th" are never mistaken for values.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup


class FetchError(Exception):
    pass


UA = {"User-Agent": "Mozilla/5.0 (ConfusedBot/1.0; local decision-support demo)"}

_PRICE_RES = [
    (re.compile(r"₹\s*([\d,]+(?:\.\d+)?)"), "INR"),
    (re.compile(r"(?:Rs\.?|INR)\s*([\d,]+(?:\.\d+)?)", re.I), "INR"),
    (re.compile(r"\$\s*([\d,]+(?:\.\d+)?)"), "USD"),
]
_RATING_RES = [
    re.compile(r"(\d\.\d)\s*(?:/|out of)\s*5"),
    re.compile(r"(\d\.\d)\s*stars?"),
]
_NUM_RE = re.compile(r"(?<![a-zA-Z0-9_.])(\d+(?:,\d{3})*(?:\.\d+)?)(?![a-zA-Z0-9_])")
_UNIT_AFTER = re.compile(
    r"^\s*(hrs?|hours?|kg|gb|tb|mah|inch(?:es)?|min(?:ute)?s?|months?|weeks?|years?|/5|%|stars?)",
    re.I)

_UNIT_CANON = {"hr": "hours", "hrs": "hours", "hour": "hours", "hours": "hours",
               "inches": "inch", "stars": "/5", "star": "/5"}


def _num(s: str) -> Optional[float]:
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def _canon_unit(u: str) -> str:
    u = u.strip()
    low = u.lower()
    if low in _UNIT_CANON:
        return _UNIT_CANON[low]
    if low in ("gb", "tb"):
        return low.upper()
    if low == "mah":
        return "mAh"
    return u


def standalone_number(text: str):
    """First standalone number + optional unit, or (None, None)."""
    m = _NUM_RE.search(text)
    if not m:
        return None, None
    unit = None
    um = _UNIT_AFTER.match(text[m.end():])
    if um:
        unit = _canon_unit(um.group(1))
    return _num(m.group(1)), unit


def fetch_html(url: str, timeout: int = 8, max_bytes: int = 2_000_000) -> str:
    try:
        r = requests.get(url, headers=UA, timeout=timeout, stream=True)
    except requests.RequestException as e:
        raise FetchError(f"Could not fetch {url}: {e}")
    if r.status_code != 200:
        raise FetchError(f"{url} returned HTTP {r.status_code}")
    chunks, size = [], 0
    for chunk in r.iter_content(65536, decode_unicode=True):
        if not isinstance(chunk, str):
            continue
        chunks.append(chunk)
        size += len(chunk)
        if size > max_bytes:
            break
    r.close()
    html = "".join(chunks)
    if len(html.strip()) < 200:
        raise FetchError(f"{url} returned almost no content (JS-only page?).")
    return html


def clean_name(title: str) -> str:
    for sep in [" | ", " - ", " – ", " (", " –"]:
        if sep in title:
            title = title.split(sep)[0]
    return title.strip()[:48] or "Imported option"


def _parse_label_value(label: str, value: str) -> Optional[dict]:
    label = " ".join(label.split())
    if not (2 <= len(label) <= 40) or not re.search(r"[a-zA-Z]", label):
        return None
    number, unit = standalone_number(value)
    return {"label": label, "text": " ".join(value.split())[:120],
            "number": number, "unit": unit}


def extract_facts(html: str, url: str = "") -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        title = og["content"]
    elif soup.title and soup.title.string:
        title = soup.title.string
    else:
        h1 = soup.find("h1")
        title = h1.get_text(" ", strip=True) if h1 else url
    title = " ".join(str(title).split())

    text = soup.get_text(" ", strip=True)

    price = None
    for attr in ("product:price:amount", "og:price:amount"):
        m = soup.find("meta", attrs={"property": attr})
        if m and m.get("content") and _num(str(m["content"])) is not None:
            price = {"number": _num(str(m["content"])), "unit": "INR",
                     "text": f"meta {attr}"}
            break
    if price is None:
        for rx, unit in _PRICE_RES:
            m = rx.search(text)
            if m and _num(m.group(1)) is not None:
                price = {"number": _num(m.group(1)), "unit": unit,
                         "text": m.group(0)[:40]}
                break

    rating = None
    for rx in _RATING_RES:
        m = rx.search(text)
        if m:
            rating = {"number": float(m.group(1)), "unit": "/5",
                      "text": m.group(0)[:40]}
            break

    specs: List[dict] = []
    seen = set()

    def _add(label: str, value: str):
        spec = _parse_label_value(label, value)
        if spec and spec["label"].lower() not in seen:
            seen.add(spec["label"].lower())
            specs.append(spec)

    for li in soup.find_all("li"):
        t = li.get_text(" ", strip=True)
        if ":" in t:
            label, value = t.split(":", 1)
            _add(label, value)
    for tr in soup.find_all("tr"):
        tds = tr.find_all(["td", "th"])
        if len(tds) == 2:
            _add(tds[0].get_text(" ", strip=True), tds[1].get_text(" ", strip=True))

    numeric = [s for s in specs if s["number"] is not None]
    return {"title": title, "name": clean_name(title), "price": price,
            "rating": rating, "specs": specs, "numeric_specs": numeric,
            "skipped_non_numeric": len(specs) - len(numeric)}
