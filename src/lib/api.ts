// Client for the local recipe database API (see backend/recipe_optimizer/api.py).

const BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const TIMEOUT_MS = 30_000;

export type GoalId = 'satFat' | 'calories' | 'protein' | 'fiber';
export type Scope = 'ingredient' | 'recipe';
export type ScoreKey = 'health' | 'flavor' | 'cuisine' | 'role';
export type Weights = Record<ScoreKey, number>;

export interface SourceInfo {
  id: string;
  name: string;
  url: string;
  license: string;
  status: 'loaded' | 'skipped' | 'unavailable';
  records: number;
  retrieved_at: string | null;
}

export interface Health {
  status: 'ok';
  stats: Record<string, number>;
  sources: SourceInfo[];
  goals: { id: GoalId; label: string; nutrient: string; direction: 'min' | 'max' }[];
  default_weights: Weights;
  presets: Record<string, Weights>;
  thresholds: {
    min_line_improvement: number;
    min_recipe_gain: number;
    min_region_recipes: number;
    min_flavor_molecules: number;
    tradeoff: number;
    min_gain_per_100g: Record<GoalId, number>;
    guardrails: Record<string, [number, number]>;
  };
}

export interface RecipeSummary {
  id: number;
  title: string;
  region: string | null;
  sub_region: string | null;
  servings: number | null;
  total_minutes: number | null;
  ingredient_lines: number;
  counted_lines: number;
}

export interface SearchResult {
  total: number;
  limit: number;
  offset: number;
  results: RecipeSummary[];
}

export interface IngredientInfo {
  id: string;
  name: string;
  role: string;
  family: string;
  substitutable: boolean;
  nutrition_source: string | null;
  nutrition_match: 'exact' | 'proxy' | null;
  nutrition_note: string;
  source_food_id: string | null;
  source_food_name: string | null;
  per_100g: Record<string, number>;
  flavor_entity: string | null;
  flavor_match: 'exact' | 'proxy' | null;
  flavor_molecules: number;
  flavor_usable: boolean;
}

export type LineStatus = 'ok' | 'unmatched' | 'no_nutrition_data' | 'unknown_quantity';

export interface RecipeLine {
  id: number;
  original_phrase: string;
  standardized_name: string;
  ingredient_id: string | null;
  grams: number | null;
  grams_method: string;
  grams_note: string;
  grams_is_estimate: boolean;
  match_method: string;
  match_confidence: number;
  match_note: string;
  missing_status: LineStatus;
  ingredient: IngredientInfo | null;
  cuisine_score: number | null;
}

export interface NutrientRow {
  key: string;
  label: string;
  unit: string;
  original: number | null;
  modified: number | null;
  change: number | null;
  percent_change: number | null;
  per_serving: { original: number; modified: number; change: number } | null;
  counted_lines: number;
  lines_missing_value: number[];
}

export interface Coverage {
  total_lines: number;
  counted_lines: number;
  fraction: number;
  excluded: { line_id: number; phrase: string; reason: LineStatus }[];
}

export interface RecipeDetail {
  id: number;
  source_id: string;
  title: string;
  region: string | null;
  sub_region: string | null;
  servings: number | null;
  servings_raw: string | null;
  servings_estimated: boolean;
  total_minutes: number | null;
  instructions: string | null;
  processes: string[];
  utensils: string[];
  diet_tags: string[];
  source_site: string | null;
  source_url: string | null;
  detail_url: string | null;
  ingredients: RecipeLine[];
  nutrition: NutrientRow[];
  coverage: Coverage;
}

export interface Tradeoff {
  key: string;
  label: string;
  unit: string;
  change: number;
  percent_change: number;
}

export interface Candidate {
  ingredient_id: string;
  name: string;
  scores: Record<ScoreKey, number | null>;
  overall: number;
  weight_with_data: number;
  flavor_detail: {
    shared: number;
    union: number;
    original_entity: string;
    candidate_entity: string;
    same_entity: boolean;
    proxy: boolean;
  } | null;
  flavor_gap: string | null;
  cuisine_detail: { recipes_using: number; region_recipes: number; region: string | null };
  line_amount: { original: number; modified: number | null };
  recipe_gain_percent: number;
  tradeoffs: Tradeoff[];
  notes: string[];
  eligible: boolean;
  reasons: string[];
}

export interface Recommendation {
  line_id: number;
  ingredient_id: string;
  ingredient_name: string;
  phrase: string;
  grams: number;
  amount: number;
  share_percent: number | null;
  best_gain_percent: number;
  relevant: boolean;
  in_title: boolean;
  candidates: Candidate[];
  eligible_count: number;
  rejected: Candidate[];
  rejected_count: number;
  rejection_reasons: Record<string, number>;
}

export interface AppliedSwap {
  line_id: number;
  from_id: string;
  from_name: string;
  to_id: string;
  to_name: string;
  grams: number;
  new_grams: number;
  ratio: number;
  ratio_basis: string;
  chosen_by: 'recommended' | 'your choice';
  eligible: boolean;
  reasons: string[];
  notes: string[];
  overall: number;
}

export interface Evaluation {
  recipe_id: number;
  goal: { id: GoalId; label: string; nutrient: string; direction: 'min' | 'max' };
  scope: Scope;
  line_id: number | null;
  weights: Weights;
  recommendations: Recommendation[];
  applied: AppliedSwap[];
  comparison: NutrientRow[];
  goal_result: {
    improved: boolean;
    gain_percent: number;
    label: string;
    unit: string;
    original: number | null;
    modified: number | null;
  };
  tradeoffs: Tradeoff[];
  similarity: {
    flavor: number | null;
    cuisine: number | null;
    flavor_swaps_with_data: number;
    flavor_same_record_swaps: number;
    cuisine_swaps_with_data: number;
    swaps: number;
  };
  coverage: Coverage;
  servings: number | null;
  servings_estimated: boolean;
}

export interface EvaluationRequest {
  goal: GoalId;
  scope: Scope;
  line_id: number | null;
  weights: Weights;
  selections: Record<number, string | null>;
  ratios: Record<number, number>;
  min_flavor: number;
  min_cuisine: number;
  keep_title_ingredients: boolean;
  guardrails: boolean;
}

export interface NetworkData {
  center: string;
  center_name: string;
  total_neighbours: number;
  nodes: { id: string; name: string; role: string }[];
  edges: {
    source: string;
    target: string;
    role_score: number;
    flavor_jaccard: number | null;
    shared_molecules: number;
    same_flavor_entity: boolean;
    weight: number;
    cuisine_score?: number | null;
  }[];
}

async function request<T>(path: string, signal: AbortSignal, body?: unknown): Promise<T> {
  const timeout = AbortSignal.timeout(TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`${BASE}/api${path}`, {
      signal: AbortSignal.any([signal, timeout]),
      ...(body === undefined
        ? {}
        : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new Error('The recipe database server could not be reached.');
  }
  const type = response.headers.get('content-type') ?? '';
  // A static host answers /api with HTML or an empty proxy error.
  if (!type.includes('application/json')) {
    throw new Error('The recipe database server is not running.');
  }
  const data = await response.json();
  if (!response.ok) {
    throw new Error(typeof data?.detail === 'string' ? data.detail : `Request failed (${response.status}).`);
  }
  return data as T;
}

export const api = {
  health: (signal: AbortSignal) => request<Health>('/health', signal),
  regions: (signal: AbortSignal) => request<{ region: string; recipes: number }[]>('/regions', signal),
  search: (
    filters: { q: string; region: string; ingredient: string; limit: number; offset: number },
    signal: AbortSignal,
  ) => {
    const params = new URLSearchParams(
      Object.entries(filters)
        .filter(([, value]) => value !== '')
        .map(([key, value]) => [key, String(value)]),
    );
    return request<SearchResult>(`/recipes?${params}`, signal);
  },
  recipe: (id: number, signal: AbortSignal) => request<RecipeDetail>(`/recipes/${id}`, signal),
  evaluate: (id: number, body: EvaluationRequest, signal: AbortSignal) =>
    request<Evaluation>(`/recipes/${id}/recommend`, signal, body),
  network: (ingredientId: string, region: string, signal: AbortSignal) =>
    request<NetworkData>(
      `/ingredients/${encodeURIComponent(ingredientId)}/network?limit=10&region=${encodeURIComponent(region)}`,
      signal,
    ),
};
