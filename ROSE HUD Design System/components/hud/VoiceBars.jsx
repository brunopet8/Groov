import React, { useMemo } from 'react';

export function VoiceBars({ count = 24, active = true, height = 18, barWidth = 2, gap = 2, tone = 'red', style }) {
  const bars = useMemo(() => Array.from({ length: count }, (_, i) => {
    const s = Math.sin(i * 12.9898) * 43758.5453;
    const r = s - Math.floor(s);
    return { d: (r * 0.8).toFixed(2), dur: (0.6 + r * 0.7).toFixed(2), amp: 0.35 + 0.65 * Math.abs(Math.sin((i / count) * Math.PI)) };
  }), [count]);
  const c = tone === 'rose' ? 'var(--rose-400)' : tone === 'white' ? 'var(--fg-1)' : 'var(--red-500)';
  return (
    <div aria-hidden="true" style={{ display: 'flex', alignItems: 'center', gap, height, ...style }}>
      {bars.map((b, i) => (
        <span key={i} style={{
          width: barWidth, height: active ? `${b.amp * 100}%` : 2, background: active ? c : 'var(--ink-500)',
          boxShadow: active && tone !== 'white' ? `0 0 4px ${c}` : 'none', transformOrigin: 'center', borderRadius: 1,
          animation: active ? `groov-bar ${b.dur}s var(--ease-in-out) ${b.d}s infinite` : 'none',
          transition: 'height var(--dur-slow) var(--ease-out), background-color var(--dur-base) var(--ease-out)',
        }} />
      ))}
    </div>
  );
}
