"use strict";
// Telas do centro (portadas de BootScreen.jsx, CoreRings.jsx e App.jsx do kit), guiadas pelo estado real.
window.GroovTelas = (function () {
  const h = React.createElement;
  const { Reticle, Progress, StatusDot, CornerBrackets } = window.ROSEHUDDesignSystem_bed3b4;
  const { PROGRESSO } = window.GroovEstado;

  const NOMES = { ouvindo: "OUVINDO", pensando: "PENSANDO", falando: "FALANDO" };
  const TONS = { ouvindo: "live", pensando: "warn", falando: "online" };

  // Sem marco só a mira; "inicio" acende anéis, GROOV e barra; "pronto" mostra ONLINE com o núcleo em 3D.
  function Boot({ marco }) {
    const mira = !marco, online = marco === "pronto";
    const [percentual, rotulo] = PROGRESSO[marco] || [0, ""];
    const marca = { position: "absolute", top: "calc(50% - 14px)", width: 1, height: 28, background: "var(--red-500)", boxShadow: "var(--glow-red-sm)", animation: "groov-flicker .8s linear both" };
    return h("div", { style: { position: "absolute", inset: 0, display: "grid", placeItems: "center", background: "var(--bg-void)", animation: "groov-fade-in .4s var(--ease-out)" } },
      h("div", { style: { position: "absolute", inset: 28 } }, h(CornerBrackets, { size: 28, color: "var(--fg-3)" })),
      h("div", { style: { position: "absolute", left: "4%", right: "4%", top: "50%", height: 1, background: "linear-gradient(90deg,transparent,var(--white-a12) 20%,var(--white-a12) 80%,transparent)" } }),
      h("div", { style: { position: "absolute", top: "6%", bottom: "6%", left: "50%", width: 1, background: "linear-gradient(180deg,transparent,var(--white-a04),transparent)" } }),
      h("span", { style: { ...marca, left: "4%" } }), h("span", { style: { ...marca, right: "4%" } }),
      h("div", { style: { position: "relative", display: "flex", flexDirection: "column", alignItems: "center", gap: 22 } },
        h("div", { style: { transform: mira ? "scale(.82)" : "none", opacity: mira ? 0.6 : 1, transition: "all .9s var(--ease-out)" } },
          h(Reticle, { size: 260, state: mira ? "off" : online ? "listening" : "idle", ticks: !mira, view: online ? "3d" : "2d", ringText: online ? "GROOV // CORE 01 // ONLINE" : undefined },
            mira
              ? h("span", { style: { font: "200 22px var(--font-sans)", color: "var(--fg-3)" } }, "+")
              : h("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", gap: 6, animation: "groov-flicker 1.1s linear both" } },
                h("span", { style: { font: "var(--type-display)", letterSpacing: ".08em", color: "var(--fg-1)", textShadow: "var(--text-glow-white)" } }, "GROOV"),
                h("span", { style: { font: "var(--type-micro)", letterSpacing: "2px", color: "var(--fg-3)" } }, "///")))),
        h("div", { style: { height: 52, width: 340, display: "grid", placeItems: "center" } },
          marco && !online && h("div", { style: { width: "100%", animation: "groov-fade-up .4s var(--ease-out)" } }, h(Progress, { label: rotulo, value: percentual })),
          online && h("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", gap: 14, animation: "groov-fade-up .6s var(--ease-out)" } },
            h(StatusDot, { tone: "online", label: "ONLINE", bracketed: true, pulse: false, size: 0 }),
            h("div", { style: { display: "flex", gap: 8 } }, [0, 1, 2].map((d) =>
              h("span", { key: d, style: { width: 4, height: 4, borderRadius: "50%", background: d === 0 ? "var(--red-500)" : "var(--ink-500)", boxShadow: d === 0 ? "var(--glow-red-sm)" : "none" } })))))),
      h("div", { style: { position: "absolute", left: 44, bottom: 44, font: "var(--type-micro)", letterSpacing: "var(--tracking-wider)", color: "var(--fg-3)" } }, "GROOV // CORE 01"));
  }

  function Ocioso() {
    return h(React.Fragment, null,
      h("div", { style: { position: "absolute", left: "50%", top: "50%", width: 520, height: 520, transform: "translate(-50%,-50%)", background: "var(--grad-core)", opacity: 0.5, animation: "groov-pulse 4s var(--ease-in-out) infinite" } }),
      // centraliza por flex: o transform da animação groov-fade-up apagaria um translate(-50%,-50%)
      h("div", { style: { position: "absolute", inset: 0, display: "grid", placeItems: "center", pointerEvents: "none" } },
        h("div", { style: { font: "var(--type-micro)", letterSpacing: "var(--tracking-widest)", color: "var(--fg-3)", whiteSpace: "nowrap", animation: "groov-fade-up .8s var(--ease-out)" } },
          "DIGA \"HEY JARVIS\" OU TOQUE NO NÚCLEO", h("span", { style: { color: "var(--red-400)", animation: "groov-blink 1s steps(1) infinite" } }, " _"))));
  }

  function Aneis({ size = 340, rapido }) {
    const palco = React.useRef(null);
    React.useEffect(() => {
      const mover = (e) => {
        if (!palco.current) return;
        const px = e.clientX / window.innerWidth - 0.5, py = e.clientY / window.innerHeight - 0.5;
        palco.current.style.transform = `rotateX(${-py * 30}deg) rotateY(${px * 40}deg) rotateZ(-24deg)`;
      };
      window.addEventListener("pointermove", mover);
      return () => window.removeEventListener("pointermove", mover);
    }, []);
    const v = rapido ? 0.4 : 1;
    const aneis = [
      { inset: "6%", ry: 64, rx: 8, w: 1.5, c: "var(--fg-1)", dur: 6, glow: "0 0 6px rgba(255,255,255,.35)" },
      { inset: "18%", ry: 58, rx: -14, w: 2.5, c: "var(--red-500)", dur: 3.2, glow: "0 0 10px var(--red-500), 0 0 28px rgba(240,31,51,.5)", rev: true },
      { inset: "28%", ry: 70, rx: 22, w: 1, c: "var(--rose-200)", dur: 4.5, glow: "none" },
      { inset: "2%", ry: 76, rx: -6, w: 1, c: "var(--white-a32)", dur: 9, glow: "none", rev: true },
    ];
    const giros = [
      { inset: "10%", c: "var(--fg-1)", w: 1, dur: 7, anim: "groov-gyro", tilt: "rotateZ(20deg)" },
      { inset: "22%", c: "var(--red-400)", w: 1.5, dur: 5, anim: "groov-gyro-x", tilt: "rotateZ(-35deg)", glow: "0 0 8px var(--red-500)" },
    ];
    const pontos = React.useMemo(() => Array.from({ length: 22 }, (_, i) => {
      const a = (i / 22) * Math.PI * 2, r = 0.42 + ((i * 37) % 10) / 60;
      return { x: 50 + Math.cos(a) * r * 100 * 0.9, y: 50 + Math.sin(a) * r * 100 * 0.5, d: (i % 6) * 0.3, s: 1 + (i % 3) };
    }), []);
    const camada = { position: "absolute", transformStyle: "preserve-3d" };
    return h("div", { style: { position: "relative", width: size, height: size, perspective: 900 } },
      h("div", { style: { position: "absolute", inset: "20%", borderRadius: "50%", background: "var(--grad-core)", animation: "groov-pulse var(--dur-pulse) var(--ease-in-out) infinite" } }),
      h("div", { ref: palco, style: { ...camada, inset: 0, transform: "rotateZ(-24deg)", transition: "transform 1.4s var(--ease-out)" } },
        h("div", { style: { ...camada, inset: 0, animation: `groov-wobble ${7 * v}s var(--ease-in-out) infinite` } },
          h("div", { style: { position: "absolute", left: "-25%", right: "-25%", top: "50%", height: 1.5, background: "linear-gradient(90deg,transparent,var(--red-500) 30%,var(--red-300) 50%,var(--red-500) 70%,transparent)", boxShadow: "0 0 8px var(--red-500)" } }),
          aneis.map((r, i) => h("div", { key: i, style: { ...camada, inset: r.inset, transform: `rotateY(${r.ry}deg) rotateX(${r.rx}deg)` } },
            h("div", { style: { position: "absolute", inset: 0, borderRadius: "50%", borderStyle: "solid", borderWidth: r.w, borderColor: `${r.c} ${r.c} transparent ${r.c}`, boxShadow: r.glow, animation: `${r.rev ? "groov-spin-rev" : "groov-spin"} ${r.dur * v}s linear infinite` } }))),
          giros.map((g, i) => h("div", { key: `g${i}`, style: { ...camada, inset: g.inset, transform: g.tilt } },
            h("div", { style: { position: "absolute", inset: 0, borderRadius: "50%", border: `${g.w}px dashed ${g.c}`, boxShadow: g.glow || "none", opacity: 0.7, animation: `${g.anim} ${g.dur * v}s linear infinite` } }))),
          h("div", { style: { position: "absolute", inset: 0, animation: `groov-spin ${14 * v}s linear infinite` } },
            pontos.map((d, i) => h("span", { key: i, style: { position: "absolute", left: `${d.x}%`, top: `${d.y}%`, width: d.s, height: d.s, background: i % 4 === 0 ? "var(--red-400)" : "var(--fg-2)", borderRadius: "50%", animation: `groov-pulse 1.8s var(--ease-in-out) ${d.d}s infinite` } }))))));
  }

  function Nucleo({ fase, texto }) {
    return h("div", { style: { position: "absolute", inset: 0, display: "grid", placeItems: "center", animation: "groov-fade-in .5s var(--ease-out)" } },
      h("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", gap: 28 } },
        h(Aneis, { size: 340, rapido: fase === "pensando" }),
        h(StatusDot, { tone: TONS[fase] || "online", label: NOMES[fase] }),
        h("div", { style: { maxWidth: 520, minHeight: 18, textAlign: "center", font: "var(--type-data)", fontSize: "var(--fs-xs)", color: "var(--fg-1)" } }, texto)));
  }

  // Coluna de 250 px com os turnos (portada de TranscriptColumn.jsx); rola até o fim a cada turno novo.
  function Historico({ turnos }) {
    const ref = React.useRef(null);
    React.useEffect(() => { if (ref.current) ref.current.scrollTop = ref.current.scrollHeight; }, [turnos.length]);
    const micro = { font: "var(--type-micro)", letterSpacing: "var(--tracking-wider)" };
    return h("aside", { "aria-label": "HISTÓRICO", style: { position: "relative", display: "flex", flexDirection: "column", minHeight: 0, borderLeft: "1px solid var(--border-subtle)", background: "rgba(5,5,6,.6)", animation: "groov-fade-in var(--dur-slow) var(--ease-out)" } },
      h("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", height: "var(--panel-header-h)", padding: "0 12px", borderBottom: "1px solid var(--border-subtle)" } },
        h("span", { style: { ...micro, color: "var(--fg-3)" } }, "HISTÓRICO"),
        h("span", { style: { font: "var(--type-micro)", color: "var(--fg-3)" } }, turnos.length)),
      h("div", { ref, style: { flex: 1, minHeight: 0, overflowY: "auto", padding: 12, display: "flex", flexDirection: "column", gap: 14 } },
        turnos.map((t, i) => h("div", { key: i, style: { display: "flex", flexDirection: "column", gap: 4, animation: "groov-fade-up var(--dur-slow) var(--ease-out)" } },
          h("div", { style: { display: "flex", alignItems: "center", gap: 8 } },
            h("span", { style: { ...micro, color: t.quem === "GROOV" ? "var(--red-400)" : "var(--fg-2)" } }, t.quem),
            h("span", { style: { font: "var(--type-micro)", color: "var(--fg-3)" } }, t.hora)),
          h("div", { style: { font: "var(--type-data)", fontSize: "var(--fs-2xs)", lineHeight: 1.55, color: t.quem === "GROOV" ? "var(--fg-1)" : "var(--fg-2)", textWrap: "pretty" } }, t.texto)))));
  }

  return { Boot, Ocioso, Nucleo, Historico };
})();
