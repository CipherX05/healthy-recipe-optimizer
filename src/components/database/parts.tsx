import type { ReactNode } from 'react';

export function Card({ title, aside, children }: { title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <div className="rise-in bg-[#4a463e] rounded-lg p-5 md:p-7 min-w-0">
      <header
        className="flex flex-wrap items-center justify-between gap-3 pb-4"
        style={{ borderBottom: '1px solid rgba(239,237,233,0.18)' }}
      >
        <h3 className="font-mono2 text-[10px] uppercase tracking-[0.2em] text-[#a39b8b]">{title}</h3>
        {aside}
      </header>
      {children}
    </div>
  );
}

export function Pill({
  active,
  onClick,
  children,
  tone = 'light',
  title,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
  tone?: 'light' | 'accent' | 'sage';
  title?: string;
}) {
  const on = {
    light: 'bg-[#efede9] border-[#efede9] text-[#3e3a32]',
    accent: 'bg-[#f26522] border-[#f26522] text-white',
    sage: 'bg-[#7a8b5a] border-[#7a8b5a] text-white',
  }[tone];
  return (
    <button
      type="button"
      title={title}
      aria-pressed={active}
      onClick={onClick}
      className={`min-h-[44px] px-4 py-2 rounded-full font-mono2 text-[12px] transition-colors border ${
        active ? on : 'border-[#efede9]/25 text-[#efede9]/80 hover:border-[#efede9]/60'
      }`}
    >
      {children}
    </button>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return (
    <p className="font-mono2 text-[10px] uppercase tracking-[0.2em] text-[#a39b8b] mb-3">{children}</p>
  );
}

export function Notice({ tone = 'info', children }: { tone?: 'info' | 'warn'; children: ReactNode }) {
  return (
    <div
      role={tone === 'warn' ? 'alert' : 'status'}
      className={`rounded-lg px-4 py-3 font-body text-[14px] leading-snug border ${
        tone === 'warn'
          ? 'border-[#f26522]/50 bg-[#f26522]/15 text-[#efede9]'
          : 'border-[#efede9]/15 bg-[#4a463e]/60 text-[#efede9]/85'
      }`}
    >
      {children}
    </div>
  );
}

export const inputClass =
  'w-full min-h-[44px] rounded-lg bg-[#3e3a32] border border-[#efede9]/25 px-3 font-body text-[15px] text-[#fdfdfd] placeholder:text-[#a39b8b] focus:border-[#f26522] focus:outline-none';
