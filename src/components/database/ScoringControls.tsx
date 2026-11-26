import type { GoalId, Health, Scope, ScoreKey, Weights } from '@/lib/api';
import { Card, Label, Pill } from './parts';
import { toSliders } from './format';

const SCORE_LABEL: Record<ScoreKey, string> = {
  health: 'Health improvement',
  flavor: 'Flavor similarity',
  cuisine: 'Cuisine compatibility',
  role: 'Cooking role',
};
const PRESET_LABEL: Record<string, string> = {
  balanced: 'Balanced (default)',
  health_first: 'Health first',
  flavor_first: 'Flavor first',
  cuisine_first: 'Cuisine first',
};

export interface Settings {
  goal: GoalId;
  scope: Scope;
  weights: Weights;
  minFlavor: number;
  minCuisine: number;
  keepTitle: boolean;
  guardrails: boolean;
}

export default function ScoringControls({
  health,
  settings,
  onChange,
}: {
  health: Health;
  settings: Settings;
  onChange: (changes: Partial<Settings>) => void;
}) {
  const total = Object.values(settings.weights).reduce((a, b) => a + b, 0);
  const limits = health.thresholds;
  const slider = (label: string, value: number, apply: (v: number) => void, shown: string) => (
    <label key={label} className="block">
      <span className="flex justify-between gap-3 font-mono2 text-[11px] text-[#efede9]/85">
        <span>{label}</span>
        <span>{shown}</span>
      </span>
      <input
        type="range"
        min={0}
        max={100}
        step={5}
        value={value}
        onChange={(e) => apply(Number(e.target.value))}
        className="w-full h-8 accent-[#f26522]"
      />
    </label>
  );

  return (
    <Card title="3 · Goal and scoring">
      <div className="mt-4 flex flex-wrap gap-x-8 gap-y-5">
        <div>
          <Label>Health goal</Label>
          <div className="flex flex-wrap gap-2">
            {health.goals.map((g) => (
              <Pill key={g.id} tone="sage" active={g.id === settings.goal} onClick={() => onChange({ goal: g.id })}>
                {g.label}
              </Pill>
            ))}
          </div>
        </div>
        <div>
          <Label>Optimization scope</Label>
          <div className="flex flex-wrap gap-2">
            <Pill active={settings.scope === 'ingredient'} onClick={() => onChange({ scope: 'ingredient' })}>
              Selected ingredient only
            </Pill>
            <Pill active={settings.scope === 'recipe'} onClick={() => onChange({ scope: 'recipe' })}>
              Whole recipe
            </Pill>
          </div>
        </div>
      </div>

      <div className="mt-6">
        <Label>Your preferences (weights)</Label>
        <div className="flex flex-wrap gap-2">
          {Object.entries(health.presets).map(([id, preset]) => (
            <Pill
              key={id}
              active={JSON.stringify(toSliders(preset)) === JSON.stringify(settings.weights)}
              onClick={() => onChange({ weights: toSliders(preset) })}
            >
              {PRESET_LABEL[id] ?? id}
            </Pill>
          ))}
        </div>
        <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-4 gap-x-6 gap-y-3">
          {(Object.keys(SCORE_LABEL) as ScoreKey[]).map((key) =>
            slider(
              SCORE_LABEL[key],
              settings.weights[key],
              (v) => onChange({ weights: { ...settings.weights, [key]: v } }),
              total > 0 ? `${Math.round((settings.weights[key] / total) * 100)}%` : '0%',
            ),
          )}
        </div>
        {total === 0 && (
          <p role="alert" className="mt-2 font-body text-[13px] text-[#f26522]">
            Raise at least one weight above zero.
          </p>
        )}
      </div>

      <details className="mt-5">
        <summary className="cursor-pointer min-h-[32px] font-mono2 text-[11px] text-[#a39b8b] hover:text-[#efede9]">
          Filters
        </summary>
        <div className="mt-3 grid sm:grid-cols-2 gap-x-8 gap-y-3">
          {slider(
            'Minimum flavor similarity',
            Math.round(settings.minFlavor * 100),
            (v) => onChange({ minFlavor: v / 100 }),
            settings.minFlavor ? settings.minFlavor.toFixed(2) : 'off',
          )}
          {slider(
            'Minimum cuisine compatibility',
            Math.round(settings.minCuisine * 100),
            (v) => onChange({ minCuisine: v / 100 }),
            settings.minCuisine ? settings.minCuisine.toFixed(2) : 'off',
          )}
          <label className="flex items-start gap-3 font-body text-[14px] text-[#efede9]/85 sm:col-span-2">
            <input
              type="checkbox"
              checked={settings.keepTitle}
              onChange={(e) => onChange({ keepTitle: e.target.checked })}
              className="mt-1 w-4 h-4 accent-[#f26522]"
            />
            In whole-recipe mode, keep ingredients named in the recipe title.
          </label>
          <label className="flex items-start gap-3 font-body text-[14px] text-[#efede9]/85 sm:col-span-2">
            <input
              type="checkbox"
              checked={settings.guardrails}
              onChange={(e) => onChange({ guardrails: e.target.checked })}
              className="mt-1 w-4 h-4 accent-[#f26522]"
            />
            Do not recommend swaps that sharply raise saturated fat, sodium or calories (recommended).
          </label>
        </div>
      </details>

      <details className="mt-2">
        <summary className="cursor-pointer min-h-[32px] font-mono2 text-[11px] text-[#a39b8b] hover:text-[#efede9]">
          How the scores are calculated
        </summary>
        <dl className="mt-3 space-y-2 font-body text-[14px] text-[#efede9]/80 max-w-3xl">
          <div>
            <dt className="inline font-semibold text-[#fdfdfd]">Health: </dt>
            <dd className="inline">
              the share of the goal nutrient removed or added on that ingredient line, gain ÷ the larger of the old and
              new amounts. It is 0 when the swap does not help.
            </dd>
          </div>
          <div>
            <dt className="inline font-semibold text-[#fdfdfd]">Flavor: </dt>
            <dd className="inline">
              Jaccard similarity of FlavorDB2 flavor molecules: shared molecules ÷ all molecules in either ingredient.
              If FlavorDB2 lists fewer than {limits.min_flavor_molecules} molecules for either food, there is no
              score. Shared molecules are a proxy and do not prove that two foods taste alike.
            </dd>
          </div>
          <div>
            <dt className="inline font-semibold text-[#fdfdfd]">Cuisine: </dt>
            <dd className="inline">
              ln(1 + n) ÷ ln(1 + n_max), where n is how many imported recipes of this cuisine use the ingredient. It
              needs at least {limits.min_region_recipes} recipes of that cuisine and reflects this sample only.
            </dd>
          </div>
          <div>
            <dt className="inline font-semibold text-[#fdfdfd]">Role: </dt>
            <dd className="inline">
              1.0 for the same cooking role, 0.6 for a related role. Roles are assigned by this project.
            </dd>
          </div>
          <div>
            <dt className="inline font-semibold text-[#fdfdfd]">Overall: </dt>
            <dd className="inline">
              the weighted sum of the four. A score with no data earns 0 points.
            </dd>
          </div>
          <div>
            <dt className="inline font-semibold text-[#fdfdfd]">Eligibility: </dt>
            <dd className="inline">
              regardless of weights, a substitute needs a compatible role and must improve the goal nutrient by more
              than {Math.round(limits.min_line_improvement * 100)}% on its line, and by at least{' '}
              {limits.min_gain_per_100g[settings.goal]} {settings.goal === 'calories' ? 'kcal' : 'g'} per 100 g
              replaced, so flavor alone or a trace amount never gets it recommended. With the guardrail on, it also must
              not raise {Object.entries(limits.guardrails)
                .map(([key, [rise, floor]]) =>
                  `${key === 'satFat' ? 'saturated fat' : key} by more than ${Math.round(rise * 100)}% (and ${floor} ${
                    key === 'sodium' ? 'mg' : key === 'calories' ? 'kcal' : 'g'
                  } per 100 g)`,
                )
                .join(' or ')}, unless that nutrient is your goal. These limits are this project’s choices, not dietary
              guidance. An ingredient counts as relevant when it can move the recipe total by at least{' '}
              {Math.round(limits.min_recipe_gain * 100)}%.
            </dd>
          </div>
        </dl>
      </details>
    </Card>
  );
}
