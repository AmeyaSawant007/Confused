import React from 'react';

/* ---------- layout ---------- */
export function Card({ className = '', children }: { className?: string; children: React.ReactNode }) {
  return (
    <div className={`rounded-2xl border border-stone-200 bg-white shadow-sm dark:border-stone-800 dark:bg-stone-900 ${className}`}>
      {children}
    </div>
  );
}

export function SectionTitle({ title, sub, right }: { title: string; sub?: string; right?: React.ReactNode }) {
  return (
    <div className="mb-3 flex items-end justify-between gap-3">
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wide text-stone-500 dark:text-stone-400">{title}</h3>
        {sub && <p className="mt-0.5 text-sm text-stone-500 dark:text-stone-400">{sub}</p>}
      </div>
      {right}
    </div>
  );
}

export function EmptyState({ title, sub, children }: { title: string; sub?: string; children?: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-stone-300 px-6 py-10 text-center dark:border-stone-700">
      <div className="text-3xl">🤔</div>
      <h3 className="mt-2 font-semibold text-stone-800 dark:text-stone-100">{title}</h3>
      {sub && <p className="mt-1 text-sm text-stone-500 dark:text-stone-400">{sub}</p>}
      {children && <div className="mt-4 flex justify-center gap-2">{children}</div>}
    </div>
  );
}

export function Spinner({ label = 'Working…' }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-stone-500 dark:text-stone-400">
      <span className="anim-pulse-soft inline-block h-3 w-3 rounded-full bg-indigo-500" />
      {label}
    </span>
  );
}

/* ---------- controls ---------- */
type BtnVariant = 'primary' | 'soft' | 'ghost' | 'danger' | 'success';
export function Btn({
  variant = 'primary', className = '', ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant }) {
  const base =
    'inline-flex items-center justify-center gap-1.5 rounded-xl px-4 py-2 text-sm font-medium transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50';
  const styles: Record<BtnVariant, string> = {
    primary: 'bg-indigo-600 text-white shadow-sm hover:bg-indigo-500',
    success: 'bg-emerald-600 text-white shadow-sm hover:bg-emerald-500',
    soft: 'bg-stone-100 text-stone-800 hover:bg-stone-200 dark:bg-stone-800 dark:text-stone-100 dark:hover:bg-stone-700',
    ghost: 'text-stone-600 hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-800',
    danger: 'bg-rose-50 text-rose-700 hover:bg-rose-100 dark:bg-rose-950/50 dark:text-rose-300 dark:hover:bg-rose-950',
  };
  return <button className={`${base} ${styles[variant]} ${className}`} {...rest} />;
}

export function Badge({ tone = 'stone', children }: { tone?: 'stone' | 'indigo' | 'emerald' | 'rose' | 'amber' | 'sky'; children: React.ReactNode }) {
  const styles: Record<string, string> = {
    stone: 'bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-200',
    indigo: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300',
    emerald: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
    rose: 'bg-rose-50 text-rose-700 dark:bg-rose-950 dark:text-rose-300',
    amber: 'bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
    sky: 'bg-sky-50 text-sky-700 dark:bg-sky-950 dark:text-sky-300',
  };
  return (
    <span className={`tnum inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[tone]}`}>
      {children}
    </span>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-stone-500 dark:text-stone-400">{label}</span>
      {children}
      {hint && <span className="mt-0.5 block text-xs text-stone-400 dark:text-stone-500">{hint}</span>}
    </label>
  );
}

const inputCls =
  'w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-900 outline-none transition placeholder:text-stone-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 dark:border-stone-700 dark:bg-stone-800/60 dark:text-stone-100 dark:focus:border-indigo-500 dark:focus:ring-indigo-950';

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputCls} ${props.className || ''}`} />;
}
export function NumInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input type="number" step="any" {...props} className={`${inputCls} tnum ${props.className || ''}`} />;
}
export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${inputCls} ${props.className || ''}`} />;
}

/* ---------- data display ---------- */
export function ScoreBar({ value, tone = 'indigo', height = 'h-2' }: { value: number; tone?: 'indigo' | 'emerald' | 'amber' | 'rose'; height?: string }) {
  const fills = {
    indigo: 'bg-indigo-500', emerald: 'bg-emerald-500',
    amber: 'bg-amber-500', rose: 'bg-rose-500',
  };
  return (
    <div className={`w-full overflow-hidden rounded-full bg-stone-100 dark:bg-stone-800 ${height}`}>
      <div className={`${fills[tone]} h-full rounded-full transition-all duration-500`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

export function MoveBadge({ status }: { status: string }) {
  if (status === 'moved_up') return <Badge tone="emerald">▲ up</Badge>;
  if (status === 'moved_down') return <Badge tone="rose">▼ down</Badge>;
  if (status === 'new') return <Badge tone="sky">✦ new</Badge>;
  if (status === 'eliminated') return <Badge tone="rose">✕ out</Badge>;
  return <Badge tone="stone">= same</Badge>;
}

export function WarnList({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
      <div className="mb-1 font-semibold">⚠ Heads up</div>
      <ul className="list-disc space-y-0.5 pl-5">
        {items.map((w, i) => <li key={i}>{w}</li>)}
      </ul>
    </div>
  );
}

export function ComplexityTable({ rows }: { rows: { operation: string; complexity: string }[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-stone-200 dark:border-stone-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-stone-50 text-left text-xs uppercase tracking-wide text-stone-500 dark:bg-stone-800/60 dark:text-stone-400">
            <th className="px-4 py-2 font-medium">Operation</th>
            <th className="px-4 py-2 text-right font-medium">Complexity</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-100 dark:divide-stone-800">
          {rows.map((r, i) => (
            <tr key={i} className="text-stone-700 dark:text-stone-200">
              <td className="px-4 py-2">{r.operation}</td>
              <td className="tnum px-4 py-2 text-right font-mono text-[13px] text-indigo-600 dark:text-indigo-400">{r.complexity}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function RankMedal({ rank }: { rank: number }) {
  const medals = ['🥇', '🥈', '🥉'];
  if (rank <= 3) return <span className="text-xl leading-none">{medals[rank - 1]}</span>;
  return (
    <span className="tnum inline-flex h-7 w-7 items-center justify-center rounded-full bg-stone-100 text-sm font-semibold text-stone-600 dark:bg-stone-800 dark:text-stone-300">
      {rank}
    </span>
  );
}
