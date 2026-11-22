const BootDS = window.ROSEHUDDesignSystem_bed3b4;

const BOOT_STEPS = [
  { at: 0, phase: 'cross' },
  { at: 700, phase: 'rings' },
  { at: 1500, phase: 'load', v: 18, l: 'Iniciando sistema...' },
  { at: 2500, phase: 'load', v: 47, l: 'Carregando módulos...' },
  { at: 3500, phase: 'load', v: 87, l: 'Finalizando inicialização...' },
  { at: 4300, phase: 'load', v: 100, l: 'Finalizando inicialização...' },
  { at: 4900, phase: 'online' },
  { at: 7200, phase: 'done' },
];

function BootScreen({ onDone }) {
  const { Reticle, Progress, StatusDot, CornerBrackets, Button } = BootDS;
  const [i, setI] = React.useState(0);
  React.useEffect(() => {
    const ts = BOOT_STEPS.map((s, k) => setTimeout(() => (s.phase === 'done' ? onDone() : setI(k)), s.at));
    return () => ts.forEach(clearTimeout);
  }, []);
  const s = BOOT_STEPS[i];
  const ph = s.phase;
  const tick = { position: 'absolute', top: 'calc(50% - 14px)', width: 1, height: 28, background: 'var(--red-500)', boxShadow: 'var(--glow-red-sm)', animation: 'groov-flicker .8s linear both' };
  return (
    <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', background: 'var(--bg-void)', animation: 'groov-fade-in .4s var(--ease-out)' }}>
      <div style={{ position: 'absolute', inset: 28 }}><CornerBrackets size={28} color="var(--fg-3)" /></div>
      <div style={{ position: 'absolute', left: '4%', right: '4%', top: '50%', height: 1, background: 'linear-gradient(90deg,transparent,var(--white-a12) 20%,var(--white-a12) 80%,transparent)' }} />
      <div style={{ position: 'absolute', top: '6%', bottom: '6%', left: '50%', width: 1, background: 'linear-gradient(180deg,transparent,var(--white-a04),transparent)' }} />
      <span style={{ ...tick, left: '4%' }} /><span style={{ ...tick, right: '4%' }} />
      <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 22 }}>
        <div style={{ transform: ph === 'cross' ? 'scale(.82)' : 'none', opacity: ph === 'cross' ? 0.6 : 1, transition: 'all .9s var(--ease-out)' }}>
          <Reticle size={260} state={ph === 'cross' ? 'off' : ph === 'online' ? 'listening' : 'idle'} ticks={ph !== 'cross'} view={ph === 'online' ? '3d' : '2d'} ringText={ph === 'online' ? 'GROOV // CORE 01 // ONLINE' : undefined}>
            {ph === 'cross' ? (
              <span style={{ font: '200 22px var(--font-sans)', color: 'var(--fg-3)' }}>+</span>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, animation: 'groov-flicker 1.1s linear both' }}>
                <span style={{ font: 'var(--type-display)', letterSpacing: '.08em', color: 'var(--fg-1)', textShadow: 'var(--text-glow-white)' }}>GROOV</span>
                <span style={{ font: 'var(--type-micro)', letterSpacing: '2px', color: 'var(--fg-3)' }}>///</span>
              </div>
            )}
          </Reticle>
        </div>
        <div style={{ height: 52, width: 340, display: 'grid', placeItems: 'center' }}>
          {ph === 'load' && (
            <div style={{ width: '100%', animation: 'groov-fade-up .4s var(--ease-out)' }}><Progress label={s.l} value={s.v} /></div>
          )}
          {ph === 'online' && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, animation: 'groov-fade-up .6s var(--ease-out)' }}>
              <StatusDot tone="online" label="Online" bracketed pulse={false} size={0} />
              <div style={{ display: 'flex', gap: 8 }}>
                {[0, 1, 2].map((d) => <span key={d} style={{ width: 4, height: 4, borderRadius: '50%', background: d === 0 ? 'var(--red-500)' : 'var(--ink-500)', boxShadow: d === 0 ? 'var(--glow-red-sm)' : 'none' }} />)}
              </div>
            </div>
          )}
        </div>
      </div>
      <div style={{ position: 'absolute', right: 44, bottom: 40 }}><Button variant="ghost" size="sm" iconRight="skip-forward" onClick={onDone}>Skip</Button></div>
      <div style={{ position: 'absolute', left: 44, bottom: 44, font: 'var(--type-micro)', letterSpacing: 'var(--tracking-wider)', color: 'var(--fg-3)' }}>GROOV // CORE 01 · BOOT {String(i).padStart(2, '0')}/06</div>
    </div>
  );
}

window.BootScreen = BootScreen;
