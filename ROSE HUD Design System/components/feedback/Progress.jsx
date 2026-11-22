import React from 'react';

export function Progress({ value = 0, label, showValue = true, size = 'md', tone = 'red', indeterminate = false, width = '100%', style }) {
  const v = Math.max(0, Math.min(100, value));
  const h = size === 'sm' ? 2 : size === 'lg' ? 8 : 6;
  const fill = tone === 'rose' ? 'var(--grad-rose-red)' : tone === 'white' ? 'var(--fg-1)' : 'var(--grad-red-bar)';
  const glow = tone === 'white' ? 'var(--glow-white-sm)' : tone === 'rose' ? 'var(--glow-rose-sm)' : 'var(--glow-red-sm)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width, ...style }}>
      {label && (
        <div style={{ font: 'var(--type-label)', letterSpacing: 'var(--tracking-widest)', textTransform: 'uppercase', color: 'var(--fg-1)', textAlign: 'center' }}>{label}</div>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div role="progressbar" aria-valuenow={indeterminate ? undefined : v} aria-valuemin={0} aria-valuemax={100}
          style={{
            position: 'relative', flex: 1, height: h, overflow: 'hidden', borderRadius: 'var(--radius-pill)',
            background: 'var(--ink-200)', border: size === 'sm' ? 0 : '1px solid var(--border-subtle)',
          }}>
          <div style={{
            position: 'absolute', top: 0, bottom: 0, left: 0, borderRadius: 'inherit', background: fill, boxShadow: glow,
            width: indeterminate ? '35%' : `${v}%`,
            animation: indeterminate ? 'groov-sweep 1.4s var(--ease-in-out) infinite' : 'none',
            transition: 'width var(--dur-slower) var(--ease-out)',
          }}>
            {!indeterminate && v > 0 && (
              <span style={{ position: 'absolute', inset: 0, overflow: 'hidden', borderRadius: 'inherit' }}>
                <span style={{ position: 'absolute', top: 0, bottom: 0, width: '40%', background: 'var(--grad-red-sweep)', opacity: 0.6, animation: 'groov-sweep 2.2s var(--ease-in-out) infinite' }} />
              </span>
            )}
          </div>
        </div>
        {showValue && !indeterminate && (
          <span style={{ minWidth: 30, textAlign: 'right', font: 'var(--type-data)', fontSize: 'var(--fs-xs)', letterSpacing: 'var(--tracking-wide)', color: 'var(--fg-1)', fontVariantNumeric: 'tabular-nums' }}>{Math.round(v)}%</span>
        )}
      </div>
    </div>
  );
}
