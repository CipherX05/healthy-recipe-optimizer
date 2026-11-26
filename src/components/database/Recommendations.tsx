import type { Candidate, Evaluation, Recommendation, ScoreKey } from '@/lib/api';
import { ScoreBar } from '@/components/optimizer/shared';
import { Card, Label, Pill } from './parts';
import { signed } from './format';

const BARS: { key: ScoreKey; label: string; color: string }[] = [
  { key: 'health', label: 'Health', color: '#f26522' },
  { key: 'flavor', label: 'Flavor', color: '#efede9' },
  { key: 'cuisine', label: 'Cuisine', color: '#7a8b5a' },
  { key: 'role', label: 'Role', color: '#a39b8b' },
];

function Evidence({ candidate }: { candidate: Candidate }) {
  const flavor = candidate.flavor_detail;
  const cuisine = candidate.cuisine_detail;
  return (
    <ul className="mt-2 space-y-0.5 font-body text-[12px] text-[#efede9]/65">
      <li>
        {flavor
          ? `Flavor: ${flavor.shared} of ${flavor.union} molecules shared (FlavorDB2 “${flavor.original_entity}” vs “${
              flavor.candidate_entity
            }”)${flavor.same_entity ? '. Same FlavorDB2 record, so it cannot tell these two apart' : ''}${
              flavor.proxy ? '. Includes a stand-in entity' : ''
            }.`
          : `Flavor: not enough data (${candidate.flavor_gap}), so this score earns no points.`}
      </li>
      <li>
        {candidate.scores.cuisine !== null
          ? `Cuisine: used in ${cuisine.recipes_using} of ${cuisine.region_recipes} imported ${cuisine.region} recipes.`
          : 'Cuisine: too few imported recipes of this cuisine to score it.'}
      </li>
      {candidate.notes.map((note) => (
        <li key={note} className="text-[#efede9]/80">
          ⚠ {note}
        </li>
      ))}
    </ul>
  );
}

function CandidateRow({
  candidate,
  rank,
  goalLabel,
  applied,
  recommended,
  onUse,
}: {
  candidate: Candidate;
  rank: number | null;
  goalLabel: string;
  applied: boolean;
  recommended: boolean;
  onUse: () => void;
}) {
  return (
    <li
      className={`rounded-lg border p-4 ${applied ? 'border-[#f26522] bg-[#3e3a32]/70' : 'border-[#efede9]/12'}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-display font-semibold text-[15px] md:text-base text-[#fdfdfd]">
          {rank !== null && <span className="font-mono2 text-[11px] text-[#a39b8b] mr-2">{rank}.</span>}
          {candidate.name}
          {recommended && (
            <span className="ml-2 font-mono2 text-[9px] uppercase tracking-[0.14em] text-[#f26522] border border-[#f26522]/60 rounded-full px-2 py-0.5 align-middle">
              recommended
            </span>
          )}
        </span>
        <button
          type="button"
          onClick={onUse}
          aria-pressed={applied}
          aria-label={applied ? `${candidate.name} is applied` : `Use ${candidate.name}`}
          className={`min-h-[40px] px-4 rounded-full border font-mono2 text-[11px] ${
            applied ? 'bg-[#f26522] border-[#f26522] text-white' : 'border-[#efede9]/30 hover:border-[#efede9]/70'
          }`}
        >
          {applied ? '✓ Applied' : 'Use this'}
        </button>
      </div>
      <p className="mt-1 font-mono2 text-[11px]">
        <span className={candidate.recipe_gain_percent > 0 ? 'text-[#a9bd80]' : 'text-[#f26522]'}>
          {goalLabel} on this recipe:{' '}
          {candidate.recipe_gain_percent >= 0 ? 'better by ' : 'worse by '}
          {Math.abs(candidate.recipe_gain_percent).toFixed(1)}%
        </span>
        {candidate.tradeoffs.length > 0 && (
          <span className="text-[#f2a07a]">
            {' '}
            · trade-off: {candidate.tradeoffs.map((t) => `${t.label} ${signed(t.percent_change, '%')}`).join(', ')}
          </span>
        )}
      </p>
      <div className="mt-3 space-y-1.5">
        {BARS.map((bar, i) => {
          const value = candidate.scores[bar.key];
          return value === null ? (
            <div key={bar.key} className="flex items-center gap-3 font-mono2">
              <span className="text-[10px] uppercase tracking-[0.14em] text-[#a39b8b] w-16 shrink-0">{bar.label}</span>
              <span className="text-[10px] text-[#a39b8b] italic">no data · 0 points</span>
            </div>
          ) : (
            <ScoreBar key={bar.key} label={bar.label} value={value} color={bar.color} delay={i * 60} />
          );
        })}
        <ScoreBar label="Overall" value={candidate.overall} color="#fdfdfd" delay={280} />
      </div>
      <Evidence candidate={candidate} />
    </li>
  );
}

export default function Recommendations({
  evaluation,
  focus,
  onFocus,
  onSelect,
  onReset,
  hasOverride,
  ratio,
  onRatio,
}: {
  evaluation: Evaluation;
  focus: Recommendation | undefined;
  onFocus: (lineId: number) => void;
  onSelect: (lineId: number, ingredientId: string | null) => void;
  onReset: (lineId: number) => void;
  hasOverride: boolean;
  ratio: number;
  onRatio: (lineId: number, ratio: number) => void;
}) {
  const goalLabel = evaluation.goal.label.replace(/^(Reduce|Increase) /, '');
  const shortGoal = goalLabel.charAt(0).toUpperCase() + goalLabel.slice(1);
  const applied = evaluation.applied.find((s) => s.line_id === focus?.line_id);

  return (
    <Card
      title="4 · Ranked substitutes"
      aside={
        <span className="font-mono2 text-[10px] px-2.5 py-1 rounded-full bg-[#f26522] text-white uppercase tracking-[0.12em]">
          {evaluation.goal.label}
        </span>
      }
    >
      {evaluation.recommendations.length === 0 ? (
        <p className="mt-4 font-body text-[14px] text-[#efede9]/80">
          No ingredient in this recipe can be assessed for substitution. Swappable ingredients need a catalog match, a
          known quantity and nutrition data.
        </p>
      ) : (
        <>
          <div className="mt-4">
            <Label>Ingredients, most useful to swap first</Label>
            <div className="flex flex-wrap gap-2">
              {evaluation.recommendations.map((r) => (
                <Pill key={r.line_id} active={r.line_id === focus?.line_id} onClick={() => onFocus(r.line_id)} title={r.phrase}>
                  <span className={r.relevant ? '' : 'opacity-55'}>
                    {r.ingredient_name}
                    {r.relevant ? ` · up to ${r.best_gain_percent.toFixed(0)}%` : ' · little to gain'}
                  </span>
                </Pill>
              ))}
            </div>
          </div>

          {focus && (
            <>
              <p className="mt-4 font-body text-[14px] text-[#efede9]/80">
                “{focus.phrase}” supplies{' '}
                {focus.share_percent === null ? 'an unknown share' : `${focus.share_percent.toFixed(1)}%`} of the
                recipe’s estimated {goalLabel}.{' '}
                {focus.eligible_count > 0
                  ? `${focus.eligible_count} substitute${focus.eligible_count === 1 ? '' : 's'} would improve it.`
                  : 'No role-compatible substitute meets the requirements.'}
                {focus.in_title &&
                  evaluation.scope === 'recipe' &&
                  ' It is named in the title, so whole-recipe mode keeps it unless you choose a substitute.'}
              </p>

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => onSelect(focus.line_id, null)}
                  aria-pressed={!applied}
                  className={`min-h-[40px] px-4 rounded-full border font-mono2 text-[11px] ${
                    !applied ? 'bg-[#efede9] border-[#efede9] text-[#3e3a32]' : 'border-[#efede9]/30'
                  }`}
                >
                  Keep original
                </button>
                {hasOverride && (
                  <button
                    type="button"
                    onClick={() => onReset(focus.line_id)}
                    className="min-h-[40px] px-4 rounded-full border border-[#efede9]/30 font-mono2 text-[11px]"
                  >
                    ↺ Back to recommendation
                  </button>
                )}
              </div>

              {applied && (
                <label className="mt-4 block rounded-lg bg-[#3e3a32] px-4 py-3">
                  <span className="flex flex-wrap justify-between gap-2 font-mono2 text-[11px] text-[#efede9]/85">
                    <span>Quantity of substitute per gram replaced</span>
                    <span>
                      {ratio.toFixed(2)} × = {applied.new_grams.toFixed(0)} g
                    </span>
                  </span>
                  <input
                    type="range"
                    min={0.25}
                    max={2}
                    step={0.05}
                    value={ratio}
                    onChange={(e) => onRatio(focus.line_id, Number(e.target.value))}
                    className="w-full h-8 accent-[#f26522]"
                  />
                  <span className="block font-body text-[12px] text-[#a39b8b]">
                    Estimate: {applied.ratio_basis}. Candidates are ranked at 1:1.
                  </span>
                </label>
              )}

              <ol className="mt-4 grid lg:grid-cols-2 gap-3">
                {focus.candidates.map((c, i) => (
                  <CandidateRow
                    key={c.ingredient_id}
                    candidate={c}
                    rank={c.eligible ? i + 1 : null}
                    goalLabel={shortGoal}
                    recommended={i === 0 && c.eligible}
                    applied={applied?.to_id === c.ingredient_id}
                    onUse={() => onSelect(focus.line_id, c.ingredient_id)}
                  />
                ))}
              </ol>
              {focus.eligible_count > focus.candidates.length && (
                <p className="mt-2 font-body text-[12px] text-[#a39b8b]">
                  Showing the top {focus.candidates.length} of {focus.eligible_count} eligible substitutes.
                </p>
              )}

              {focus.rejected_count > 0 && (
                <details className="mt-4">
                  <summary className="cursor-pointer min-h-[32px] font-mono2 text-[11px] text-[#a39b8b] hover:text-[#efede9]">
                    Why {focus.rejected_count} role-compatible ingredients were not recommended
                  </summary>
                  <ul className="mt-2 font-body text-[13px] text-[#efede9]/75">
                    {Object.entries(focus.rejection_reasons).map(([reason, count]) => (
                      <li key={reason}>
                        {count} × {reason}
                      </li>
                    ))}
                  </ul>
                  <p className="mt-2 font-body text-[13px] text-[#a39b8b]">
                    Highest-scoring examples: {focus.rejected.map((c) => `${c.name} (${c.overall.toFixed(2)})`).join(', ')}.
                  </p>
                </details>
              )}
            </>
          )}
        </>
      )}
    </Card>
  );
}
