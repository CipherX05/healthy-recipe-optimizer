import { useState } from 'react';
import { LORA_DATA, getLoraCase, type LoraModeResult } from '@/data/lora';
import { INGREDIENTS } from '@/data/food';

interface LoraPanelProps {
  recipeId: string;
  ingredientId: string;
  goalId: string;
  recipeName: string;
  ingredientName: string;
  goalLabel: string;
  liveRecommendationId: string | null;
}

export default function LoraPanel({
  recipeId,
  ingredientId,
  goalId,
  recipeName,
  ingredientName,
  goalLabel,
  liveRecommendationId,
}: LoraPanelProps) {
  const [selectedMode, setSelectedMode] = useState<'lora' | 'base' | 'both'>('lora');
  const [showTrainingDetails, setShowTrainingDetails] = useState(false);

  const loraCase = getLoraCase(recipeId, ingredientId, goalId);
  const baseResult = loraCase?.modes.base;
  const loraResult = loraCase?.modes.lora;
  const training = LORA_DATA.training;
  const metrics = LORA_DATA.test_metrics;

  const formatIngredient = (id: string | null | undefined) => {
    if (!id) return 'None (no substitute / keep original)';
    return INGREDIENTS[id]?.name ?? id;
  };

  const renderModeCard = (modeName: string, result: LoraModeResult | undefined, isLora: boolean) => {
    if (!result) {
      return (
        <div className="p-5 rounded-lg bg-[#3e3a32] border border-[#efede9]/10 text-[#a39b8b] text-sm">
          No recorded data for this query.
        </div>
      );
    }

    return (
      <div className="p-5 rounded-lg bg-[#3e3a32] border border-[#efede9]/15 flex flex-col justify-between">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-[#efede9]/10">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${isLora ? 'bg-[#7a8b5a]' : 'bg-[#f26522]'}`} />
              <span className="font-display font-semibold text-base text-[#fdfdfd]">{modeName}</span>
            </div>
            <span className="font-mono2 text-[10px] uppercase tracking-[0.14em] px-2 py-0.5 rounded bg-[#575349]/40 text-[#efede9]/80">
              {(result.latency_seconds * 1000).toFixed(0)} ms
            </span>
          </div>

          {/* Raw Model Output */}
          <div className="mt-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-mono2 text-[10px] uppercase tracking-[0.14em] text-[#a39b8b]">Raw model output</span>
              <span className="font-mono2 text-[10px] text-[#a39b8b]">JSON Valid: {result.json_valid ? '✓' : '✗'}</span>
            </div>
            <pre className="font-mono2 text-[12px] bg-[#292620] text-[#efede9] p-3 rounded border border-[#575349]/40 overflow-x-auto selection:bg-[#f26522]/30">
              <code>{result.raw_output}</code>
            </pre>
          </div>

          {/* Candidate & Eligibility */}
          <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
            <div className="bg-[#4a463e]/60 p-2.5 rounded border border-[#efede9]/8">
              <span className="font-mono2 text-[10px] uppercase tracking-[0.12em] text-[#a39b8b] block mb-1">
                Raw Selected
              </span>
              <span className="font-medium text-[#fdfdfd] text-[13px]">
                {formatIngredient(result.selected)}
              </span>
            </div>
            <div className="bg-[#4a463e]/60 p-2.5 rounded border border-[#efede9]/8">
              <span className="font-mono2 text-[10px] uppercase tracking-[0.12em] text-[#a39b8b] block mb-1">
                Nutritional Eligibility
              </span>
              <span
                className={`font-mono2 text-[12px] font-semibold flex items-center gap-1.5 ${
                  result.eligible ? 'text-[#7a8b5a]' : 'text-[#f26522]'
                }`}
              >
                {result.eligible ? '✓ Eligible' : '✗ Ineligible'}
              </span>
            </div>
          </div>

          {/* Rule Fallback Banner */}
          <div className="mt-4">
            {result.used_fallback ? (
              <div className="p-3 rounded border border-[#f26522]/40 bg-[#f26522]/15 text-[#efede9]">
                <div className="flex items-center gap-2 text-[#f26522] font-semibold text-xs tracking-wide uppercase font-mono2">
                  <span>⚠ Rule fallback activated</span>
                </div>
                <p className="mt-1.5 text-xs text-[#efede9]/90 font-body leading-relaxed">
                  The recorded output <span className="font-semibold text-[#fdfdfd]">{formatIngredient(result.selected)}</span> failed
                  the rule check. The evaluation used its saved rule baseline of{' '}
                  <span className="font-semibold text-[#7a8b5a]">{formatIngredient(result.recommendation_id)}</span>.
                </p>
              </div>
            ) : (
              <div className="p-3 rounded border border-[#7a8b5a]/40 bg-[#7a8b5a]/15 text-[#efede9]">
                <div className="flex items-center gap-2 text-[#7a8b5a] font-semibold text-xs tracking-wide uppercase font-mono2">
                  <span>✓ Direct model output accepted</span>
                </div>
                <p className="mt-1.5 text-xs text-[#efede9]/90 font-body leading-relaxed">
                  {result.selected
                    ? 'The candidate passed the nutrition rule check during evaluation.'
                    : 'The model chose to keep the original ingredient, which passed the rule check.'}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Recorded recommendation */}
        <div className="mt-4 pt-3 border-t border-[#efede9]/10 flex items-center justify-between text-xs">
          <span className="font-mono2 text-[10px] uppercase tracking-[0.14em] text-[#a39b8b]">Recorded recommendation</span>
          <span className="font-semibold text-[#fdfdfd] font-body text-sm">
            {formatIngredient(result.recommendation_id)}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="rise-in mt-10 bg-[#4a463e] rounded-lg p-6 md:p-8 border border-[#efede9]/10">
      {/* Header with requested exact label */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-[#efede9]/18">
        <div>
          <div className="flex items-center gap-3">
            <span className="font-mono2 text-[11px] px-2.5 py-1 rounded-full bg-[#f26522] text-white uppercase tracking-[0.14em]">
              LoRA Evaluation
            </span>
            <span className="font-mono2 text-[12px] text-[#efede9]/90 font-medium">
              Saved outputs from the evaluation run
            </span>
          </div>
          <h3 className="font-display font-semibold text-xl text-[#fdfdfd] mt-2">
            Base Model vs. LoRA Fine-Tuned Comparison
          </h3>
          <p className="font-body text-xs text-[#efede9]/75 mt-1">
            Inspecting query: <span className="text-[#fdfdfd] font-medium">{recipeName}</span> · replacing{' '}
            <span className="text-[#fdfdfd] font-medium">{ingredientName}</span> for{' '}
            <span className="text-[#7a8b5a] font-medium">{goalLabel}</span>
            {loraCase?.split && (
              <span className="ml-2 font-mono2 text-[10px] uppercase tracking-[0.12em] px-2 py-0.5 rounded bg-[#3e3a32] text-[#a39b8b] border border-[#efede9]/10">
                Split: {loraCase.split}
              </span>
            )}
          </p>
        </div>

        {/* Switcher between base and LoRA outputs */}
        <div className="flex items-center gap-1.5 bg-[#3e3a32] p-1.5 rounded-full border border-[#efede9]/15 shrink-0 self-start md:self-auto">
          <button
            onClick={() => setSelectedMode('lora')}
            className={`px-3.5 py-1.5 rounded-full font-mono2 text-[11px] transition-all ${
              selectedMode === 'lora'
                ? 'bg-[#7a8b5a] text-white shadow-sm font-semibold'
                : 'text-[#efede9]/70 hover:text-white'
            }`}
          >
            LoRA Model
          </button>
          <button
            onClick={() => setSelectedMode('base')}
            className={`px-3.5 py-1.5 rounded-full font-mono2 text-[11px] transition-all ${
              selectedMode === 'base'
                ? 'bg-[#f26522] text-white shadow-sm font-semibold'
                : 'text-[#efede9]/70 hover:text-white'
            }`}
          >
            Base Model
          </button>
          <button
            onClick={() => setSelectedMode('both')}
            className={`px-3.5 py-1.5 rounded-full font-mono2 text-[11px] transition-all ${
              selectedMode === 'both'
                ? 'bg-[#efede9] text-[#3e3a32] shadow-sm font-semibold'
                : 'text-[#efede9]/70 hover:text-white'
            }`}
          >
            Side-by-Side
          </button>
        </div>
      </div>

      <p className="font-body text-xs text-[#efede9]/75 mt-3">
        The comparison replays saved model outputs. The live recipe uses the current rule-based optimizer.
      </p>
      {loraCase && loraCase.rule_baseline !== liveRecommendationId && (
        <p className="font-body text-xs text-[#efede9]/75 mt-1">
          Saved rule baseline: {formatIngredient(loraCase.rule_baseline)}. Current live recommendation: {formatIngredient(liveRecommendationId)}.
        </p>
      )}

      {/* Model Output Cards */}
      <div className="mt-6">
        {selectedMode === 'both' ? (
          <div className="grid md:grid-cols-2 gap-5">
            {renderModeCard('Base Model (Qwen2.5-0.5B-Instruct)', baseResult, false)}
            {renderModeCard('LoRA Adapter (Fine-Tuned)', loraResult, true)}
          </div>
        ) : selectedMode === 'lora' ? (
          <div>{renderModeCard('LoRA Adapter (Fine-Tuned)', loraResult, true)}</div>
        ) : (
          <div>{renderModeCard('Base Model (Qwen2.5-0.5B-Instruct)', baseResult, false)}</div>
        )}
      </div>

      {/* Actual Results Benchmark Section */}
      <div className="mt-8 pt-6 border-t border-[#efede9]/18">
        <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
          <span className="font-mono2 text-[11px] uppercase tracking-[0.16em] text-[#a39b8b]">
            Held-out evaluation · {metrics.base.records} records from {metrics.base.independent_queries} distinct queries
          </span>
          <span className="font-mono2 text-[10px] text-[#a39b8b]">Held-out family: Carbonara</span>
        </div>

        {/* Results grid showing both actual results */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="bg-[#3e3a32] p-4 rounded-lg border border-[#efede9]/12">
            <span className="font-mono2 text-[10px] uppercase tracking-[0.14em] text-[#a39b8b] block">
              Eligibility-rule compliance
            </span>
            <div className="mt-2.5 flex items-baseline justify-between">
              <div>
                <span className="font-mono2 text-[11px] text-[#a39b8b]">Base: </span>
                <span className="font-mono2 text-base font-semibold text-[#efede9]/90">
                  {(metrics.base.eligible_rate * 100).toFixed(1)}%
                </span>
              </div>
              <span className="text-[#a39b8b] font-mono2 text-xs">→</span>
              <div>
                <span className="font-mono2 text-[11px] text-[#7a8b5a]">LoRA: </span>
                <span className="font-mono2 text-2xl font-bold text-[#7a8b5a]">
                  {(metrics.lora.eligible_rate * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            <p className="mt-2 text-[11px] text-[#efede9]/70 font-body">
              All {metrics.lora.records} recorded LoRA test outputs passed the eligibility rule.
            </p>
          </div>

          <div className="bg-[#3e3a32] p-4 rounded-lg border border-[#efede9]/12">
            <span className="font-mono2 text-[10px] uppercase tracking-[0.14em] text-[#a39b8b] block">
              Exact rule agreement
            </span>
            <div className="mt-2.5 flex items-baseline justify-between">
              <div>
                <span className="font-mono2 text-[11px] text-[#a39b8b]">Base: </span>
                <span className="font-mono2 text-base font-semibold text-[#efede9]/90">
                  {(metrics.base.rule_agreement * 100).toFixed(1)}%
                </span>
              </div>
              <span className="text-[#a39b8b] font-mono2 text-xs">→</span>
              <div>
                <span className="font-mono2 text-[11px] text-[#efede9]">LoRA: </span>
                <span className="font-mono2 text-2xl font-bold text-[#efede9]">
                  {(metrics.lora.rule_agreement * 100).toFixed(1)}%
                </span>
              </div>
            </div>
            <p className="mt-2 text-[11px] text-[#efede9]/70 font-body">
              Exact candidate match against rule teacher on unseen test family.
            </p>
          </div>
        </div>

        <div className="mt-4 p-3.5 rounded bg-[#2d2a24] border border-[#575349]/35 text-xs leading-relaxed text-[#efede9]/80 font-body">
          <strong className="text-[#f26522] font-semibold font-mono2 uppercase tracking-wide mr-1">
            Evaluation scope
          </strong>
          The test labels come from fixed rules. Eligibility measures whether an output passes those rules.
          Exact agreement measures whether it matches the specific rule recommendation. Taste validation would require separate cooking tests.
        </div>

        {/* Collapsible Training Metadata */}
        <div className="mt-3">
          <button
            onClick={() => setShowTrainingDetails(!showTrainingDetails)}
            className="text-[11px] font-mono2 text-[#a39b8b] hover:text-[#efede9] flex items-center gap-1.5 transition-colors"
          >
            <span>{showTrainingDetails ? '▼ Hide' : '▶ Show'} Training & Run Metadata</span>
          </button>
          {showTrainingDetails && (
            <div className="mt-2 p-3 rounded bg-[#3e3a32] border border-[#efede9]/10 text-xs font-mono2 grid grid-cols-2 sm:grid-cols-3 gap-2 text-[#efede9]/80">
              <div>
                <span className="text-[#a39b8b] block text-[10px]">Base Model:</span>
                {training.base_model}
              </div>
              <div>
                <span className="text-[#a39b8b] block text-[10px]">Adapter:</span>
                LoRA (r={training.lora_rank}, α={training.lora_alpha})
              </div>
              <div>
                <span className="text-[#a39b8b] block text-[10px]">Trainable Params:</span>
                {training.trainable_parameters.toLocaleString()} / {(training.total_parameters / 1e6).toFixed(1)}M ({((training.trainable_parameters / training.total_parameters) * 100).toFixed(2)}%)
              </div>
              <div>
                <span className="text-[#a39b8b] block text-[10px]">Device & Runtime:</span>
                {training.device} ({training.training_seconds.toFixed(0)}s, {training.epochs} epochs)
              </div>
              <div>
                <span className="text-[#a39b8b] block text-[10px]">Validation Loss:</span>
                {training.initial_validation_completion_loss.toFixed(3)} → {training.best_validation_completion_loss.toFixed(3)}
              </div>
              <div>
                <span className="text-[#a39b8b] block text-[10px]">Dataset Splits:</span>
                Train 224 · Val 24 · Test 24
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
