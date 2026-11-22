import React, { useState } from 'react';

export function Switch({ checked, defaultChecked = false, onChange, label, disabled = false, style }) {
  const [inner, setInner] = useState(defaultChecked);
  const [hover, setHover] = useState(false);
  const on = checked ?? inner;
  const toggle = () => { if (disabled) return; if (checked === undefined) setInner(!on); onChange && onChange(!on); };
  return (
    <label onPointerEnter={() => setHover(true)} onPointerLeave={() => setHover(false)}
      style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.4 : 1, userSelect: 'none', ...style }}>
      <span role="switch" aria-checked={on} tabIndex={disabled ? -1 : 0} onClick={toggle}
        onKeyDown={(e) => { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); toggle(); } }}
        style={{
          position: 'relative', width: 26, height: 14, flex: 'none', borderRadius: 'var(--radius-pill)',
          background: on ? 'var(--red-a40)' : 'var(--ink-300)',
          border: `1px solid ${on ? 'var(--red-500)' : hover ? 'var(--border-strong)' : 'var(--border-default)'}`,
          boxShadow: on ? 'var(--glow-red-sm)' : 'none', transition: 'var(--transition-color)',
        }}>
        <span style={{
          position: 'absolute', top: 1, left: 1, width: 10, height: 10, borderRadius: '50%',
          background: on ? 'var(--white-pure)' : 'var(--fg-2)', boxShadow: on ? 'var(--glow-white-sm)' : 'none',
          transform: on ? 'translateX(12px)' : 'none', transition: 'transform var(--dur-base) var(--ease-spring), background-color var(--dur-base) var(--ease-out)',
        }} />
      </span>
      {label && <span onClick={toggle} style={{ font: 'var(--type-label)', letterSpacing: 'var(--tracking-wider)', textTransform: 'uppercase', color: on ? 'var(--fg-1)' : 'var(--fg-2)', transition: 'var(--transition-color)' }}>{label}</span>}
    </label>
  );
}
