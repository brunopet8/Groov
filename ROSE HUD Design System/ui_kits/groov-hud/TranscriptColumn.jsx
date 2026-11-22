const TxDS = window.ROSEHUDDesignSystem_bed3b4;

function TranscriptColumn({ turns }) {
  const ref = React.useRef(null);
  React.useEffect(() => { if (ref.current) ref.current.scrollTop = ref.current.scrollHeight; }, [turns.length]);
  return (
    <aside style={{ position: 'relative', display: 'flex', flexDirection: 'column', minHeight: 0, borderLeft: '1px solid var(--border-subtle)', background: 'rgba(5,5,6,.6)', animation: 'groov-fade-in var(--dur-slow) var(--ease-out)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 'var(--panel-header-h)', padding: '0 12px', borderBottom: '1px solid var(--border-subtle)' }}>
        <span style={{ font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wider)', color: 'var(--fg-3)' }}>TRANSCRIPT</span>
        <span style={{ font: 'var(--type-micro)', color: 'var(--fg-3)' }}>{turns.length}</span>
      </div>
      <div ref={ref} style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 14 }}>
        {turns.map((t, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 4, animation: 'groov-fade-up var(--dur-slow) var(--ease-out)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wider)', color: t.who === 'GROOV' ? 'var(--red-400)' : 'var(--fg-2)' }}>{t.who}</span>
              <span style={{ font: 'var(--type-micro)', color: 'var(--fg-3)' }}>{t.time}</span>
            </div>
            <div style={{ font: 'var(--type-data)', fontSize: 'var(--fs-2xs)', lineHeight: 1.55, color: t.who === 'GROOV' ? 'var(--fg-1)' : 'var(--fg-2)', textWrap: 'pretty' }}>{t.text}</div>
          </div>
        ))}
      </div>
    </aside>
  );
}

window.TranscriptColumn = TranscriptColumn;
