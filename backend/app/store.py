"""Lightweight SQLite persistence for saved decisions."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("CONFUSED_DB",
                              Path(__file__).resolve().parent.parent / "confused.db"))


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'custom',
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                category TEXT PRIMARY KEY,
                weights TEXT NOT NULL,
                criteria TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL
            )
        """)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_decision(decision_id: str, payload: dict) -> dict:
    init_db()
    title = str(payload.get("title", "Untitled"))
    category = str(payload.get("category", "custom") or "custom")
    now = _now()
    with _conn() as c:
        row = c.execute("SELECT created_at FROM decisions WHERE id = ?",
                        (decision_id,)).fetchone()
        created = row["created_at"] if row else now
        c.execute(
            """INSERT INTO decisions (id, title, category, data, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET title=excluded.title,
                 category=excluded.category, data=excluded.data,
                 updated_at=excluded.updated_at""",
            (decision_id, title, category, json.dumps(payload), created, now))
    return {"id": decision_id, "title": title, "category": category,
            "created_at": created, "updated_at": now}


def list_decisions(limit: int = 20) -> list:
    init_db()
    with _conn() as c:
        rows = c.execute(
            """SELECT id, title, category, created_at, updated_at,
                      json_extract(data, '$.options') AS opts
               FROM decisions ORDER BY updated_at DESC LIMIT ?""",
            (limit,)).fetchall()
    out = []
    for r in rows:
        try:
            n_opts = len(json.loads(r["opts"])) if r["opts"] else 0
        except (TypeError, ValueError):
            n_opts = 0
        out.append({"id": r["id"], "title": r["title"], "category": r["category"],
                    "options": n_opts, "created_at": r["created_at"],
                    "updated_at": r["updated_at"]})
    return out


def get_decision(decision_id: str) -> dict | None:
    init_db()
    with _conn() as c:
        row = c.execute("SELECT data FROM decisions WHERE id = ?",
                        (decision_id,)).fetchone()
    return json.loads(row["data"]) if row else None


def delete_decision(decision_id: str) -> bool:
    init_db()
    with _conn() as c:
        cur = c.execute("DELETE FROM decisions WHERE id = ?", (decision_id,))
        return cur.rowcount > 0


# --------------------------------------------------------------------------- #
# preference profiles: remembered per-category weights (personalization)
# --------------------------------------------------------------------------- #
def save_profile(category: str, weights: dict, criteria: list) -> dict:
    init_db()
    now = _now()
    with _conn() as c:
        c.execute(
            """INSERT INTO profiles (category, weights, criteria, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(category) DO UPDATE SET weights=excluded.weights,
                 criteria=excluded.criteria, updated_at=excluded.updated_at""",
            (category, json.dumps(weights), json.dumps(criteria), now))
    return {"category": category, "weights": weights, "criteria": criteria,
            "updated_at": now}


def get_profile(category: str) -> dict | None:
    init_db()
    with _conn() as c:
        row = c.execute("SELECT weights, criteria, updated_at FROM profiles "
                        "WHERE category = ?", (category,)).fetchone()
    if not row:
        return None
    return {"category": category, "weights": json.loads(row["weights"]),
            "criteria": json.loads(row["criteria"]),
            "updated_at": row["updated_at"]}


def list_profiles() -> list:
    init_db()
    with _conn() as c:
        rows = c.execute("SELECT category, weights, updated_at FROM profiles "
                         "ORDER BY updated_at DESC").fetchall()
    return [{"category": r["category"], "weights": json.loads(r["weights"]),
             "updated_at": r["updated_at"]} for r in rows]


def delete_profile(category: str) -> bool:
    init_db()
    with _conn() as c:
        cur = c.execute("DELETE FROM profiles WHERE category = ?", (category,))
        return cur.rowcount > 0
