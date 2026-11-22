import React, { useState } from 'react';
import { Icon } from './Icon.jsx';

const DIM = { sm: 22, md: 28, lg: 34 };
const ICON = { sm: 11, md: 13, lg: 15 };

export function IconButton({ icon, label, size = 'md', variant = 'ghost', active = false, disabled = false, onClick, style, ...rest }) {
  const [hover, setHover] = useState(false);
  const h = hover && !disabled;
  const d = DIM[size] || DIM.md;
  const on = active;
  const look = {
    ghost: { background: on ? 'var(--red-a14)' : h ? 'var(--white-a04)' : 'transparent', border: `1px solid ${on ? 'var(--red-a40)' : 'transparent'}` },
    outline: { background: on ? 'var(--red-a14)' : 'transparent', border: `1px solid ${on ? 'var(--red-500)' : h ? 'var(--border-strong)' : 'var(--border-default)'}` },
    solid: { background: h ? 'var(--accent-hover)' : 'var(--accent)', border: '1px solid transparent', boxShadow: h ? 'var(--glow-red-md)' : 'var(--glow-red-xs)' },
  }[variant];
  const color = variant === 'solid' ? 'var(--fg-on-accent)' : on ? 'var(--red-400)' : h ? 'var(--fg-1)' : 'var(--fg-2)';
  return (
    <button
      type="button" aria-label={label} title={label} aria-pressed={active || undefined} disabled={disabled} onClick={onClick}
      onPointerEnter={() => setHover(true)} onPointerLeave={() => setHover(false)}
      {...rest}
      style={{
        display: 'inline-grid', placeItems: 'center', width: d, height: d, padding: 0, color,
        borderRadius: 'var(--radius-sm)', cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.35 : 1,
        filter: on && variant !== 'solid' ? 'drop-shadow(0 0 4px rgba(240,31,51,.6))' : 'none',
        transition: 'var(--transition-color), filter var(--dur-slow) var(--ease-out)', ...look, ...style,
      }}
    >
      <Icon name={icon} size={ICON[size] || 13} />
    </button>
  );
}
