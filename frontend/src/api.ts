import type {
  AnalysisResult, Category, Decision, DuelPair, ImportResult, LearnResult,
  MatchResult, SavedDecision, SearchHit, TemplateMeta, WeightProfile, WhatIfResult,
} from './types';

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => req<{ status: string; trie_words: number }>('/api/health'),
  categories: () => req<{ categories: Category[] }>('/api/categories'),
  templates: () => req<{ templates: TemplateMeta[] }>('/api/templates'),
  template: (id: string) => req<Decision>(`/api/templates/${id}`),
  analyze: (d: Decision) =>
    req<AnalysisResult>('/api/analyze', { method: 'POST', body: JSON.stringify(d) }),
  whatif: (payload: {
    baseline: Decision;
    weights: Record<string, number>;
    disable_constraints: string[];
    disable_options: string[];
  }) => req<WhatIfResult>('/api/whatif', { method: 'POST', body: JSON.stringify(payload) }),
  decisions: () => req<{ decisions: SavedDecision[] }>('/api/decisions'),
  createDecision: (d: Decision) =>
    req<{ id: string; data: Decision }>('/api/decisions', {
      method: 'POST', body: JSON.stringify(d),
    }),
  getDecision: (id: string) => req<Decision>(`/api/decisions/${id}`),
  updateDecision: (id: string, d: Decision) =>
    req<{ id: string }>(`/api/decisions/${id}`, {
      method: 'PUT', body: JSON.stringify(d),
    }),
  deleteDecision: (id: string) =>
    req<{ deleted: string }>(`/api/decisions/${id}`, { method: 'DELETE' }),
  checkpoint: (id: string, label: string, state: Decision) =>
    req<{ saved: string; history: { depth: number; labels_top_first: string[] } }>(
      `/api/decisions/${id}/checkpoint`,
      { method: 'POST', body: JSON.stringify({ label, state }) }
    ),
  undo: (id: string) =>
    req<{ restored: Decision; undone: string; history: { depth: number; labels_top_first: string[] } }>(
      `/api/decisions/${id}/undo`, { method: 'POST' }
    ),
  history: (id: string) =>
    req<{ depth: number; capacity: number; labels_top_first: string[] }>(
      `/api/decisions/${id}/history`
    ),
  search: (q: string) =>
    req<{ query: string; results: SearchHit[] }>(`/api/search?q=${encodeURIComponent(q)}`),
  trie: () => req<any>('/api/trie'),
  play: (kind: 'heap' | 'trie' | 'graph' | 'segment' | 'hash' | 'stack', body: any) =>
    req<any>(`/api/play/${kind}`, { method: 'POST', body: JSON.stringify(body) }),
  importUrls: (urls: string[], criteria: string[]) =>
    req<ImportResult>('/api/import', {
      method: 'POST', body: JSON.stringify({ mode: 'urls', urls, criteria }),
    }),
  importSamples: (criteria: string[]) =>
    req<ImportResult>('/api/import', {
      method: 'POST', body: JSON.stringify({ mode: 'samples', criteria }),
    }),
  importSamplesList: () =>
    req<{ samples: { id: string; label: string; url: string }[] }>('/api/import/samples'),
  matchFields: (criteria: string[], phrases: string[]) =>
    req<MatchResult>('/api/match', {
      method: 'POST', body: JSON.stringify({ criteria, phrases }),
    }),
  listProfiles: () => req<{ profiles: WeightProfile[] }>('/api/profiles'),
  saveProfile: (category: string, weights: Record<string, number>, criteria: { name: string; type: string }[]) =>
    req<WeightProfile>('/api/profiles', {
      method: 'POST', body: JSON.stringify({ category, weights, criteria }),
    }),
  getProfile: (category: string) => req<WeightProfile>(`/api/profiles/${category}`),
  deleteProfile: (category: string) =>
    req<{ deleted: string }>(`/api/profiles/${category}`, { method: 'DELETE' }),
  duels: (decision: Decision, n = 6) =>
    req<{ pairs: DuelPair[]; criteria: string[]; weights: Record<string, number>; warnings: string[] }>(
      '/api/duels', { method: 'POST', body: JSON.stringify({ decision, n }) }
    ),
  learn: (decision: Decision, answers: { a: string; b: string; winner: string }[]) =>
    req<LearnResult>('/api/learn', {
      method: 'POST', body: JSON.stringify({ decision, answers }),
    }),
};
