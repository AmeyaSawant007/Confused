import type { GEdge, GNode, HashSnap, SegmentData } from '../types';

/* ================= decision graph ================= */
const KIND_ORDER = ['decision', 'option', 'criterion', 'constraint'];
const KIND_FILL: Record<string, string> = {
  decision: 'fill-indigo-600 dark:fill-indigo-500',
  option: 'fill-emerald-600 dark:fill-emerald-500',
  criterion: 'fill-sky-600 dark:fill-sky-500',
  constraint: 'fill-amber-500 dark:fill-amber-400',
};

const short = (s: string, n = 22) => (s.length > n ? s.slice(0, n - 1) + '…' : s);

export function GraphSVG({ nodes, edges }: { nodes: GNode[]; edges: GEdge[] }) {
  const groups = KIND_ORDER.map((k) => nodes.filter((n) => n.kind === k)).filter((g) => g.length);
  const rowH = 46, colW = 220, padX = 95, padY = 26;
  const height = Math.max(120, Math.max(...groups.map((g) => g.length)) * rowH + padY * 2);
  const width = groups.length * colW + padX;
  const pos = new Map<string, { x: number; y: number }>();
  const kindOf = new Map(nodes.map((n) => [n.id, n.kind]));
  groups.forEach((g, ci) => {
    const x = padX + ci * colW;
    const startY = (height - g.length * rowH) / 2 + rowH / 2;
    g.forEach((n, ri) => pos.set(n.id, { x, y: startY + ri * rowH }));
  });

  const edgeStyle = (e: GEdge) => {
    if (e.weight >= 1e8)
      return { stroke: 'stroke-rose-400', dash: 'stroke-dasharray="5 4"', w: 1.5 };
    const fk = kindOf.get(e.from);
    const tk = kindOf.get(e.to);
    if (fk === 'decision') return { stroke: 'stroke-indigo-400', dash: '', w: 2 };
    if (tk === 'criterion') return { stroke: 'stroke-emerald-400', dash: '', w: 1.5 };
    if (tk === 'constraint') return { stroke: 'stroke-amber-400', dash: '', w: 1.5 };
    return { stroke: 'stroke-stone-400', dash: 'stroke-dasharray="4 4"', w: 1.5 };
  };

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" style={{ minWidth: width * 0.7 }}>
      {edges.map((e, i) => {
        const a = pos.get(e.from), b = pos.get(e.to);
        if (!a || !b) return null;
        const st = edgeStyle(e);
        const sameCol = Math.abs(a.x - b.x) < 1;
        const x1 = sameCol ? a.x : a.x + 78, x2 = sameCol ? b.x : b.x - 78;
        const d = sameCol
          ? `M ${a.x - 60} ${a.y} C ${a.x - 130} ${a.y}, ${b.x - 130} ${b.y}, ${b.x - 60} ${b.y}`
          : `M ${x1} ${a.y} C ${x1 + 40} ${a.y}, ${x2 - 40} ${b.y}, ${x2} ${b.y}`;
        const mx = sameCol ? Math.min(a.x, b.x) - 105 : (x1 + x2) / 2;
        const my = (a.y + b.y) / 2 - 5;
        const label = e.weight >= 1e8 ? '∞' : e.label;
        return (
          <g key={i}>
            <path d={d} fill="none" className={st.stroke} strokeWidth={st.w} {...(st.dash ? { strokeDasharray: st.dash.split('=')[1].replace(/"/g, '') } : {})} opacity={0.85} />
            {label && (
              <text x={mx} y={my} textAnchor="middle" fontSize={9.5}
                className="fill-stone-500 dark:fill-stone-400" paintOrder="stroke"
                strokeWidth={3} stroke="white" style={{ stroke: 'var(--viz-halo, white)' }}>
                {label}
              </text>
            )}
          </g>
        );
      })}
      {nodes.map((n) => {
        const p = pos.get(n.id);
        if (!p) return null;
        const w = n.kind === 'decision' ? 190 : 156;
        const darkText = n.kind === 'constraint';
        return (
          <g key={n.id}>
            <rect x={p.x - w / 2} y={p.y - 15} width={w} height={30} rx={9}
              className={`${KIND_FILL[n.kind] || 'fill-stone-500'} opacity-95`} />
            <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize={11} fontWeight={600}
              className={darkText ? 'fill-stone-950' : 'fill-white'}>
              {short(n.label, n.kind === 'decision' ? 28 : 20)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* ================= heap ================= */
export function HeapSVG({ array, names }: { array: { index: number; key: string; priority: number }[]; names?: Record<string, string> }) {
  if (!array.length)
    return <p className="py-6 text-center text-sm text-stone-500">Heap is empty (no feasible options).</p>;
  const depthOf = (i: number) => Math.floor(Math.log2(i + 1));
  const maxD = depthOf(array.length - 1);
  const width = Math.max(340, Math.pow(2, maxD) * 96);
  const pos = (i: number) => {
    const d = depthOf(i), first = Math.pow(2, d) - 1, count = Math.pow(2, d);
    return { x: ((i - first) + 0.5) * (width / count), y: 36 + d * 78 };
  };
  const height = 36 + maxD * 78 + 48;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full">
      {array.map((e, i) => {
        if (i === 0) return null;
        const a = pos(Math.floor((i - 1) / 2)), b = pos(i);
        return <line key={i} x1={a.x} y1={a.y + 20} x2={b.x} y2={b.y - 20} className="stroke-stone-300 dark:stroke-stone-700" strokeWidth={2} />;
      })}
      {array.map((e, i) => {
        const p = pos(i);
        const label = short(names?.[e.key] || e.key, 14);
        return (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r={21}
              className={i === 0 ? 'fill-emerald-500' : 'fill-indigo-500'} opacity={0.95} />
            <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize={10.5} fontWeight={700} className="fill-white tnum">
              {e.priority.toFixed(1)}
            </text>
            <text x={p.x} y={p.y + 36} textAnchor="middle" fontSize={10}
              className="fill-stone-600 dark:fill-stone-300">{label}</text>
          </g>
        );
      })}
    </svg>
  );
}

/* ================= trie ================= */
export function TrieSVG({ nodes, edges }: {
  nodes: { id: number; char: string; is_end: boolean; words: string[] }[];
  edges: { from: number; to: number; char: string }[];
}) {
  const children = new Map<number, number[]>();
  edges.forEach((e) => {
    if (!children.has(e.from)) children.set(e.from, []);
    children.get(e.from)!.push(e.to);
  });
  const depth = new Map<number, number>([[0, 0]]);
  const q = [0];
  while (q.length) {
    const u = q.shift()!;
    for (const v of children.get(u) || []) {
      if (!depth.has(v)) { depth.set(v, depth.get(u)! + 1); q.push(v); }
    }
  }
  const maxD = Math.max(...depth.values());
  const byDepth: number[][] = Array.from({ length: maxD + 1 }, () => []);
  nodes.forEach((n) => byDepth[depth.get(n.id) || 0].push(n.id));
  const nodeById = new Map(nodes.map((n) => [n.id, n]));
  const colW = 86, rowH = 30, padX = 40, padY = 24;
  const height = Math.max(120, Math.max(...byDepth.map((g) => g.length)) * rowH + padY * 2);
  const width = (maxD + 1) * colW + padX + 170;
  const pos = new Map<number, { x: number; y: number }>();
  byDepth.forEach((g, d) => {
    const x = padX + d * colW;
    const startY = (height - g.length * rowH) / 2 + rowH / 2;
    g.forEach((id, ri) => pos.set(id, { x, y: startY + ri * rowH }));
  });
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" style={{ minWidth: 560 }}>
      {edges.map((e, i) => {
        const a = pos.get(e.from), b = pos.get(e.to);
        if (!a || !b) return null;
        return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} className="stroke-stone-300 dark:stroke-stone-700" strokeWidth={1.5} />;
      })}
      {nodes.map((n) => {
        const p = pos.get(n.id);
        if (!p) return null;
        return (
          <g key={n.id}>
            <circle cx={p.x} cy={p.y} r={n.id === 0 ? 15 : 11}
              className={n.id === 0 ? 'fill-indigo-600' : n.is_end ? 'fill-emerald-500' : 'fill-stone-400 dark:fill-stone-500'} />
            <text x={p.x} y={p.y + 3.5} textAnchor="middle" fontSize={n.id === 0 ? 8 : 10} fontWeight={700} className="fill-white">
              {n.id === 0 ? 'root' : n.char === ' ' ? '␣' : n.char}
            </text>
            {n.is_end && n.words[0] && (
              <text x={p.x + 15} y={p.y + 3.5} fontSize={10} className="fill-stone-600 dark:fill-stone-300">
                · {short(n.words[0], 24)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

/* ================= segment tree ================= */
export function SegSVG({ nodes }: { nodes: SegmentData['nodes'] }) {
  if (!nodes.length) return <p className="py-6 text-center text-sm text-stone-500">No weights.</p>;
  const depthOf = (id: number) => Math.floor(Math.log2(id));
  const maxD = Math.max(...nodes.map((n) => depthOf(n.id)));
  const width = Math.max(420, Math.pow(2, maxD) * 120);
  const pos = (id: number) => {
    const d = depthOf(id), first = Math.pow(2, d), count = Math.pow(2, d);
    return { x: ((id - first) + 0.5) * (width / count), y: 30 + d * 72 };
  };
  const height = 30 + maxD * 72 + 44;
  const ids = new Set(nodes.map((n) => n.id));
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full">
      {nodes.map((n) => {
        if (n.id === 1) return null;
        const a = pos(Math.floor(n.id / 2)), b = pos(n.id);
        if (!ids.has(Math.floor(n.id / 2))) return null;
        return <line key={n.id} x1={a.x} y1={a.y + 19} x2={b.x} y2={b.y - 19}
          className={n.touched ? 'stroke-amber-500' : 'stroke-stone-300 dark:stroke-stone-700'} strokeWidth={n.touched ? 2.5 : 1.5} />;
      })}
      {nodes.map((n) => {
        const p = pos(n.id);
        return (
          <g key={n.id}>
            <rect x={p.x - 46} y={p.y - 19} width={92} height={38} rx={9}
              className={n.touched
                ? 'fill-amber-400 dark:fill-amber-500'
                : n.is_leaf
                  ? 'fill-sky-100 dark:fill-sky-950 stroke-sky-300 dark:stroke-sky-800'
                  : 'fill-stone-100 dark:fill-stone-800 stroke-stone-300 dark:stroke-stone-700'}
              strokeWidth={1.5} />
            <text x={p.x} y={p.y - 3} textAnchor="middle" fontSize={9.5}
              className="fill-stone-500 dark:fill-stone-400">{short(n.range, 16)}</text>
            <text x={p.x} y={p.y + 11} textAnchor="middle" fontSize={12} fontWeight={700}
              className="tnum fill-stone-800 dark:fill-stone-100">{n.value}</text>
          </g>
        );
      })}
    </svg>
  );
}

/* ================= hash table ================= */
export function HashViz({ snap }: { snap: HashSnap }) {
  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-2 text-xs">
        <span className="rounded-full bg-stone-100 px-2.5 py-1 dark:bg-stone-800 tnum">capacity {snap.capacity}</span>
        <span className="rounded-full bg-stone-100 px-2.5 py-1 dark:bg-stone-800 tnum">size {snap.size}</span>
        <span className="rounded-full bg-stone-100 px-2.5 py-1 dark:bg-stone-800 tnum">load {snap.load}</span>
        <span className="rounded-full bg-stone-100 px-2.5 py-1 dark:bg-stone-800 tnum">collisions {snap.collisions}</span>
        <span className="rounded-full bg-stone-100 px-2.5 py-1 dark:bg-stone-800 tnum">resizes {snap.resizes}</span>
      </div>
      <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
        {snap.buckets.map((b) => (
          <div key={b.index} className={`flex items-center gap-2 rounded-lg border px-2 py-1.5 text-xs ${b.count ? 'border-indigo-200 bg-indigo-50/50 dark:border-indigo-900 dark:bg-indigo-950/30' : 'border-stone-100 dark:border-stone-800/60 opacity-60'}`}>
            <span className="tnum w-8 shrink-0 font-mono text-stone-400">[{b.index}]</span>
            {b.count === 0 ? (
              <span className="text-stone-400">∅</span>
            ) : (
              <span className="flex flex-wrap gap-1">
                {b.keys.map((k, i) => (
                  <span key={i} className="flex items-center gap-1">
                    {i > 0 && <span className="text-stone-400">→</span>}
                    <code className="rounded bg-white px-1.5 py-0.5 font-mono text-[11px] text-stone-700 shadow-sm dark:bg-stone-800 dark:text-stone-200">{k}</code>
                  </span>
                ))}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ================= stack ================= */
export function StackViz({ labels, depth, capacity }: { labels: string[]; depth: number; capacity?: number }) {
  if (!depth)
    return <p className="py-6 text-center text-sm text-stone-500">Stack is empty — no checkpoints yet.</p>;
  return (
    <div className="mx-auto max-w-md space-y-1.5">
      {labels.map((l, i) => (
        <div key={i}
          className={`flex items-center justify-between rounded-xl border px-4 py-2.5 text-sm ${i === 0
            ? 'border-indigo-300 bg-indigo-50 font-semibold text-indigo-900 dark:border-indigo-700 dark:bg-indigo-950 dark:text-indigo-100'
            : 'border-stone-200 bg-white text-stone-600 dark:border-stone-800 dark:bg-stone-900 dark:text-stone-300'}`}>
          <span className="truncate">{l}</span>
          {i === 0 && <span className="ml-2 shrink-0 rounded-full bg-indigo-600 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">top</span>}
        </div>
      ))}
      <p className="pt-1 text-center text-xs text-stone-400">depth {depth}{capacity ? ` / ${capacity}` : ''} · pop = undo</p>
    </div>
  );
}
