import React, { useState } from 'react';
import { Icon } from '../core/Icon.jsx';

export function Checkbox({ checked, defaultChecked = false, onChange, label, disabled = false, style }) {
  const [inner, setInner] = useState(defaultChecked);
  const [hover, setHover] = useState(false);
  const on = checked ?? inner;
  const toggle = () => { if (disabled) return; if (checked === undefined) setInner(!on); onChange && onChange(!on); };
  return (
    <label onPointerEnter={() => setHover(true)} onPointerLeave={() => setHover(false)}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.4 : 1, userSelect: 'none', ...style }}>
      <span role="checkbox" aria-checked={on} tabIndex={disabled ? -1 : 0} onClick={toggle}
        onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); toggle(); } }}
        style={{
          display: 'grid', placeItems: 'center', width: 12, height: 12, flex: 'none', borderRadius: 'var(--radius-xs)',
          background: on ? 'var(--accent)' : 'transparent', color: 'var(--fg-on-accent)',
          border: `1px solid ${on ? 'var(--accent)' : hover ? 'var(--red-400)' : 'var(--border-strong)'}`,
          boxShadow: on ? 'var(--glow-red-sm)' : 'none', transition: 'var(--transition-color)',
        }}>
        <Icon name="check" size={9} style={{ opacity: on ? 1 : 0, transform: on ? 'scale(1)' : 'scale(.4)', transition: 'all var(--dur-base) var(--ease-spring)' }} />
      </span>
      {label && <span onClick={toggle} style={{ font: 'var(--type-body-sm)', color: on || hover ? 'var(--fg-1)' : 'var(--fg-2)', transition: 'var(--transition-color)' }}>{label}</span>}
    </label>
  );
}
