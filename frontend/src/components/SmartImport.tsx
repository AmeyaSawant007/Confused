import { useEffect, useState } from 'react';
import { api } from '../api';
import type { ImportResult } from '../types';
import { Badge, Btn, Card, ScoreBar, SectionTitle, Spinner, WarnList } from './ui';

interface Props {
  criteria: string[];
  onApply: (res: ImportResult) => void;
  onDone?: (res: ImportResult) => void;
}

const toneOf = (s: number) => (s >= 0.7 ? 'emerald' : s >= 0.4 ? 'indigo' : 'amber') as 'emerald' | 'indigo' | 'amber';

export default function SmartImport({ criteria, onApply, onDone }: Props) {
  const [urls, setUrls] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [samples, setSamples] = useState<{ id: string; label: string; url: string }[]>([]);

  useEffect(() => {
    api.importSamplesList().then((s) => setSamples(s.samples)).catch(() => {});
  }, []);

  const run = async (mode: 'urls' | 'samples') => {
    if (!criteria.length) {
      setError('Add criteria first — Smart Import matches page facts to them.');
      return;
    }
    const list = urls.split('\n').map((u) => u.trim()).filter(Boolean);
    if (mode === 'urls' && !list.length) {
      setError('Paste at least one URL.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = mode === 'urls'
        ? await api.importUrls(list, criteria)
        : await api.importSamples(criteria);
      setResult(res);
      onDone?.(res);
    } catch (e: any) {
      setError(e.message || 'Import failed');
    } finally {
      setBusy(false);
    }
  };

  const usable = result?.options.filter((o) => o.filled.length > 0) || [];

  return (
    <Card className="p-5">
      <SectionTitle
        title="Smart Import 🔗"
        sub="Paste product / job links — a neural network reads each page and maps its facts to your criteria."
        right={result && (
          <Badge tone={result.matcher === 'neural' ? 'emerald' : 'amber'}>
            {result.matcher === 'neural' ? `🧠 neural (${result.model})` : '🔤 keyword fallback'}
          </Badge>
        )}
      />
      <div className="mb-2 flex flex-wrap gap-1.5 text-xs">
        <span className="py-1 text-stone-400">matching against:</span>
        {criteria.length === 0 && <span className="py-1 text-stone-400">— no criteria yet —</span>}
        {criteria.map((c) => (
          <span key={c} className="rounded-full bg-indigo-50 px-2.5 py-1 font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">{c}</span>
        ))}
      </div>
      <textarea
        value={urls}
        onChange={(e) => setUrls(e.target.value)}
        rows={2}
        placeholder={"https://shop.example/laptop-a\nhttps://shop.example/laptop-b"}
        className="w-full rounded-xl border border-stone-200 bg-white px-3 py-2 font-mono text-xs text-stone-900 outline-none transition placeholder:text-stone-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 dark:border-stone-700 dark:bg-stone-800/60 dark:text-stone-100 dark:focus:ring-indigo-950"
      />
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Btn onClick={() => run('urls')} disabled={busy}>
          {busy ? <Spinner label="Reading pages…" /> : '🔗 Import from links'}
        </Btn>
        <Btn variant="soft" onClick={() => run('samples')} disabled={busy}>
          Try offline samples{samples.length ? ` (${samples.length})` : ''}
        </Btn>
      </div>
      {error && (
        <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">
          {error}
        </div>
      )}
      {result && (
        <div className="mt-4 space-y-3">
          <WarnList items={result.warnings} />
          {result.options.map((o, i) => (
            <div key={i} className={`rounded-xl border p-3 ${o.filled.length ? 'border-stone-200 dark:border-stone-800' : 'border-dashed opacity-60'}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-stone-800 dark:text-stone-100">{o.name}</div>
                  <div className="truncate font-mono text-[11px] text-stone-400">{o.url}</div>
                </div>
                <div className="flex gap-1.5">
                  <Badge tone="emerald">{o.filled.length} filled</Badge>
                  {o.missing.length > 0 && <Badge tone="amber">{o.missing.length} missing</Badge>}
                </div>
              </div>
              {o.sources.length > 0 && (
                <div className="mt-2 space-y-1.5">
                  {o.sources.map((s, j) => (
                    <div key={j} className="text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-stone-600 dark:text-stone-300">
                          <b className="text-stone-800 dark:text-stone-100">{s.criterion}</b>
                          {' ← “'}{s.phrase}”{' '}
                          <span className="tnum font-semibold text-indigo-600 dark:text-indigo-400">{s.score.toFixed(2)}</span>
                        </span>
                        <span className="tnum shrink-0 font-bold text-stone-800 dark:text-stone-100">= {o.scores[s.criterion]}</span>
                      </div>
                      <ScoreBar value={s.score * 100} tone={toneOf(s.score)} height="h-1.5" />
                    </div>
                  ))}
                </div>
              )}
              {o.missing.length > 0 && (
                <p className="mt-2 text-xs text-stone-400">missing (will default to 0 — edit after applying): {o.missing.join(', ')}</p>
              )}
            </div>
          ))}
          <Btn onClick={() => onApply(result)} disabled={!usable.length} className="w-full sm:w-auto">
            Apply {usable.length} option{usable.length === 1 ? '' : 's'} to decision →
          </Btn>
        </div>
      )}
    </Card>
  );
}
