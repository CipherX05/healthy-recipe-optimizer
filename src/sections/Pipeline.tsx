import { useRevealRoot } from '@/hooks/useReveal';

const STEPS = [
  { n: '01', title: 'Select a recipe', body: 'Search recipes imported from RecipeDB and load their ingredient lines, quantities, cuisine and processes.' },
  { n: '02', title: 'Match and enrich', body: 'Match each line to a reviewed ingredient, convert quantities to grams where there is evidence, and attach USDA nutrition and FlavorDB2 molecules.' },
  { n: '03', title: 'Find candidates', body: 'Take every role-compatible ingredient from the substitution network.' },
  { n: '04', title: 'Rank the candidates', body: 'Score each on health, flavor, cuisine and cooking role, weighted by your preferences.' },
  { n: '05', title: 'Choose an eligible substitute', body: 'Recommend only candidates that meaningfully improve the target without sharply raising saturated fat, sodium or calories. You can choose another.' },
  { n: '06', title: 'Apply one or more swaps', body: 'Assume the same weight unless you change the ratio. Whole-recipe mode treats each ingredient independently.' },
  { n: '07', title: 'Compare before / after', body: 'Report nutrient changes, trade-offs, flavor similarity, cuisine compatibility and any missing data.' },
];

export default function Pipeline() {
  const ref = useRevealRoot<HTMLElement>();

  return (
    <section id="pipeline" ref={ref} className="py-24 md:py-36 bg-[#eeece8]">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="reveal flex items-baseline gap-4">
          <span className="font-mono2 text-[12px] text-[#f26522]">02</span>
          <p className="eyebrow">The pipeline</p>
          <span className="flex-1 rule" />
        </div>

        <div className="mt-10 grid md:grid-cols-12 gap-10">
          <div className="md:col-span-4">
            <h2 className="reveal font-display font-semibold tracking-tight text-[#3e3a32] text-3xl md:text-[2.4rem] leading-[1.12] md:sticky md:top-28">
              From raw recipe to optimized recipe, in seven steps.
            </h2>
          </div>

          <ol className="md:col-span-8 relative">
            {/* connecting rule */}
            <span className="absolute left-[19px] md:left-[23px] top-4 bottom-4 w-px bg-[#575349]/20" aria-hidden />
            {STEPS.map((s, i) => (
              <li key={s.n} className="reveal relative pl-16 md:pl-20 pb-10 last:pb-0" data-delay={i * 70}>
                <span className="absolute left-0 top-0 w-10 h-10 md:w-12 md:h-12 rounded-full bg-[#fdfdfd] border border-[#575349]/25 flex items-center justify-center font-mono2 text-[12px] text-[#575349]">
                  {s.n}
                </span>
                <h3 className="font-display font-semibold text-[#3e3a32] text-lg md:text-xl pt-1.5">{s.title}</h3>
                <p className="font-body text-[#575349]/85 mt-1.5 max-w-lg">{s.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
