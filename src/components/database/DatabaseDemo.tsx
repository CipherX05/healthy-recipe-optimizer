import { useCallback, useMemo, useState } from 'react';
import { api, type EvaluationRequest, type Health } from '@/lib/api';
import { useAsync } from '@/hooks/useAsync';
import { useDebounced } from '@/hooks/useDebounced';
import Comparison, { ModifiedRecipe } from './Comparison';
import NetworkGraph from './NetworkGraph';
import RecipeDetails from './RecipeDetails';
import RecipeSearch from './RecipeSearch';
import Recommendations from './Recommendations';
import ScoringControls, { type Settings } from './ScoringControls';
import { Notice } from './parts';
import { toSliders } from './format';

/** Per-recipe choices. They reset when the recipe or the goal changes. */
interface Choices {
  lineId: number | null;
  selections: Record<number, string | null>;
  ratios: Record<number, number>;
}
const NO_CHOICES: Choices = { lineId: null, selections: {}, ratios: {} };
const STARTING_SEARCH = 'butter chicken';

export default function DatabaseDemo({ health }: { health: Health }) {
  const [pickedId, setPickedId] = useState<number | null>(null);
  const [settings, setSettings] = useState<Settings>(() => ({
    goal: 'satFat',
    scope: 'ingredient',
    weights: toSliders(health.default_weights),
    minFlavor: 0,
    minCuisine: 0,
    keepTitle: true,
    guardrails: true,
  }));
  const [choices, setChoices] = useState<Choices>(NO_CHOICES);

  // Before the user picks one, open the best-covered "butter chicken" (or any recipe).
  const starter = useAsync(
    useCallback(async (signal: AbortSignal) => {
      const filters = { region: '', ingredient: '', limit: 1, offset: 0 };
      const preferred = await api.search({ ...filters, q: STARTING_SEARCH }, signal);
      const found = preferred.total ? preferred : await api.search({ ...filters, q: '' }, signal);
      return found.results[0]?.id ?? null;
    }, []),
  );
  const recipeId = pickedId ?? starter.data;

  const recipe = useAsync(
    useMemo(
      () => (recipeId === null ? null : (signal: AbortSignal) => api.recipe(recipeId, signal)),
      [recipeId],
    ),
  );

  const request: EvaluationRequest = {
    goal: settings.goal,
    scope: settings.scope,
    line_id: choices.lineId,
    weights: settings.weights,
    selections: choices.selections,
    ratios: choices.ratios,
    min_flavor: settings.minFlavor,
    min_cuisine: settings.minCuisine,
    keep_title_ingredients: settings.keepTitle,
    guardrails: settings.guardrails,
  };
  // Debounced so that dragging a slider sends one request, not dozens.
  const body = useDebounced(JSON.stringify([recipeId, request]), 250);
  const evaluation = useAsync(
    useMemo(() => {
      const [id, payload] = JSON.parse(body) as [number | null, EvaluationRequest];
      // Checked on the payload itself: the debounced copy can lag behind the sliders.
      if (id === null || !Object.values(payload.weights).some((w) => w > 0)) return null;
      return (signal: AbortSignal) => api.evaluate(id, payload, signal);
    }, [body]),
  );

  const chooseRecipe = (id: number) => {
    setPickedId(id);
    setChoices(NO_CHOICES);
  };
  const changeSettings = (changes: Partial<Settings>) => {
    setSettings((current) => ({ ...current, ...changes }));
    if (changes.goal) setChoices(NO_CHOICES);
  };

  const shownRecipe = recipe.data?.id === recipeId ? recipe.data : null;
  const shown = shownRecipe && evaluation.data?.recipe_id === recipeId ? evaluation.data : null;
  const focusId = shown?.scope === 'ingredient' ? shown.line_id : choices.lineId;
  const focus =
    shown?.recommendations.find((r) => r.line_id === focusId) ??
    shown?.recommendations.find((r) => r.candidates.length > 0) ??
    shown?.recommendations[0];

  return (
    <div className="mt-8 space-y-6">
      <p className="font-mono2 text-[11px] text-[#a39b8b] leading-relaxed">
        {health.stats.recipes.toLocaleString()} RecipeDB recipes · {health.stats.ingredients_with_nutrition} ingredients
        with nutrition data · {health.stats.ingredients_with_usable_flavor} with usable FlavorDB2 profiles · stored locally
      </p>
      <RecipeSearch selectedId={recipeId} onSelect={chooseRecipe} />

      {(starter.error || recipe.error) && <Notice tone="warn">{starter.error ?? recipe.error}</Notice>}
      {recipe.loading && <Notice>Loading the recipe…</Notice>}
      {!recipe.loading && !starter.loading && recipeId === null && (
        <Notice tone="warn">The database holds no recipes yet. Run the build command in backend/README.md.</Notice>
      )}

      {shownRecipe && (
        <>
          <RecipeDetails recipe={shownRecipe} />
          <ScoringControls health={health} settings={settings} onChange={changeSettings} />
          {evaluation.error && <Notice tone="warn">{evaluation.error}</Notice>}
          <p className="font-mono2 text-[11px] text-[#a39b8b] min-h-[1em]" aria-live="polite">
            {evaluation.loading ? 'Updating recommendations…' : ''}
          </p>
          {shown && (
            <div className={`space-y-6 transition-opacity ${evaluation.loading ? 'opacity-60' : ''}`}>
              <Recommendations
                evaluation={shown}
                focus={focus}
                onFocus={(lineId) => setChoices((c) => ({ ...c, lineId }))}
                onSelect={(lineId, ingredientId) =>
                  setChoices((c) => ({ ...c, lineId, selections: { ...c.selections, [lineId]: ingredientId } }))
                }
                onReset={(lineId) =>
                  setChoices((c) => {
                    const selections = { ...c.selections };
                    const ratios = { ...c.ratios };
                    delete selections[lineId];
                    delete ratios[lineId];
                    return { ...c, selections, ratios };
                  })
                }
                hasOverride={focus ? focus.line_id in choices.selections || focus.line_id in choices.ratios : false}
                ratio={focus ? (choices.ratios[focus.line_id] ?? 1) : 1}
                onRatio={(lineId, value) =>
                  setChoices((c) => ({ ...c, lineId, ratios: { ...c.ratios, [lineId]: value } }))
                }
              />
              <div className="grid lg:grid-cols-2 gap-6 items-start">
                <ModifiedRecipe recipe={shownRecipe} evaluation={shown} />
                <Comparison evaluation={shown} />
              </div>
              {focus && <NetworkGraph ingredientId={focus.ingredient_id} region={shownRecipe.region ?? ''} />}
            </div>
          )}
        </>
      )}

      <p className="font-mono2 text-[11px] text-[#a39b8b] max-w-3xl leading-relaxed">
        Data:{' '}
        {health.sources
          .filter((s) => s.status === 'loaded')
          .map((s, i) => (
            <span key={s.id}>
              {i > 0 && ' · '}
              <a href={s.url} target="_blank" rel="noreferrer" className="underline underline-offset-2 hover:text-[#efede9]">
                {s.name}
              </a>{' '}
              ({s.license})
            </span>
          ))}
        . Ingredient matching and cooking roles are curated by this project. Estimates are not dietary advice.
      </p>
    </div>
  );
}
