import { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import type { Category, SavedDecision, SearchHit, TemplateMeta } from '../types';
import { Badge, Btn, Card, EmptyState, SectionTitle, Spinner } from './ui';

interface Props {
  onNew: (categoryId?: string) => void;
  onTemplate: (id: string) => void;
  onSaved: (id: string) => void;
  onSearchHit: (hit: SearchHit) => void;
  onImport: () => void;
  refreshKey: number;
}

export default function Dashboard({ onNew, onTemplate, onSaved, onSearchHit, onImport, refreshKey }: Props) {
  const [cats, setCats] = useState<Category[]>([]);
  const [templates, setTemplates] = useState<TemplateMeta[]>([]);
  const [recent, setRecent] = useState<SavedDecision[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [searching, setSearching] = useState(false);
  const [showHits, setShowHits] = useState(false);
  const timer = useRef<any>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [c, t, r] = await Promise.all([api.categories(), api.templates(), api.decisions()]);
        setCats(c.categories);
        setTemplates(t.templates);
        setRecent(r.decisions);
      } catch {
        /* API down — page still renders */
      } finally {
        setLoading(false);
      }
    })();
  }, [refreshKey]);

  const onQuery = (v: string) => {
    setQ(v);
    setShowHits(true);
    clearTimeout(timer.current);
    if (!v.trim()) { setHits([]); setSearching(false); return; }
    setSearching(true);
    timer.current = setTimeout(async () => {
      try {
        const r = await api.search(v.trim());
        setHits(r.results);
      } catch {
        setHits([]);
      } finally {
        setSearching(false);
      }
    }, 160);
  };

  const remove = async (id: string) => {
    if (!confirm('Delete this saved decision?')) return;
    await api.deleteDecision(id);
    setRecent((rs) => rs.filter((r) => r.id !== id));
  };

  return (
    <div className="space-y-8">
      {/* hero */}
      <div className="anim-fade-up pt-4 text-center">
        <div className="mx-auto inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600 text-3xl shadow-lg shadow-indigo-600/25">
          <span className="text-white">?</span>
        </div>
        <h1 className="mt-4 text-4xl font-bold tracking-tight text-stone-900 dark:text-white sm:text-5xl">
          Confused?
        </h1>
        <p className="mx-auto mt-2 max-w-xl text-stone-500 dark:text-stone-400">
          What are you trying to decide? List your options, weigh your criteria,
          and let graphs, heaps and segment trees rank them — transparently.
        </p>
        <div className="relative mx-auto mt-6 max-w-xl">
          <input
            value={q}
            onChange={(e) => onQuery(e.target.value)}
            onFocus={() => setShowHits(true)}
            onBlur={() => setTimeout(() => setShowHits(false), 150)}
            placeholder='Try "lap…" — instant trie search over decisions'
            className="w-full rounded-2xl border border-stone-200 bg-white px-5 py-3.5 text-[15px] shadow-sm outline-none transition placeholder:text-stone-400 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100 dark:focus:ring-indigo-950"
          />
          {showHits && q.trim() && (
            <div className="absolute z-20 mt-2 w-full overflow-hidden rounded-2xl border border-stone-200 bg-white text-left shadow-xl dark:border-stone-700 dark:bg-stone-900">
              {searching ? (
                <div className="px-4 py-3"><Spinner label="Searching trie…" /></div>
              ) : hits.length === 0 ? (
                <div className="px-4 py-3 text-sm text-stone-500">No prefix matches. Press “Start” below to create it.</div>
              ) : (
                hits.map((h, i) => (
                  <button key={i} onClick={() => onSearchHit(h)}
                    className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-stone-50 dark:hover:bg-stone-800">
                    <span className="text-lg">{h.kind === 'category' ? '🏷️' : h.kind === 'template' ? '📦' : '💾'}</span>
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-stone-800 dark:text-stone-100">{h.label}</span>
                      <span className="block text-xs text-stone-400">{h.kind} · {h.match}</span>
                    </span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <Btn onClick={() => onNew()}>＋ Start a Decision</Btn>
          <Btn variant="soft" onClick={() => onTemplate('laptop')}>Run the laptop demo →</Btn>
          <Btn variant="soft" onClick={onImport}>🔗 Import from links</Btn>
        </div>
      </div>

      {loading ? (
        <div className="py-10 text-center"><Spinner label="Loading…" /></div>
      ) : (
        <>
          {/* categories */}
          <div className="anim-fade-up-1">
            <SectionTitle title="Start from a category" sub="Each one suggests sensible criteria — everything stays editable." />
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {cats.map((c) => (
                <button key={c.id} onClick={() => onNew(c.id)}
                  className="group rounded-2xl border border-stone-200 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-md dark:border-stone-800 dark:bg-stone-900 dark:hover:border-indigo-700">
                  <div className="text-2xl">{c.icon}</div>
                  <div className="mt-2 text-sm font-semibold text-stone-800 dark:text-stone-100">{c.label}</div>
                  <div className="mt-0.5 text-xs leading-snug text-stone-500 dark:text-stone-400">{c.blurb}</div>
                </button>
              ))}
            </div>
          </div>

          {/* templates */}
          <div className="anim-fade-up-2">
            <SectionTitle title="Ready-made demos" sub="One click loads a full decision — perfect for a live demo or viva." />
            <div className="grid gap-3 sm:grid-cols-2">
              {templates.map((t) => (
                <Card key={t.id} className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-stone-800 dark:text-stone-100">{t.title}</div>
                      <div className="mt-1.5 flex gap-1.5">
                        <Badge>{t.options} options</Badge>
                        <Badge tone="indigo">{t.criteria} criteria</Badge>
                        <Badge tone="stone">{t.category}</Badge>
                      </div>
                    </div>
                    <Btn variant="soft" onClick={() => onTemplate(t.id)}>Open</Btn>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          {/* recent */}
          <div className="anim-fade-up-3">
            <SectionTitle title="Recent decisions" sub="Saved in the local database." />
            {recent.length === 0 ? (
              <EmptyState title="Nothing saved yet" sub="Analyze a decision and hit Save — it will show up here." />
            ) : (
              <div className="divide-y divide-stone-100 overflow-hidden rounded-2xl border border-stone-200 bg-white dark:divide-stone-800 dark:border-stone-800 dark:bg-stone-900">
                {recent.map((r) => (
                  <div key={r.id} className="flex items-center justify-between gap-3 px-4 py-3">
                    <button onClick={() => onSaved(r.id)} className="min-w-0 text-left">
                      <div className="truncate font-medium text-stone-800 hover:text-indigo-600 dark:text-stone-100 dark:hover:text-indigo-400">{r.title}</div>
                      <div className="text-xs text-stone-400">{r.options} options · {new Date(r.updated_at).toLocaleString()}</div>
                    </button>
                    <div className="flex shrink-0 gap-1">
                      <Btn variant="ghost" onClick={() => onSaved(r.id)}>Open</Btn>
                      <Btn variant="ghost" onClick={() => remove(r.id)} aria-label="Delete">🗑</Btn>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
