import { useRevealRoot } from '@/hooks/useReveal';
import { DEMO_EXAMPLE, GOALS, RECIPES, optimizeRecipe, recipeNutrition } from '@/data/food';

const exampleRecipe = RECIPES.find((recipe) => recipe.id === DEMO_EXAMPLE.recipeId)!;
const exampleGoal = GOALS.find((goal) => goal.id === DEMO_EXAMPLE.goalId)!;
const example = optimizeRecipe(exampleRecipe, exampleGoal, DEMO_EXAMPLE.ingredientId);
const swap = example.swaps[0];
const before = recipeNutrition(exampleRecipe).satFat / exampleRecipe.serves;
const after = recipeNutrition(exampleRecipe, example.subs).satFat / exampleRecipe.serves;
const reduction = ((before - after) / before * 100).toFixed(1);

export default function Problem() {
  const ref = useRevealRoot<HTMLElement>();

  return (
    <section id="problem" ref={ref} className="py-24 md:py-36">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="reveal flex items-baseline gap-4">
          <span className="font-mono2 text-[12px] text-[#f26522]">01</span>
          <p className="eyebrow">The problem</p>
          <span className="flex-1 rule" />
        </div>

        <div className="mt-10 grid md:grid-cols-12 gap-10 md:gap-14">
          <div className="md:col-span-7">
            <h2 className="reveal font-display font-semibold tracking-tight text-[#3e3a32] text-3xl md:text-[2.6rem] leading-[1.12]">
              If I replace an ingredient, what is the best replacement to make the recipe
              healthier — <em className="not-italic text-[#f26522]">without changing its flavor
              and cuisine too much?</em>
            </h2>
            <p className="reveal font-body mt-8 text-[#575349]/90 max-w-xl" data-delay="80">
              Most existing work stops at “what can replace X?” or “how do I make this
              healthier?”. This project asks a harder question: which replacement gives the
              best health improvement <em>while still being appropriate for this particular
              recipe and cuisine</em>. The answer depends on context — not just on whichever
              ingredient has the fewest calories.
            </p>
            <p className="reveal font-body mt-5 text-[#575349]/90 max-w-xl" data-delay="140">
              A technically healthy but unrecognizable result — Butter Chicken turned into
              a salad — is not useful. The optimized recipe must still resemble the original.
            </p>
          </div>

          <div className="md:col-span-5">
            <div className="reveal bg-[#efede9] rounded-lg p-6 md:p-8" data-delay="120">
              <p className="eyebrow mb-5">Worked example · offline demo data</p>
              <dl className="font-mono2 text-[13px] space-y-2.5 text-[#575349]">
                <div className="flex justify-between gap-4"><dt className="text-[#a39b8b]">Recipe</dt><dd>{exampleRecipe.name}</dd></div>
                {swap && (
                  <>
                    <div className="flex justify-between gap-4"><dt className="text-[#a39b8b]">Replace</dt><dd>{swap.grams} g {swap.from.name.toLowerCase()}</dd></div>
                    <div className="flex justify-between gap-4"><dt className="text-[#a39b8b]">With</dt><dd>{swap.grams} g {swap.to.name.toLowerCase()}</dd></div>
                  </>
                )}
                <div className="flex justify-between gap-4"><dt className="text-[#a39b8b]">Goal</dt><dd>↓ saturated fat</dd></div>
              </dl>
              <div className="rule mt-6 pt-6 space-y-2.5 font-mono2 text-[13px] text-[#575349]">
                <div className="flex justify-between gap-4"><span className="text-[#a39b8b]">Sat. fat per serving</span><span>{before.toFixed(1)} g → {after.toFixed(1)} g</span></div>
                <div className="flex justify-between gap-4"><span className="text-[#a39b8b]">Cream-only reduction</span><span className="text-[#4a5636]">↓ {reduction}%</span></div>
              </div>
            </div>

            <div className="reveal mt-5 border border-[#575349]/25 rounded-lg px-6 py-5 text-center" data-delay="200">
              <span className="font-mono2 text-[13px] md:text-[15px] tracking-[0.08em] text-[#3e3a32]">
                HEALTH <span className="text-[#f26522]">+</span> FLAVOR <span className="text-[#f26522]">+</span> CUISINE
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
