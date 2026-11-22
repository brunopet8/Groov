import React, { useLayoutEffect, useRef, useState } from 'react';

export function Tabs({ items = [], value, onChange, variant = 'line', style }) {
  const refs = useRef({});
  const [bar, setBar] = useState({ left: 0, width: 0 });
  const [hov, setHov] = useState(null);
  const list = items.map((i) => (typeof i === 'string' ? { id: i, label: i } : i));

  useLayoutEffect(() => {
    const el = refs.current[value];
    if (el) setBar({ left: el.offsetLeft, width: el.offsetWidth });
  }, [value, items.length]);

  const chips = variant === 'chips';
  return (
    <div role="tablist" style={{
      position: 'relative', display: 'flex', gap: chips ? 4 : 18,
      borderBottom: chips ? 'none' : '1px solid var(--border-subtle)', ...style,
    }}>
      {list.map((t) => {
        const on = t.id === value; const h = hov === t.id;
        return (
          <button key={t.id} ref={(el) => { refs.current[t.id] = el; }} role="tab" aria-selected={on} type="button"
            onClick={() => onChange && onChange(t.id)} onPointerEnter={() => setHov(t.id)} onPointerLeave={() => setHov(null)}
            style={{
              position: 'relative', display: 'inline-flex', alignItems: 'center', gap: 6,
              height: chips ? 20 : 26, padding: chips ? '0 8px' : 0, cursor: 'pointer',
              font: 'var(--type-label)', fontSize: chips ? 'var(--fs-micro)' : 'var(--fs-2xs)', letterSpacing: 'var(--tracking-wider)', textTransform: 'uppercase',
              color: on ? 'var(--fg-1)' : h ? 'var(--fg-1)' : 'var(--fg-3)',
              background: chips ? (on ? 'var(--red-a14)' : 'transparent') : 'transparent',
              border: chips ? `1px solid ${on ? 'var(--red-500)' : h ? 'var(--border-strong)' : 'var(--border-default)'}` : 0,
              borderRadius: chips ? 'var(--radius-sm)' : 0, boxShadow: chips && on ? 'var(--glow-red-xs)' : 'none',
              transition: 'var(--transition-color)',
            }}>
            {t.label}
            {t.count != null && <span style={{ font: 'var(--type-micro)', color: on ? 'var(--red-400)' : 'var(--fg-3)' }}>{t.count}</span>}
          </button>
        );
      })}
      {!chips && (
        <span aria-hidden="true" style={{
          position: 'absolute', bottom: -1, height: 1, left: bar.left, width: bar.width, background: 'var(--red-400)',
          boxShadow: '0 0 6px var(--red-500), 0 0 12px var(--red-500)',
          transition: 'left var(--dur-slow) var(--ease-out), width var(--dur-slow) var(--ease-out)',
        }} />
      )}
    </div>
  );
}
