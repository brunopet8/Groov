import React, { useState } from 'react';
import { Icon } from '../core/Icon.jsx';
import { CornerBrackets } from '../surfaces/CornerBrackets.jsx';

const H = { sm: 'var(--control-h-sm)', md: 'var(--control-h-md)', lg: 'var(--control-h-lg)' };

export function Input({
  label, hint, error, icon, suffix, size = 'md', mono = false, disabled = false,
  value, defaultValue, onChange, placeholder, type = 'text', style, inputStyle, ...rest
}) {
  const [focus, setFocus] = useState(false);
  const [hover, setHover] = useState(false);
  const bad = !!error;
  const border = bad ? 'var(--red-400)' : focus ? 'var(--red-a40)' : hover && !disabled ? 'var(--border-strong)' : 'var(--border-default)';
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 5, minWidth: 0, opacity: disabled ? 0.4 : 1, ...style }}>
      {label && <span style={{ font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wider)', textTransform: 'uppercase', color: focus ? 'var(--fg-1)' : 'var(--fg-3)', transition: 'var(--transition-color)' }}>{label}</span>}
      <span
        onPointerEnter={() => setHover(true)} onPointerLeave={() => setHover(false)}
        style={{
          position: 'relative', display: 'flex', alignItems: 'center', gap: 6, height: H[size] || H.md, padding: '0 8px',
          background: focus ? 'var(--ink-100)' : 'var(--surface-sunken)', border: `1px solid ${border}`, borderRadius: 'var(--radius-xs)',
          boxShadow: focus ? 'var(--glow-inset-red)' : 'none', transition: 'var(--transition-color)',
          color: focus ? 'var(--red-400)' : 'var(--fg-3)',
        }}>
        <CornerBrackets active={focus || bad} color="transparent" size={0} activeSize={6} />
        {icon && <Icon name={icon} size={12} />}
        <input
          type={type} value={value} defaultValue={defaultValue} onChange={onChange} placeholder={placeholder} disabled={disabled}
          onFocus={() => setFocus(true)} onBlur={() => setFocus(false)} {...rest}
          style={{
            flex: 1, minWidth: 0, height: '100%', background: 'transparent', border: 0, outline: 0, padding: 0,
            color: 'var(--fg-1)', caretColor: 'var(--red-400)',
            font: mono ? 'var(--type-data)' : 'var(--type-body)', fontSize: size === 'sm' ? 'var(--fs-xs)' : undefined, ...inputStyle,
          }} />
        {suffix && <span style={{ font: 'var(--type-micro)', color: 'var(--fg-3)', letterSpacing: 'var(--tracking-wide)' }}>{suffix}</span>}
      </span>
      {(error || hint) && <span style={{ font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wide)', color: bad ? 'var(--red-400)' : 'var(--fg-3)' }}>{error || hint}</span>}
    </label>
  );
}
