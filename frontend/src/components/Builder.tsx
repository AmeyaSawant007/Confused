import { useEffect, useState } from 'react';
import { api } from '../api';
import type { Category, Decision, ImportResult, LearnResult, WeightProfile } from '../types';
import SmartImport from './SmartImport';
import SmartWeights from './SmartWeights';
import { Badge, Btn, Card, Field, NumInput, ScoreBar, SectionTitle, Select, Spinner, TextInput } from './ui';

interface Props {
  decision: Decision;
  update: (fn: (d: Decision) => Decision) => void;
  onAnalyze: () => void;
  analyzing: boolean;
  error: string | null;
  savedId: string | null;
  history: { depth: number; labels_top_first: string[] } | null;
  onSave: () => void;
  onCheckpoint: (label: string) => void;
  onUndo: () => void;
  busy: boolean;
  categories: Category[];
  onImportDone: (res: ImportResult) => void;
  onLearnDone: (res: LearnResult) => void;
  onNotify: (msg: string) => void;
}

const OPERATORS = ['<=', '<', '>=', '>', '==', '!='];

export default function Builder(p: Props) {
  const { decision: d, update } = p;
  const [cpLabel, setCpLabel] = useState('');
  const [profile, setProfile] = useState<WeightProfile | null>(null);
  const [profileDismissed, setProfileDismissed] = useState(false);
  const total = d.criteria.reduce((s, c) => s + (Number(c.weight) || 0), 0);

  useEffect(() => {
    setProfileDismissed(false);
    api.getProfile(d.category).then(setProfile).catch(() => setProfile(null));
  }, [d.category]);

  const applyProfile = () => {
    if (!profile) return;
    let applied = 0;
    update((dd) => ({
      ...dd,
      criteria: dd.criteria.map((c) => {
        const w = profile.weights[c.name];
        if (w === undefined) return c;
        applied += 1;
        return { ...c, weight: w };
      }),
    }));
    setProfileDismissed(true);
    p.onNotify(applied ? `Applied your usual ${d.category} weights (${applied} matched) 🧠` : 'No criteria names matched your profile');
  };

  const forgetProfile = async () => {
    try {
      await api.deleteProfile(d.category);
      setProfile(null);
      p.onNotify('Profile forgotten');
    } catch (e: any) {
      p.onNotify(e.message);
    }
  };

  const applyImport = (res: ImportResult) => {
    const usable = res.options.filter((o) => o.filled.length > 0);
    if (!usable.length) {
      p.onNotify('No page facts matched your criteria — nothing applied');
      return;
    }
    update((dd) => {
      const options = [...dd.options];
      usable.forEach((imp) => {
        const idx = options.findIndex((o) => o.name.toLowerCase() === imp.name.toLowerCase());
        if (idx >= 0) {
          const merged = { ...options[idx].scores };
          imp.filled.forEach((f) => { merged[f] = imp.scores[f]; });
          options[idx] = { ...options[idx], scores: merged };
        } else {
          const scores: Record<string, number> = {};
          dd.criteria.forEach((c) => { scores[c.name] = imp.scores[c.name] ?? 0; });
          options.push({ name: imp.name, description: `Imported from ${imp.url}`, scores });
        }
      });
      return { ...dd, options };
    });
    const missing = usable.reduce((n, o) => n + o.missing.length, 0);
    p.onNotify(missing
      ? `Imported ${usable.length} options — fill ${missing} missing values below`
      : `Imported ${usable.length} options ✓`);
  };

  const applyLearned = (weights: Record<string, number>) => {
    update((dd) => ({
      ...dd,
      criteria: dd.criteria.map((c) =>
        weights[c.name] !== undefined ? { ...c, weight: weights[c.name] } : c),
    }));
    p.onNotify('Learned weights applied — analyze to see the effect ✨');
  };

  const setCrit = (i: number, patch: Partial<{ name: string; weight: number; type: 'benefit' | 'cost' }>) => {
    update((dd) => {
      const crits = dd.criteria.map((c, j) => (j === i ? { ...c, ...patch } : c));
      let options = dd.options;
      let constraints = dd.constraints;
      if (patch.name !== undefined && patch.name !== dd.criteria[i].name) {
        const oldN = dd.criteria[i].name, newN = patch.name;
        options = dd.options.map((o) => {
          const scores: Record<string, number> = {};
          for (const [k, v] of Object.entries(o.scores)) scores[k === oldN ? newN : k] = v;
          return { ...o, scores };
        });
        constraints = dd.constraints.map((k) => (k.target === oldN ? { ...k, target: newN } : k));
      }
      return { ...dd, criteria: crits, options, constraints };
    });
  };

  const addCrit = () =>
    update((dd) => {
      const name = `Criterion ${dd.criteria.length + 1}`;
      return {
        ...dd,
        criteria: [...dd.criteria, { name, weight: 10, type: 'benefit' as const }],
        options: dd.options.map((o) => ({ ...o, scores: { ...o.scores, [name]: 0 } })),
      };
    });

  const delCrit = (i: number) =>
    update((dd) => {
      const name = dd.criteria[i].name;
      return {
        ...dd,
        criteria: dd.criteria.filter((_, j) => j !== i),
        options: dd.options.map((o) => {
          const scores = { ...o.scores };
          delete scores[name];
          return { ...o, scores };
        }),
        constraints: dd.constraints.filter((k) => k.target !== name),
      };
    });

  const normalize = () =>
    update((dd) => {
      const s = dd.criteria.reduce((x, c) => x + (Number(c.weight) || 0), 0);
      if (s <= 0) return dd;
      const crits = dd.criteria.map((c) => ({ ...c, weight: Math.round(((Number(c.weight) || 0) / s) * 10000) / 100 }));
      const drift = 100 - crits.reduce((x, c) => x + c.weight, 0);
      if (crits.length) crits[0].weight = Math.round((crits[0].weight + drift) * 100) / 100;
      return { ...dd, criteria: crits };
    });

  const setOpt = (i: number, patch: Partial<{ name: string; description: string }>) =>
    update((dd) => ({ ...dd, options: dd.options.map((o, j) => (j === i ? { ...o, ...patch } : o)) }));

  const setScore = (i: number, critName: string, v: number) =>
    update((dd) => ({
      ...dd,
      options: dd.options.map((o, j) => (j === i ? { ...o, scores: { ...o.scores, [critName]: v } } : o)),
    }));

  const addOpt = () =>
    update((dd) => {
      const scores: Record<string, number> = {};
      dd.criteria.forEach((c) => (scores[c.name] = 0));
      const letter = String.fromCharCode(65 + dd.options.length);
      return { ...dd, options: [...dd.options, { name: `Option ${letter}`, description: '', scores }] };
    });

  const delOpt = (i: number) =>
    update((dd) => ({ ...dd, options: dd.options.filter((_, j) => j !== i) }));

  const setCon = (i: number, patch: any) =>
    update((dd) => ({ ...dd, constraints: dd.constraints.map((k, j) => (j === i ? { ...k, ...patch } : k)) }));

  const addCon = () =>
    update((dd) => ({
      ...dd,
      constraints: [...dd.constraints, {
        name: '', target: dd.criteria[0]?.name || '', operator: '<=',
        value: 0, hard: true, enabled: true,
      }],
    }));

  const delCon = (i: number) =>
    update((dd) => ({ ...dd, constraints: dd.constraints.filter((_, j) => j !== i) }));

  return (
    <div className="space-y-5">
      <div className="anim-fade-up">
        <h2 className="text-2xl font-bold text-stone-900 dark:text-white">Decision Builder</h2>
        <p className="text-sm text-stone-500 dark:text-stone-400">
          Describe the problem once — values can use natural units (₹, hours, kg, ratings). Min-max normalization handles mixed scales.
        </p>
      </div>

      {p.error && (
        <div className="anim-fade-up rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200">
          <span className="font-semibold">Cannot analyze: </span>{p.error}
        </div>
      )}

      {profile && !profileDismissed && (
        <div className="anim-fade-up flex flex-wrap items-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50 p-3 text-sm dark:border-indigo-900 dark:bg-indigo-950/40">
          <span>🧠</span>
          <span className="text-stone-700 dark:text-stone-200">
            Your usual <b>{d.category}</b> weights: {Object.entries(profile.weights).map(([k, v]) => `${k} ${v}`).join(' · ')}
          </span>
          <span className="flex gap-1.5">
            <Btn variant="primary" onClick={applyProfile} className="!px-3 !py-1 !text-xs">Apply</Btn>
            <Btn variant="ghost" onClick={forgetProfile} className="!px-2 !py-1 !text-xs">Forget</Btn>
            <Btn variant="ghost" onClick={() => setProfileDismissed(true)} className="!px-2 !py-1 !text-xs">✕</Btn>
          </span>
        </div>
      )}

      {/* question */}
      <Card className="anim-fade-up-1 p-5">
        <div className="grid gap-4 sm:grid-cols-[1fr_220px]">
          <Field label="What are you deciding?">
            <TextInput value={d.title} onChange={(e) => update((dd) => ({ ...dd, title: e.target.value }))}
              placeholder="e.g. Which laptop should I buy?" />
          </Field>
          <Field label="Category">
            <Select value={d.category} onChange={(e) => update((dd) => ({ ...dd, category: e.target.value }))}>
              {p.categories.map((c) => <option key={c.id} value={c.id}>{c.icon} {c.label}</option>)}
              {p.categories.length === 0 && <option value="custom">✨ Custom</option>}
            </Select>
          </Field>
        </div>
      </Card>

      {/* criteria */}
      <Card className="anim-fade-up-1 p-5">
        <SectionTitle title={`Criteria (${d.criteria.length})`}
          sub="Benefit ↑ higher is better · Cost ↓ lower is better"
          right={<Btn variant="soft" onClick={addCrit}>＋ Add</Btn>} />
        <div className="space-y-2.5">
          {d.criteria.map((c, i) => (
            <div key={i} className="grid items-center gap-2 rounded-xl bg-stone-50 p-2.5 dark:bg-stone-800/50 sm:grid-cols-[1fr_130px_90px_110px_36px]">
              <TextInput value={c.name} onChange={(e) => setCrit(i, { name: e.target.value })} placeholder="Criterion name" />
              <Select value={c.type} onChange={(e) => setCrit(i, { type: e.target.value as any })}>
                <option value="benefit">↑ Benefit</option>
                <option value="cost">↓ Cost</option>
              </Select>
              <div className="flex items-center gap-1">
                <NumInput value={c.weight} onChange={(e) => setCrit(i, { weight: Number(e.target.value) })} />
                <span className="text-xs text-stone-400">%</span>
              </div>
              <input type="range" min={0} max={100} step={1} value={c.weight}
                onChange={(e) => setCrit(i, { weight: Number(e.target.value) })} className="w-full" />
              <button onClick={() => delCrit(i)} className="rounded-lg px-2 py-1 text-stone-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950" title="Remove">✕</button>
            </div>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <div className="min-w-[200px] flex-1"><ScoreBar value={total} tone={Math.abs(total - 100) < 1e-9 ? 'emerald' : 'amber'} /></div>
          <Badge tone={Math.abs(total - 100) < 1e-9 ? 'emerald' : 'amber'}>total {Math.round(total * 100) / 100}%</Badge>
          <Btn variant="ghost" onClick={normalize}>Normalize to 100</Btn>
        </div>
      </Card>

      {/* smart import */}
      <div className="anim-fade-up-1">
        <SmartImport criteria={d.criteria.map((c) => c.name)} onApply={applyImport} onDone={p.onImportDone} />
      </div>

      {/* smart weights */}
      <div className="anim-fade-up-1">
        <SmartWeights decision={d} onApply={applyLearned} onDone={p.onLearnDone} />
      </div>

      {/* options */}
      <Card className="anim-fade-up-2 p-5">
        <SectionTitle title={`Options (${d.options.length})`} sub="Raw values per criterion — any scale works."
          right={<Btn variant="soft" onClick={addOpt}>＋ Add option</Btn>} />
        <div className="grid gap-3 lg:grid-cols-2">
          {d.options.map((o, i) => (
            <div key={i} className="rounded-xl border border-stone-200 p-3.5 dark:border-stone-800">
              <div className="flex items-start gap-2">
                <div className="grid flex-1 gap-2">
                  <TextInput value={o.name} onChange={(e) => setOpt(i, { name: e.target.value })} placeholder="Option name" />
                  <TextInput value={o.description || ''} onChange={(e) => setOpt(i, { description: e.target.value })} placeholder="Short note (optional)" />
                </div>
                <button onClick={() => delOpt(i)} className="rounded-lg px-2 py-1 text-stone-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950" title="Remove">✕</button>
              </div>
              <div className="mt-2.5 grid gap-2 sm:grid-cols-2">
                {d.criteria.map((c) => (
                  <Field key={c.name} label={`${c.name} ${c.type === 'cost' ? '↓' : '↑'}`}>
                    <NumInput value={o.scores[c.name] ?? 0}
                      onChange={(e) => setScore(i, c.name, Number(e.target.value))} />
                  </Field>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* constraints */}
      <Card className="anim-fade-up-2 p-5">
        <SectionTitle title={`Constraints (${d.constraints.length})`} sub="Hard violations eliminate an option. Soft ones only warn."
          right={<Btn variant="soft" onClick={addCon}>＋ Add</Btn>} />
        {d.constraints.length === 0 ? (
          <p className="text-sm text-stone-400">No constraints — every option stays feasible.</p>
        ) : (
          <div className="space-y-2.5">
            {d.constraints.map((k, i) => (
              <div key={i} className="grid items-center gap-2 rounded-xl bg-stone-50 p-2.5 dark:bg-stone-800/50 sm:grid-cols-[1fr_150px_90px_110px_auto_auto_36px]">
                <TextInput value={k.name || ''} onChange={(e) => setCon(i, { name: e.target.value })} placeholder="Label e.g. Budget" />
                <Select value={k.target} onChange={(e) => setCon(i, { target: e.target.value })}>
                  {d.criteria.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
                </Select>
                <Select value={k.operator} onChange={(e) => setCon(i, { operator: e.target.value })}>
                  {OPERATORS.map((op) => <option key={op} value={op}>{op}</option>)}
                </Select>
                <NumInput value={k.value} onChange={(e) => setCon(i, { value: Number(e.target.value) })} />
                <label className="flex items-center gap-1.5 text-xs text-stone-600 dark:text-stone-300">
                  <input type="checkbox" checked={k.hard} onChange={(e) => setCon(i, { hard: e.target.checked })} className="h-4 w-4 accent-indigo-600" /> hard
                </label>
                <label className="flex items-center gap-1.5 text-xs text-stone-600 dark:text-stone-300">
                  <input type="checkbox" checked={k.enabled} onChange={(e) => setCon(i, { enabled: e.target.checked })} className="h-4 w-4 accent-indigo-600" /> on
                </label>
                <button onClick={() => delCon(i)} className="rounded-lg px-2 py-1 text-stone-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-950" title="Remove">✕</button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* actions */}
      <Card className="anim-fade-up-3 p-5">
        <div className="flex flex-wrap items-center gap-2">
          <Btn onClick={p.onAnalyze} disabled={p.analyzing} className="px-6 py-2.5 text-[15px]">
            {p.analyzing ? <Spinner label="Analyzing…" /> : '⚡ Analyze Decision'}
          </Btn>
          <Btn variant="soft" onClick={p.onSave} disabled={p.busy}>{p.savedId ? '💾 Save changes' : '💾 Save'}</Btn>
          {p.savedId && (
            <>
              <div className="flex items-center gap-1.5">
                <TextInput value={cpLabel} onChange={(e) => setCpLabel(e.target.value)}
                  placeholder="Version label…" className="!w-44 !py-1.5" />
                <Btn variant="soft" disabled={p.busy || !cpLabel.trim()}
                  onClick={() => { p.onCheckpoint(cpLabel.trim()); setCpLabel(''); }}>
                  Save version
                </Btn>
              </div>
              <Btn variant="soft" onClick={p.onUndo} disabled={p.busy || !p.history?.depth}>
                ↩ Undo{p.history?.depth ? ` (${p.history.depth})` : ''}
              </Btn>
            </>
          )}
        </div>
        {p.history && p.history.depth > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5 text-xs text-stone-500">
            <span className="font-medium">History stack (top first):</span>
            {p.history.labels_top_first.slice(0, 6).map((l, i) => (
              <span key={i} className={`rounded-full px-2.5 py-0.5 ${i === 0 ? 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200' : 'bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-300'}`}>{l}</span>
            ))}
            {p.history.depth > 6 && <span>+{p.history.depth - 6} more</span>}
          </div>
        )}
      </Card>
    </div>
  );
}
