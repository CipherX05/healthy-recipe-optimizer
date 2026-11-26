import type { RecipeDetail, RecipeLine } from '@/lib/api';
import { Card, Label, Notice } from './parts';
import { SOURCE_LABEL, STATUS_LABEL, amount, grams } from './format';

function Provenance({ line }: { line: RecipeLine }) {
  const item = line.ingredient;
  const rows: [string, string][] = [
    ['Original line', line.original_phrase],
    ['Standardized name', line.standardized_name],
    [
      'Name match',
      line.ingredient_id
        ? `${line.match_method.replace(/_/g, ' ')} · confidence ${line.match_confidence.toFixed(2)}${
            line.match_note ? ` · ${line.match_note}` : ''
          }`
        : line.match_note,
    ],
    ['Grams', line.grams === null ? line.grams_note : `${line.grams_note} (${line.grams_method.replace(/_/g, ' ')})`],
  ];
  if (item) {
    rows.push([
      'Nutrition',
      item.nutrition_source
        ? `${SOURCE_LABEL[item.nutrition_source] ?? item.nutrition_source} #${item.source_food_id}: ${
            item.source_food_name
          }${item.nutrition_match === 'proxy' ? ' (stand-in record)' : ''}${
            item.nutrition_note ? `. ${item.nutrition_note}` : ''
          }`
        : 'No nutrition record',
    ]);
    if (item.per_100g.calories !== undefined) {
      rows.push([
        'Per 100 g',
        `${amount(item.per_100g.calories)} kcal · sat. fat ${amount(item.per_100g.satFat)} g · protein ${amount(
          item.per_100g.protein,
        )} g · fiber ${amount(item.per_100g.fiber)} g`,
      ]);
    }
    rows.push([
      'Flavor',
      item.flavor_entity
        ? `FlavorDB2 “${item.flavor_entity}”, ${item.flavor_molecules} molecules${
            item.flavor_match === 'proxy' ? ' (stand-in entity)' : ''
          }${item.flavor_usable ? '' : '. Too few to compare flavors'}`
        : 'No FlavorDB2 data',
    ]);
  }
  return (
    <dl className="mt-2 mb-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[12px] font-body text-[#efede9]/75">
      {rows.map(([term, value]) => (
        <div key={term} className="contents">
          <dt className="font-mono2 text-[10px] uppercase tracking-[0.1em] text-[#a39b8b] pt-0.5">{term}</dt>
          <dd className="min-w-0 break-words">{value || '—'}</dd>
        </div>
      ))}
    </dl>
  );
}

export default function RecipeDetails({ recipe }: { recipe: RecipeDetail }) {
  const { coverage } = recipe;
  return (
    <Card
      title="2 · Recipe"
      aside={
        <span className="font-mono2 text-[10px] text-[#a39b8b]">
          {[recipe.region, recipe.sub_region !== recipe.region ? recipe.sub_region : null]
            .filter(Boolean)
            .join(' · ') || 'Cuisine unknown'}
        </span>
      }
    >
      <h4 className="mt-4 font-display font-semibold text-xl md:text-2xl text-[#fdfdfd]">{recipe.title}</h4>
      <p className="mt-2 font-mono2 text-[11px] text-[#efede9]/70">
        {recipe.servings
          ? `Serves ${recipe.servings}${recipe.servings_estimated ? ` (midpoint of ${recipe.servings_raw})` : ''}`
          : 'Servings unknown'}
        {recipe.total_minutes ? ` · ${recipe.total_minutes} min` : ''}
        {recipe.diet_tags.length ? ` · ${recipe.diet_tags.join(', ')} (RecipeDB tag)` : ''}
      </p>

      <div className="mt-4">
        <Notice tone={coverage.fraction < 0.7 ? 'warn' : 'info'}>
          Nutrition estimates cover <strong>{coverage.counted_lines} of {coverage.total_lines}</strong> ingredient
          lines. The others are left out of every total, not counted as zero.
          {coverage.fraction < 0.7 && ' Treat the totals for this recipe with particular caution.'}
        </Notice>
      </div>

      <div className="mt-5 grid lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 min-w-0">
          <Label>Ingredients · select a line to see where its data comes from</Label>
          <ul className="space-y-1">
            {recipe.ingredients.map((line) => (
              <li key={line.id} style={{ borderBottom: '1px solid rgba(239,237,233,0.08)' }}>
                <details>
                  <summary className="flex items-center gap-3 min-h-[40px] cursor-pointer list-none">
                    <span
                      aria-hidden
                      className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                        line.missing_status === 'ok' ? 'bg-[#7a8b5a]' : 'bg-[#f26522]'
                      }`}
                    />
                    <span className="font-body text-[15px] min-w-0 flex-1">{line.original_phrase}</span>
                    {line.missing_status !== 'ok' && (
                      <span className="font-mono2 text-[9px] uppercase tracking-[0.1em] text-[#f26522] text-right">
                        {STATUS_LABEL[line.missing_status]}
                      </span>
                    )}
                    <span className="font-mono2 text-[11px] text-[#efede9]/70 w-16 text-right shrink-0">
                      {grams(line.grams, line.grams_is_estimate)}
                    </span>
                  </summary>
                  <Provenance line={line} />
                </details>
              </li>
            ))}
          </ul>
          <p className="mt-2 font-body text-[12px] text-[#a39b8b]">
            ≈ marks grams estimated from household measures. Quantities come from RecipeDB.
          </p>
        </div>

        <div className="lg:col-span-2 min-w-0">
          <Label>Instructions</Label>
          {recipe.instructions ? (
            <p className="font-body text-[15px] whitespace-pre-line text-[#efede9]/85">{recipe.instructions}</p>
          ) : (
            <p className="font-body text-[14px] text-[#efede9]/75">
              RecipeDB did not provide written instructions for this recipe.
              {recipe.source_url && (
                <>
                  {' '}
                  <a
                    href={recipe.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="underline decoration-[#f26522] underline-offset-2 hover:text-white"
                  >
                    Try the original page{recipe.source_site ? ` (${recipe.source_site})` : ''}
                  </a>
                  . Older links may no longer work.
                </>
              )}
            </p>
          )}
          {recipe.processes.length > 0 && (
            <div className="mt-5">
              <Label>Cooking processes, in RecipeDB order</Label>
              <ol className="flex flex-wrap gap-1.5">
                {recipe.processes.map((step, index) => (
                  <li
                    key={`${step}-${index}`}
                    className="font-mono2 text-[10px] px-2 py-1 rounded bg-[#3e3a32] text-[#efede9]/80"
                  >
                    {index + 1}. {step}
                  </li>
                ))}
              </ol>
            </div>
          )}
          {recipe.utensils.length > 0 && (
            <p className="mt-4 font-body text-[13px] text-[#efede9]/70">
              Utensils: {recipe.utensils.join(', ')}
            </p>
          )}
          {recipe.detail_url && (
            <a
              href={recipe.detail_url}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-flex min-h-[44px] items-center font-mono2 text-[11px] text-[#a39b8b] hover:text-[#f26522]"
            >
              View in RecipeDB ↗
            </a>
          )}
        </div>
      </div>
    </Card>
  );
}
