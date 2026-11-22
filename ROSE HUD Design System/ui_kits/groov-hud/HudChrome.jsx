const ChromeDS = window.ROSEHUDDesignSystem_bed3b4;

function HudTopLeft({ phase, onReboot }) {
  const { StatusDot } = ChromeDS;
  const [now, setNow] = React.useState(new Date());
  React.useEffect(() => { const id = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(id); }, []);
  const label = { idle: 'Online', listening: 'Listening', thinking: 'Thinking', dashboard: 'Online' }[phase] || 'Online';
  return (
    <div style={{ position: 'absolute', top: 18, left: 22, display: 'flex', alignItems: 'center', gap: 16, zIndex: 5 }}>
      <button type="button" onClick={onReboot} title="Replay boot" style={{ padding: 0, background: 'none', border: 0, cursor: 'pointer', font: 'var(--type-micro)', letterSpacing: 'var(--tracking-widest)', color: 'var(--fg-rose)' }}>GROOV // CORE 01</button>
      <StatusDot tone={phase === 'listening' ? 'live' : 'online'} label={label} size={5} />
      <span style={{ font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wide)', color: 'var(--fg-3)', fontVariantNumeric: 'tabular-nums' }}>{now.toTimeString().slice(0, 8)}</span>
    </div>
  );
}

function HudTopRight({ chips, onChip, voice, onVoice }) {
  const { Tag, Select } = ChromeDS;
  const items = [['history', 'History'], ['text', 'Text'], ['clear', 'Clear text'], ['camera', 'Camera']];
  return (
    <div style={{ position: 'absolute', top: 14, right: 18, display: 'flex', alignItems: 'center', gap: 6, zIndex: 5 }}>
      {items.map(([id, l]) => <Tag key={id} selected={!!chips[id]} onClick={() => onChip(id)}>{l}</Tag>)}
      <span style={{ width: 8 }} />
      <Select size="sm" value={voice} onChange={onVoice} width={170} options={['Groov — warm', 'Groov — neutral', 'Groov — fast']} />
    </div>
  );
}

function TranscriptStrip({ who, text, speaking }) {
  const { VoiceBars, Badge } = ChromeDS;
  return (
    <div style={{ position: 'absolute', left: 22, bottom: 20, right: 180, display: 'flex', alignItems: 'center', gap: 12, zIndex: 5, minWidth: 0 }}>
      <VoiceBars active={speaking} count={16} height={14} tone={who === 'GROOV' ? 'red' : 'white'} />
      <Badge tone={who === 'GROOV' ? 'red' : 'neutral'}>{who}</Badge>
      <span style={{ font: 'var(--type-data)', fontSize: 'var(--fs-2xs)', color: 'var(--fg-1)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {text}{speaking && <span style={{ color: 'var(--red-400)', animation: 'groov-blink 1s steps(1) infinite' }}>▍</span>}
      </span>
    </div>
  );
}

function CornerOrb({ phase, onClick }) {
  const { Reticle } = ChromeDS;
  const [hover, setHover] = React.useState(false);
  const st = phase === 'listening' ? 'listening' : phase === 'thinking' ? 'thinking' : 'online';
  return (
    <button type="button" aria-label="Talk to GROOV" onClick={onClick}
      onPointerEnter={() => setHover(true)} onPointerLeave={() => setHover(false)}
      style={{ position: 'absolute', right: 14, bottom: 10, padding: 0, background: 'none', border: 0, cursor: 'pointer', zIndex: 6, transform: hover ? 'scale(1.05)' : 'none', transition: 'transform var(--dur-slow) var(--ease-out)' }}>
      <Reticle size={130} state={st} tone="rose" view={hover || st !== 'online' ? '3d' : '2d'} ringText="GROOV // CORE 01">
        <span style={{ font: 'var(--type-display)', fontSize: 'var(--fs-md)', letterSpacing: '.08em', color: 'var(--fg-1)', textShadow: hover ? 'var(--text-glow-red)' : 'var(--text-glow-white)', transition: 'text-shadow var(--dur-slow) var(--ease-out)' }}>GROOV</span>
      </Reticle>
    </button>
  );
}

Object.assign(window, { HudTopLeft, HudTopRight, TranscriptStrip, CornerOrb });
