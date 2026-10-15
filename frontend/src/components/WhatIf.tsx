import { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import type { AnalysisResult, Decision, Movement } from '../types';
import { Badge, Btn, Card, MoveBadge, RankMedal, ScoreBar, SectionTitle, Spinner, WarnList } from './ui';

interface Props {
  baseline: Decision;
  onBack: () => void;
  onApply: (d: Decision) => void;
  onWhatIfDone: (w: any) => void;
}

function RankCol({ title, tone, rows, moves }: {
  title: string; tone: 'before' | 'after';
  rows: { rank: number; name: string; score: number }[];
  moves?: Map<string, Movement>;
}) {
  return (
    <div className={`flex-1 rounded-xl border p-3 ${tone === 'before' ? 'border-stone-200 dark:border-stone-800' : 'border-indigo-200 bg-indigo-50/40 dark:border-indigo-900 dark:bg-indigo-950/20'}`}>
      <div className="mb-2 text-xs font-bold uppercase tracking-widest text-stone-400">{title}</div>
      <div className="space-y-1.5">
        {rows.map((r) => {
          const m = moves?.get(r.name);
          return (
            <div key={r.rank} className="flex items-center gap-2 rounded-lg bg-white px-2.5 py-2 shadow-sm dark:bg-stone-900">
              <RankMedal rank={r.rank} />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-stone-800 dark:text-stone-100">{r.name}</span>
                <span className="tnum text-xs text-stone-400">{r.score.toFixed(1)} pts</span>
              </span>
              {tone === 'after' && m && (
                <span className="flex flex-col items-end gap-0.5">
                  <MoveBadge status={m.status} />
                  {m.delta_score !== null && m.delta_score !== undefined && (
                    <span className={`tnum text-[11px] font-semibold ${m.delta_score > 0 ? 'text-emerald-600' : m.delta_score < 0 ? 'text-rose-500' : 'text-stone-400'}`}>
                      {m.delta_score > 0 ? '+' : ''}{m.delta_score.toFixed(1)}
                    </span>
                  )}
                </span>
              )}
            </div>
          );
        })}
        {rows.length === 0 && <p className="py-4 text-center text-sm text-stone-400">No feasible options.</p>}
      </div>
    </div>
  );
}

export default function WhatIf({ baseline, onBack, onApply, onWhatIfDone }: Props) {
  const [weights, setWeights] = useState<Record<string, number>>(() =>
    Object.fromEntries(baseline.criteria.map((c) => [c.name, c.weight])));
  const [offCons, setOffCons] = useState<Set<string>>(new Set());
  const [offOpts, setOffOpts] = useState<Set<string>>(new Set());
  const [res, setRes] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [auto, setAuto] = useState(true);
  const skipFirst = useRef(true);
  const timer = useRef<any>(null);

  const run = async (w: Record<string, number>, oc: Set<string>, oo: Set<string>) => {
    setLoading(true);
    setError(null);
    try {
      const out = await api.whatif({
        baseline,
        weights: w,
        disable_constraints: [...oc],
        disable_options: [...oo],
      });
      setRes(out);
      onWhatIfDone(out);
    } catch (e: any) {
      setError(e.message || 'What-if failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { run(weights, offCons, offOpts); /* eslint-disable-next-line */ }, []);
  useEffect(() => {
    if (skipFirst.current) { skipFirst.current = false; return; }
    if (!auto) return;
    clearTimeout(timer.current);
    timer.current = setTimeout(() => run(weights, offCons, offOpts), 450);
    return () => clearTimeout(timer.current);
    /* eslint-disable-next-line */
  }, [weights, offCons, offOpts, auto]);

  const toggleSet = (s: Set<string>, v: string) => {
    const n = new Set(s);
    if (n.has(v)) n.delete(v); else n.add(v);
    return n;
  };

  const reset = () => {
    setWeights(Object.fromEntries(baseline.criteria.map((c) => [c.name, c.weight])));
    setOffCons(new Set());
    setOffOpts(new Set());
  };

  const adopt = () => {
    onApply({
      ...baseline,
      criteria: baseline.criteria.map((c) => ({ ...c, weight: weights[c.name] ?? c.weight })),
      constraints: baseline.constraints.map((k) =>
        offCons.has(k.name || k.target) ? { ...k, enabled: false } : k),
      options: baseline.options.filter((o) => !offOpts.has(o.name)),
    });
  };

  const changedCount =
    baseline.criteria.filter((c) => (weights[c.name] ?? c.weight) !== c.weight).length +
    offCons.size + offOpts.size;

  const moves = new Map<string, Movement>((res?.movements || []).map((m: Movement) => [m.name, m]));
  const rowsOf = (a: AnalysisResult | undefined) =>
    (a?.ranked || []).map((r) => ({ rank: r.rank, name: r.name, score: r.score }));

  return (
    <div className="space-y-5">
      <div className="anim-fade-up flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-stone-900 dark:text-white">What-If Mode 🔀</h2>
          <p className="text-sm text-stone-500 dark:text-stone-400">
            Drag a weight and watch the ranking react — updates travel the segment tree in O(log C).
          </p>
        </div>
        <div className="flex gap-2">
          <Btn variant="soft" onClick={onBack}>← Results</Btn>
          <Btn variant="soft" onClick={reset}>Reset</Btn>
          <Btn onClick={adopt} disabled={!changedCount}>Adopt scenario →</Btn>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">
          <span className="font-semibold">What-if failed: </span>{error}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
        {/* controls */}
        <Card className="anim-fade-up-1 h-fit p-5">
          <SectionTitle title="Scenario controls"
            right={<label className="flex items-center gap-1.5 text-xs text-stone-500">
              <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} className="h-4 w-4 accent-indigo-600" /> live
            </label>} />
          <div className="space-y-3">
            {baseline.criteria.map((c) => {
              const v = weights[c.name] ?? c.weight;
              const changed = v !== c.weight;
              return (
                <div key={c.name} className={`rounded-xl p-2.5 ${changed ? 'bg-indigo-50 dark:bg-indigo-950/40' : 'bg-stone-50 dark:bg-stone-800/50'}`}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-stone-700 dark:text-stone-200">
                      {c.name} <span className="text-stone-400">{c.type === 'cost' ? '↓' : '↑'}</span>
                    </span>
                    <span className="tnum text-sm font-bold text-stone-800 dark:text-stone-100">
                      {v}
                      {changed && <span className="ml-1 text-xs font-normal text-stone-400">(was {c.weight})</span>}
                    </span>
                  </div>
                  <input type="range" min={0} max={100} step={1} value={v}
                    onChange={(e) => setWeights((w) => ({ ...w, [c.name]: Number(e.target.value) }))}
                    className="mt-1.5 w-full" />
                </div>
              );
            })}
          </div>

          {baseline.constraints.length > 0 && (
            <>
              <div className="mb-1.5 mt-5 text-xs font-semibold uppercase tracking-wide text-stone-500">Constraints</div>
              <div className="space-y-1.5">
                {baseline.constraints.map((k, i) => {
                  const key = k.name || k.target;
                  const off = offCons.has(key);
                  return (
                    <button key={i} onClick={() => setOffCons((s) => toggleSet(s, key))}
                      className={`flex w-full items-center justify-between rounded-xl border px-3 py-2 text-sm transition ${off ? 'border-rose-200 bg-rose-50 text-rose-700 line-through dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-300' : 'border-stone-200 text-stone-700 dark:border-stone-700 dark:text-stone-200'}`}>
                      <span className="truncate">{k.name || `${k.target} ${k.operator} ${k.value}`}</span>
                      <span className="ml-2 text-xs no-underline">{off ? 'disabled' : 'enabled'}</span>
                    </button>
                  );
                })}
              </div>
            </>
          )}

          <div className="mb-1.5 mt-5 text-xs font-semibold uppercase tracking-wide text-stone-500">Options</div>
          <div className="space-y-1.5">
            {baseline.options.map((o) => {
              const off = offOpts.has(o.name);
              return (
                <button key={o.name} onClick={() => setOffOpts((s) => toggleSet(s, o.name))}
                  className={`flex w-full items-center justify-between rounded-xl border px-3 py-2 text-sm transition ${off ? 'border-rose-200 bg-rose-50 text-rose-700 line-through dark:border-rose-900 dark:bg-rose-950/30 dark:text-rose-300' : 'border-stone-200 text-stone-700 dark:border-stone-700 dark:text-stone-200'}`}>
                  <span className="truncate">{o.name}</span>
                  <span className="ml-2 text-xs no-underline">{off ? 'removed' : 'in race'}</span>
                </button>
              );
            })}
          </div>

          {!auto && <Btn className="mt-4 w-full" onClick={() => run(weights, offCons, offOpts)}>Compare now</Btn>}
        </Card>

        {/* comparison */}
        <div className="anim-fade-up-2 space-y-5">
          <Card className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <SectionTitle title="Before vs after" />
              {loading && <Spinner label="Re-ranking…" />}
            </div>
            {res ? (
              <div className="flex flex-col gap-3 md:flex-row">
                <RankCol title="⬅ Before" tone="before" rows={rowsOf(res.before)} />
                <div className="hidden items-center text-2xl text-stone-300 md:flex">→</div>
                <RankCol title="After ➡" tone="after" rows={rowsOf(res.after)} moves={moves} />
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-stone-400">Run a comparison to see the effect.</p>
            )}
          </Card>

          {res && (
            <>
              <Card className="p-5">
                <SectionTitle title="What caused the change?" />
                {res.causes.length === 0 && offCons.size === 0 && offOpts.size === 0 ? (
                  <p className="text-sm text-stone-500">No changes yet — move a slider to experiment.</p>
                ) : (
                  <ul className="space-y-2 text-sm">
                    {res.causes.map((c: any, i: number) => (
                      <li key={i} className="rounded-xl bg-stone-50 p-3 dark:bg-stone-800/60">
                        <span className="font-semibold text-stone-800 dark:text-stone-100">{c.criterion}</span>
                        <span className="tnum text-stone-500"> {c.old_weight} → {c.new_weight} </span>
                        <Badge tone={c.delta > 0 ? 'emerald' : 'rose'}>{c.delta > 0 ? '+' : ''}{c.delta}</Badge>
                        <p className="mt-1 text-stone-500 dark:text-stone-400">{c.note}</p>
                      </li>
                    ))}
                    {[...offCons].map((k) => (
                      <li key={k} className="rounded-xl bg-amber-50 p-3 text-stone-700 dark:bg-amber-950/30 dark:text-stone-200">
                        🚫 Constraint disabled: <b>{k}</b> — previously eliminated options may re-enter.
                      </li>
                    ))}
                    {[...offOpts].map((o) => (
                      <li key={o} className="rounded-xl bg-amber-50 p-3 text-stone-700 dark:bg-amber-950/30 dark:text-stone-200">
                        ➖ Option removed from race: <b>{o}</b>.
                      </li>
                    ))}
                  </ul>
                )}
              </Card>

              <Card className="p-5">
                <SectionTitle title="Dynamic update trace" sub="How the engine avoided a full recompute." />
                <div className="flex flex-wrap gap-1.5">
                  <Badge tone={res.incremental_used ? 'emerald' : 'stone'}>
                    {res.incremental_used ? '⚡ incremental path O(n + log C)' : '🔁 full recompute (structural change)'}
                  </Badge>
                  {res.incremental_verified !== null && (
                    <Badge tone={res.incremental_verified ? 'emerald' : 'rose'}>
                      {res.incremental_verified ? '✓ matches full recompute' : '✕ mismatch!'}
                    </Badge>
                  )}
                  <Badge tone="stone">total {res.segment_trace.old_total} → {res.segment_trace.new_total}</Badge>
                  <Badge tone="stone">{res.total_ms} ms</Badge>
                </div>
                {res.segment_trace.updates.length > 0 && (
                  <div className="mt-3 space-y-1.5 text-sm">
                    {res.segment_trace.updates.map((u: any, i: number) => (
                      <div key={i} className="tnum rounded-lg bg-stone-50 px-3 py-2 dark:bg-stone-800/60">
                        <span className="text-stone-500">touched segment nodes →</span>{' '}
                        <span className="font-mono font-semibold text-amber-600 dark:text-amber-400">
                          [{u.touched_nodes.join(' → ')}]
                        </span>{' '}
                        <span className="text-stone-400">({u.old} → {u.new})</span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="mt-3"><WarnList items={res.patch_warnings || []} /></div>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
