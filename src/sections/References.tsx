import { useRevealRoot } from '@/hooks/useReveal';

const DATA = [
  { k: 'Recipe data', v: 'Five built-in recipes with ingredients, gram quantities, cuisine labels and preset substitutes.' },
  { k: 'Nutrition data', v: 'Illustrative per-100 g values for calories, protein, fat, saturated fat, carbohydrates and fiber.' },
  { k: 'Flavor data', v: 'Six manually assigned flavor scores per ingredient, inspired by the FlavorDB material from CGAS Lecture 4.' },
];

const PAPERS = [
  {
    n: 'P1',
    title: 'Identifying Ingredient Substitutions Using a Knowledge Graph of Food',
    why: 'The basic substitution problem and graph-based candidate generation.',
  },
  {
    n: 'P2',
    title: 'Eating Healthier: Exploring Nutrition Information for Healthier Recipe Recommendation',
    why: 'The nutritional recommendation component.',
  },
  {
    n: 'P3',
    title: 'Optimizing Ingredient Substitution Using Large Language Models to Enhance Phytochemical Content in Recipes',
    why: 'Recent work on substitution for nutritional improvement.',
  },
];

export default function References() {
  const ref = useRevealRoot<HTMLElement>();

  return (
    <section id="references" ref={ref} className="py-24 md:py-36 bg-[#eeece8]">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="reveal flex items-baseline gap-4">
          <span className="font-mono2 text-[12px] text-[#f26522]">06</span>
          <p className="eyebrow">Data & references</p>
          <span className="flex-1 rule" />
        </div>

        <div className="mt-12 grid md:grid-cols-2 gap-12">
          <div>
            <h3 className="reveal font-display font-semibold text-[#3e3a32] text-2xl">Datasets</h3>
            <ul className="mt-6 space-y-5">
              {DATA.map((d, i) => (
                <li key={d.k} className="reveal flex gap-5" data-delay={i * 70}>
                  <span className="font-mono2 text-[11px] text-[#f26522] pt-1 shrink-0 w-6">{String(i + 1).padStart(2, '0')}</span>
                  <div>
                    <p className="font-display font-medium text-[#3e3a32]">{d.k}</p>
                    <p className="font-body text-[#575349]/85 mt-1">{d.v}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="reveal font-display font-semibold text-[#3e3a32] text-2xl">Supporting papers</h3>
            <ul className="mt-6 space-y-5">
              {PAPERS.map((p, i) => (
                <li key={p.n} className="reveal bg-[#fdfdfd] rounded-lg px-6 py-5" data-delay={i * 70}>
                  <div className="flex items-start gap-4">
                    <span className="font-mono2 text-[11px] px-2 py-1 rounded bg-[#efede9] text-[#575349] shrink-0 mt-0.5">{p.n}</span>
                    <div>
                      <p className="font-body font-medium text-[#3e3a32] leading-snug">{p.title}</p>
                      <p className="font-mono2 text-[11px] text-[#a39b8b] mt-2 uppercase tracking-[0.12em]">{p.why}</p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
