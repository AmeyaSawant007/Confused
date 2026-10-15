import { useEffect, useState } from 'react';
import { api } from './api';
import Builder from './components/Builder';
import Dashboard from './components/Dashboard';
import Hood from './components/Hood';
import Results from './components/Results';
import WhatIf from './components/WhatIf';
import { Btn, EmptyState } from './components/ui';
import type {
  AnalysisResult, Category, Decision, ImportResult, LearnResult, SearchHit,
} from './types';

type View = 'dashboard' | 'builder' | 'results' | 'whatif' | 'hood';

const VIEWS: { id: View; label: string; icon: string }[] = [
  { id: 'dashboard', label: 'Home', icon: '🏠' },
  { id: 'builder', label: 'Builder', icon: '🛠' },
  { id: 'results', label: 'Results', icon: '🏆' },
  { id: 'whatif', label: 'What-If', icon: '🔀' },
  { id: 'hood', label: 'Under the Hood', icon: '🧠' },
];

const DRAFT_KEY = 'confused:draft';

function normalizeScores(d: Decision): Decision {
  const names = d.criteria.map((c) => c.name);
  return {
    ...d,
    options: d.options.map((o) => {
      const scores: Record<string, number> = {};
      names.forEach((n) => { scores[n] = o.scores?.[n] ?? 0; });
      return { ...o, scores };
    }),
  };
}

function blankDecision(cat: Category | undefined, catId?: string): Decision {
  const suggested = cat?.suggested_criteria?.length
    ? cat.suggested_criteria
    : [{ name: 'Criterion 1', type: 'benefit' as const }, { name: 'Criterion 2', type: 'benefit' as const }];
  const criteria = suggested.map((s, i) => ({
    name: s.name,
    type: s.type as 'benefit' | 'cost',
    weight: Math.round(100 / suggested.length),
  }));
  const options = ['Option A', 'Option B', 'Option C'].map((name) => ({
    name,
    description: '',
    scores: Object.fromEntries(criteria.map((c) => [c.name, 0])),
  }));
  void catId;
  return {
    title: cat ? `Which ${cat.label.toLowerCase()}?` : 'My decision',
    category: cat?.id || 'custom',
    criteria, options, constraints: [],
  };
}

function loadDraft(): Decision | null {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (raw) return normalizeScores(JSON.parse(raw));
  } catch {
    /* ignore */
  }
  return null;
}

export default function App() {
  const [view, setView] = useState<View>('dashboard');
  const [decision, setDecision] = useState<Decision>(() => loadDraft() || blankDecision(undefined));
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [history, setHistory] = useState<{ depth: number; labels_top_first: string[] } | null>(null);
  const [lastImport, setLastImport] = useState<ImportResult | null>(null);
  const [lastLearn, setLastLearn] = useState<LearnResult | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const notify = (msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 3600);
  };

  useEffect(() => {
    api.categories().then((r) => setCategories(r.categories)).catch(() => {});
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(decision));
    } catch {
      /* ignore */
    }
  }, [decision]);

  const refreshHistory = async (id: string) => {
    try {
      setHistory(await api.history(id));
    } catch {
      setHistory(null);
    }
  };

  const update = (fn: (d: Decision) => Decision) => {
    setDecision((prev) => normalizeScores(fn(prev)));
    setResult(null);
    setError(null);
  };

  const analyze = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const r = await api.analyze(decision);
      setResult(r);
      setView('results');
    } catch (e: any) {
      setError(e.message || 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const save = async () => {
    setBusy(true);
    try {
      if (savedId) {
        await api.updateDecision(savedId, decision);
        notify('Saved ✓');
      } else {
        const r = await api.createDecision(decision);
        setSavedId(r.id);
        notify('Saved ✓');
      }
      setRefreshKey((k) => k + 1);
    } catch (e: any) {
      notify(e.message || 'Save failed');
    } finally {
      setBusy(false);
    }
  };

  const checkpoint = async (label: string) => {
    if (!savedId) return;
    setBusy(true);
    try {
      const r = await api.checkpoint(savedId, label, decision);
      setHistory(r.history);
      notify(`Version "${label}" saved`);
    } catch (e: any) {
      notify(e.message || 'Checkpoint failed');
    } finally {
      setBusy(false);
    }
  };

  const undo = async () => {
    if (!savedId) return;
    setBusy(true);
    try {
      const r = await api.undo(savedId);
      setDecision(normalizeScores(r.restored));
      setHistory(r.history);
      setResult(null);
      notify(`Undid "${r.undone}"`);
    } catch (e: any) {
      notify(e.message || 'Nothing to undo');
    } finally {
      setBusy(false);
    }
  };

  const onNew = (catId?: string) => {
    const cat = categories.find((c) => c.id === catId);
    setDecision(blankDecision(cat, catId));
    setSavedId(null);
    setHistory(null);
    setResult(null);
    setError(null);
    setView('builder');
  };

  const onTemplate = async (id: string) => {
    setBusy(true);
    try {
      const d = await api.template(id);
      setDecision(normalizeScores(d));
      setSavedId(null);
      setHistory(null);
      setResult(null);
      setError(null);
      setView('builder');
      notify('Template loaded — hit Analyze ⚡');
    } catch (e: any) {
      notify(e.message || 'Template failed');
    } finally {
      setBusy(false);
    }
  };

  const onSaved = async (id: string) => {
    setBusy(true);
    try {
      const d = await api.getDecision(id);
      setDecision(normalizeScores(d));
      setSavedId(id);
      setResult(null);
      setError(null);
      refreshHistory(id);
      setView('builder');
    } catch (e: any) {
      notify(e.message || 'Load failed');
    } finally {
      setBusy(false);
    }
  };

  const onSearchHit = (hit: SearchHit) => {
    if (hit.kind === 'decision') onSaved(hit.id);
    else if (hit.kind === 'template') onTemplate(hit.id);
    else onNew(hit.id);
  };

  const onExport = () => {
    const blob = new Blob([JSON.stringify({ decision, result }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${decision.title || 'decision'}.json`;
    a.click();
    URL.revokeObjectURL(url);
    notify('Exported JSON ⇩');
  };

  const onRemember = async () => {
    try {
      await api.saveProfile(
        decision.category,
        Object.fromEntries(decision.criteria.map((c) => [c.name, c.weight])),
        decision.criteria.map((c) => ({ name: c.name, type: c.type }))
      );
      notify(`I'll remember your ${decision.category} weights 🧠`);
    } catch (e: any) {
      notify(e.message || 'Remember failed');
    }
  };

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-stone-200/80 bg-white/80 backdrop-blur dark:border-stone-800 dark:bg-stone-950/80">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-3 sm:gap-3">
          <button onClick={() => setView('dashboard')} className="mr-auto flex items-center gap-2.5">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-indigo-600 text-lg font-bold text-white shadow-lg shadow-indigo-500/25">
              ?
            </div>
            <div className="text-left">
              <div className="text-[17px] font-bold leading-tight text-stone-900 dark:text-white">
                Confused?
              </div>
              <div className="text-[11px] leading-tight text-stone-500">
                decide with data structures
              </div>
            </div>
          </button>
          <nav className="flex flex-wrap gap-1.5">
            {VIEWS.map((t) => (
              <button
                key={t.id}
                onClick={() => setView(t.id)}
                className={`rounded-full px-3.5 py-1.5 text-[13px] font-medium transition ${
                  view === t.id
                    ? 'bg-stone-900 text-white shadow dark:bg-white dark:text-stone-900'
                    : 'text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-800'
                }`}
              >
                {t.icon} {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-24 pt-6">
        {view === 'dashboard' && (
          <Dashboard
            onNew={onNew}
            onTemplate={onTemplate}
            onSaved={onSaved}
            onSearchHit={onSearchHit}
            onImport={() => onNew()}
            refreshKey={refreshKey}
          />
        )}
        {view === 'builder' && (
          <Builder
            decision={decision}
            update={update}
            onAnalyze={analyze}
            analyzing={analyzing}
            error={error}
            savedId={savedId}
            history={history}
            onSave={save}
            onCheckpoint={checkpoint}
            onUndo={undo}
            busy={busy}
            categories={categories}
            onImportDone={setLastImport}
            onLearnDone={setLastLearn}
            onNotify={notify}
          />
        )}
        {view === 'results' && (
          result ? (
            <Results
              result={result}
              onWhatIf={() => setView('whatif')}
              onHood={() => setView('hood')}
              onEdit={() => setView('builder')}
              onSave={save}
              onExport={onExport}
              onRemember={onRemember}
              savedId={savedId}
            />
          ) : (
            <EmptyState title="No results yet" sub="Build a decision, then analyze it.">
              <Btn onClick={() => setView('builder')}>Open Builder →</Btn>
            </EmptyState>
          )
        )}
        {view === 'whatif' && (
          <WhatIf
            baseline={decision}
            onBack={() => setView(result ? 'results' : 'builder')}
            onApply={(d) => {
              setDecision(normalizeScores(d));
              setResult(null);
              setView('builder');
              notify('What-if applied to builder');
            }}
            onWhatIfDone={() => {}}
          />
        )}
        {view === 'hood' && <Hood lastImport={lastImport} lastLearn={lastLearn} />}
      </main>

      {toast && (
        <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 anim-fade-up">
          <div className="flex items-center gap-2 rounded-full bg-stone-900 px-4 py-2.5 text-sm font-medium text-white shadow-xl dark:bg-white dark:text-stone-900">
            {toast}
          </div>
        </div>
      )}

      <footer className="border-t border-stone-200 py-8 text-center dark:border-stone-800">
        <p className="text-sm text-stone-500">
          Confused? — a decision engine built on heaps, tries, graphs & dynamic programming.
        </p>
        <Btn variant="ghost" className="mt-2 !text-xs" onClick={() => setView('hood')}>
          🧠 See what's under the hood
        </Btn>
      </footer>
    </div>
  );
}
