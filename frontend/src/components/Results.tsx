import { useState } from 'react';
import type { AnalysisResult } from '../types';
import { Badge, Btn, Card, EmptyState, RankMedal, ScoreBar, SectionTitle, WarnList } from './ui';
import { GraphSVG } from './viz';

interface Props {
  result: AnalysisResult;
  onWhatIf: () => void;
  onHood: () => void;
  onEdit: () => void;
  onSave: () => void;
  onExport: () => void;
  onRemember: () => void;
  savedId: string | null;
}

const SEG_COLORS = ['bg-indigo-500', 'bg-emerald-500', 'bg-amber-500', 'bg-sky-500', 'bg-rose-500', 'bg-violet-500', 'bg-teal-500', 'bg-orange-500'];

export default function Results({ result: r, onWhatIf, onHood, onEdit, onSave, onExport, onRemember, savedId }: Props) {
  const [open, setOpen] = useState<Set<number>>(new Set([1]));
  const toggle = (rank: number) =>
    setOpen((s) => {
      const n = new Set(s);
      if (n.has(rank)) n.delete(rank); else n.add(rank);
      return n;
    });

  if (!r.winner) {
    return (
      <div className="space-y-5">
        <h2 className="text-2xl font-bold text-stone-900 dark:text-white">Results</h2>
        <WarnList items={r.warnings} />
        <EmptyState title="No feasible option" sub="Every option violates a hard constraint. Relax a constraint or fix a value, then re-analyze.">
          <Btn onClick={onEdit}>← Edit inputs</Btn>
        </EmptyState>
        {r.eliminated.length > 0 && (
          <Card className="p-5">
            <SectionTitle title="Eliminated" />
            <ul className="space-y-2 text-sm">
              {r.eliminated.map((e) => (
                <li key={e.option_id} className="rounded-xl bg-rose-50 p-3 dark:bg-rose-950/30">
                  <span className="font-semibold text-rose-800 dark:text-rose-200">{e.name}</span>
                  <ul className="mt-1 list-disc pl-5 text-rose-700 dark:text-rose-300">
                    {e.reasons.map((x, i) => <li key={i}>{x}</li>)}
                  </ul>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    );
  }

  const w = r.winner;
  const colorOf = (critId: string) => {
    const i = r.criteria.findIndex((c) => c.id === critId);
    return SEG_COLORS[Math.max(0, i) % SEG_COLORS.length];
  };

  return (
    <div className="space-y-5">
      <div className="anim-fade-up flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-stone-900 dark:text-white">{r.title}</h2>
          <p className="text-sm text-stone-500 dark:text-stone-400">
            {r.ranked.length} feasible · {r.eliminated.length} eliminated · analyzed in {r.timings.total ?? '—'} ms
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Btn variant="soft" onClick={onEdit}>← Edit</Btn>
          <Btn variant="soft" onClick={onHood}>🧠 Under the Hood</Btn>
          <Btn variant="soft" onClick={onSave}>{savedId ? '💾 Saved ✓' : '💾 Save'}</Btn>
          <Btn variant="soft" onClick={onRemember}>🧠 Remember</Btn>
          <Btn variant="soft" onClick={onExport}>⇩ Export</Btn>
          <Btn onClick={onWhatIf}>🔀 What-If mode</Btn>
        </div>
      </div>

      <WarnList items={r.warnings} />

      {/* winner */}
      <Card className="anim-fade-up-1 overflow-hidden">
        <div className="bg-emerald-600 px-5 py-4 text-white dark:bg-emerald-700">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-4xl">🏆</span>
            <div className="min-w-0 flex-1">
              <div className="text-xs font-semibold uppercase tracking-widest opacity-80">Top recommendation</div>
              <div className="truncate text-2xl font-bold">{w.name}</div>
              {w.description && <div className="truncate text-sm opacity-85">{w.description}</div>}
            </div>
            <div className="text-right">
              <div className="tnum text-4xl font-bold">{w.score.toFixed(1)}</div>
              <div className="text-xs opacity-80">/ 100 pts</div>
            </div>
          </div>
        </div>
        <div className="p-5">
          <div className="mb-1.5 flex h-3 w-full gap-0.5 overflow-hidden rounded-full">
            {w.contributions.map((c) => (
              <div key={c.criterion_id} className={colorOf(c.criterion_id)} style={{ width: `${c.points}%` }} title={`${c.criterion}: +${c.points}`} />
            ))}
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-stone-500 dark:text-stone-400">
            {w.contributions.map((c) => (
              <span key={c.criterion_id} className="inline-flex items-center gap-1.5">
                <span className={`h-2.5 w-2.5 rounded-sm ${colorOf(c.criterion_id)}`} />
                {c.criterion} <b className="tnum text-stone-700 dark:text-stone-200">+{c.points}</b>
              </span>
            ))}
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-xl bg-stone-50 p-3 dark:bg-stone-800/60">
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="font-medium text-stone-500 dark:text-stone-400">Decision confidence</span>
                <Badge tone="emerald">{r.confidence?.toFixed(0)}%</Badge>
              </div>
              <ScoreBar value={r.confidence ?? 0} tone="emerald" />
              <p className="mt-1.5 text-xs text-stone-500 dark:text-stone-400">{r.confidence_note}</p>
            </div>
            <div className="rounded-xl bg-stone-50 p-3 text-sm dark:bg-stone-800/60">
              <span className="font-medium text-stone-500 dark:text-stone-400">Closest alternative </span>
              {r.nearest_alternative ? (
                <span className="text-stone-700 dark:text-stone-200">
                  <b>{r.nearest_alternative.name}</b> (Dijkstra distance {r.nearest_alternative.distance}) — your backup if the winner falls through.
                </span>
              ) : (
                <span className="text-stone-500">— only one feasible option.</span>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* ranking */}
      <Card className="anim-fade-up-2 p-5">
        <SectionTitle title="Ranking (max-heap order)" sub="Click a row to see exactly where its points came from." />
        <div className="space-y-2">
          {r.ranked.map((row) => (
            <div key={row.option_id} className="overflow-hidden rounded-xl border border-stone-200 dark:border-stone-800">
              <button onClick={() => toggle(row.rank)} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-stone-50 dark:hover:bg-stone-800/50">
                <RankMedal rank={row.rank} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold text-stone-800 dark:text-stone-100">{row.name}</span>
                  <span className="mt-1 block"><ScoreBar value={row.score} tone={row.rank === 1 ? 'emerald' : 'indigo'} /></span>
                </span>
                <span className="tnum text-lg font-bold text-stone-800 dark:text-stone-100">{row.score.toFixed(1)}</span>
                <span className="text-stone-400">{open.has(row.rank) ? '▾' : '▸'}</span>
              </button>
              {open.has(row.rank) && (
                <div className="border-t border-stone-100 px-4 py-3 dark:border-stone-800">
                  {row.description && <p className="mb-2 text-sm text-stone-500">{row.description}</p>}
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs uppercase tracking-wide text-stone-400">
                        <th className="py-1 font-medium">Criterion</th>
                        <th className="py-1 text-right font-medium">Raw</th>
                        <th className="py-1 text-right font-medium">Norm</th>
                        <th className="py-1 text-right font-medium">Weight</th>
                        <th className="py-1 text-right font-medium">Points</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-100 dark:divide-stone-800">
                      {row.contributions.map((c) => (
                        <tr key={c.criterion_id} className="text-stone-700 dark:text-stone-200">
                          <td className="py-1.5">
                            <span className="inline-flex items-center gap-2">
                              <span className={`h-2.5 w-2.5 rounded-sm ${colorOf(c.criterion_id)}`} />
                              {c.criterion} <span className="text-stone-400">{c.type === 'cost' ? '↓' : '↑'}</span>
                            </span>
                          </td>
                          <td className="tnum py-1.5 text-right">{c.raw}</td>
                          <td className="py-1.5">
                            <span className="ml-auto flex w-24 items-center gap-1.5">
                              <span className="tnum text-xs">{c.norm.toFixed(2)}</span>
                              <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-stone-100 dark:bg-stone-800">
                                <span className="block h-full rounded-full bg-indigo-400" style={{ width: `${c.norm * 100}%` }} />
                              </span>
                            </span>
                          </td>
                          <td className="tnum py-1.5 text-right">{c.weight_pct}%</td>
                          <td className="tnum py-1.5 text-right font-semibold text-indigo-600 dark:text-indigo-400">+{c.points}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>

      {r.eliminated.length > 0 && (
        <Card className="anim-fade-up-2 p-5">
          <SectionTitle title={`Eliminated (${r.eliminated.length})`} sub="Violated a hard constraint." />
          <ul className="space-y-2 text-sm">
            {r.eliminated.map((e) => (
              <li key={e.option_id} className="rounded-xl bg-rose-50 p-3 dark:bg-rose-950/30">
                <span className="font-semibold text-rose-800 dark:text-rose-200">✕ {e.name}</span>
                <ul className="mt-1 list-disc pl-5 text-rose-700 dark:text-rose-300">
                  {e.reasons.map((x, i) => <li key={i}>{x}</li>)}
                </ul>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* graph */}
      <Card className="anim-fade-up-3 p-5">
        <SectionTitle title="Decision graph" sub={`${r.graph.num_vertices} nodes · ${r.graph.num_edges} edges · decision→option cost = 100 − score`} />
        <div className="viz-scroll overflow-x-auto rounded-xl bg-stone-50 p-3 dark:bg-stone-800/40">
          <GraphSVG nodes={r.graph.nodes} edges={r.graph.edges} />
        </div>
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-stone-500">
          <span><span className="inline-block h-2.5 w-2.5 rounded-sm bg-indigo-600" /> decision</span>
          <span><span className="inline-block h-2.5 w-2.5 rounded-sm bg-emerald-600" /> option</span>
          <span><span className="inline-block h-2.5 w-2.5 rounded-sm bg-sky-600" /> criterion</span>
          <span><span className="inline-block h-2.5 w-2.5 rounded-sm bg-amber-500" /> constraint</span>
          <span className="tnum">BFS: {r.graph.bfs.length} visited · DFS: {r.graph.dfs.length} visited</span>
        </div>
      </Card>

      {/* how it worked */}
      <Card className="anim-fade-up-3 p-5">
        <SectionTitle title="How this result was produced" />
        <ol className="space-y-2">
          {r.explanations.map((x, i) => (
            <li key={i} className="flex gap-3 text-sm text-stone-600 dark:text-stone-300">
              <span className="tnum flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">{i + 1}</span>
              <span className="pt-0.5">{x}</span>
            </li>
          ))}
        </ol>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {Object.entries(r.timings).map(([k, v]) => (
            <Badge key={k} tone="stone">{k}: {v} ms</Badge>
          ))}
        </div>
        <p className="mt-4 border-t border-stone-100 pt-3 text-xs italic text-stone-400 dark:border-stone-800">
          ⚖ {r.disclaimer}
        </p>
      </Card>
    </div>
  );
}
