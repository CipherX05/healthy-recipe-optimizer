import { useCountUp } from '@/hooks/useCountUp';

export function ScoreBar({ label, value, color, delay }: { label: string; value: number; color: string; delay: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="font-mono2 text-[10px] uppercase tracking-[0.14em] text-[#a39b8b] w-16 shrink-0">{label}</span>
      <div className="flex-1 h-[6px] rounded-full bg-[#575349]/10 overflow-hidden">
        <div className="bar-fill h-full rounded-full" style={{ width: `${value * 100}%`, background: color, transitionDelay: `${delay}ms` }} />
      </div>
      <span className="font-mono2 text-[11px] text-[#efede9]/85 w-9 text-right">{value.toFixed(2)}</span>
    </div>
  );
}

export function Gauge({ label, value, color }: { label: string; value: number; color: string }) {
  const v = useCountUp(value, true, 1100);
  return (
    <div className="flex-1 min-w-[130px] bg-[#efede9] rounded-lg px-5 py-4">
      <p className="font-mono2 text-[10px] uppercase tracking-[0.16em] text-[#a39b8b]">{label}</p>
      <p className="font-display font-bold text-3xl mt-1 text-[#3e3a32]">{v.toFixed(2)}</p>
      <div className="mt-2 h-[3px] w-10 rounded-full" style={{ background: color }} />
    </div>
  );
}
