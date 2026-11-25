import { useEffect, useState } from 'react';

const LINKS = [
  { href: '#problem', label: 'Problem' },
  { href: '#pipeline', label: 'Pipeline' },
  { href: '#method', label: 'Method' },
  { href: '#demo', label: 'Live demo' },
  { href: '#deliverables', label: 'Deliverables' },
  { href: '#references', label: 'References' },
];

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled || open
          ? 'bg-[#fdfdfd]/90 backdrop-blur-md border-b border-[#575349]/15'
          : 'bg-transparent border-b border-transparent'
      }`}
    >
      <div className="mx-auto max-w-6xl px-5 md:px-8 h-14 flex items-center justify-between">
        <a href="#top" className="flex items-center gap-2.5 min-h-[44px]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#f26522] inline-block" />
          <span className="font-display font-semibold tracking-tight text-[15px] text-[#3e3a32]">
            Healthy Recipe Optimizer
          </span>
        </a>

        <nav className="hidden md:flex items-center gap-6">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="font-mono2 text-[11px] uppercase tracking-[0.18em] text-[#575349]/70 hover:text-[#f26522] transition-colors"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <button
          aria-label="Toggle menu"
          onClick={() => setOpen((v) => !v)}
          className="md:hidden w-11 h-11 flex flex-col items-center justify-center gap-1.5"
        >
          <span className={`block w-5 h-px bg-[#575349] transition-transform ${open ? 'rotate-45 translate-y-[3.5px]' : ''}`} />
          <span className={`block w-5 h-px bg-[#575349] transition-transform ${open ? '-rotate-45 -translate-y-[3px]' : ''}`} />
        </button>
      </div>

      {open && (
        <nav className="md:hidden border-t border-[#575349]/10 bg-[#fdfdfd]/95 backdrop-blur-md px-5 py-2">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="block py-3 min-h-[44px] font-mono2 text-[12px] uppercase tracking-[0.18em] text-[#575349]"
            >
              {l.label}
            </a>
          ))}
        </nav>
      )}
    </header>
  );
}
