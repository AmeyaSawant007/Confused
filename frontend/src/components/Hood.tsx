import { useEffect, useState } from 'react';
import { api } from '../api';
import type { ImportResult, LearnResult } from '../types';
import { LossCurve } from './SmartWeights';
import { Badge, Btn, Card, SectionTitle, Spinner } from './ui';

interface Props {
  lastImport: ImportResult | null;
  lastLearn: LearnResult | null;
}

type PlayKind = 'heap' | 'trie' | 'graph' | 'segment' | 'hash' | 'stack';

const SECTIONS: { id: PlayKind; tab: string; icon: string; title: string; subtitle: string; bullets: string[] }[] = [
  {
    id: 'heap', tab: 'Ranking', icon: '🥇', title: 'Rank options with a max-heap',
    subtitle: 'Weighted score → heap push → pop k winners. O(n + k log n) — no full sort needed.',
    bullets: ['Engine pushes every feasible option with its weighted score', 'Top ranks emerge by repeated pop — BinaryHeap under the hood', 'Playground: push keys, then topk them back out'],
  },
  {
    id: 'trie', tab: 'Search', icon: '🔍', title: 'Prefix-search past decisions',
    subtitle: 'Saved titles are indexed word-by-word in a trie for instant prefix lookup.',
    bullets: ['Lowercased tokens from titles and options are inserted', 'Dashboard suggestions complete as you type', 'Playground: insert words, then query prefixes'],
  },
  {
    id: 'graph', tab: 'Graph', icon: '🕸', title: 'Decisions form a weighted graph',
    subtitle: 'Options link to criteria with contribution weights; BFS/DFS/Dijkstra explore it.',
    bullets: ['Edges carry each criterion contribution to an option score', 'Shortest paths reveal the nearest alternative', 'Playground: run BFS, DFS and Dijkstra on a live graph'],
  },
  {
    id: 'segment', tab: 'What-if', icon: '📊', title: 'Segment tree caches range scores',
    subtitle: 'Point updates + range sums in O(log n) keep the What-if lab instant.',
    bullets: ['Each leaf stores one criterion contribution', 'Drag a weight slider → only affected nodes recompute', 'Playground: update indices and query ranges'],
  },
  {
    id: 'hash', tab: 'Registry', icon: '🗄', title: 'Hash tables index everything',
    subtitle: 'Options, criteria and cached results live in O(1) hash registries.',
    bullets: ['Separate chaining with automatic resizes', 'Result cache fingerprints decisions for instant replay', 'Playground: put keys and watch collisions happen'],
  },
  {
    id: 'stack', tab: 'History', icon: '🗂', title: 'Version history is a stack',
    subtitle: 'Checkpoints push, undo pops. Bounded — LIFO, exactly like git stash.',
    bullets: ['Every checkpoint stores a full decision snapshot', 'Undo restores top-of-stack and discards it', 'Playground: push labels and pop them back'],
  },
];

const SAMPLES: Record<PlayKind, string> = {
  heap: '{\n  "mode": "max",\n  "ops": [\n    {"op": "push", "key": "Laptop A", "priority": 82},\n    {"op": "push", "key": "Laptop B", "priority": 91},\n    {"op": "push", "key": "Laptop C", "priority": 77},\n    {"op": "peek"},\n    {"op": "topk", "k": 2}\n  ]\n}',
  trie: '{\n  "ops": [\n    {"op": "insert", "word": "laptop"},\n    {"op": "insert", "word": "lamp"},\n    {"op": "insert", "word": "laptop stand"},\n    {"op": "prefix", "prefix": "lap", "limit": 5}\n  ]\n}',
  graph: '{\n  "ops": [\n    {"op": "bfs", "start": "A"},\n    {"op": "dijkstra", "start": "A"},\n    {"op": "path", "start": "A", "target": "E"}\n  ]\n}',
  segment: '{\n  "values": [30, 35, 20, 15],\n  "labels": ["price", "battery", "weight", "screen"],\n  "ops": [\n    {"op": "total"},\n    {"op": "update", "index": 1, "value": 45},\n    {"op": "query", "l": 0, "r": 2}\n  ]\n}',
  hash: '{\n  "capacity": 4,\n  "ops": [\n    {"op": "put", "key": "price", "value": 30},\n    {"op": "put", "key": "battery", "value": 25},\n    {"op": "put", "key": "weight", "value": 20},\n    {"op": "get", "key": "battery"}\n  ]\n}',
  stack: '{\n  "ops": [\n    {"op": "push", "label": "v1 baseline"},\n    {"op": "push", "label": "v2 raised battery"},\n    {"op": "peek"},\n    {"op": "pop"}\n  ]\n}',
};

export default function Hood({ lastImport, lastLearn }: Props) {
  const [kind, setKind] = useState<PlayKind>('heap');
  const [input, setInput] = useState(SAMPLES.heap);
  const [out, setOut] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [pErr, setPErr] = useState<string | null>(null);
  const active = SECTIONS.find((s) => s.id === kind)!;

  useEffect(() => {
    setInput(SAMPLES[kind]);
    setOut(null);
    setPErr(null);
  }, [kind]);

  const run = async () => {
    setLoading(true);
    setPErr(null);
    try {
      const body = input.trim() ? JSON.parse(input) : {};
      const r = await api.play(kind, body);
      setOut(r);
    } catch (e: any) {
      setPErr(e.message || 'Invalid JSON');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="anim-fade-up">
        <h2 className="text-2xl font-bold text-stone-900 dark:text-white">Under the Hood 🧠</h2>
        <p className="text-sm text-stone-500 dark:text-stone-400">
          Not magic — six data structures, one neural matcher, and one classical learner run this app. Read the tour, then drive each machine yourself.
        </p>
      </div>

      {/* neural import card */}
      <Card className="anim-fade-up-1 overflow-hidden p-0">
        <div className="bg-gradient-to-r from-indigo-600 via-violet-600 to-sky-500 p-5 text-white">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-2xl">🧬</span>
            <div>
              <h3 className="text-lg font-bold leading-tight">Smart Import runs on a neural network</h3>
              <p className="text-[13px] text-indigo-100">Transformer embeddings + cosine similarity align page phrases with your criteria.</p>
            </div>
            <span className="ml-auto hidden gap-1.5 sm:flex">
              {lastImport ? (
                <>
                  <Badge tone={lastImport.matcher === 'neural' ? 'emerald' : 'amber'}>● {lastImport.matcher}</Badge>
                  {lastImport.model && <Badge tone="sky">{lastImport.model}</Badge>}
                </>
              ) : (
                <Badge tone="stone">awaiting first import</Badge>
              )}
            </span>
          </div>
        </div>
        <div className="grid gap-4 p-5 md:grid-cols-[1fr_1fr]">
          <div>
            <h4 className="mb-2 text-[13px] font-bold uppercase tracking-wide text-stone-500">How it thinks</h4>
            <ol className="space-y-2 text-sm text-stone-700 dark:text-stone-200">
              {[
                ['📄', 'Page text is cleaned and split into candidate phrases (headings, bullets, table cells).'],
                ['🧠', 'A transformer encodes every phrase and every criterion into a vector — meaning, not spelling.'],
                ['📐', 'Cosine similarity pairs each phrase with its best criterion; weak links stay unmatched.'],
                ['🔢', 'Numbers are parsed with units (₹/L, hours, kg) and scored on the criterion scale.'],
                ['🧩', 'Gaps are flagged as missing — you fill them in, then everything becomes structured data.'],
              ].map(([icon, t], i) => (
                <li key={i} className="flex gap-2.5">
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-indigo-100 text-sm dark:bg-indigo-950">{icon}</span>
                  <span>{t}</span>
                </li>
              ))}
            </ol>
          </div>
          <div className="rounded-xl bg-stone-50 p-4 dark:bg-stone-800/50">
            <h4 className="mb-2 text-[13px] font-bold uppercase tracking-wide text-stone-500">Live proof — your last import</h4>
            {!lastImport ? (
              <p className="text-sm text-stone-500">
                No import yet this session. Run a Smart Import in the Builder — this panel will show the live matcher, model and phrase matches.
              </p>
            ) : (
              <div className="space-y-2 text-sm">
                <div className="flex flex-wrap gap-1.5">
                  <Badge tone={lastImport.matcher === 'neural' ? 'emerald' : 'amber'}>{lastImport.matcher}</Badge>
                  {lastImport.model && <Badge tone="sky">{lastImport.model}</Badge>}
                </div>
                {lastImport.options.slice(0, 2).map((o, i) => (
                  <div key={i} className="rounded-lg bg-white p-2.5 text-[13px] dark:bg-stone-900">
                    <div className="font-semibold">{o.name} <span className="font-normal text-stone-400">· {o.filled.length} filled</span></div>
                    {o.sources.slice(0, 3).map((s, j) => (
                      <div key={j} className="mt-1 text-stone-500">
                        “{s.phrase}” <span className="text-stone-300">→</span> <b className="text-stone-700 dark:text-stone-200">{s.criterion}</b>{' '}
                        <span className="tnum font-mono text-[11px] text-indigo-600">{s.score.toFixed(3)}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* preference learning card */}
      <Card className="anim-fade-up-1 overflow-hidden p-0">
        <div className="bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 p-5 text-white">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-2xl">📈</span>
            <div>
              <h3 className="text-lg font-bold leading-tight">Smart Weights learns from your duels</h3>
              <p className="text-[13px] text-emerald-100">Classical ML: pairwise logistic regression, coded from scratch with NumPy.</p>
            </div>
            <span className="ml-auto hidden gap-1.5 sm:flex">
              {lastLearn && (
                <>
                  <Badge tone="emerald">train {(lastLearn.train_acc * 100).toFixed(0)}%</Badge>
                  <Badge tone="sky">LOO {(lastLearn.loo_acc * 100).toFixed(0)}%</Badge>
                </>
              )}
            </span>
          </div>
        </div>
        <div className="grid gap-4 p-5 md:grid-cols-[1fr_1fr]">
          <div>
            <h4 className="mb-2 text-[13px] font-bold uppercase tracking-wide text-stone-500">How it learns</h4>
            <ol className="space-y-2 text-sm text-stone-700 dark:text-stone-200">
              {[
                ['⚔️', 'Each duel answer becomes one training row: normalized(winner) − normalized(loser), label 1.'],
                ['🧮', 'A from-scratch logistic regression (gradient descent, L2, no intercept) fits one coefficient per criterion.'],
                ['📉', 'Loss must decrease across epochs; train accuracy and leave-one-out CV verify the fit generalizes.'],
                ['⚖️', 'Coefficients pass through softmax → weights that sum to 100, ready to apply to your decision.'],
              ].map(([icon, t], i) => (
                <li key={i} className="flex gap-2.5">
                  <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-emerald-100 text-sm dark:bg-emerald-950">{icon}</span>
                  <span>{t}</span>
                </li>
              ))}
            </ol>
          </div>
          <div className="rounded-xl bg-stone-50 p-4 dark:bg-stone-800/50">
            <h4 className="mb-2 text-[13px] font-bold uppercase tracking-wide text-stone-500">Live proof — your last training</h4>
            {!lastLearn ? (
              <p className="text-sm text-stone-500">
                No training yet this session. Duel some options in the Builder — this panel will show the learned weights, accuracy, and loss curve.
              </p>
            ) : (
              <div className="space-y-2 text-sm">
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(lastLearn.weights).map(([k, v]) => (
                    <Badge key={k} tone="emerald">{k} {v}</Badge>
                  ))}
                </div>
                <p className="text-xs text-stone-500">
                  {lastLearn.n_samples} duels · {lastLearn.n_criteria} criteria ·
                  train {(lastLearn.train_acc * 100).toFixed(0)}% · LOO {(lastLearn.loo_acc * 100).toFixed(0)}%
                  {lastLearn.uniform_fallback ? ' · uniform fallback' : ''}
                </p>
                <LossCurve losses={lastLearn.loss_curve} />
                <p className="font-mono text-[11px] leading-relaxed text-stone-400">{lastLearn.method_detail}</p>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* DS tour */}
      <Card className="anim-fade-up-2 p-5">
        <SectionTitle title="The six machines" sub="Pick a tab — read what it does, scroll for the interactive demo." />
        <div className="flex flex-wrap gap-1.5">
          {SECTIONS.map((s) => (
            <button key={s.id} onClick={() => setKind(s.id)}
              className={`rounded-full px-3.5 py-1.5 text-[13px] font-medium transition ${
                kind === s.id
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/25'
                  : 'bg-stone-100 text-stone-600 hover:bg-stone-200 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-stone-700'
              }`}>
              {s.icon} {s.tab}
            </button>
          ))}
        </div>
        <div className="mt-4">
          <h3 className="text-lg font-bold text-stone-900 dark:text-white">{active.icon} {active.title}</h3>
          <p className="text-sm text-stone-500">{active.subtitle}</p>
          <ul className="mt-2 grid gap-1.5 sm:grid-cols-3">
            {active.bullets.map((b, i) => (
              <li key={i} className="rounded-xl bg-stone-50 p-3 text-[13px] text-stone-700 dark:bg-stone-800/60 dark:text-stone-200">{b}</li>
            ))}
          </ul>
        </div>
      </Card>

      {/* playground */}
      <Card className="anim-fade-up-3 p-5">
        <SectionTitle title={`Playground — ${kind}`}
          sub="Edit the JSON, run it against the live backend structures."
          right={<Btn onClick={run} disabled={loading}>{loading ? <Spinner label="Running…" /> : '▶ Run'}</Btn>} />
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-stone-500">Input JSON</label>
            <textarea value={input} onChange={(e) => setInput(e.target.value)} rows={12} spellCheck={false}
              className="w-full rounded-xl border border-stone-200 bg-stone-950 p-3 font-mono text-[13px] leading-relaxed text-emerald-200 outline-none focus:border-indigo-400 dark:border-stone-700" />
            {pErr && <p className="mt-2 text-sm text-rose-600">{pErr}</p>}
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-stone-500">Output</label>
            <pre className="max-h-[320px] min-h-[280px] overflow-auto rounded-xl border border-stone-200 bg-stone-50 p-3 font-mono text-[13px] leading-relaxed text-stone-800 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100">
              {out ? JSON.stringify(out, null, 2) : '— press Run —'}
            </pre>
          </div>
        </div>
      </Card>
    </div>
  );
}
