export default function Footer() {
  return (
    <footer className="bg-[#3e3a32] text-[#efede9] py-14">
      <div className="mx-auto max-w-6xl px-5 md:px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-8">
          <div>
            <p className="font-display font-semibold text-[#fdfdfd] text-xl tracking-tight">
              Healthy Recipe Optimizer
            </p>
            <p className="font-body text-[#efede9]/70 mt-2 max-w-md">
              “We are developing a system that finds ingredient replacements that make a recipe
              healthier while preserving its original flavor and cuisine.”
            </p>
          </div>
          <div className="font-mono2 text-[11px] uppercase tracking-[0.16em] text-[#a39b8b] space-y-2 md:text-right">
            <p>CGAS · Computational Gastronomy</p>
            <p>Health <span className="text-[#f26522]">+</span> Flavor <span className="text-[#f26522]">+</span> Cuisine</p>
          </div>
        </div>
        <div className="mt-10 pt-6 flex flex-col sm:flex-row justify-between gap-3 font-mono2 text-[10px] uppercase tracking-[0.16em] text-[#a39b8b]" style={{ borderTop: '1px solid rgba(239,237,233,0.15)' }}>
          <span>Course project website · demo data is illustrative</span>
          <a href="#top" className="hover:text-[#f26522] transition-colors min-h-[44px] inline-flex items-center">Back to top ↑</a>
        </div>
      </div>
    </footer>
  );
}
