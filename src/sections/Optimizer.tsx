import { useCallback, useState } from 'react';
import { api } from '@/lib/api';
import { useAsync } from '@/hooks/useAsync';
import { useRevealRoot } from '@/hooks/useReveal';
import BuiltInDemo from '@/components/optimizer/BuiltInDemo';
import DatabaseDemo from '@/components/database/DatabaseDemo';
import { Notice, Pill } from '@/components/database/parts';

type Mode = 'database' | 'builtin';

export default function Optimizer() {
  const rootRef = useRevealRoot<HTMLElement>();
  const [attempt, setAttempt] = useState(0);
  const health = useAsync(
    // `attempt` only changes the identity, which makes "Try again" re-run the check.
    useCallback((signal: AbortSignal) => (void attempt, api.health(signal)), [attempt]),
  );
  const [chosen, setChosen] = useState<Mode | null>(null);
  // Database mode when the server answers; otherwise the built-in examples.
  const mode: Mode = chosen ?? (health.error ? 'builtin' : 'database');

  return (
    <section id="demo" ref={rootRef} className="py-24 md:py-36 bg-[#3e3a32] text-[#efede9]">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="reveal flex items-baseline gap-4">
          <span className="font-mono2 text-[12px] text-[#f26522]">04</span>
          <p className="eyebrow" style={{ color: '#a39b8b' }}>Live demo — Deliverable 4</p>
          <span className="flex-1" style={{ borderTop: '1px solid rgba(239,237,233,0.25)' }} />
        </div>

        <h2 className="reveal mt-10 font-display font-semibold tracking-tight text-[#fdfdfd] text-3xl md:text-[2.6rem] leading-[1.1] max-w-2xl">
          The optimizer, running on your machine.
        </h2>
        <p className="reveal mt-5 font-body text-[#efede9]/75 max-w-2xl">
          {mode === 'database'
            ? 'Search imported recipes, pick a health goal and compare substitutes using the local recipe database.'
            : 'Pick a recipe, an ingredient and a health goal. Compare one ingredient swap or optimize every replaceable ingredient using the built-in demo data.'}
        </p>

        <div className="mt-8 flex flex-wrap gap-2" role="group" aria-label="Demo data source">
          <Pill tone="accent" active={mode === 'database'} onClick={() => setChosen('database')}>
            Recipe database
          </Pill>
          <Pill tone="accent" active={mode === 'builtin'} onClick={() => setChosen('builtin')}>
            Built-in examples (offline)
          </Pill>
        </div>

        {health.error && (
          <div className="mt-5 max-w-3xl">
            <Notice tone={mode === 'database' ? 'warn' : 'info'}>
              {health.error} To use the recipe database, run{' '}
              <code className="font-mono2 text-[12px]">python -m recipe_optimizer serve</code> in the backend folder.{' '}
              <button
                type="button"
                onClick={() => setAttempt((n) => n + 1)}
                className="underline decoration-[#f26522] underline-offset-2"
              >
                Try again
              </button>
            </Notice>
          </div>
        )}

        {mode === 'builtin' ? (
          <BuiltInDemo />
        ) : health.data ? (
          <DatabaseDemo health={health.data} />
        ) : (
          health.loading && (
            <p className="mt-8 font-mono2 text-[12px] text-[#a39b8b]" aria-live="polite">
              Connecting to the recipe database…
            </p>
          )
        )}
      </div>
    </section>
  );
}
