import { useCallback, useState } from 'react';
import { api } from '@/lib/api';
import { useAsync } from '@/hooks/useAsync';
import { useDebounced } from '@/hooks/useDebounced';
import { Card, Notice, inputClass } from './parts';

const PAGE = 8;

export default function RecipeSearch({
  selectedId,
  onSelect,
}: {
  selectedId: number | null;
  onSelect: (id: number) => void;
}) {
  const [q, setQ] = useState('');
  const [region, setRegion] = useState('');
  const [ingredient, setIngredient] = useState('');
  const [offset, setOffset] = useState(0);
  const query = useDebounced(q.trim());
  const containing = useDebounced(ingredient.trim());

  const regions = useAsync(useCallback((signal: AbortSignal) => api.regions(signal), []));
  const results = useAsync(
    useCallback(
      (signal: AbortSignal) =>
        api.search({ q: query, region, ingredient: containing, limit: PAGE, offset }, signal),
      [query, region, containing, offset],
    ),
  );
  const total = results.data?.total ?? 0;

  const change = (setter: (value: string) => void) => (value: string) => {
    setter(value);
    setOffset(0);
  };

  return (
    <Card
      title="1 · Find a recipe"
      aside={
        <span className="font-mono2 text-[11px] text-[#efede9]/70" aria-live="polite">
          {results.loading ? 'Searching…' : `${total.toLocaleString()} recipes`}
        </span>
      }
    >
      <div className="mt-4 grid sm:grid-cols-3 gap-3">
        <input
          type="search"
          aria-label="Search recipe titles"
          placeholder="Title, e.g. butter chicken"
          maxLength={120}
          value={q}
          onChange={(e) => change(setQ)(e.target.value)}
          className={inputClass}
        />
        <select
          aria-label="Filter by cuisine"
          value={region}
          onChange={(e) => change(setRegion)(e.target.value)}
          className={inputClass}
        >
          <option value="">All cuisines</option>
          {regions.data?.map((r) => (
            <option key={r.region} value={r.region}>
              {r.region} ({r.recipes})
            </option>
          ))}
        </select>
        <input
          type="search"
          aria-label="Filter by ingredient"
          placeholder="Contains ingredient…"
          maxLength={80}
          value={ingredient}
          onChange={(e) => change(setIngredient)(e.target.value)}
          className={inputClass}
        />
      </div>

      {results.error && (
        <div className="mt-4">
          <Notice tone="warn">{results.error}</Notice>
        </div>
      )}
      {results.data && total === 0 && (
        <p className="mt-4 font-body text-[14px] text-[#efede9]/75">
          No imported recipe matches. Try fewer words, or import more recipes (see backend/README.md).
        </p>
      )}

      <ul className="mt-4 grid sm:grid-cols-2 gap-2">
        {results.data?.results.map((r) => (
          <li key={r.id}>
            <button
              type="button"
              aria-pressed={r.id === selectedId}
              onClick={() => onSelect(r.id)}
              className={`w-full h-full text-left min-h-[56px] rounded-lg border px-4 py-2.5 transition-colors ${
                r.id === selectedId
                  ? 'bg-[#f26522] border-[#f26522] text-white'
                  : 'border-[#efede9]/20 text-[#efede9] hover:border-[#efede9]/60'
              }`}
            >
              <span className="block font-display font-medium text-[14px] leading-snug">{r.title}</span>
              <span className="block mt-1 font-mono2 text-[10px] opacity-75">
                {r.region ?? 'Cuisine unknown'} · nutrition for {r.counted_lines}/{r.ingredient_lines} lines
              </span>
            </button>
          </li>
        ))}
      </ul>

      {total > PAGE && (
        <div className="mt-4 flex items-center justify-between gap-3 font-mono2 text-[11px]">
          <button
            type="button"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - PAGE))}
            className="min-h-[44px] px-4 rounded-full border border-[#efede9]/25 disabled:opacity-35"
          >
            ← Previous
          </button>
          <span className="text-[#a39b8b]">
            {offset + 1}–{Math.min(offset + PAGE, total)} of {total.toLocaleString()}
          </span>
          <button
            type="button"
            disabled={offset + PAGE >= total}
            onClick={() => setOffset(offset + PAGE)}
            className="min-h-[44px] px-4 rounded-full border border-[#efede9]/25 disabled:opacity-35"
          >
            Next →
          </button>
        </div>
      )}
      <p className="mt-3 font-body text-[13px] text-[#a39b8b]">
        Recipes with the most complete nutrition data are listed first.
      </p>
    </Card>
  );
}
