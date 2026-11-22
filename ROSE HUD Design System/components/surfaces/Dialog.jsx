import React, { useEffect } from 'react';
import { Panel } from './Panel.jsx';

export function Dialog({ open, onClose, eyebrow, title, children, actions, width = 360 }) {
  useEffect(() => {
    if (!open) return;
    const k = (e) => { if (e.key === 'Escape' && onClose) onClose(); };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div role="dialog" aria-modal="true" onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 100, display: 'grid', placeItems: 'center',
        background: 'var(--surface-overlay)', backdropFilter: 'blur(var(--blur-overlay))',
        animation: 'groov-fade-in var(--dur-base) var(--ease-out)',
      }}>
      <div onClick={(e) => e.stopPropagation()} style={{ width, maxWidth: 'calc(100vw - 32px)' }}>
        <Panel active eyebrow={eyebrow} onClose={onClose} title={title} interactive={false}
          style={{ background: 'var(--ink-100)' }}
          footer={actions ? <div style={{ display: 'flex', gap: 6, marginLeft: 'auto' }}>{actions}</div> : undefined}>
          <div style={{ font: 'var(--type-body-sm)', color: 'var(--fg-2)' }}>{children}</div>
        </Panel>
      </div>
    </div>
  );
}
