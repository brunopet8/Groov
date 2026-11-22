import React, { useEffect, useState } from 'react';
import { Icon } from '../core/Icon.jsx';
import { IconButton } from '../core/IconButton.jsx';

export function Toast({ title, message, tone = 'neutral', icon, duration = 0, onClose, action, style }) {
  const [left, setLeft] = useState(100);
  useEffect(() => {
    if (!duration) return;
    const id = setTimeout(() => setLeft(0), 30);
    const t = setTimeout(() => onClose && onClose(), duration);
    return () => { clearTimeout(id); clearTimeout(t); };
  }, [duration]);
  const c = tone === 'red' ? 'var(--red-400)' : tone === 'rose' ? 'var(--rose-200)' : 'var(--fg-1)';
  const border = tone === 'red' ? 'var(--red-a40)' : tone === 'rose' ? 'var(--rose-a32)' : 'var(--border-default)';
  return (
    <div role="status" style={{
      position: 'relative', display: 'flex', alignItems: 'flex-start', gap: 10, width: 280, padding: '10px 8px 10px 10px', overflow: 'hidden',
      background: 'var(--surface-panel)', backdropFilter: 'blur(var(--blur-panel))', border: `1px solid ${border}`,
      boxShadow: tone === 'red' ? 'var(--glow-inset-red)' : 'none',
      animation: 'groov-fade-up var(--dur-slow) var(--ease-out)', ...style,
    }}>
      {icon && <Icon name={icon} size={13} color={c} style={{ marginTop: 1, filter: tone === 'red' ? 'drop-shadow(0 0 4px var(--red-500))' : 'none' }} />}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 3 }}>
        {title && <div style={{ font: 'var(--type-label)', letterSpacing: 'var(--tracking-wider)', textTransform: 'uppercase', color: c }}>{title}</div>}
        {message && <div style={{ font: 'var(--type-body-sm)', color: 'var(--fg-2)' }}>{message}</div>}
        {action && <div style={{ marginTop: 4 }}>{action}</div>}
      </div>
      {onClose && <IconButton icon="x" label="Dismiss" size="sm" onClick={onClose} style={{ width: 18, height: 18, marginTop: -2 }} />}
      {duration > 0 && (
        <span style={{ position: 'absolute', left: 0, bottom: 0, height: 1, width: `${left}%`, background: c, boxShadow: `0 0 6px ${c}`, transition: `width ${duration}ms linear` }} />
      )}
    </div>
  );
}
