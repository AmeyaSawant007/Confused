# Confused? — Decide with Data Structures

A decision-support platform that ranks your options using **real, hand-implemented
advanced data structures** — not a spreadsheet with a sort button — plus a
**neural Smart Import** that reads product/job pages from links you paste.

> "I'm confused about which final-year project to choose."
> — Confused? turns that into options × criteria × constraints, then produces a
> transparent, explainable ranking.

---

## 2. Problem Statement

Everyday decisions (which laptop, project, internship, job…) involve multiple
options, conflicting criteria, hard constraints and shifting priorities. People decide
by gut feel, lose track of trade-offs, and can't answer *"what if price mattered more?"*
Typing every spec by hand is tedious — and the data already exists on the web.

## 3. Motivation

Build a tool that makes decisions **systematic and explainable**, while proving that
classic advanced data structures — graphs, heaps, tries, segment trees, hash tables,
stacks — are the natural machinery for the job, not textbook curiosities. A small,
honest dose of deep learning (neural semantic matching) removes manual data entry
without ever replacing the exact, explainable engine.

## 4. Objectives

1. Accept a decision problem (question, options, criteria, weights, constraints).
2. Import options from web links via neural field matching (or offline samples).
3. Eliminate options that violate hard constraints.
4. Normalize and score options with dynamic weights.
5. Rank with a heap, explain with a graph.
6. Support live **What-If** exploration with incremental re-scoring.
7. Support **Undo** over decision history.
8. Remember per-category **preference profiles** for personalization.
9. Visualize every data structure — and the neural matcher — live
   (**Under the Hood**) for lab/viva demonstration.

## 5. Features

- 🔗 **Smart Import** — paste product/job URLs; the importer fetches each page,
  extracts facts (price, rating, specs) and a MiniLM transformer maps them to
  *your* criteria with visible similarity scores. Offline samples included.
- 📊 **Decision Builder** — question, category, options with natural-unit values
  (₹, hours, kg, ratings), benefit/cost criteria, hard/soft constraints.
- 🧠 **Preference Profiles** — one-click "Remember my weights" per category;
  new decisions offer to apply your usual weights automatically.
- ⚔️ **Smart Weights** — duel your options head-to-head; a from-scratch
  pairwise logistic regression (NumPy, no sklearn) learns weights that sum
  to 100, with train/leave-one-out accuracy and a live loss curve.
- ⚡ **Analysis engine** — constraint filtering → min-max normalization →
  weighted scoring → graph reasoning → heap ranking → explanation.
- 🏆 **Results** — winner banner, expandable per-criterion point breakdown,
  eliminated list with reasons, confidence heuristic, nearest-alternative backup pick.
- 🔀 **What-If mode** — drag weights / toggle constraints / drop options; see
  before-vs-after rankings, movement badges, causes, and the segment-tree update trace.
- 🧠 **Under the Hood** — live neural-match and preference-learning panels
  from *your* run, a six-data-structure tour, plus an interactive playground
  driving the real backend structures.
- 🔤 **Trie search** — type `lap…` and instantly find laptop decisions.
- ↩ **Undo** — version checkpoints on a history stack, restored in one click.
- 💾 **Persistence** — SQLite storage for decisions and profiles; JSON export.
- 🌙 Dark / light mode, responsive card UI.

## 6. System Architecture

```
┌──────────────────────────── React + TypeScript + Tailwind (Vite) ─────────────────────────┐
│ Dashboard · Builder(+Smart Import) · Results · What-If · Under-the-Hood(+Neural tab)     │
└─────────────────────────────────────── │ /api (JSON) ─────────────────────────────────────┘
┌──────────────────────────── Python FastAPI ───────────────────────────────────────────────┐
│ routes: analyze · whatif · import · match · profiles · decisions(+checkpoint/undo)       │
│         search · play/* (DS playground)                                                  │
│ store: SQLite (decisions + profiles) · in-memory: trie index + history stacks            │
│ decision-engine/                                                                        │
│   graph/  Graph + BFS + DFS + Dijkstra (adjacency list, weighted edges)                 │
│   heap/   BinaryHeap (max/min, index map, stable ties)                                  │
│   trie/   Trie (insert/search/prefix/delete + refs)                                     │
│   range/  SegmentTree (point update, range sum, touched-node trace)                     │
│   hash/   HashTable (djb2, chaining, auto-resize)                                       │
│   stack/  HistoryStack (push/pop/peek snapshots)                                        │
│   scoring/ min-max normalize + weighted + incremental re-score                          │
│   engine/ DecisionEngine pipeline (analyze · what_if · rank_with_heap)                  │
│ ml/       NeuralFieldMatcher (MiniLM + cosine) + keyword fallback                       │
│ importer/ fetch + extract facts + match-to-criteria + build options (+offline fixtures) │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

Pipeline: `validate → hash registries → constraints → normalize → segment-tree
weights → scores → decision graph → BFS/DFS/Dijkstra → heap rank → explain`.
Smart Import feeds the pipeline: `URL → fetch → extract → neural match → values`.

## 7. Data Structures Used

| Structure | File | Role in the product |
|---|---|---|
| Weighted **Graph** (adjacency list) | `graph.py` | Central model: decision→options→criteria/constraints + option similarity |
| **Max-Heap** priority queue | `heap.py` | Holds feasible options; ranking = heap extraction |
| **Trie** | `trie.py` | Prefix search over titles, options, categories, keywords |
| **Segment Tree** | `segment_tree.py` | Criterion weights; O(log C) updates for What-If |
| **Hash Table** | `hash_table.py` | ID registries + fingerprint result cache |
| **Stack** | `history_stack.py` | Version checkpoints / undo |
| Transformer embeddings (MiniLM) | `ml/semantic.py` | DL model: semantic phrase→criterion matching for Smart Import |

## 8. Algorithms Used

- **BFS / DFS** — traverse decision relationships (O(V+E)).
- **Dijkstra** (with our own binary heap) — shortest decision path = winner;
  closest-alternative search over similarity edges (O((V+E) log V)).
- **Transformer cosine matching** — MiniLM embeds phrases/criteria (384-dim);
  best match above 0.30 fills the value. Keyword-overlap fallback without torch.
- **Pairwise logistic regression** — duel answers become training rows
  `X = norm(winner) − norm(loser)`, `y = 1`; batch gradient descent with L2
  (from-scratch NumPy, no intercept); softmax maps coefficients to weights.
- **Min-max normalization** — per criterion over feasible options; benefit ↑ / cost ↓.
- **Weighted-sum scoring** — `score = 100 · Σ(norm·w) / W`.
- **Incremental re-scoring** — cached numerators + segment-tree total ⇒ O(n + log C)
  weight updates, verified against full recompute every run.
- **Heap drain / top-K** — rank order without any generic sort.

## 9. Why Each Data Structure Was Selected

- **Graph** — a decision *is* a network of relationships; edges carry the exact
  costs/points the explanation needs. No flat table expresses that.
- **Heap** — rankings are dynamic (weights change, options drop). A heap gives
  top-K in O(k log n) and O(log n) updates; re-sorting is O(n log n) every time
  and discards structure.
- **Trie** — prefix completion in O(prefix) time regardless of stored decisions.
- **Segment tree** — weights change constantly in What-If; point update + total
  in O(log C) with a visible touched path.
- **Hash table** — O(1) ID lookups and memoization of repeated analyses.
- **Stack** — undo is inherently LIFO.
- **Transformer (DL)** — page authors never use your exact criterion names;
  only semantic embeddings can map "battery backup" → Battery Life or
  "how much does it cost" → Price. Regex can't; the full score matrix keeps it
  explainable.

## 10. Time Complexity

| Operation | Complexity |
|---|---|
| BFS / DFS | O(V+E) |
| Dijkstra (own binary heap) | O((V+E) log V) |
| Heap insert / update / remove / extract | O(log n) |
| Top-K ranking | O(k log n) |
| Trie prefix search | O(P + M) |
| Hash lookup (average) | O(1) |
| Segment-tree update / range sum | O(log C) |
| Neural match (P phrases × C criteria) | O(P·C) cosine ops after one batched embed |
| Incremental re-score on weight change | O(n + log C) |
| History push / pop | O(1) |

## 11. Space Complexity

Graph O(V+E) · heap O(n) · trie O(total indexed chars) · segment tree O(C) ·
hash tables O(entries) · history O(versions × decision size, capped at 50) ·
MiniLM weights ~80MB (optional, lazy-loaded).

## 12. Screenshots

> Placeholders — run the app and capture these for your report.

- `docs/shot-dashboard.png` — Dashboard with trie search + templates
- `docs/shot-builder.png` — Decision Builder (criteria/options/constraints)
- `docs/shot-smartimport.png` — Smart Import matches with similarity scores
- `docs/shot-results.png` — Winner + ranking + contribution breakdown
- `docs/shot-whatif.png` — Before/after + movement + segment trace
- `docs/shot-hood-graph.png` — Decision graph + BFS/DFS/Dijkstra panels
- `docs/shot-hood-heap.png` — Heap tree + operation log
- `docs/shot-hood-neural.png` — Neural match tables + playground

## 13. Installation

Prerequisites: **Python 3.10+**, **Node.js 18+**.

```bash
# 1. backend
cd confused/backend
pip install -r requirements.txt

# 1b. backend ML (optional but recommended: enables the neural matcher;
#     without it Smart Import uses the keyword fallback)
pip install -r requirements-ml.txt

# 2. frontend
cd ../frontend
npm install
```

> First neural use downloads the ~80MB MiniLM model (then cached). Run once
> with internet before an offline demo.

## 14. Running Instructions

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu

# terminal 1 — API (http://localhost:8000, docs at /docs)
cd confused/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# terminal 2 — UI (http://localhost:5173)
cd confused/frontend
npm run dev
```

Run the test suite (75 tests: every DS + importer + matcher + 4 engine
scenarios + edge cases + API):

```bash
cd confused/backend
python -m pytest -q
```

Production frontend build: `cd confused/frontend && npm run build`.

## 15. Example Workflow

1. Open the app → **🔗 Import from links** (or Builder → Smart Import).
2. Click **Try offline samples** → 3 laptops import with neural match scores
   (Price 1.00, Battery Backup → Battery Life ~0.8, …).
3. **Apply options** → add Budget ≤ ₹80,000 + Weight ≤ 2 kg → **⚡ Analyze**.
4. Winner: **EcoLite 13 (65.0)**; Titan Gaming 15 eliminated (2.3 kg > 2 kg).
5. **🧠 Remember** your weights → start any new gadgets decision → one-click
   **Apply your usual weights**.
6. Builder → **⚔️ Start dueling**: pick winners head-to-head, train, and
   **Apply learned weights** (train 100%, LOO shown, loss curve decreasing).
7. Open **🔀 What-If**: disable the weight constraint and raise Performance to 80 →
   **Titan Gaming 15 takes the lead**; the trace shows touched segment nodes and
   verifies the incremental O(n + log C) path matches a full recompute.
8. Open **🧠 Under the Hood** → inspect the neural + learning panels
   and try the playground (heap push/topk, trie prefixes, Dijkstra paths).
9. Search `lap…` on the dashboard to see trie prefix search.

## 16. Future Scope

- Pairwise (AHP-style) weight elicitation with consistency ratio.
- MLP preference ranker (nonlinear upgrade over the logistic Smart Weights).
- Sensitivity analysis: how much must a weight move to flip the winner.
- More importers (job boards, course catalogs) + richer extractors.
- Multi-user collaborative decisions; persistent history + accounts.

---

*Ranking reflects only the criteria, weights, scores and constraints you supplied.
It is not an objectively "correct" decision.*
