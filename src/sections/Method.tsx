import { useRevealRoot } from '@/hooks/useReveal';
import { WEIGHTS } from '@/data/food';

const CARDS = [
  {
    tag: 'Similarity',
    title: 'Cosine similarity',
    formula: 'cos(A, B) = A·B / (‖A‖‖B‖)',
    body: 'Cosine similarity compares six manually assigned flavor features: creamy, rich, umami, sweet, tangy and earthy. Nutrition is scored separately.',
  },
  {
    tag: 'Ranking',
    title: 'Weighted candidate score',
    formula: 'Score = w₁·Flavor + w₂·Nutrition + w₃·Cuisine + w₄·Category',
    body: 'The weights are fixed. Changing the health goal changes the nutrition score for each candidate.',
  },
  {
    tag: 'Optimization',
    title: 'Goal-driven search',
    formula: 'min Calories · min SatFat · max Protein · max Fiber',
    body: 'For each ingredient in scope, pick the highest-ranked candidate that improves the chosen nutrient by more than 2% at the same weight. Each swap is evaluated independently.',
  },
  {
    tag: 'Evaluation',
    title: 'Before / after metrics',
    formula: 'Change (%) = (Modified − Original) / Original × 100',
    body: 'A reduction helps calorie and saturated-fat goals. An increase helps protein and fiber goals. The demo also reports flavor and cuisine proxy scores.',
  },
];

export default function Method() {
  const ref = useRevealRoot<HTMLElement>();

  return (
    <section id="method" ref={ref} className="py-24 md:py-36">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="reveal flex items-baseline gap-4">
          <span className="font-mono2 text-[12px] text-[#f26522]">03</span>
          <p className="eyebrow">The method</p>
          <span className="flex-1 rule" />
        </div>

        <h2 className="reveal mt-10 font-display font-semibold tracking-tight text-[#3e3a32] text-3xl md:text-[2.4rem] leading-[1.12] max-w-2xl">
          No heavy AI required — vectors, weights, and a search loop.
        </h2>

        <div className="mt-12 grid sm:grid-cols-2 gap-5">
          {CARDS.map((c, i) => (
            <article key={c.tag} className="reveal bg-[#efede9] rounded-lg overflow-hidden" data-delay={i * 80}>
              <header className="px-6 pt-5 pb-4 flex items-center justify-between gap-4">
                <span className="font-mono2 text-[10px] uppercase tracking-[0.2em] text-[#a39b8b]">{c.tag}</span>
                <span className="w-1.5 h-1.5 rounded-full bg-[#f26522]" />
              </header>
              <div className="rule mx-6" />
              <div className="px-6 py-5">
                <h3 className="font-display font-semibold text-[#3e3a32] text-xl">{c.title}</h3>
                <p className="font-mono2 text-[12px] md:text-[13px] text-[#f26522] mt-3 leading-relaxed">{c.formula}</p>
                <p className="font-body text-[#575349]/85 mt-3 text-[16px]">{c.body}</p>
              </div>
            </article>
          ))}
        </div>

        {/* weight bar */}
        <div className="reveal mt-10 border border-[#575349]/25 rounded-lg p-6" data-delay="120">
          <p className="eyebrow mb-5">Scoring weights used in the demo</p>
          <div className="flex h-12 rounded-md overflow-hidden font-mono2 text-[11px] uppercase tracking-[0.12em]">
            <div className="bg-[#575349] text-[#fdfdfd] flex items-center justify-center" style={{ width: `${WEIGHTS.flavor * 100}%` }}>
              Flavor {WEIGHTS.flavor}
            </div>
            <div className="bg-[#f26522] text-white flex items-center justify-center" style={{ width: `${WEIGHTS.nutrition * 100}%` }}>
              Nutrition {WEIGHTS.nutrition}
            </div>
            <div className="bg-[#7a8b5a] text-white flex items-center justify-center" style={{ width: `${WEIGHTS.cuisine * 100}%` }}>
              Cuisine {WEIGHTS.cuisine}
            </div>
            <div className="bg-[#d7d1c6] text-[#575349] flex items-center justify-center" style={{ width: `${WEIGHTS.category * 100}%` }}>
              Role {WEIGHTS.category}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
