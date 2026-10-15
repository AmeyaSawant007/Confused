# Confused? — DS Lab Viva Guide

One-line answers plus the 30-second explanation for each expected question.

## Why Graph?

**A decision is a network, not a table.** Nodes = decision, options, criteria,
constraints; edges carry costs (decision→option = 100 − score), points
(option→criterion) and feasibility (option→constraint, 0 or ∞). The graph is the
single structure the explanation, traversal and shortest-path features all read.

## Why Heap?

**Rankings must stay dynamic and support top-K.** Our hand-written max-heap
(array + index map) holds feasible options by score. Extract-max yields the
ranking in O(n log n) total, top-K in O(k log n), and a re-score is an O(log n)
update — with stable FIFO ties so equal scores rank deterministically.

## Why Trie?

**Instant prefix search.** Every title, option, category and keyword is indexed,
so `lap…` finds laptop decisions in O(prefix + matches) time, independent of
how many decisions exist. Hashing can't do prefixes; scanning is O(N·L).

## Why Segment Tree?

**Weights change all the time.** The criterion-weight array lives in a segment
tree, so a What-If edit is a point update in O(log C) touching only the
root→leaf path (shown amber in the UI), and the weight total is always O(1)/O(log C).

## Why Hashing?

**O(1) identity + memoization.** A djb2/chaining/resizing table maps option and
criterion IDs during analysis, and a second table caches whole results by
decision fingerprint so identical problems never recompute.

## Why Stack?

**Undo is LIFO.** Each saved version is pushed with a label; Undo pops it back.
Push/pop/peek are O(1); depth is capped at 50.

## Why Dijkstra?

**Two genuine uses:** (1) decision→option edge cost is defined as 100 − score,
so the shortest path from the decision node *is* the winner — an independent
graph-theoretic confirmation of the heap ranking; (2) from the winner, Dijkstra
over option⇄option similarity edges finds the **closest alternative** (backup pick).

## Why not simply sort the options?

Sorting is a one-shot O(n log n) dead end: every weight tweak re-sorts from
scratch and top-K still costs full sorting. The heap maintains rank *dynamically*
(top-K in O(k log n), updates in O(log n)) and its array *is* the inspectable
ranking state shown in Under the Hood. Also — the lab is about data structures.

## Where is dynamic updating used?

What-If weight edits: the segment tree absorbs the change in O(log C); cached
per-option numerators re-score each option in O(changed criteria); the heap
re-ranks. Total **O(n + log C)** vs O(n·C) naive — and the engine verifies the
incremental result equals a full recompute on every run.

## What is the time complexity?

BFS/DFS O(V+E); Dijkstra O((V+E) log V); heap ops O(log n); trie O(L);
hash O(1) avg; segment update/query O(log C); end-to-end analysis is linearithmic
in options with tiny constants (typical run < 5 ms).

## What happens when a criterion weight changes?

1. Segment-tree point update touches the root→leaf path (O(log C)) → new total W′.
2. Each option's numerator shifts by `norm·Δw` only for changed criteria.
3. Scores recomputed as `100·num′/W′`; heap re-ranks; graph costs refresh.
4. UI shows before/after ranks, score deltas, which criterion caused it, and the
   touched nodes. Full trace in What-If → "Dynamic update trace".

## Where exactly is the deep learning?

**Smart Import's field matcher.** Page phrases and criterion names are embedded
by a MiniLM transformer (6 layers, 384-dim vectors); cosine similarity maps
each fact to the best criterion above 0.30. One line: *"the neural net decides
which page fact fills which criterion."* The full score matrix is rendered in
the UI, and `/api/match` + the Neural playground let anyone probe it live.

## Why neural matching instead of regex?

Regex matches strings, not meaning. "Battery backup" vs "Battery Life" and
"how much does it cost" vs "Price" (zero shared words!) only match
semantically — MiniLM scores them ~0.5–0.9 vs ~0.2 for wrong criteria.
Keyword overlap is kept as the fallback when torch isn't installed.

## What if there's no internet / no torch?

Two independent fallbacks: (1) offline sample pages exercise the exact same
extraction + matching code path, so the demo never needs the web; (2) without
`requirements-ml.txt`, matching degrades to token-overlap + unit hints and the
UI badges it honestly as "keyword fallback". The core engine never needs either.

## Why aren't preference profiles called deep learning?

Because with single-user local data they'd be statistics wearing a costume —
there is no training set for a persona model, and cold-start would make the
headline feature silent on first run. Profiles are honestly what they are:
remembered per-category weights. The *real* DL is the matcher, which is
pretrained and works on day one.

## Where exactly is the classical ML?

**Smart Weights.** Duel answers ("I pick A over B") become supervised training
rows `X = norm(winner) − norm(loser)`, `y = 1`, and a logistic regression
coded from scratch in NumPy (batch gradient descent, L2, no intercept, no
sklearn) fits one coefficient per criterion. Softmax turns coefficients into
weights summing to 100. One line: *"the model learns which criteria explain
your picks."* Diagnostics shown live: train accuracy, leave-one-out accuracy,
loss curve, and honest warnings (too few duels, contradictory picks).

## Why logistic regression and not a neural net?

Duel data is tiny (3–6 answers) — an MLP would memorize it and prove nothing.
A linear model with L2 is the right capacity: it generalizes (LOO accuracy is
reported live), trains in milliseconds on CPU, and its coefficients *are* the
explanation. The synthetic-user test proves it recovers hidden weights exactly.

## Demo script (3 minutes)

1. Dashboard → **🔗 Import from links** → Try offline samples → point at the
   neural scores (Price 1.00, "battery backup" → Battery Life).
2. Apply → add Budget + Weight constraints → Analyze → EcoLite 13 wins (65.0),
   Titan eliminated. **🧠 Remember** the weights.
3. Builder → **⚔️ Start dueling** → pick 3+ winners → train → point at train
   100%, the loss curve, and Apply learned weights.
4. What-If → disable weight constraint, Performance → 80 → Titan takes the lead;
   point at touched nodes + "verified vs full recompute".
5. Under the Hood → neural + learning panels show your live import/learn;
   Graph tab: BFS/Dijkstra playground. Done — every claim on screen is live data.
