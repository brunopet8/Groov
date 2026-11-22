function CoreRings({ size = 340, mode = 'listening' }) {
  const fast = mode === 'thinking' ? 0.4 : 1;
  const stage = React.useRef(null);
  React.useEffect(() => {
    const mv = (e) => {
      if (!stage.current) return;
      const px = e.clientX / window.innerWidth - 0.5; const py = e.clientY / window.innerHeight - 0.5;
      stage.current.style.transform = `rotateX(${-py * 30}deg) rotateY(${px * 40}deg) rotateZ(-24deg)`;
    };
    window.addEventListener('pointermove', mv);
    return () => window.removeEventListener('pointermove', mv);
  }, []);
  const rings = [
    { inset: '6%', ry: 64, rx: 8, w: 1.5, c: 'var(--fg-1)', dur: 6, glow: '0 0 6px rgba(255,255,255,.35)' },
    { inset: '18%', ry: 58, rx: -14, w: 2.5, c: 'var(--red-500)', dur: 3.2, glow: '0 0 10px var(--red-500), 0 0 28px rgba(240,31,51,.5)', rev: true },
    { inset: '28%', ry: 70, rx: 22, w: 1, c: 'var(--rose-200)', dur: 4.5, glow: 'none' },
    { inset: '2%', ry: 76, rx: -6, w: 1, c: 'var(--white-a32)', dur: 9, glow: 'none', rev: true },
  ];
  const gyros = [
    { inset: '10%', c: 'var(--fg-1)', w: 1, dur: 7, anim: 'groov-gyro', tilt: 'rotateZ(20deg)' },
    { inset: '22%', c: 'var(--red-400)', w: 1.5, dur: 5, anim: 'groov-gyro-x', tilt: 'rotateZ(-35deg)', glow: '0 0 8px var(--red-500)' },
  ];
  const dots = React.useMemo(() => Array.from({ length: 22 }, (_, i) => {
    const a = (i / 22) * Math.PI * 2; const r = 0.42 + ((i * 37) % 10) / 60;
    return { x: 50 + Math.cos(a) * r * 100 * 0.9, y: 50 + Math.sin(a) * r * 100 * 0.5, d: (i % 6) * 0.3, s: 1 + (i % 3) };
  }), []);
  return (
    <div style={{ position: 'relative', width: size, height: size, perspective: 900 }}>
      <div style={{ position: 'absolute', inset: '20%', borderRadius: '50%', background: 'var(--grad-core)', animation: 'groov-pulse var(--dur-pulse) var(--ease-in-out) infinite' }} />
      <div ref={stage} style={{ position: 'absolute', inset: 0, transformStyle: 'preserve-3d', transform: 'rotateZ(-24deg)', transition: 'transform 1.4s var(--ease-out)' }}>
        <div style={{ position: 'absolute', inset: 0, transformStyle: 'preserve-3d', animation: `groov-wobble ${7 * fast}s var(--ease-in-out) infinite` }}>
          <div style={{ position: 'absolute', left: '-25%', right: '-25%', top: '50%', height: 1.5, background: 'linear-gradient(90deg,transparent,var(--red-500) 30%,var(--red-300) 50%,var(--red-500) 70%,transparent)', boxShadow: '0 0 8px var(--red-500)' }} />
          {rings.map((r, i) => (
            <div key={i} style={{ position: 'absolute', inset: r.inset, transformStyle: 'preserve-3d', transform: `rotateY(${r.ry}deg) rotateX(${r.rx}deg)` }}>
              <div style={{
                position: 'absolute', inset: 0, borderRadius: '50%', borderStyle: 'solid', borderWidth: r.w,
                borderColor: `${r.c} ${r.c} transparent ${r.c}`, boxShadow: r.glow,
                animation: `${r.rev ? 'groov-spin-rev' : 'groov-spin'} ${r.dur * fast}s linear infinite`,
              }} />
            </div>
          ))}
          {gyros.map((g, i) => (
            <div key={`g${i}`} style={{ position: 'absolute', inset: g.inset, transformStyle: 'preserve-3d', transform: g.tilt }}>
              <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: `${g.w}px dashed ${g.c}`, boxShadow: g.glow || 'none', opacity: 0.7, animation: `${g.anim} ${g.dur * fast}s linear infinite` }} />
            </div>
          ))}
          <div style={{ position: 'absolute', inset: 0, animation: `groov-spin ${14 * fast}s linear infinite` }}>
            {dots.map((d, i) => (
              <span key={i} style={{ position: 'absolute', left: `${d.x}%`, top: `${d.y}%`, width: d.s, height: d.s, background: i % 4 === 0 ? 'var(--red-400)' : 'var(--fg-2)', borderRadius: '50%', animation: `groov-pulse 1.8s var(--ease-in-out) ${d.d}s infinite` }} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

window.CoreRings = CoreRings;
