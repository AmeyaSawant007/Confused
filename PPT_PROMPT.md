# AI PPT Generator Prompt — "Confused?" Project Presentation

Copy everything below the line into any AI presentation tool
(Gamma, Tome, Beautiful.ai, Canva, Slidesgo, etc.).

---

Create a professional academic project presentation titled
**"Confused? — Decide with Data Structures"**.

**Context:** This is an Advanced Data Structures laboratory mini-project:
a decision-support web app that ranks a user's options (e.g. which laptop,
project, or internship to choose) using hand-implemented data structures —
not spreadsheet sorting. Audience: computer science professors and lab
examiners during a project demo + viva. Tone: confident, technical, concise.
Length: 13 slides. Design: clean, minimal, premium; white/slate background
with one indigo accent color; no cluttered gradients; use tables, a simple
architecture diagram, and icons for each data structure.

**Slide 1 — Title:** "Confused? — Decide with Data Structures". Subtitle:
"An explainable decision-support platform powered by Graphs, Heaps, Tries,
Segment Trees, Hash Tables and Stacks". Footer: ADS Lab Mini-Project.

**Slide 2 — Problem Statement:** Everyday decisions (which laptop, final-year
project, internship, technology) involve many options, conflicting criteria,
hard constraints and changing priorities. People decide by gut feel, lose
track of trade-offs, and cannot answer "what if price mattered more?".

**Slide 3 — Objectives:** Accept a decision problem (options, criteria,
weights, constraints); eliminate options violating hard constraints; score
and rank the rest transparently; support live What-If exploration and Undo;
visualize every data structure live for demonstration.

**Slide 4 — Key Features (the product):** Decision Builder with
benefit/cost criteria and natural units (₹, hours, kg); one-click analysis
with winner, per-criterion point breakdowns and elimination reasons;
What-If mode with before/after rankings; Under-the-Hood visualizer; instant
trie search; version history with undo; dark mode; 4 ready-made demos.

**Slide 5 — System Architecture:** Two-tier app. Frontend: React +
TypeScript + Tailwind (Vite). Backend: Python FastAPI + SQLite, containing a
modular decision-engine (graph, heap, trie, range, hash, stack, scoring,
engine packages). Show a simple diagram: UI → REST /api → engine pipeline →
JSON result with scores + DS snapshots.

**Slide 6 — Data Structures Used (table):** Graph = central decision model
(decision→options→criteria/constraints + similarity edges); Max-Heap =
live ranking via extraction; Trie = prefix search over titles/options;
Segment Tree = criterion weights for O(log C) updates; Hash Table (djb2 +
chaining) = ID registries + result cache; Stack = version history/undo.

**Slide 7 — Algorithms & Complexity (table):** BFS/DFS O(V+E); Dijkstra
O((V+E) log V); heap ops O(log n); top-K O(k log n); trie search O(L);
hash lookup O(1) average; segment update/query O(log C); incremental
re-score O(n + log C); stack push/pop O(1).

**Slide 8 — How the Decision Engine Works:** 8-stage pipeline: validate →
hash registries → constraint filter → min-max normalization (benefit ↑ /
cost ↓) → segment-tree weights → weighted scores (score = 100·Σ(norm·w)/W)
→ decision graph + BFS/DFS/Dijkstra → max-heap ranking → explanation.
Stress: ranking NEVER uses a generic sort.

**Slide 9 — Live Demo Walkthrough:** "Which laptop should I buy?" — 3
options × 4 criteria (Price 30, Performance 35, Battery 20, Weight 15) with
Budget ≤ ₹80,000 and Weight ≤ 2 kg. Result: EcoLite 13 wins with 65.0,
AeroBook 14 second with 35.0, Titan Gaming 15 eliminated (2.3 kg > 2 kg).

**Slide 10 — What-If Dynamic Update:** Disable the weight constraint and
raise Performance to 80 → Titan Gaming 15 takes the lead. Only the
segment-tree root→leaf path is touched (O(log C)); cached numerators
re-score in O(n + log C); engine verifies the incremental result matches a
full recompute; UI shows rank movements, score deltas and causes.

**Slide 11 — Testing & Verification:** 65 automated pytest tests covering
every data structure, 4 realistic scenarios and edge cases (no options,
single option, tied scores, weights ≠ 100%, all options infeasible,
duplicates, repeated weight changes, undo). Typical analysis runs in under
5 ms. Manual end-to-end verification of all UI flows.

**Slide 12 — Screens Tour:** Six panels with placeholder captions:
Dashboard with instant search; Decision Builder; Results with contribution
breakdown; What-If before/after; Under-the-Hood graph + heap views; DS
playgrounds. (I will replace placeholders with real screenshots.)

**Slide 13 — Future Scope + Thank You:** Pairwise (AHP) weight elicitation;
sensitivity analysis (how much must a weight move to flip the winner?);
multi-user collaborative decisions; persistent history + accounts. End with
"Thank You — Questions?" and the tagline: "Rankings reflect your inputs,
not objective truth."
