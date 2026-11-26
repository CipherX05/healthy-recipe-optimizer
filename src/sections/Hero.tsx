import { useCallback, useRef, useState } from 'react';

// ── constellation data ──────────────────────────────────────
interface Node {
  id: string;
  label: string;
  x: number; // % of hero width
  y: number; // % of hero height
  d: number; // diameter, vw
  kind: 'original' | 'substitute' | 'context';
  float: 'node-float-a' | 'node-float-b' | 'node-float-c';
}

// clustered to the right half so the copy stays readable
const NODES: Node[] = [
  { id: 'butter', label: 'Butter', x: 72, y: 34, d: 11, kind: 'original', float: 'node-float-a' },
  { id: 'cream', label: 'Cream', x: 85, y: 62, d: 9.5, kind: 'original', float: 'node-float-b' },
  { id: 'ghee', label: 'Ghee', x: 56, y: 14, d: 7, kind: 'substitute', float: 'node-float-c' },
  { id: 'oliveoil', label: 'Olive oil', x: 58, y: 68, d: 7.5, kind: 'substitute', float: 'node-float-b' },
  { id: 'avocado', label: 'Avocado', x: 88, y: 12, d: 6.5, kind: 'substitute', float: 'node-float-a' },
  { id: 'yogurt', label: 'Greek yogurt', x: 94, y: 86, d: 7.5, kind: 'substitute', float: 'node-float-c' },
  { id: 'cashew', label: 'Cashew cream', x: 66, y: 84, d: 6.5, kind: 'substitute', float: 'node-float-a' },
  { id: 'tomato', label: 'Tomato', x: 93, y: 34, d: 5.5, kind: 'context', float: 'node-float-b' },
  { id: 'garam', label: 'Garam masala', x: 63, y: 5, d: 5.5, kind: 'context', float: 'node-float-c' },
];

const EDGES: [string, string, string][] = [
  ['butter', 'ghee', '0.96'],
  ['butter', 'oliveoil', '0.62'],
  ['butter', 'avocado', '0.71'],
  ['cream', 'yogurt', '0.74'],
  ['cream', 'cashew', '0.83'],
  ['butter', 'cream', ''],
  ['cream', 'garam', ''],
  ['butter', 'tomato', ''],
];

const byId = Object.fromEntries(NODES.map((n) => [n.id, n]));

function nodeStyle(kind: Node['kind'], active: boolean) {
  if (kind === 'original')
    return { fill: active ? '#f26522' : '#575349', text: '#fdfdfd', ring: active ? '#f26522' : '#575349' };
  if (kind === 'substitute')
    return { fill: active ? '#f26522' : '#efede9', text: active ? '#fdfdfd' : '#575349', ring: active ? '#f26522' : '#a39b8b' };
  return { fill: '#d7d1c6', text: '#575349', ring: '#d7d1c6' };
}

export default function Hero() {
  const [active, setActive] = useState<string | null>(null);
  const [par, setPar] = useState({ x: 0, y: 0 });
  const wrapRef = useRef<HTMLElement>(null);

  const onMove = useCallback((e: React.PointerEvent) => {
    const el = wrapRef.current;
    if (!el || e.pointerType === 'touch') return;
    const rect = el.getBoundingClientRect();
    const nx = (e.clientX - rect.left) / rect.width - 0.5;
    const ny = (e.clientY - rect.top) / rect.height - 0.5;
    setPar({ x: nx, y: ny });
  }, []);

  const linked = (id: string) =>
    active !== null &&
    (id === active || EDGES.some(([a, b]) => (a === active && b === id) || (b === active && a === id)));

  return (
    <section id="top" ref={wrapRef} onPointerMove={onMove} className="relative min-h-[100svh] flex flex-col overflow-hidden">
      {/* constellation layer */}
      <div
        className="absolute inset-0 transition-transform duration-500 ease-out hidden sm:block"
        style={{ transform: `translate(${par.x * -14}px, ${par.y * -10}px)` }}
        aria-hidden={false}
      >
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 w-full h-full" aria-hidden>
          {EDGES.map(([a, b, label], i) => {
            const na = byId[a];
            const nb = byId[b];
            const hot = active !== null && (a === active || b === active);
            return (
              <g key={i}>
                <line
                  x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
                  stroke={hot ? '#f26522' : '#a39b8b'}
                  strokeWidth={hot ? 2 : 1}
                  vectorEffect="non-scaling-stroke"
                  strokeDasharray={label ? 'none' : '4 5'}
                  opacity={active === null ? 0.45 : hot ? 0.95 : 0.1}
                  style={{ transition: 'opacity .3s, stroke .3s' }}
                />
                {label && (
                  <text
                    x={(na.x + nb.x) / 2} y={(na.y + nb.y) / 2 - 1}
                    textAnchor="middle"
                    fontSize="2.4"
                    className="font-mono2"
                    fill={hot ? '#f26522' : '#a39b8b'}
                    opacity={active === null ? 0.7 : hot ? 1 : 0.1}
                  >
                    {label}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

        {/* HTML nodes */}
        {NODES.map((n) => {
          const s = nodeStyle(n.kind, linked(n.id));
          const dim = active !== null && !linked(n.id);
          return (
            <button
              key={n.id}
              onPointerEnter={() => setActive(n.id)}
              onPointerLeave={() => setActive(null)}
              onFocus={() => setActive(n.id)}
              onBlur={() => setActive(null)}
              className={`absolute rounded-full flex items-center justify-center font-mono2 text-center leading-tight transition-[background,color,opacity,box-shadow] duration-300 ${n.float}`}
              style={{
                left: `${n.x}%`, top: `${n.y}%`,
                width: `${n.d}vw`, height: `${n.d}vw`,
                maxWidth: 170, maxHeight: 170, minWidth: 56, minHeight: 56,
                translate: '-50% -50%',
                background: s.fill,
                color: s.text,
                border: `1px solid ${s.ring}`,
                fontSize: 'clamp(9px, 1.05vw, 15px)',
                opacity: dim ? 0.22 : 1,
                boxShadow: linked(n.id) && n.kind !== 'context' ? '0 8px 24px rgba(242,101,34,0.25)' : 'none',
              }}
            >
              {n.label}
            </button>
          );
        })}
      </div>

      {/* mobile hint */}
      <div className="sm:hidden absolute top-[72px] right-4 font-mono2 text-[10px] uppercase tracking-[0.2em] text-[#a39b8b]">
        Illustrative flavor graph
      </div>

      {/* hero copy */}
      <div className="relative z-10 mx-auto max-w-6xl px-5 md:px-8 w-full flex-1 flex flex-col justify-center pt-28 pb-16 pointer-events-none">
        <p className="eyebrow mb-6 pointer-events-auto">CGAS · Computational Gastronomy · Course Project</p>
        <h1 className="font-display font-bold tracking-[-0.03em] leading-[0.98] text-[#3e3a32] text-[clamp(2.6rem,7.5vw,5.6rem)] max-w-3xl pointer-events-auto">
          Healthier recipes,
          <br />
          <span className="text-[#f26522]">with flavor</span>
          <br className="hidden sm:block" /> and cuisine in mind.
        </h1>
        <p className="font-body text-lg md:text-xl text-[#575349]/85 mt-7 max-w-xl pointer-events-auto">
          Compare ingredient substitutes for a nutrition goal while accounting for flavor
          similarity and cuisine compatibility.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row gap-3 pointer-events-auto">
          <a
            href="#demo"
            className="inline-flex items-center justify-center min-h-[48px] px-8 rounded-full bg-[#f26522] text-white font-mono2 text-[12px] uppercase tracking-[0.18em] hover:bg-[#d9541a] transition-colors"
          >
            Try the live demo
          </a>
          <a
            href="#problem"
            className="inline-flex items-center justify-center min-h-[48px] px-8 rounded-full border border-[#575349]/30 text-[#575349] font-mono2 text-[12px] uppercase tracking-[0.18em] hover:border-[#575349] transition-colors"
          >
            Read the proposal
          </a>
        </div>

        <div className="mt-14 flex flex-wrap gap-x-10 gap-y-4 font-mono2 text-[11px] uppercase tracking-[0.15em] text-[#a39b8b] pointer-events-auto">
          <span>Health <span className="text-[#575349]">+</span> Flavor <span className="text-[#575349]">+</span> Cuisine</span>
          <span>4 deliverables</span>
          <span>Database + offline demo</span>
        </div>
      </div>

      {/* ticker */}
      <div className="relative z-10 border-t border-[#575349]/15 py-3 overflow-hidden bg-[#eeece8]/60">
        <div className="marquee-track flex whitespace-nowrap font-mono2 text-[11px] uppercase tracking-[0.2em] text-[#a39b8b]">
          {[0, 1].map((k) => (
            <span key={k} className="flex shrink-0">
              {['Jaccard similarity · flavor molecules', 'weighted candidate ranking', 'goal-driven optimization', 'before and after evaluation', 'nutrition per 100 g', 'cuisine affinity'].map((t) => (
                <span key={t + k} className="mx-6">{t} <span className="text-[#f26522] ml-6">+</span></span>
              ))}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
