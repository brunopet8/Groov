import React, { useState } from 'react';
import { Icon } from './Icon.jsx';

export function Tag({ children, selected = false, onClick, onRemove, icon, disabled = false, style, ...rest }) {
  const [hover, setHover] = useState(false);
  const h = hover && !disabled;
  const interactive = !!onClick;
  return (
    <span
      role={interactive ? 'button' : undefined} tabIndex={interactive && !disabled ? 0 : undefined}
      aria-pressed={interactive ? selected : undefined}
      onClick={disabled ? undefined : onClick}
      onKeyDown={(e) => { if (interactive && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); onClick(e); } }}
      onPointerEnter={() => setHover(true)} onPointerLeave={() => setHover(false)}
      {...rest}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 5, height: 20, padding: '0 7px',
        font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wider)', textTransform: 'uppercase', whiteSpace: 'nowrap',
        borderRadius: 'var(--radius-sm)', userSelect: 'none',
        cursor: disabled ? 'not-allowed' : interactive ? 'pointer' : 'default', opacity: disabled ? 0.35 : 1,
        color: selected ? 'var(--fg-1)' : h && interactive ? 'var(--fg-1)' : 'var(--fg-2)',
        background: selected ? 'var(--red-a14)' : 'var(--surface-panel)',
        border: `1px solid ${selected ? 'var(--red-500)' : h && interactive ? 'var(--border-strong)' : 'var(--border-default)'}`,
        boxShadow: selected ? 'var(--glow-red-xs)' : 'none',
        transition: 'var(--transition-color)', ...style,
      }}
    >
      {icon && <Icon name={icon} size={10} />}
      {children}
      {onRemove && (
        <span role="button" aria-label="Remove" onClick={(e) => { e.stopPropagation(); onRemove(e); }}
          style={{ display: 'inline-grid', placeItems: 'center', marginRight: -3, cursor: 'pointer', color: 'var(--fg-3)' }}>
          <Icon name="x" size={9} />
        </span>
      )}
    </span>
  );
}
