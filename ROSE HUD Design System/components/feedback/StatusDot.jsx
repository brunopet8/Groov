import React from 'react';

const TONE = {
  online: 'var(--status-online)', live: 'var(--status-live)', idle: 'var(--status-idle)',
  ok: 'var(--status-ok)', warn: 'var(--status-warn)', error: 'var(--status-error)',
};

export function StatusDot({ tone = 'online', label, size = 6, pulse, ping, bracketed = false, style }) {
  const c = TONE[tone] || tone;
  const hot = tone === 'online' || tone === 'live' || tone === 'error';
  const doPulse = pulse ?? hot;
  const doPing = ping ?? tone === 'live';
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: c, ...style }}>
      <span style={{ position: 'relative', display: 'inline-grid', placeItems: 'center', width: size, height: size, flex: 'none' }}>
        {doPing && <span style={{ position: 'absolute', inset: -size, borderRadius: '50%', border: `1px solid ${c}`, animation: 'groov-ping 1.8s var(--ease-out) infinite' }} />}
        <span style={{
          width: size, height: size, borderRadius: '50%', background: c, boxShadow: hot ? `0 0 ${size + 2}px ${c}` : 'none',
          animation: doPulse ? 'groov-pulse var(--dur-pulse) var(--ease-in-out) infinite' : 'none',
        }} />
      </span>
      {label && (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, font: 'var(--type-label)', letterSpacing: 'var(--tracking-widest)', textTransform: 'uppercase', textShadow: hot ? 'var(--text-glow-red)' : 'none' }}>
          {bracketed && <span style={{ width: 8, height: 1, background: 'currentColor' }} />}
          {label}
          {bracketed && <span style={{ width: 8, height: 1, background: 'currentColor' }} />}
        </span>
      )}
    </span>
  );
}
