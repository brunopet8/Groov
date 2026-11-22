import React, { useRef, useState } from 'react';
import { Icon } from './Icon.jsx';
import { CornerBrackets } from '../surfaces/CornerBrackets.jsx';

const SIZES = {
  sm: { h: 'var(--control-h-sm)', px: 8, fs: 9, icon: 10 },
  md: { h: 'var(--control-h-md)', px: 12, fs: 10, icon: 12 },
  lg: { h: 'var(--control-h-lg)', px: 16, fs: 11, icon: 13 },
};

export function Button({
  children, variant = 'primary', size = 'md', icon, iconRight, disabled = false,
  fullWidth = false, type = 'button', onClick, style, ...rest
}) {
  const [hover, setHover] = useState(false);
  const [press, setPress] = useState(false);
  const ref = useRef(null);
  const s = SIZES[size] || SIZES.md;
  const h = hover && !disabled;

  const v = {
    primary: {
      background: press && h ? 'var(--accent-press)' : h ? 'var(--accent-hover)' : 'var(--accent)',
      color: 'var(--fg-on-accent)', border: '1px solid transparent',
      boxShadow: press && h ? 'var(--glow-red-xs)' : h ? 'var(--glow-red-md)' : 'var(--glow-red-xs)',
    },
    secondary: {
      background: 'transparent', color: h ? 'var(--fg-1)' : 'var(--fg-2)',
      border: `1px solid ${h ? 'var(--red-a40)' : 'var(--border-default)'}`, boxShadow: 'none',
    },
    ghost: {
      background: h ? 'var(--white-a04)' : 'transparent', color: h ? 'var(--fg-1)' : 'var(--fg-2)',
      border: '1px solid transparent', boxShadow: 'none',
    },
    rose: {
      background: h ? 'var(--rose-a08)' : 'transparent', color: 'var(--rose-200)',
      border: `1px solid ${h ? 'var(--rose-200)' : 'var(--rose-a32)'}`, boxShadow: h ? 'var(--glow-rose-sm)' : 'none',
    },
  }[variant];

  const glowColor = variant === 'rose' ? 'rgba(246,193,206,.18)' : variant === 'primary' ? 'rgba(255,255,255,.22)' : 'rgba(240,31,51,.28)';

  return (
    <button
      ref={ref} type={type} disabled={disabled} onClick={onClick}
      onPointerEnter={() => setHover(true)}
      onPointerLeave={() => { setHover(false); setPress(false); }}
      onPointerDown={() => setPress(true)} onPointerUp={() => setPress(false)}
      onPointerMove={(e) => {
        const r = ref.current.getBoundingClientRect();
        ref.current.style.setProperty('--mx', `${e.clientX - r.left}px`);
        ref.current.style.setProperty('--my', `${e.clientY - r.top}px`);
      }}
      {...rest}
      style={{
        position: 'relative', display: fullWidth ? 'flex' : 'inline-flex', width: fullWidth ? '100%' : undefined,
        alignItems: 'center', justifyContent: 'center', gap: 6, height: s.h, padding: `0 ${s.px}px`,
        fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: s.fs, letterSpacing: 'var(--tracking-wider)',
        textTransform: 'uppercase', whiteSpace: 'nowrap', borderRadius: 'var(--radius-sm)',
        cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.35 : 1, overflow: variant === 'secondary' ? 'visible' : 'hidden',
        transform: press && h ? 'scale(.98)' : 'none', outlineOffset: 2,
        transition: 'var(--transition-color), transform var(--dur-instant) var(--ease-out)',
        ...v, ...style,
      }}
    >
      {variant !== 'ghost' && (
        <span aria-hidden="true" style={{
          position: 'absolute', inset: 0, pointerEvents: 'none', opacity: h ? 1 : 0,
          background: `radial-gradient(70px circle at var(--mx,50%) var(--my,50%), ${glowColor}, transparent 70%)`,
          transition: 'opacity var(--dur-slow) var(--ease-out)',
        }} />
      )}
      {variant === 'primary' && h && (
        <span aria-hidden="true" style={{
          position: 'absolute', top: 0, bottom: 0, left: 0, width: '45%', pointerEvents: 'none',
          background: 'var(--grad-red-sweep)', animation: 'groov-sweep 900ms var(--ease-out) 1',
        }} />
      )}
      {variant === 'secondary' && <CornerBrackets active={h} color="transparent" size={0} activeSize={6} offset={-1} />}
      {icon && <Icon name={icon} size={s.icon} style={{ position: 'relative' }} />}
      {children != null && <span style={{ position: 'relative' }}>{children}</span>}
      {iconRight && <Icon name={iconRight} size={s.icon} style={{ position: 'relative' }} />}
    </button>
  );
}
