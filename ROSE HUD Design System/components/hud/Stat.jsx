import React, { useEffect, useRef, useState } from 'react';

const FS = { sm: 'var(--fs-2xl)', md: 'var(--fs-3xl)', lg: 'var(--fs-4xl)' };

export function Stat({ value, prefix, suffix, label, caption, size = 'md', tone = 'white', decimals = 0, animate = true, align = 'left', style }) {
  const numeric = typeof value === 'number';
  const [shown, setShown] = useState(numeric && animate ? 0 : value);
  const raf = useRef(0);
  useEffect(() => {
    if (!numeric || !animate) { setShown(value); return; }
    const start = performance.now(); const from = 0; const dur = 1100;
    const tick = (t) => {
      const p = Math.min(1, (t - start) / dur); const e = 1 - Math.pow(1 - p, 4);
      setShown(from + (value - from) * e);
      if (p < 1) raf.current = setTimeout(() => tick(performance.now()), 16);
    };
    raf.current = setTimeout(() => tick(performance.now()), 16);
    return () => clearTimeout(raf.current);
  }, [value]);
  const text = numeric ? Number(shown).toFixed(decimals) : shown;
  const red = tone === 'red';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: align === 'center' ? 'center' : 'flex-start', textAlign: align, ...style }}>
      {label && <div style={{ font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wider)', textTransform: 'uppercase', color: 'var(--fg-3)' }}>{label}</div>}
      <div style={{
        display: 'flex', alignItems: 'baseline', gap: 2, fontFamily: 'var(--font-mono)', fontWeight: 300, fontSize: FS[size] || FS.md,
        lineHeight: 1, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums',
        color: red ? 'var(--red-400)' : 'var(--fg-1)', textShadow: red ? 'var(--text-glow-red)' : 'var(--text-glow-white)',
      }}>
        {prefix && <span style={{ opacity: 0.7 }}>{prefix}</span>}
        <span>{text}</span>
        {suffix && <span style={{ fontSize: '0.55em', color: red ? 'var(--red-300)' : 'var(--fg-2)', marginLeft: 2 }}>{suffix}</span>}
      </div>
      {caption && <div style={{ font: 'var(--type-body-sm)', color: 'var(--fg-2)', maxWidth: 240, textWrap: 'pretty' }}>{caption}</div>}
    </div>
  );
}
