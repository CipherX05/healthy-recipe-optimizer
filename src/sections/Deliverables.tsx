import { useRevealRoot } from '@/hooks/useReveal';

const DELIVERABLES = [
  {
    id: 'D1',
    title: 'Find suitable substitutes',
    body: 'Rank built-in replacements for an ingredient by comparing flavor, nutrition, cuisine and category compatibility.',
  },
  {
    id: 'D2',
    title: 'Make recipes healthier',
    body: 'Create healthier versions of whole recipes by replacing ingredients according to a chosen goal — fewer calories, less saturated fat, more protein or more fiber.',
  },
  {
    id: 'D3',
    title: 'Compare original and modified recipes',
    body: 'Compare nutrient amounts per serving and report flavor similarity and cuisine consistency as proxy scores.',
  },
  {
    id: 'D4',
    title: 'Ship a simple app',
    body: 'An interactive tool where users pick a recipe, an ingredient and a health goal, and get ranked substitutes plus an improved recipe. You used it above.',
  },
];

export default function Deliverables() {
  const ref = useRevealRoot<HTMLElement>();

  return (
    <section id="deliverables" ref={ref} className="py-24 md:py-36">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="reveal flex items-baseline gap-4">
          <span className="font-mono2 text-[12px] text-[#f26522]">05</span>
          <p className="eyebrow">The four deliverables</p>
          <span className="flex-1 rule" />
        </div>

        <div className="mt-12 grid sm:grid-cols-2 gap-5">
          {DELIVERABLES.map((d, i) => (
            <article key={d.id} className="reveal group border border-[#575349]/20 rounded-lg overflow-hidden hover:border-[#575349]/45 transition-colors" data-delay={i * 70}>
              <header className="px-6 pt-5 pb-4 flex items-center justify-between">
                <span className="font-mono2 text-[12px] px-2.5 py-1 rounded-full bg-[#575349] text-[#fdfdfd] tracking-[0.1em]">{d.id}</span>
                <span className="w-1.5 h-1.5 rounded-full bg-[#f26522] opacity-0 group-hover:opacity-100 transition-opacity" />
              </header>
              <div className="rule mx-6" />
              <div className="px-6 py-5">
                <h3 className="font-display font-semibold text-[#3e3a32] text-xl">{d.title}</h3>
                <p className="font-body text-[#575349]/85 mt-2.5">{d.body}</p>
              </div>
            </article>
          ))}
        </div>

        {/* positioning */}
        <div className="reveal mt-14 grid md:grid-cols-2 gap-10" data-delay="100">
          <div>
            <p className="eyebrow mb-4">Not another assignment</p>
            <p className="font-body text-[#575349]/90">
              The assignments covered extraction, frequency, itemsets and food-pairing analysis.
              This project is a different task entirely:
            </p>
            <p className="font-mono2 text-[13px] md:text-sm text-[#3e3a32] mt-4 border border-[#575349]/25 rounded-lg px-5 py-4 leading-relaxed">
              Ingredient substitution → Health optimization → Recipe improvement
            </p>
          </div>
          <div>
            <p className="eyebrow mb-4">Not a claim of novelty</p>
            <p className="font-body text-[#575349]/90">
              Ingredient substitution and healthy recipe recommendation exist in the literature.
              The contribution is combining them: <em>nutritional improvement selected jointly
              with flavor similarity and cuisine consistency</em> — a defensible, focused angle.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
