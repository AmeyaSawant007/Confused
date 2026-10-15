import { useState } from 'react';
import { api } from '../api';
import type { Decision, DuelPair, LearnResult } from '../types';
import { Badge, Btn, Card, ScoreBar, SectionTitle, Spinner, WarnList } from './ui';

interface Props {
  decision: Decision;
  onApply: (weights: Record<string, number>) => void;
  onDone?: (res: LearnResult) => void;
}

interface Answer {
  a: string;
  b: string;
  winner: string;
}

export function LossCurve({ losses, height = 72 }: { losses: number[]; height?: number }) {
  if (!losses.length) return null;
  const w = 260;
  const min = Math.min(...losses);
  const max = Math.max(...losses);
  const span = max - min || 1;
  const pts = losses.map((l, i) => {
    const x = (i / Math.max(1, losses.length - 1)) * (w - 8) + 4;
    const y = height - 6 - ((l - min) / span) * (height - 14);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full rounded-lg bg-white dark:bg-stone-900">
      <polyline points={pts.join(' ')} fill="none" stroke="#10b981" strokeWidth="2" strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1].split(',')[0]} cy={pts[pts.length - 1].split(',')[1]} r="3" fill="#10b981" />
    </svg>
  );
}

export default function SmartWeights({ decision, onApply, onDone }: Props) {
  const [pairs, setPairs] = useState<DuelPair[] | null>(null);
  const [criteria, setCriteria] = useState<string[]>([]);
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState<Answer[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LearnResult | null>(null);
  const [duelWarnings, setDuelWarnings] = useState<string[]>([]);

  const start = async () => {
    if (decision.options.length < 3) {
      setError('Add at least 3 options first — duels need a field to choose from.');
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const d = await api.duels(decision, 6);
      setPairs(d.pairs);
      setCriteria(d.criteria);
      setDuelWarnings(d.warnings);
      setIdx(0);
      setAnswers([]);
    } catch (e: any) {
      setError(e.message || 'Could not start duels');
    } finally {
      setBusy(false);
    }
  };

  const pick = (side: 'a' | 'b') => {
    if (!pairs) return;
    const pair = pairs[idx];
    const winner = side === 'a' ? pair.a.id : pair.b.id;
    const next = [...answers, { a: pair.a.id, b: pair.b.id, winner }];
    setAnswers(next);
    if (idx + 1 < pairs.length) {
      setIdx(idx + 1);
    } else {
      train(next);
    }
  };

  const train = async (ans: Answer[]) => {
    setBusy(true);
    setError(null);
    try {
      const res = await api.learn(decision, ans);
      setResult(res);
      onDone?.(res);
    } catch (e: any) {
      setError(e.message || 'Training failed');
    } finally {
      setBusy(false);
    }
  };

  const scoresOf = (name: string): Record<string, number> => {
    const o = decision.options.find((x) => x.name === name);
    return o ? o.scores : {};
  };

  const pair = pairs?.[idx];
  const done = pairs !== null && idx >= pairs.length - 1 && answers.length >= pairs.length;

  return (
    <Card className="p-5">
      <SectionTitle
        title="Smart Weights ⚔️"
        sub="Can't put weights into words? Duel your options — logistic regression learns what you value."
        right={
          result ? (
            <span className="flex gap-1.5">
              <Badge tone="emerald">train {(result.train_acc * 100).toFixed(0)}%</Badge>
              <Badge tone="sky">LOO {(result.loo_acc * 100).toFixed(0)}%</Badge>
            </span>
          ) : pairs ? (
            <Badge tone="indigo">duel {Math.min(idx + 1, pairs.length)} / {pairs.length}</Badge>
          ) : undefined
        }
      />

      {!pairs && !result && (
        <div className="flex flex-wrap items-center gap-2">
          <Btn onClick={start} disabled={busy}>
            {busy ? <Spinner label="Picking duels…" /> : '⚔️ Start dueling'}
          </Btn>
          <span className="text-xs text-stone-400">~6 head-to-head picks · closest races first</span>
        </div>
      )}

      {error && (
        <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">
          {error}
        </div>
      )}

      {pairs && pair && !done && !result && (
        <div className="anim-fade-up">
          <WarnList items={duelWarnings} />
          <p className="mb-2 mt-1 text-center text-sm text-stone-500">
            Which would you actually pick? <Badge tone="amber">margin {pair.margin} pts — close race</Badge>
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {(['a', 'b'] as const).map((side) => {
              const opt = side === 'a' ? pair.a : pair.b;
              const scores = scoresOf(opt.name);
              return (
                <button
                  key={side}
                  onClick={() => pick(side)}
                  className="group rounded-2xl border-2 border-stone-200 bg-white p-4 text-left transition hover:-translate-y-0.5 hover:border-emerald-400 hover:shadow-lg dark:border-stone-700 dark:bg-stone-900 dark:hover:border-emerald-600"
                >
                  <div className="text-base font-bold text-stone-900 group-hover:text-emerald-700 dark:text-white dark:group-hover:text-emerald-300">
                    {opt.name}
                  </div>
                  <div className="mt-2 space-y-1.5">
                    {criteria.map((c) => (
                      <div key={c} className="flex items-center gap-2 text-xs">
                        <span className="w-24 shrink-0 truncate text-stone-500">{c}</span>
                        <span className="tnum w-14 shrink-0 text-right font-semibold text-stone-700 dark:text-stone-200">
                          {scores[c] ?? '—'}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 text-center text-sm font-semibold text-emerald-600 opacity-0 transition group-hover:opacity-100">
                    Pick {opt.name} →
                  </div>
                </button>
              );
            })}
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-stone-400">
            <span>{answers.length} answered · you can stop any time after 2</span>
            {answers.length >= 2 && (
              <Btn variant="soft" onClick={() => train(answers)} disabled={busy} className="!px-3 !py-1.5 !text-xs">
                {busy ? <Spinner label="Training…" /> : `Train on ${answers.length} duels →`}
              </Btn>
            )}
          </div>
        </div>
      )}

      {busy && pairs && !result && done && (
        <div className="py-6 text-center"><Spinner label="Training logistic regression…" /></div>
      )}

      {result && (
        <div className="anim-fade-up space-y-3">
          <WarnList items={result.warnings} />
          {result.uniform_fallback && (
            <div className="rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900 dark:border-sky-900 dark:bg-sky-950/40 dark:text-sky-200">
              Your picks were perfectly balanced, so every criterion matters equally — uniform weights returned.
            </div>
          )}
          <div className="grid gap-3 md:grid-cols-[1fr_260px]">
            <div className="space-y-2">
              {Object.entries(result.weights).map(([k, v]) => (
                <div key={k}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-stone-700 dark:text-stone-200">{k}</span>
                    <span className="tnum font-bold text-stone-900 dark:text-white">
                      {v}% <span className="font-normal text-stone-400">(β {result.coefficients[k]?.toFixed(2)})</span>
                    </span>
                  </div>
                  <ScoreBar value={v} tone="emerald" />
                </div>
              ))}
            </div>
            <div>
              <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-stone-500">Loss curve</div>
              <LossCurve losses={result.loss_curve} />
              <p className="tnum mt-1 text-[11px] text-stone-400">
                {result.loss_curve[0]?.toFixed(3)} → {result.loss_curve[result.loss_curve.length - 1]?.toFixed(3)}
              </p>
            </div>
          </div>
          <p className="text-xs text-stone-500">
            {result.method} · {result.n_samples} duels · {result.n_criteria} criteria ·
            train {(result.train_acc * 100).toFixed(0)}% · leave-one-out {(result.loo_acc * 100).toFixed(0)}%
          </p>
          <p className="font-mono text-[11px] leading-relaxed text-stone-400">{result.method_detail}</p>
          <div className="flex flex-wrap gap-2">
            <Btn variant="success" onClick={() => onApply(result.weights)}>
              ✨ Apply learned weights
            </Btn>
            <Btn variant="soft" onClick={() => { setPairs(null); setResult(null); setAnswers([]); }}>
              Duel again
            </Btn>
          </div>
        </div>
      )}
    </Card>
  );
}
