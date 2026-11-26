import { useState } from 'react';
import type { Evaluation, NutrientRow, RecipeDetail } from '@/lib/api';
import { Card, Notice, Pill } from './parts';
import { STATUS_LABEL, amount, grams, signed } from './format';

const MAIN = ['calories', 'satFat', 'protein', 'fiber', 'fat', 'carbs'];
// true: more is better · false: less is better · absent: no judgement made
const BETTER_IF_HIGHER: Record<string, boolean> = {
  calories: false, satFat: false, sodium: false, sugars: false, protein: true, fiber: true,
};

function tone(row: NutrientRow, change: number): string {
  const higher = BETTER_IF_HIGHER[row.key];
  if (higher === undefined || Math.abs(change) < 0.005) return 'text-[#efede9]';
  return change > 0 === higher ? 'text-[#a9bd80]' : 'text-[#f26522]';
}

export function ModifiedRecipe({ recipe, evaluation }: { recipe: RecipeDetail; evaluation: Evaluation }) {
  const swaps = new Map(evaluation.applied.map((s) => [s.line_id, s]));
  return (
    <Card
      title="5 · Modified recipe"
      aside={
        <span className="font-mono2 text-[10px] text-[#a39b8b]">
          {evaluation.applied.length} swap{evaluation.applied.length === 1 ? '' : 's'}
        </span>
      }
    >
      <ul className="mt-4 space-y-2">
        {recipe.ingredients.map((line) => {
          const swap = swaps.get(line.id);
          return (
            <li key={line.id} className="flex items-start gap-3 font-body text-[15px]">
              <span className={`mt-2.5 w-1.5 h-1.5 rounded-full shrink-0 ${swap ? 'bg-[#f26522]' : 'bg-[#a39b8b]/50'}`} />
              <span className="min-w-0 flex-1">
                {swap ? (
                  <>
                    <span className="line-through decoration-[#a39b8b]/70 text-[#a39b8b]">{line.original_phrase}</span>
                    <span className="mx-2 text-[#f26522] font-mono2 text-[12px]">→</span>
                    <span className="text-[#fdfdfd] font-medium">{swap.to_name}</span>
                    <span className="block font-mono2 text-[10px] text-[#a39b8b]">
                      {swap.chosen_by} · {swap.ratio_basis}
                    </span>
                    {!swap.eligible && (
                      <span className="block font-body text-[12px] text-[#f26522]">
                        This choice {swap.reasons.join('; ')}.
                      </span>
                    )}
                  </>
                ) : (
                  <span className="text-[#efede9]/80">{line.original_phrase}</span>
                )}
              </span>
              <span className="shrink-0 font-mono2 text-[11px] text-[#efede9]/70">
                {swap ? `≈ ${swap.new_grams.toFixed(0)} g` : grams(line.grams, line.grams_is_estimate)}
              </span>
            </li>
          );
        })}
      </ul>
      {evaluation.applied.length === 0 && (
        <p className="mt-3 font-mono2 text-[11px] text-[#a39b8b]">
          The recipe keeps its original ingredients for this scope and goal.
        </p>
      )}
      <p className="mt-4 font-body text-[12px] text-[#a39b8b]">
        These are nutritional suggestions. None has been cooked or taste-tested, and a swap may need method changes.
        Check allergens yourself.
      </p>
    </Card>
  );
}

export default function Comparison({ evaluation }: { evaluation: Evaluation }) {
  const [perServing, setPerServing] = useState(true);
  const useServing = perServing && evaluation.servings !== null;
  const scale = useServing ? 1 / evaluation.servings! : 1;
  const result = evaluation.goal_result;
  const { similarity, coverage } = evaluation;
  const rows = [...evaluation.comparison].sort((a, b) => {
    const rank = (row: NutrientRow) => (MAIN.includes(row.key) ? MAIN.indexOf(row.key) : MAIN.length);
    return rank(a) - rank(b);
  });
  const change =
    result.original === null || result.modified === null ? null : (result.modified - result.original) * scale;

  const table = (subset: NutrientRow[], bars: boolean) => (
    <table className="w-full font-mono2 text-[11px] md:text-[13px]">
      <thead className="sr-only">
        <tr>
          <th>Nutrient</th>
          <th>Original</th>
          <th>Modified</th>
          <th>Change</th>
          <th>Percent change</th>
        </tr>
      </thead>
      <tbody>
        {subset.map((row) => {
          const known = row.original !== null && row.modified !== null;
          const largest = known ? Math.max(row.original!, row.modified!) : 0;
          return (
            <tr key={row.key} className="border-b border-[#efede9]/10 last:border-0 align-top">
              <th scope="row" className="py-2.5 pr-2 text-left font-normal text-[#a39b8b] uppercase tracking-[0.08em] text-[10px]">
                {row.label}
                {row.lines_missing_value.length > 0 && known && (
                  <abbr
                    title={`${row.lines_missing_value.length} line(s) have no ${row.label.toLowerCase()} value and are left out of both totals.`}
                    className="ml-1 no-underline text-[#f2a07a]"
                  >
                    *
                  </abbr>
                )}
                {bars && known && largest > 0 && (
                  <span aria-hidden className="mt-1.5 block space-y-1">
                    <span className="block h-[4px] rounded-full bg-[#a39b8b]" style={{ width: `${(row.original! / largest) * 100}%` }} />
                    <span className="block h-[4px] rounded-full bg-[#f26522]" style={{ width: `${(row.modified! / largest) * 100}%` }} />
                  </span>
                )}
              </th>
              {known ? (
                <>
                  <td className="py-2.5 text-right text-[#efede9]/70 whitespace-nowrap">{amount(row.original! * scale)}</td>
                  <td className={`py-2.5 pl-3 text-right font-semibold whitespace-nowrap ${tone(row, row.change!)}`}>
                    {amount(row.modified! * scale)} {row.unit}
                  </td>
                  <td className={`py-2.5 pl-3 text-right whitespace-nowrap ${tone(row, row.change!)}`}>
                    {signed(row.change! * scale)}
                  </td>
                  <td className={`py-2.5 pl-3 text-right whitespace-nowrap ${tone(row, row.change!)}`}>
                    {signed(row.percent_change, '%')}
                  </td>
                </>
              ) : (
                <td colSpan={4} className="py-2.5 text-right text-[#a39b8b] italic">no data</td>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );

  return (
    <Card
      title={`6 · Original vs modified · ${useServing ? 'per serving' : 'whole recipe'}`}
      aside={
        evaluation.servings !== null ? (
          <div className="flex gap-2">
            <Pill active={perServing} onClick={() => setPerServing(true)}>Per serving</Pill>
            <Pill active={!perServing} onClick={() => setPerServing(false)}>Whole recipe</Pill>
          </div>
        ) : (
          <span className="font-mono2 text-[10px] text-[#a39b8b]">Servings unknown</span>
        )
      }
    >
      <div className="mt-4" aria-live="polite">
        {result.improved && change !== null ? (
          <p className="font-display font-semibold text-lg text-[#a9bd80]">
            {result.label}: {signed(change)} {result.unit} ({result.gain_percent.toFixed(1)}%{' '}
            {evaluation.goal.direction === 'min' ? 'lower' : 'higher'})
          </p>
        ) : (
          <p className="font-display font-semibold text-lg text-[#f2a07a]">
            {evaluation.applied.length === 0
              ? 'No swap applied, so nothing changes.'
              : `This selection does not improve: ${evaluation.goal.label.toLowerCase()}.`}
          </p>
        )}
        <p className="mt-1 font-body text-[13px] text-[#efede9]/70">
          This describes the chosen goal only. It does not make the recipe healthier overall.
        </p>
      </div>
      {evaluation.tradeoffs.length > 0 && (
        <div className="mt-3">
          <Notice tone="warn">
            Trade-offs (worse by more than 5%):{' '}
            {evaluation.tradeoffs
              .map((t) => `${t.label} ${signed(t.change * scale)} ${t.unit} (${signed(t.percent_change, '%')})`)
              .join('; ')}
            .
          </Notice>
        </div>
      )}

      <p className="mt-4 flex gap-4 font-mono2 text-[10px] text-[#a39b8b]">
        <span><span className="inline-block w-3 h-[4px] rounded-full bg-[#a39b8b] mr-1.5 align-middle" />original</span>
        <span><span className="inline-block w-3 h-[4px] rounded-full bg-[#f26522] mr-1.5 align-middle" />modified</span>
        <span className="ml-auto">before · after · change · %</span>
      </p>
      <div className="mt-1 overflow-x-auto">{table(rows.slice(0, MAIN.length), true)}</div>
      <details className="mt-2">
        <summary className="cursor-pointer min-h-[32px] font-mono2 text-[11px] text-[#a39b8b] hover:text-[#efede9]">
          Other available nutrients
        </summary>
        <div className="overflow-x-auto">{table(rows.slice(MAIN.length), false)}</div>
      </details>

      <div className="mt-5 flex flex-wrap gap-3">
        {(
          [
            ['Flavor similarity', similarity.flavor, similarity.flavor_swaps_with_data, '#efede9'],
            ['Cuisine compatibility', similarity.cuisine, similarity.cuisine_swaps_with_data, '#7a8b5a'],
          ] as const
        ).map(([label, value, known, color]) => (
          <div key={label} className="flex-1 min-w-[140px] bg-[#efede9] rounded-lg px-4 py-3">
            <p className="font-mono2 text-[10px] uppercase tracking-[0.14em] text-[#7d766a]">{label}</p>
            <p className="font-display font-bold text-3xl mt-1 text-[#3e3a32]">{value === null ? 'n/a' : value.toFixed(2)}</p>
            <div className="mt-1.5 h-[3px] w-10 rounded-full" style={{ background: color }} />
            <p className="mt-1.5 font-body text-[12px] text-[#575349]">
              {similarity.swaps === 0 ? 'No swaps' : `Swapped lines only · data for ${known} of ${similarity.swaps}`}
            </p>
          </div>
        ))}
      </div>

      {similarity.flavor_same_record_swaps > 0 && (
        <p className="mt-3 font-body text-[13px] text-[#f2a07a]">
          {similarity.flavor_same_record_swaps === 1
            ? '1 swap uses'
            : `${similarity.flavor_same_record_swaps} swaps use`}{' '}
          one FlavorDB2 record for both foods. A 1.00 there means FlavorDB2 cannot tell them apart, not that they taste
          the same.
        </p>
      )}

      <div className="mt-4 font-body text-[13px] text-[#efede9]/70">
        <p>
          Estimates from raw-ingredient records for {coverage.counted_lines} of {coverage.total_lines} lines. Cooking
          losses and absorbed oil are not modelled. * means some lines lack that value.
        </p>
        {coverage.excluded.length > 0 && (
          <details className="mt-1">
            <summary className="cursor-pointer min-h-[28px] font-mono2 text-[11px] text-[#a39b8b] hover:text-[#efede9]">
              Lines left out of the totals
            </summary>
            <ul className="mt-1">
              {coverage.excluded.map((line) => (
                <li key={line.line_id}>
                  {line.phrase} <span className="text-[#a39b8b]">({STATUS_LABEL[line.reason]})</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </Card>
  );
}
