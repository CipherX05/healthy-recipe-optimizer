import { useState } from 'react';
import {
  RECIPES, GOALS, INGREDIENTS, CUISINE_LABEL, DEMO_EXAMPLE,
  rankCandidates, optimizeRecipe, recipeNutrition, recipeSimilarity,
  type Goal, type GoalId, type Nutrients,
} from '@/data/food';
import { useRevealRoot } from '@/hooks/useReveal';
import { useCountUp } from '@/hooks/useCountUp';
import LoraPanel from '@/components/LoraPanel';

const fmt = (v: number) => v.toFixed(1);
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const changeArrow = (change: number) => (change > 0 ? '↑' : change < 0 ? '↓' : '·');

function ScoreBar({ label, value, color, delay }: { label: string; value: number; color: string; delay: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="font-mono2 text-[10px] uppercase tracking-[0.14em] text-[#a39b8b] w-16 shrink-0">{label}</span>
      <div className="flex-1 h-[6px] rounded-full bg-[#575349]/10 overflow-hidden">
        <div className="bar-fill h-full rounded-full" style={{ width: `${value * 100}%`, background: color, transitionDelay: `${delay}ms` }} />
      </div>
      <span className="font-mono2 text-[11px] text-[#efede9]/85 w-9 text-right">{value.toFixed(2)}</span>
    </div>
  );
}

function Gauge({ label, value, color }: { label: string; value: number; color: string }) {
  const v = useCountUp(value, true, 1100);
  return (
    <div className="flex-1 min-w-[130px] bg-[#efede9] rounded-lg px-5 py-4">
      <p className="font-mono2 text-[10px] uppercase tracking-[0.16em] text-[#a39b8b]">{label}</p>
      <p className="font-display font-bold text-3xl mt-1 text-[#3e3a32]">{v.toFixed(2)}</p>
      <div className="mt-2 h-[3px] w-10 rounded-full" style={{ background: color }} />
    </div>
  );
}

const NUTRIENT_ROWS: { key: keyof Nutrients; label: string; unit: string; better: 'min' | 'max' }[] = [
  { key: 'calories', label: 'Calories', unit: 'kcal', better: 'min' },
  { key: 'satFat', label: 'Saturated fat', unit: 'g', better: 'min' },
  { key: 'protein', label: 'Protein', unit: 'g', better: 'max' },
  { key: 'fiber', label: 'Fiber', unit: 'g', better: 'max' },
];

const SCOPES = [
  { id: 'ingredient', label: 'Selected ingredient only' },
  { id: 'recipe', label: 'Whole recipe' },
] as const;

export default function Optimizer() {
  const rootRef = useRevealRoot<HTMLElement>();
  const [recipeId, setRecipeId] = useState<string>(DEMO_EXAMPLE.recipeId);
  const [goalId, setGoalId] = useState<GoalId>(DEMO_EXAMPLE.goalId);
  const [ingredientId, setIngredientId] = useState<string>(DEMO_EXAMPLE.ingredientId);
  const [scope, setScope] = useState<(typeof SCOPES)[number]['id']>('ingredient');
  const [runId, setRunId] = useState(0); // bump to re-run animation

  const recipe = RECIPES.find((r) => r.id === recipeId)!;
  const goal: Goal = GOALS.find((g) => g.id === goalId)!;
  const replaceable = recipe.items.filter((i) => i.replaceable);
  const item = recipe.items.find((i) => i.ingredientId === ingredientId && i.replaceable) ?? replaceable[0];

  // D1 and D2 share the same selection so the badge agrees with the applied swap.
  const ranked = rankCandidates(recipe, item, goal);
  const opt = optimizeRecipe(recipe, goal, scope === 'ingredient' ? item.ingredientId : undefined);
  const recommendedId = opt.subs[item.ingredientId] ?? null;
  // D3 evaluates the complete recipe before and after the swaps in scope.
  const before = recipeNutrition(recipe);
  const after = recipeNutrition(recipe, opt.subs);
  const sim = recipeSimilarity(recipe, opt);

  const chooseRecipe = (id: string) => {
    setRecipeId(id);
    const r = RECIPES.find((x) => x.id === id)!;
    const exampleIngredient = r.id === DEMO_EXAMPLE.recipeId ? DEMO_EXAMPLE.ingredientId : undefined;
    setIngredientId(exampleIngredient ?? r.items.find((i) => i.replaceable)!.ingredientId);
  };

  const goalChange = after[goal.id] - before[goal.id];
  const goalChangeFraction = Math.abs(goalChange) / Math.max(before[goal.id], 1e-6);

  return (
    <section id="demo" ref={rootRef} className="py-24 md:py-36 bg-[#3e3a32] text-[#efede9]">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="reveal flex items-baseline gap-4">
          <span className="font-mono2 text-[12px] text-[#f26522]">04</span>
          <p className="eyebrow" style={{ color: '#a39b8b' }}>Live demo — Deliverable 4</p>
          <span className="flex-1" style={{ borderTop: '1px solid rgba(239,237,233,0.25)' }} />
        </div>

        <h2 className="reveal mt-10 font-display font-semibold tracking-tight text-[#fdfdfd] text-3xl md:text-[2.6rem] leading-[1.1] max-w-2xl">
          The optimizer, running in your browser.
        </h2>
        <p className="reveal mt-5 font-body text-[#efede9]/75 max-w-2xl">
          Pick a recipe, an ingredient and a health goal. Compare one ingredient swap or
          optimize every replaceable ingredient using the built-in demo data.
        </p>

        {/* ── controls ── */}
        <div className="reveal mt-12 grid md:grid-cols-3 gap-6 md:gap-8">
          <div>
            <p className="font-mono2 text-[10px] uppercase tracking-[0.2em] text-[#a39b8b] mb-3">Recipe</p>
            <div className="flex flex-wrap gap-2">
              {RECIPES.map((r) => (
                <button
                  key={r.id}
                  aria-pressed={r.id === recipeId}
                  onClick={() => chooseRecipe(r.id)}
                  className={`min-h-[44px] px-4 rounded-full font-mono2 text-[12px] transition-colors border ${
                    r.id === recipeId
                      ? 'bg-[#f26522] border-[#f26522] text-white'
                      : 'border-[#efede9]/25 text-[#efede9]/80 hover:border-[#efede9]/60'
                  }`}
                >
                  {r.name}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="font-mono2 text-[10px] uppercase tracking-[0.2em] text-[#a39b8b] mb-3">Ingredient to replace</p>
            <div className="flex flex-wrap gap-2">
              {replaceable.map((i) => (
                <button
                  key={i.ingredientId}
                  aria-pressed={i.ingredientId === item.ingredientId}
                  onClick={() => setIngredientId(i.ingredientId)}
                  className={`min-h-[44px] px-4 rounded-full font-mono2 text-[12px] transition-colors border ${
                    i.ingredientId === item.ingredientId
                      ? 'bg-[#efede9] border-[#efede9] text-[#3e3a32]'
                      : 'border-[#efede9]/25 text-[#efede9]/80 hover:border-[#efede9]/60'
                  }`}
                >
                  {INGREDIENTS[i.ingredientId].name}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="font-mono2 text-[10px] uppercase tracking-[0.2em] text-[#a39b8b] mb-3">Health goal</p>
            <div className="flex flex-wrap gap-2">
              {GOALS.map((g) => (
                <button
                  key={g.id}
                  aria-pressed={g.id === goalId}
                  onClick={() => setGoalId(g.id)}
                  className={`min-h-[44px] px-4 rounded-full font-mono2 text-[12px] transition-colors border ${
                    g.id === goalId
                      ? 'bg-[#7a8b5a] border-[#7a8b5a] text-white'
                      : 'border-[#efede9]/25 text-[#efede9]/80 hover:border-[#efede9]/60'
                  }`}
                >
                  {g.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="reveal mt-8 flex flex-wrap items-end gap-5">
          <fieldset>
            <legend className="font-mono2 text-[10px] uppercase tracking-[0.2em] text-[#a39b8b] mb-3">Optimization scope</legend>
            <div className="flex flex-wrap gap-2">
              {SCOPES.map((choice) => (
                <button
                  key={choice.id}
                  aria-pressed={scope === choice.id}
                  onClick={() => setScope(choice.id)}
                  className={`min-h-[44px] px-4 rounded-full font-mono2 text-[12px] transition-colors border ${
                    scope === choice.id
                      ? 'bg-[#efede9] border-[#efede9] text-[#3e3a32]'
                      : 'border-[#efede9]/25 text-[#efede9]/80 hover:border-[#efede9]/60'
                  }`}
                >
                  {choice.label}
                </button>
              ))}
            </div>
          </fieldset>
          <button
            onClick={() => {
              setRunId((n) => n + 1);
              document.getElementById('demo-results')?.scrollIntoView();
            }}
            className="w-full sm:w-auto min-h-[44px] px-8 rounded-full bg-[#f26522] text-white font-mono2 text-[13px] uppercase tracking-[0.18em] hover:bg-[#d9541a] active:scale-[0.98] transition-all"
          >
            Optimize ↓
          </button>
        </div>

        {/* ── results ── */}
        <div id="demo-results" key={`${runId}-${recipeId}-${ingredientId}-${goalId}-${scope}`} className="mt-10 scroll-mt-20 grid lg:grid-cols-2 gap-6">
          {/* D1 ranked substitutes */}
          <div className="rise-in bg-[#4a463e] rounded-lg p-6 md:p-7">
            <header className="flex items-center justify-between gap-4 pb-4" style={{ borderBottom: '1px solid rgba(239,237,233,0.18)' }}>
              <span className="font-mono2 text-[10px] uppercase tracking-[0.2em] text-[#a39b8b]">
                D1 · Ranked substitutes for {INGREDIENTS[item.ingredientId].name}
              </span>
              <span className="font-mono2 text-[10px] px-2.5 py-1 rounded-full bg-[#f26522] text-white uppercase tracking-[0.12em]">
                {goal.label}
              </span>
            </header>
            <p className="mt-4 font-body text-[14px] leading-snug text-[#efede9]/75">
              {recommendedId
                ? `${INGREDIENTS[recommendedId].name} has the highest score among candidates that improve the target nutrient by more than 2% at the same weight.`
                : 'Each candidate falls short of the nutrition requirement for this ingredient.'}
            </p>
            <ol className="mt-5 space-y-5">
              {ranked.map((c, i) => (
                <li key={c.ingredient.id} className={c.ingredient.id === recommendedId ? '' : 'opacity-90'}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="font-display font-semibold text-[15px] md:text-base text-[#fdfdfd]">
                      <span className="font-mono2 text-[11px] text-[#a39b8b] mr-2">{i + 1}.</span>
                      {c.ingredient.name}
                      {c.ingredient.id === recommendedId && (
                        <span className="ml-2 font-mono2 text-[9px] uppercase tracking-[0.14em] text-[#f26522] border border-[#f26522]/60 rounded-full px-2 py-0.5 align-middle">
                          recommended
                        </span>
                      )}
                    </span>
                    <span className={`font-mono2 text-[12px] whitespace-nowrap ${c.improvement > 0 ? 'text-[#7a8b5a]' : c.improvement < 0 ? 'text-[#f26522]' : 'text-[#a39b8b]'}`}>
                      {changeArrow(goal.direction === 'min' ? -c.improvement : c.improvement)}{' '}
                      {pct(Math.abs(c.improvement))} <span className="text-[#a39b8b]">{goal.id === 'satFat' ? 'sat. fat' : goal.id}</span>
                    </span>
                  </div>
                  <div className="mt-2.5 space-y-1.5">
                    <ScoreBar label="Flavor" value={c.flavor} color="#efede9" delay={100 + i * 120} />
                    <ScoreBar label="Nutrition" value={c.nutrition} color="#f26522" delay={160 + i * 120} />
                    <ScoreBar label="Cuisine" value={c.cuisine} color="#7a8b5a" delay={220 + i * 120} />
                    <ScoreBar label="Role" value={c.category} color="#a39b8b" delay={250 + i * 120} />
                    <ScoreBar label="Overall" value={c.overall} color="#fdfdfd" delay={280 + i * 120} />
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <div className="space-y-6">
            {/* D2 optimized recipe */}
            <div className="rise-in bg-[#4a463e] rounded-lg p-6 md:p-7" style={{ animationDelay: '120ms' }}>
              <header className="flex items-center justify-between gap-4 pb-4" style={{ borderBottom: '1px solid rgba(239,237,233,0.18)' }}>
                <span className="font-mono2 text-[10px] uppercase tracking-[0.2em] text-[#a39b8b]">D2 · Optimized {recipe.name}</span>
                <span className="font-mono2 text-[10px] text-[#a39b8b]">{CUISINE_LABEL[recipe.cuisine]} · serves {recipe.serves}</span>
              </header>
              <p className="mt-3 font-mono2 text-[11px] text-[#efede9]/70">
                {scope === 'ingredient' ? 'Selected ingredient only' : 'Whole recipe'}
              </p>
              <ul className="mt-4 space-y-2">
                {recipe.items.map((i) => {
                  const sub = opt.subs[i.ingredientId];
                  const orig = INGREDIENTS[i.ingredientId];
                  return (
                    <li key={i.ingredientId} className="flex items-center gap-3 font-body text-[15px] min-h-[28px]">
                      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${sub ? 'bg-[#f26522]' : 'bg-[#a39b8b]/50'}`} />
                      {sub ? (
                        <span>
                          <span className="line-through decoration-[#a39b8b]/70 text-[#a39b8b]">{orig.name}</span>
                          <span className="mx-2 text-[#f26522] font-mono2 text-[12px]">→</span>
                          <span className="text-[#fdfdfd] font-medium">{INGREDIENTS[sub].name}</span>
                        </span>
                      ) : (
                        <span className="text-[#efede9]/80">{orig.name}</span>
                      )}
                      <span className="ml-auto shrink-0 font-mono2 text-[11px] text-[#efede9]/70">{i.grams} g</span>
                    </li>
                  );
                })}
              </ul>
              {opt.swaps.length === 0 && (
                <p className="mt-3 font-mono2 text-[11px] text-[#a39b8b]">
                  The recipe keeps its original ingredients for this scope and goal.
                </p>
              )}
            </div>

            {/* D3 evaluation */}
            <div className="rise-in bg-[#4a463e] rounded-lg p-6 md:p-7" style={{ animationDelay: '220ms' }}>
              <header className="flex items-center justify-between gap-4 pb-4" style={{ borderBottom: '1px solid rgba(239,237,233,0.18)' }}>
                <span className="font-mono2 text-[10px] uppercase tracking-[0.2em] text-[#a39b8b]">D3 · Evaluation · per serving</span>
                <span className="font-mono2 text-[13px] font-semibold text-[#7a8b5a]">
                  {changeArrow(goalChange)} {pct(goalChangeFraction)} {goal.id === 'satFat' ? 'sat. fat' : goal.id}
                </span>
              </header>
              <table className="w-full mt-4 font-mono2 text-[12px] md:text-[13px]">
                <tbody>
                  {NUTRIENT_ROWS.map((row) => {
                    const b = before[row.key] / recipe.serves;
                    const a = after[row.key] / recipe.serves;
                    const change = a - b;
                    const improvement = row.better === 'min' ? -change : change;
                    const good = improvement > 0.01;
                    const bad = improvement < -0.01;
                    return (
                      <tr key={row.key} className="border-b border-[#efede9]/8 last:border-0">
                        <td className="py-2.5 text-[#a39b8b] uppercase tracking-[0.1em] text-[10px]">{row.label}</td>
                        <td className="py-2.5 text-right text-[#efede9]/70">{fmt(b)} {row.unit}</td>
                        <td className="py-2.5 text-center text-[#a39b8b]">→</td>
                        <td className={`py-2.5 text-right font-semibold ${good ? 'text-[#7a8b5a]' : bad ? 'text-[#f26522]' : 'text-[#efede9]'}`}>
                          {fmt(a)} {row.unit}
                        </td>
                        <td className={`py-2.5 text-right w-16 ${good ? 'text-[#7a8b5a]' : bad ? 'text-[#f26522]' : 'text-[#a39b8b]'}`}>
                          {changeArrow(good || bad ? change : 0)} {b > 0.05 ? pct(Math.abs(change / b)) : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="mt-5 flex flex-wrap gap-3">
                <Gauge label="Flavor similarity" value={sim.flavor} color="#efede9" />
                <Gauge label="Cuisine consistency" value={sim.cuisine} color="#7a8b5a" />
              </div>
            </div>
          </div>
        </div>

        {/* LoRA Model Comparison Panel */}
        <LoraPanel
          recipeId={recipeId}
          ingredientId={item.ingredientId}
          goalId={goalId}
          recipeName={recipe.name}
          ingredientName={INGREDIENTS[item.ingredientId].name}
          goalLabel={goal.label}
          liveRecommendationId={recommendedId}
        />

        <p className="reveal mt-10 font-mono2 text-[11px] text-[#a39b8b] max-w-2xl leading-relaxed">
          Demo data: nutrition per 100 g (USDA-style values), 6-dimension flavor vectors in the
          spirit of FlavorDB, and hand-tuned cuisine affinities. The final system scales the same
          scoring to full recipe and flavor databases.
        </p>
      </div>
    </section>
  );
}
