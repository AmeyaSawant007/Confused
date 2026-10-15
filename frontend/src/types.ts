export interface Criterion {
  id?: string;
  name: string;
  weight: number;
  type: 'benefit' | 'cost';
  weight_pct?: number;
}

export interface Option {
  id?: string;
  name: string;
  description?: string;
  scores: Record<string, number>;
}

export interface Constraint {
  id?: string;
  name?: string;
  target: string;
  operator: string;
  value: number;
  hard: boolean;
  enabled: boolean;
}

export interface Decision {
  id?: string;
  title: string;
  category: string;
  criteria: Criterion[];
  options: Option[];
  constraints: Constraint[];
}

export interface Contribution {
  criterion_id: string;
  criterion: string;
  type: string;
  raw: number;
  norm: number;
  weight_pct: number;
  points: number;
}

export interface RankedRow {
  rank: number;
  option_id: string;
  name: string;
  description: string;
  score: number;
  contributions: Contribution[];
}

export interface EliminatedRow {
  option_id: string;
  name: string;
  reasons: string[];
}

export interface GNode {
  id: string;
  kind: string;
  label: string;
  meta?: Record<string, any>;
}
export interface GEdge {
  from: string;
  to: string;
  weight: number;
  label: string;
}
export interface GraphData {
  nodes: GNode[];
  edges: GEdge[];
  adjacency: Record<string, { to: string; w: number }[]>;
  num_vertices: number;
  num_edges: number;
  bfs: string[];
  dfs: string[];
  dijkstra: { dist: Record<string, number | null>; paths: Record<string, string[]> };
}

export interface HeapData {
  mode: string;
  array: { index: number; key: string; priority: number }[];
  size: number;
  ops: string[];
}

export interface SegmentData {
  n: number;
  labels: string[];
  total: number;
  nodes: { id: number; range: string; value: number; touched: boolean; is_leaf: boolean }[];
  affected: number[];
}

export interface HashSnap {
  capacity: number;
  size: number;
  load: number;
  collisions: number;
  resizes: number;
  buckets: { index: number; keys: string[]; count: number }[];
}

export interface AnalysisResult {
  title: string;
  category: string;
  warnings: string[];
  explanations: string[];
  timings: Record<string, number>;
  complexities: { operation: string; complexity: string }[];
  disclaimer: string;
  criteria: Criterion[];
  options: { id: string; name: string; description: string; values: Record<string, number> }[];
  ranked: RankedRow[];
  eliminated: EliminatedRow[];
  winner: RankedRow | null;
  confidence: number | null;
  confidence_note: string;
  nearest_alternative: { option_id: string; name: string; distance: number; path: string[] } | null;
  graph: GraphData;
  heap: HeapData;
  segment: SegmentData;
  hash: {
    options_registry: HashSnap;
    criteria_registry: HashSnap;
    result_cache: HashSnap;
    fingerprint: string;
  };
  score_table: Record<string, Record<string, number>>;
  weight_vector: Record<string, number>;
  weight_total: number;
  numerators: Record<string, number>;
}

export interface Movement {
  option_id: string;
  name: string;
  status: 'moved_up' | 'moved_down' | 'same' | 'new' | 'eliminated';
  before_rank: number | null;
  after_rank: number | null;
  before_score: number | null;
  after_score: number | null;
  delta_rank: number | null;
  delta_score: number | null;
}

export interface WhatIfResult {
  before: AnalysisResult;
  after: AnalysisResult;
  movements: Movement[];
  causes: { criterion: string; old_weight: number; new_weight: number; delta: number; top_beneficiary: string | null; note: string }[];
  segment_trace: {
    updates: { criterion_id: string; old: number; new: number; touched_nodes: number[] }[];
    affected_union: number[];
    old_total: number;
    new_total: number;
  };
  incremental_used: boolean;
  incremental_verified: boolean | null;
  incremental_scores: Record<string, number> | null;
  patch_warnings: string[];
  total_ms: number;
}

export interface Category {
  id: string;
  label: string;
  icon: string;
  blurb: string;
  suggested_criteria: { name: string; type: 'benefit' | 'cost' }[];
}

export interface TemplateMeta {
  id: string;
  title: string;
  category: string;
  options: number;
  criteria: number;
}

export interface SavedDecision {
  id: string;
  title: string;
  category: string;
  options: number;
  created_at: string;
  updated_at: string;
}

export interface SearchHit {
  word: string;
  kind: 'template' | 'decision' | 'category';
  id: string;
  label: string;
  match: string;
}

export type View = 'dashboard' | 'builder' | 'results' | 'whatif' | 'hood';

export interface ImportedOption {
  name: string;
  url: string;
  scores: Record<string, number>;
  filled: string[];
  missing: string[];
  confidence: Record<string, number>;
  sources: { criterion: string; phrase: string; score: number; text: string }[];
}

export interface MatchTable {
  url: string;
  title: string;
  candidates: { text: string; number: number | null; unit: string | null }[];
  matrix: Record<string, Record<string, number>>;
  assignments: { phrase: string; criterion: string | null; score: number }[];
  unmatched: string[];
}

export interface ImportResult {
  mode: string;
  matcher: 'neural' | 'keyword';
  model: string | null;
  options: ImportedOption[];
  match_tables: MatchTable[];
  warnings: string[];
}

export interface MatchResult {
  matcher: string;
  model: string | null;
  matrix: Record<string, Record<string, number>>;
  assignments: { phrase: string; criterion: string | null; score: number }[];
}

export interface WeightProfile {
  category: string;
  weights: Record<string, number>;
  criteria: { name: string; type: string }[];
  updated_at: string;
}

export interface DuelPair {
  a: { id: string; name: string };
  b: { id: string; name: string };
  margin: number;
}

export interface LearnResult {
  method: string;
  method_detail: string;
  weights: Record<string, number>;
  coefficients: Record<string, number>;
  loss_curve: number[];
  train_acc: number;
  loo_acc: number;
  n_samples: number;
  n_criteria: number;
  uniform_fallback: boolean;
  warnings: string[];
}
