import React, { useState } from 'react';

const POS = {
  top: { bottom: '100%', left: '50%', transform: 'translate(-50%,-6px)' },
  bottom: { top: '100%', left: '50%', transform: 'translate(-50%,6px)' },
  left: { right: '100%', top: '50%', transform: 'translate(-6px,-50%)' },
  right: { left: '100%', top: '50%', transform: 'translate(6px,-50%)' },
};

export function Tooltip({ content, placement = 'top', children, delay = 120, style }) {
  const [open, setOpen] = useState(false);
  const [t, setT] = useState(null);
  const show = () => setT(setTimeout(() => setOpen(true), delay));
  const hide = () => { clearTimeout(t); setOpen(false); };
  return (
    <span style={{ position: 'relative', display: 'inline-flex', ...style }}
      onPointerEnter={show} onPointerLeave={hide} onFocus={show} onBlur={hide}>
      {children}
      {open && (
        <span role="tooltip" style={{
          position: 'absolute', zIndex: 50, pointerEvents: 'none', whiteSpace: 'nowrap', ...POS[placement],
          padding: '4px 7px', font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wide)', textTransform: 'uppercase',
          color: 'var(--fg-1)', background: 'var(--ink-150)', border: '1px solid var(--red-a40)',
          boxShadow: 'var(--glow-red-xs)', animation: 'groov-fade-in var(--dur-fast) var(--ease-out)',
        }}>{content}</span>
      )}
    </span>
  );
}
