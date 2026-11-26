import type { LineStatus, Weights } from '@/lib/api';

/** Slider positions (0–100); the server rescales them to sum to 1. */
export const toSliders = (weights: Weights): Weights => ({
  health: Math.round(weights.health * 100),
  flavor: Math.round(weights.flavor * 100),
  cuisine: Math.round(weights.cuisine * 100),
  role: Math.round(weights.role * 100),
});

export const STATUS_LABEL: Record<LineStatus, string> = {
  ok: 'counted',
  unmatched: 'not matched',
  no_nutrition_data: 'no nutrition data',
  unknown_quantity: 'quantity unknown',
};

export const SOURCE_LABEL: Record<string, string> = {
  usda_sr_legacy: 'USDA SR Legacy',
  indb: 'Indian Nutrient Databank',
};

export function amount(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  const size = Math.abs(value);
  return value.toFixed(size >= 100 ? 0 : size >= 10 ? 1 : 2);
}

export function signed(value: number | null | undefined, suffix = ''): string {
  if (value === null || value === undefined) return '—';
  if (Math.abs(value) < 0.005) return `0${suffix}`;
  return `${value > 0 ? '+' : '−'}${amount(Math.abs(value))}${suffix}`;
}

export function grams(value: number | null, isEstimate: boolean): string {
  if (value === null) return '? g';
  return `${isEstimate ? '≈ ' : ''}${value >= 10 ? Math.round(value) : value.toFixed(1)} g`;
}
