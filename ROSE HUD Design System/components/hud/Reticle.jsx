import React, { useRef } from 'react';

const SPEED = { off: 0, idle: 1, online: 1.15, listening: 1.7, thinking: 3 };

export function Reticle({
  size = 180, state = 'idle', tone = 'red', view = '2d', tilt = 52, interactive = true,
  ticks = true, ringText, children, style,
}) {
  const k = SPEED[state] ?? 1;
  const off = state === 'off';
  const is3d = view === '3d';
  const stageRef = useRef(null);
  const main = off ? 'var(--ink-600)' : tone === 'rose' ? 'var(--rose-500)' : 'var(--red-500)';
  const hot = off ? 'transparent' : tone === 'rose' ? 'rgba(236,63,122,.85)' : 'rgba(255,51,70,.85)';
  const spin = (sec, rev) => (k ? `${rev ? 'groov-spin-rev' : 'groov-spin'} ${sec / k}s linear infinite` : 'none');
  const base3d = `rotateX(${tilt}deg) rotateY(-14deg)`;
  const tr = 'transform 1.2s var(--ease-out)';
  const fill = { position: 'absolute', inset: 0, transformStyle: 'preserve-3d' };
  const svgS = { position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible' };
  const layer = (z, extra = '') => ({ ...fill, transform: is3d ? `translateZ(${z * size / 180}px) ${extra}` : 'none', transition: tr });

  const tickEls = [];
  if (ticks) for (let i = 0; i < 72; i++) {
    const a = (i * 5 * Math.PI) / 180; const long = i % 6 === 0;
    const r1 = long ? 89 : 93, r2 = 98;
    tickEls.push(<line key={i} x1={100 + r1 * Math.sin(a)} y1={100 - r1 * Math.cos(a)} x2={100 + r2 * Math.sin(a)} y2={100 - r2 * Math.cos(a)}
      stroke={long ? 'var(--rose-200)' : 'var(--fg-3)'} strokeOpacity={long ? 0.55 : 0.4} strokeWidth={long ? 0.8 : 0.5} />);
  }

  const onMove = (e) => {
    if (!is3d || !interactive || !stageRef.current) return;
    const r = e.currentTarget.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5; const py = (e.clientY - r.top) / r.height - 0.5;
    stageRef.current.style.transform = `rotateX(${tilt - py * 28}deg) rotateY(${-14 + px * 40}deg)`;
  };
  const onLeave = () => { if (stageRef.current) stageRef.current.style.transform = is3d ? base3d : 'none'; };

  return (
    <div onPointerMove={onMove} onPointerLeave={onLeave}
      style={{ position: 'relative', width: size, height: size, flex: 'none', perspective: size * 3.2, ...style }}>
      <div aria-hidden="true" style={{
        position: 'absolute', inset: '12%', borderRadius: '50%',
        background: off ? 'none' : `radial-gradient(circle, ${tone === 'rose' ? 'rgba(236,63,122,.24)' : 'rgba(240,31,51,.24)'}, transparent 68%)`,
        animation: off ? 'none' : 'groov-pulse var(--dur-pulse) var(--ease-in-out) infinite',
      }} />
      {state === 'listening' && [0, 0.7, 1.4].map((d) => (
        <span key={d} aria-hidden="true" style={{ position: 'absolute', inset: '24%', borderRadius: '50%', border: `1px solid ${main}`, animation: `groov-ping 2.1s var(--ease-out) ${d}s infinite` }} />
      ))}
      <div ref={stageRef} style={{ ...fill, transform: is3d ? base3d : 'none', transition: tr }}>
        <div style={{ ...fill, animation: is3d && k ? `groov-wobble ${9 / k}s var(--ease-in-out) infinite` : 'none' }}>
          <div style={layer(-18)}><svg viewBox="0 0 200 200" style={{ ...svgS, animation: spin(40) }}>{tickEls}</svg></div>
          <div style={layer(0, 'rotateY(16deg)')}>
            <svg viewBox="0 0 200 200" style={{ ...svgS, animation: spin(10, true) }}>
              <circle cx="100" cy="100" r="84" fill="none" stroke="var(--fg-1)" strokeOpacity=".1" strokeWidth=".6" />
              <circle cx="100" cy="100" r="84" fill="none" stroke="var(--fg-1)" strokeOpacity=".45" strokeWidth=".8" strokeDasharray="40 92" />
              {!off && <circle cx="100" cy="16" r="2.2" fill="var(--rose-200)" style={{ filter: 'drop-shadow(0 0 3px var(--rose-500))' }} />}
            </svg>
          </div>
          {is3d && !off && (
            <>
              <div style={{ ...fill, animation: `groov-gyro ${8 / k}s linear infinite` }}>
                <svg viewBox="0 0 200 200" style={svgS}><circle cx="100" cy="100" r="80" fill="none" stroke="var(--fg-1)" strokeOpacity=".55" strokeWidth=".9" strokeDasharray="150 40" style={{ filter: 'drop-shadow(0 0 2px rgba(255,255,255,.5))' }} /></svg>
              </div>
              <div style={{ ...fill, transform: 'rotateZ(60deg)' }}>
                <div style={{ ...fill, animation: `groov-gyro-x ${11 / k}s linear infinite reverse` }}>
                  <svg viewBox="0 0 200 200" style={svgS}><circle cx="100" cy="100" r="70" fill="none" stroke={tone === 'rose' ? 'var(--rose-200)' : 'var(--rose-300)'} strokeOpacity=".5" strokeWidth=".7" strokeDasharray="3 5" /></svg>
                </div>
              </div>
            </>
          )}
          <div style={layer(12)}>
            <svg viewBox="0 0 200 200" style={{ ...svgS, animation: spin(4.5), filter: off ? 'none' : `drop-shadow(0 0 3px ${hot}) drop-shadow(0 0 8px ${hot})` }}>
              <circle cx="100" cy="100" r="74" fill="none" stroke={main} strokeWidth="2.2" strokeLinecap="round" strokeDasharray="130 102.5"
                style={{ animation: k ? `groov-arc ${3.2 / k}s var(--ease-in-out) infinite` : 'none' }} />
              <polygon points="100,20 97,15 103,15" fill={main} />
            </svg>
          </div>
          <div style={layer(24, 'rotateX(-18deg)')}>
            <svg viewBox="0 0 200 200" style={{ ...svgS, animation: spin(6, true) }}>
              <circle cx="100" cy="100" r="64" fill="none" stroke={tone === 'rose' ? 'var(--rose-200)' : 'var(--fg-1)'} strokeOpacity=".24" strokeWidth=".6" strokeDasharray="2 4" />
              <circle cx="100" cy="100" r="58" fill="none" stroke="var(--fg-1)" strokeOpacity=".08" strokeWidth=".6" />
            </svg>
          </div>
          {ringText && (
            <div style={layer(-8)}>
              <svg viewBox="0 0 200 200" style={{ ...svgS, animation: spin(24) }}>
                <defs><path id={`rt-${size}-${view}`} d="M100,100 m-80,0 a80,80 0 1,1 160,0 a80,80 0 1,1 -160,0" /></defs>
                <text fill="var(--rose-200)" fillOpacity=".7" style={{ font: '500 5px var(--font-mono)', letterSpacing: '1.4px' }}>
                  <textPath href={`#rt-${size}-${view}`} startOffset="62%">{ringText}</textPath>
                </text>
              </svg>
            </div>
          )}
        </div>
      </div>
      {children != null && (
        <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', textAlign: 'center', pointerEvents: 'none' }}>{children}</div>
      )}
    </div>
  );
}
