import React from 'react';

export function Badge({ children, tone = 'neutral', variant = 'soft', dot = false, style, ...rest }) {
  const c = { neutral: 'var(--fg-2)', red: 'var(--red-400)', rose: 'var(--rose-200)', white: 'var(--fg-1)' }[tone] || 'var(--fg-2)';
  const bg = { neutral: 'var(--white-a08)', red: 'var(--red-a14)', rose: 'var(--rose-a08)', white: 'var(--white-a12)' }[tone];
  const solid = variant === 'solid';
  return (
    <span {...rest} style={{
      display: 'inline-flex', alignItems: 'center', gap: 4, height: 16, padding: '0 5px',
      font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wide)', textTransform: 'uppercase', whiteSpace: 'nowrap',
      borderRadius: 'var(--radius-sm)',
      color: solid ? (tone === 'red' ? 'var(--fg-on-accent)' : 'var(--ink-50)') : c,
      background: solid ? (tone === 'red' ? 'var(--accent)' : c) : variant === 'outline' ? 'transparent' : bg,
      border: variant === 'outline' ? `1px solid ${c}` : '1px solid transparent',
      boxShadow: solid && tone === 'red' ? 'var(--glow-red-xs)' : 'none', ...style,
    }}>
      {dot && <span style={{ width: 4, height: 4, borderRadius: '50%', background: 'currentColor', boxShadow: '0 0 4px currentColor' }} />}
      {children}
    </span>
  );
}
