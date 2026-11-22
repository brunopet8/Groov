import React, { useRef, useState } from 'react';
import { CornerBrackets } from './CornerBrackets.jsx';
import { IconButton } from '../core/IconButton.jsx';

export function Panel({
  eyebrow, meta, title, children, footer, onClose, actions, active = false, brackets = true,
  interactive = true, enter = true, delay = 0, padding = 'var(--panel-pad)', width, height, style, bodyStyle, ...rest
}) {
  const [hover, setHover] = useState(false);
  const ref = useRef(null);
  const lit = active || (hover && interactive);
  const hasHeader = eyebrow || meta || onClose || actions;
  return (
    <section
      ref={ref}
      onPointerEnter={() => setHover(true)} onPointerLeave={() => setHover(false)}
      onPointerMove={interactive ? (e) => {
        const r = ref.current.getBoundingClientRect();
        ref.current.style.setProperty('--mx', `${e.clientX - r.left}px`);
        ref.current.style.setProperty('--my', `${e.clientY - r.top}px`);
      } : undefined}
      {...rest}
      style={{
        position: 'relative', display: 'flex', flexDirection: 'column', width, height, minWidth: 0,
        background: 'var(--surface-panel)', backdropFilter: 'blur(var(--blur-panel))', WebkitBackdropFilter: 'blur(var(--blur-panel))',
        border: `1px solid ${active ? 'var(--red-a60)' : lit ? 'var(--red-a40)' : 'var(--border-default)'}`,
        boxShadow: active ? 'var(--glow-inset-red), var(--glow-red-sm)' : lit ? 'var(--glow-inset-red)' : 'none',
        transition: 'var(--transition-color)',
        animation: enter ? `groov-scale-in var(--dur-slow) var(--ease-out) ${delay}ms both` : 'none', ...style,
      }}
    >
      {interactive && (
        <span aria-hidden="true" style={{
          position: 'absolute', inset: 0, pointerEvents: 'none', opacity: hover ? 1 : 0,
          background: 'radial-gradient(220px circle at var(--mx,50%) var(--my,50%), rgba(240,31,51,.10), transparent 70%)',
          transition: 'opacity var(--dur-slow) var(--ease-out)',
        }} />
      )}
      {brackets && <CornerBrackets active={lit} color="var(--fg-2)" />}
      {hasHeader && (
        <header style={{
          position: 'relative', display: 'flex', alignItems: 'center', gap: 8, height: 'var(--panel-header-h)', padding: '0 4px 0 8px',
          borderBottom: '1px solid var(--border-subtle)', flex: 'none',
        }}>
          <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wider)', textTransform: 'uppercase', color: lit ? 'var(--fg-2)' : 'var(--fg-3)', transition: 'var(--transition-color)' }}>{eyebrow}</span>
          {meta && <span style={{ font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wide)', color: lit ? 'var(--red-400)' : 'var(--fg-3)', transition: 'var(--transition-color)' }}>{meta}</span>}
          {actions}
          {onClose && <IconButton icon="x" label="Close" size="sm" onClick={onClose} style={{ width: 18, height: 18 }} />}
        </header>
      )}
      <div style={{ position: 'relative', flex: 1, minHeight: 0, padding, display: 'flex', flexDirection: 'column', gap: 8, ...bodyStyle }}>
        {title && <h3 style={{ margin: 0, font: 'var(--type-heading)', textTransform: 'uppercase', color: 'var(--fg-1)', textWrap: 'pretty' }}>{title}</h3>}
        {children}
      </div>
      {footer && (
        <footer style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', borderTop: '1px solid var(--border-subtle)', font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wide)', color: 'var(--fg-3)' }}>{footer}</footer>
      )}
    </section>
  );
}
