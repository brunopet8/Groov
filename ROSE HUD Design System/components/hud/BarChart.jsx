import React, { useEffect, useState } from 'react';

export function BarChart({ data = [], height = 80, highlight = 'max', showValues = false, unit = '', animate = true, gap = 6, style }) {
  const [grown, setGrown] = useState(!animate);
  const [hov, setHov] = useState(null);
  useEffect(() => { if (animate) { const id = setTimeout(() => setGrown(true), 30); return () => clearTimeout(id); } }, []);
  const max = Math.max(1, ...data.map((d) => d.value));
  const hiIdx = highlight === 'max' ? data.findIndex((d) => d.value === max) : typeof highlight === 'number' ? highlight : -1;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 5, ...style }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap, height, borderBottom: '1px solid var(--border-strong)' }}>
        {data.map((d, i) => {
          const red = i === hiIdx || i === hov;
          return (
            <div key={i} onPointerEnter={() => setHov(i)} onPointerLeave={() => setHov(null)}
              style={{ position: 'relative', flex: 1, height: '100%', display: 'flex', alignItems: 'flex-end', cursor: 'default' }}>
              {(showValues || i === hov) && (
                <span style={{
                  position: 'absolute', left: '50%', transform: 'translateX(-50%)', bottom: `calc(${(d.value / max) * 100}% + 3px)`,
                  font: 'var(--type-micro)', color: red ? 'var(--red-400)' : 'var(--fg-2)', whiteSpace: 'nowrap',
                  opacity: grown ? 1 : 0, transition: 'opacity var(--dur-slow) var(--ease-out), color var(--dur-fast)',
                }}>{d.value}{unit}</span>
              )}
              <div style={{
                width: '100%', height: grown ? `${(d.value / max) * 100}%` : '0%',
                background: red ? 'var(--red-500)' : 'rgba(244,244,246,.85)', boxShadow: red ? 'var(--glow-red-sm)' : 'none',
                transition: `height var(--dur-slower) var(--ease-out) ${i * 60}ms, background-color var(--dur-base) var(--ease-out), box-shadow var(--dur-base) var(--ease-out)`,
              }} />
            </div>
          );
        })}
      </div>
      {data.some((d) => d.label) && (
        <div style={{ display: 'flex', gap }}>
          {data.map((d, i) => (
            <span key={i} style={{ flex: 1, textAlign: 'center', font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wide)', textTransform: 'uppercase', color: i === hov || i === hiIdx ? 'var(--fg-1)' : 'var(--fg-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', transition: 'color var(--dur-fast)' }}>{d.label}</span>
          ))}
        </div>
      )}
    </div>
  );
}
