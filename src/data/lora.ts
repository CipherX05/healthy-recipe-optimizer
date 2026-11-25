import loraRawData from '../../public/lora-demo.json';

export interface LoraModeResult {
  query_id: string;
  recipe_family: string;
  variant: number;
  target: string | null;
  raw_output: string;
  latency_seconds: number;
  json_valid: boolean;
  candidate_valid: boolean;
  eligible: boolean;
  selected: string | null;
  recommendation_id: string | null;
  used_fallback: boolean;
}

export interface LoraCase {
  split: string;
  rule_baseline: string | null;
  modes: {
    base: LoraModeResult;
    lora: LoraModeResult;
  };
}

export interface TestMetric {
  records: number;
  independent_queries: number;
  recipe_families: string[];
  json_valid_rate: number;
  candidate_valid_rate: number;
  eligible_rate: number;
  rule_agreement: number;
  interpretation: string;
}

export interface LoraDemoData {
  recorded: boolean;
  training: {
    training_completed: boolean;
    base_model: string;
    base_revision: string;
    completed_at_utc: string;
    training_code_sha256: string;
    adapter_weights_sha256: string;
    seed: number;
    epochs: number;
    optimizer_steps: number;
    learning_rate: number;
    lora_rank: number;
    lora_alpha: number;
    target_modules: string[];
    trainable_parameters: number;
    total_parameters: number;
    adapter_weight_l2_change: number;
    snapshot_sha256: string;
    initial_validation_completion_loss: number;
    best_validation_completion_loss: number;
    training_seconds: number;
    device: string;
    interpretation: string;
  };
  test_metrics: {
    base: TestMetric;
    lora: TestMetric;
  };
  cases: Record<string, LoraCase>;
}

// The UI replays the recorded run. These outputs do not control recipe optimization.
export const LORA_DATA = loraRawData as unknown as LoraDemoData;

export function getLoraCase(recipeId: string, ingredientId: string, goalId: string): LoraCase | null {
  const key = `${recipeId}/${ingredientId}/${goalId}`;
  return LORA_DATA.cases[key] ?? null;
}
