const AppDS = window.ROSEHUDDesignSystem_bed3b4;
const ROSE_QUERY = 'Research Meta Quest — sales, top genres, what ships next. Be specific.';
const ROSE_REPLY = 'Ten panels up. Short version: about 20 million sold, and social, sandbox and fitness titles keep people coming back.';
const stamp = () => new Date().toTimeString().slice(0, 5);

function IdleView() {
  const { Panel, Progress } = AppDS;
  return (
    <>
      <div style={{ position: 'absolute', left: '50%', top: '50%', width: 520, height: 520, transform: 'translate(-50%,-50%)', background: 'var(--grad-core)', opacity: 0.5, animation: 'groov-pulse 4s var(--ease-in-out) infinite' }} />
      <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%,-50%)', font: 'var(--type-micro)', letterSpacing: 'var(--tracking-widest)', color: 'var(--fg-3)', whiteSpace: 'nowrap', animation: 'groov-fade-up .8s var(--ease-out)' }}>
        PRESS SPACE OR TAP THE CORE TO TALK<span style={{ color: 'var(--red-400)', animation: 'groov-blink 1s steps(1) infinite' }}> _</span>
      </div>
      <div style={{ position: 'absolute', left: 0, top: '54%', width: 230 }}>
        <Panel eyebrow="Last session" meta="#S-041" title="Meta Quest — late 2025: real hits, hard limits" footer={<><span>64% reviewed</span><span style={{ marginLeft: 'auto' }}>10 panels</span></>}>
          <Progress size="sm" value={64} showValue={false} />
        </Panel>
      </div>
    </>
  );
}

function ThinkView({ phase, text }) {
  const { StatusDot } = AppDS;
  return (
    <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', animation: 'groov-fade-in .5s var(--ease-out)' }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28 }}>
        <CoreRings size={340} mode={phase} />
        <StatusDot tone={phase === 'listening' ? 'live' : 'online'} label={phase === 'listening' ? 'Listening...' : 'Pulling sources...'} />
        <div style={{ maxWidth: 520, minHeight: 18, textAlign: 'center', font: 'var(--type-data)', fontSize: 'var(--fs-xs)', color: 'var(--fg-1)' }}>{text}</div>
      </div>
    </div>
  );
}

function App() {
  const { Dialog, Button, Toast, Input, IconButton } = AppDS;
  const start = window.ROSE_START || 'dashboard';
  const dash = start === 'dashboard';
  const [phase, setPhase] = React.useState(start);
  const [chips, setChips] = React.useState({ history: dash, text: false, camera: false });
  const [voice, setVoice] = React.useState('Groov — warm');
  const [panels, setPanels] = React.useState(dash ? DASH_PANELS.map((p) => p.id) : []);
  const [activeId, setActiveId] = React.useState(dash ? 'sold' : null);
  const [strip, setStrip] = React.useState({ who: 'YOU', text: 'No, please. Go, please proceed! Be specific', speaking: false });
  const [turns, setTurns] = React.useState(dash ? [
    { who: 'YOU', time: '21:02', text: ROSE_QUERY },
    { who: 'GROOV', time: '21:02', text: ROSE_REPLY },
    { who: 'YOU', time: '21:04', text: 'No, please. Go, please proceed! Be specific' },
  ] : []);
  const [confirm, setConfirm] = React.useState(false);
  const [toast, setToast] = React.useState(null);
  const [draft, setDraft] = React.useState('');
  const timers = React.useRef([]);
  const phaseRef = React.useRef(phase);
  phaseRef.current = phase;
  const later = (fn, ms) => timers.current.push(setTimeout(fn, ms));

  const talk = (q = ROSE_QUERY) => {
    if (['listening', 'thinking', 'boot'].includes(phaseRef.current)) return;
    timers.current.forEach(clearTimeout); timers.current = [];
    setPhase('listening'); setActiveId(null); setToast(null);
    let n = 0;
    setStrip({ who: 'YOU', text: '', speaking: true });
    const step = () => {
      n += 2;
      setStrip({ who: 'YOU', text: q.slice(0, n), speaking: true });
      if (n < q.length) return later(step, 35);
      later(() => {
        setTurns((t) => [...t, { who: 'YOU', time: stamp(), text: q }]);
        setPhase('thinking');
        setStrip({ who: 'GROOV', text: 'Pulling sources...', speaking: true });
        later(() => {
          setPanels(DASH_PANELS.map((p) => p.id)); setPhase('dashboard'); setActiveId('sold');
          setStrip({ who: 'GROOV', text: ROSE_REPLY, speaking: true });
          setTurns((t) => [...t, { who: 'GROOV', time: stamp(), text: ROSE_REPLY }]);
          setChips((c) => ({ ...c, history: true }));
          setToast({ title: '10 panels', message: 'Research canvas ready.' });
          later(() => setStrip((s) => ({ ...s, speaking: false })), 2800);
        }, 1600);
      }, 500);
    };
    later(step, 500);
  };

  React.useEffect(() => {
    const k = (e) => { if (e.code === 'Space' && e.target === document.body) { e.preventDefault(); talk(); } };
    window.addEventListener('keydown', k);
    return () => { window.removeEventListener('keydown', k); timers.current.forEach(clearTimeout); };
  }, []);

  const onChip = (id) => {
    if (id === 'clear') { if (panels.length) setConfirm(true); return; }
    setChips((c) => ({ ...c, [id]: !c[id] }));
  };
  const clearAll = () => { setPanels([]); setActiveId(null); setConfirm(false); setPhase('idle'); setChips((c) => ({ ...c, camera: false })); };
  const closePanel = (id) => setPanels((ps) => { const nx = ps.filter((x) => x !== id); if (!nx.length) setPhase('idle'); return nx; });
  const send = () => { if (!draft.trim()) return; const q = draft.trim(); setDraft(''); talk(q); };

  if (phase === 'boot') return <BootScreen onDone={() => setPhase('idle')} />;

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, backgroundImage: 'var(--bg-grid)', backgroundSize: 'var(--bg-grid-size)', WebkitMaskImage: 'radial-gradient(ellipse at center, #000 20%, transparent 75%)', maskImage: 'radial-gradient(ellipse at center, #000 20%, transparent 75%)', opacity: 0.7 }} />
      <div style={{ position: 'absolute', inset: 0, background: 'var(--grad-vignette)', pointerEvents: 'none' }} />
      <HudTopLeft phase={phase} onReboot={() => setPhase('boot')} />
      <HudTopRight chips={{ ...chips, clear: confirm }} onChip={onChip} voice={voice} onVoice={setVoice} />
      <div style={{ position: 'absolute', top: 48, left: 22, right: 22, bottom: 52, display: 'grid', gridTemplateColumns: chips.history ? 'minmax(0,1fr) 250px' : 'minmax(0,1fr)', gap: 14 }}>
        <div style={{ position: 'relative', minHeight: 0, minWidth: 0 }}>
          {phase === 'dashboard' && <Dashboard panels={panels} activeId={activeId} onActivate={setActiveId} onClose={closePanel} camera={chips.camera} />}
          {phase === 'idle' && <IdleView />}
          {(phase === 'listening' || phase === 'thinking') && <ThinkView phase={phase} text={strip.text} />}
        </div>
        {chips.history && <div style={{ minHeight: 0, display: 'flex', flexDirection: 'column', paddingBottom: 96 }}><TranscriptColumn turns={turns} /></div>}
      </div>
      <TranscriptStrip who={strip.who} text={strip.text} speaking={strip.speaking} />
      {chips.text && (
        <div style={{ position: 'absolute', left: '50%', bottom: 56, transform: 'translateX(-50%)', width: 440, display: 'flex', gap: 6, alignItems: 'center', zIndex: 7, animation: 'groov-fade-up var(--dur-slow) var(--ease-out)' }}>
          <Input value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()} placeholder="Type to GROOV…" icon="type" style={{ flex: 1 }} />
          <IconButton icon="send" label="Send" variant="solid" onClick={send} />
        </div>
      )}
      <CornerOrb phase={phase} onClick={() => talk()} />
      {toast && <div style={{ position: 'absolute', left: 22, bottom: 48, zIndex: 8 }}><Toast icon="layout-grid" title={toast.title} message={toast.message} tone="rose" duration={3500} onClose={() => setToast(null)} /></div>}
      <Dialog open={confirm} onClose={() => setConfirm(false)} eyebrow="System" title="Clear all panels?"
        actions={<><Button variant="ghost" size="sm" onClick={() => setConfirm(false)}>Cancel</Button><Button size="sm" onClick={clearAll}>Clear</Button></>}>
        Removes {panels.length} panels from the canvas. Transcript is kept.
      </Dialog>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
