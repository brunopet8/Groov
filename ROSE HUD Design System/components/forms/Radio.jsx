import React, { useState } from 'react';

export function Radio({ options = [], value, defaultValue, onChange, name, direction = 'column', disabled = false, style }) {
  const [inner, setInner] = useState(defaultValue);
  const [hov, setHov] = useState(null);
  const cur = value ?? inner;
  const opts = options.map((o) => (typeof o === 'string' ? { value: o, label: o } : o));
  const pick = (v) => { if (disabled) return; if (value === undefined) setInner(v); onChange && onChange(v); };
  return (
    <div role="radiogroup" aria-label={name} style={{ display: 'flex', flexDirection: direction, gap: direction === 'row' ? 16 : 8, opacity: disabled ? 0.4 : 1, ...style }}>
      {opts.map((o) => {
        const on = o.value === cur; const h = hov === o.value;
        return (
          <label key={o.value} onPointerEnter={() => setHov(o.value)} onPointerLeave={() => setHov(null)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: disabled ? 'not-allowed' : 'pointer', userSelect: 'none' }}>
            <span role="radio" aria-checked={on} tabIndex={disabled ? -1 : 0} onClick={() => pick(o.value)}
              onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); pick(o.value); } }}
              style={{
                display: 'grid', placeItems: 'center', width: 12, height: 12, flex: 'none', borderRadius: '50%',
                border: `1px solid ${on ? 'var(--red-500)' : h ? 'var(--red-400)' : 'var(--border-strong)'}`,
                boxShadow: on ? 'var(--glow-red-xs)' : 'none', transition: 'var(--transition-color)',
              }}>
              <span style={{
                width: 6, height: 6, borderRadius: '50%', background: 'var(--red-400)', boxShadow: 'var(--glow-red-sm)',
                transform: on ? 'scale(1)' : 'scale(0)', transition: 'transform var(--dur-base) var(--ease-spring)',
              }} />
            </span>
            <span onClick={() => pick(o.value)} style={{ font: 'var(--type-body-sm)', color: on || h ? 'var(--fg-1)' : 'var(--fg-2)', transition: 'var(--transition-color)' }}>{o.label}</span>
          </label>
        );
      })}
    </div>
  );
}
