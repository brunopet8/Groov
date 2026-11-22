import React, { useEffect, useRef, useState } from 'react';
import { Icon } from '../core/Icon.jsx';

export function Select({ options = [], value, onChange, placeholder = 'Select', label, size = 'md', disabled = false, width, style }) {
  const [open, setOpen] = useState(false);
  const [hover, setHover] = useState(false);
  const [hi, setHi] = useState(-1);
  const ref = useRef(null);
  const opts = options.map((o) => (typeof o === 'string' ? { value: o, label: o } : o));
  const cur = opts.find((o) => o.value === value);
  const h = size === 'sm' ? 'var(--control-h-sm)' : size === 'lg' ? 'var(--control-h-lg)' : 'var(--control-h-md)';

  useEffect(() => {
    if (!open) return;
    const off = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('pointerdown', off);
    return () => document.removeEventListener('pointerdown', off);
  }, [open]);

  const pick = (o) => { onChange && onChange(o.value); setOpen(false); };
  const onKey = (e) => {
    if (e.key === 'Escape') setOpen(false);
    else if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setHi((i) => Math.min(opts.length - 1, i + 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setHi((i) => Math.max(0, i - 1)); }
    else if (e.key === 'Enter' && open && hi >= 0) { e.preventDefault(); pick(opts[hi]); }
  };

  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-flex', flexDirection: 'column', gap: 5, width, opacity: disabled ? 0.4 : 1, ...style }}>
      {label && <span style={{ font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wider)', textTransform: 'uppercase', color: 'var(--fg-3)' }}>{label}</span>}
      <button type="button" disabled={disabled} aria-haspopup="listbox" aria-expanded={open}
        onClick={() => setOpen((o) => !o)} onKeyDown={onKey}
        onPointerEnter={() => setHover(true)} onPointerLeave={() => setHover(false)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, height: h, padding: '0 8px', minWidth: 120,
          background: 'var(--surface-sunken)', color: cur ? 'var(--fg-1)' : 'var(--fg-3)', cursor: disabled ? 'not-allowed' : 'pointer',
          border: `1px solid ${open ? 'var(--red-500)' : hover ? 'var(--border-strong)' : 'var(--border-default)'}`,
          borderRadius: 'var(--radius-xs)', boxShadow: open ? 'var(--glow-red-xs)' : 'none',
          font: 'var(--type-micro)', fontSize: size === 'lg' ? 'var(--fs-xs)' : 'var(--fs-2xs)', letterSpacing: 'var(--tracking-wide)', textTransform: 'uppercase',
          transition: 'var(--transition-color)',
        }}>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{cur ? cur.label : placeholder}</span>
        <Icon name="chevron-down" size={11} color={open ? 'var(--red-400)' : 'var(--fg-3)'}
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform var(--dur-base) var(--ease-out)' }} />
      </button>
      {open && (
        <div role="listbox" style={{
          position: 'absolute', top: '100%', left: 0, right: 0, marginTop: 4, zIndex: 40, padding: 3,
          background: 'var(--ink-100)', border: '1px solid var(--border-default)', backdropFilter: 'blur(var(--blur-panel))',
          boxShadow: '0 12px 32px rgba(0,0,0,.6)', animation: 'groov-fade-up var(--dur-base) var(--ease-out)',
        }}>
          {opts.map((o, i) => {
            const sel = o.value === value; const act = i === hi;
            return (
              <div key={o.value} role="option" aria-selected={sel} onPointerEnter={() => setHi(i)} onClick={() => pick(o)}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, padding: '6px 7px', cursor: 'pointer',
                  font: 'var(--type-micro)', fontSize: 'var(--fs-2xs)', letterSpacing: 'var(--tracking-wide)', textTransform: 'uppercase',
                  color: sel || act ? 'var(--fg-1)' : 'var(--fg-2)', background: act ? 'var(--red-a14)' : 'transparent',
                  transition: 'background-color var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out)',
                }}>
                {o.label}
                {sel && <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--red-500)', boxShadow: 'var(--glow-red-sm)' }} />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
