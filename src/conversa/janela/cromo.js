"use strict";
// Moldura fixa da janela (portada de HudChrome.jsx do kit): fundo, topo esquerdo, topo direito, faixa de fala e orbe do canto.
window.GroovCromo = (function () {
  const h = React.createElement;
  const { StatusDot, VoiceBars, Badge, Reticle, Tag, IconButton } = window.ROSEHUDDesignSystem_bed3b4;

  const ROTULOS = { ocioso: "OCIOSO", ouvindo: "OUVINDO", pensando: "PENSANDO", falando: "FALANDO" };
  const TONS = { ocioso: "idle", ouvindo: "live", pensando: "warn", falando: "online" };
  const dois = (n) => String(n).padStart(2, "0");

  function Fundo() {
    const mascara = "radial-gradient(ellipse at center, #000 20%, transparent 75%)";
    return h(React.Fragment, null,
      h("div", { style: { position: "absolute", inset: 0, backgroundImage: "var(--bg-grid)", backgroundSize: "var(--bg-grid-size)", WebkitMaskImage: mascara, maskImage: mascara, opacity: 0.7 } }),
      h("div", { style: { position: "absolute", inset: 0, background: "var(--grad-vignette)", pointerEvents: "none" } }));
  }

  function TopoEsquerdo({ fase, desligaEm }) {
    const [agora, setAgora] = React.useState(() => new Date());
    React.useEffect(() => { const id = setInterval(() => setAgora(new Date()), 1000); return () => clearInterval(id); }, []);
    const resta = desligaEm == null ? null : Math.max(0, Math.floor(desligaEm - agora.getTime() / 1000));
    const mini = { font: "var(--type-micro)", letterSpacing: "var(--tracking-wide)", color: "var(--fg-3)", fontVariantNumeric: "tabular-nums" };
    return h("div", { style: { position: "absolute", top: 18, left: 22, display: "flex", alignItems: "center", gap: 16, zIndex: 5 } },
      h("span", { style: { font: "var(--type-micro)", letterSpacing: "var(--tracking-widest)", color: "var(--fg-rose)" } }, "GROOV // CORE 01"),
      h(StatusDot, { tone: TONS[fase] || "online", label: ROTULOS[fase] || "ONLINE", size: 5 }),
      h("span", { style: mini }, agora.toTimeString().slice(0, 8)),
      fase === "ocioso" && resta != null && h("span", { style: mini }, `DESLIGA EM ${dois(Math.floor(resta / 60))}:${dois(resta % 60)}`));
  }

  const CHIPS = [["historico", "HISTÓRICO"], ["texto", "TEXTO"], ["projetos", "PROJETOS"], ["limpar", "LIMPAR"], ["sistema", "SISTEMA"]];

  // LIMPAR não guarda estado: o chip só acende enquanto o diálogo dele está aberto (limpando).
  function TopoDireito({ chips, limpando, aoChip, aoDesligar, aoMemoria, surdo, aoSurdo }) {
    return h("div", { style: { position: "absolute", top: 14, right: 18, display: "flex", alignItems: "center", gap: 6, zIndex: 5 } },
      CHIPS.map(([id, rotulo]) => h(Tag, { key: id, selected: id === "limpar" ? !!limpando : !!chips[id], onClick: () => aoChip(id) }, rotulo)),
      h("span", { style: { width: 8 } }),
      // modo surdo: o microfone não chega ao GROOV; volta pelo botão ou "Hey JARVIS"
      h(IconButton, { icon: surdo ? "mic-off" : "mic", label: surdo ? "VOLTAR A OUVIR" : "MODO SURDO", size: "sm", active: !!surdo, onClick: aoSurdo }),
      h(IconButton, { icon: "cpu", label: "LIBERAR A MEMÓRIA", size: "sm", onClick: aoMemoria }),
      h(IconButton, { icon: "power", label: "DESLIGAR", size: "sm", onClick: aoDesligar }));
  }

  function FaixaDeFala({ quem, texto, falando }) {
    const groov = quem === "GROOV";
    return h("div", { style: { position: "absolute", left: 22, bottom: 20, right: 180, display: "flex", alignItems: "center", gap: 12, zIndex: 5, minWidth: 0 } },
      h(VoiceBars, { active: falando, count: 16, height: 14, tone: groov ? "red" : "white" }),
      h(Badge, { tone: groov ? "red" : "neutral" }, quem),
      h("span", { style: { font: "var(--type-data)", fontSize: "var(--fs-2xs)", color: "var(--fg-1)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" } },
        texto, falando && h("span", { style: { color: "var(--red-400)", animation: "groov-blink 1s steps(1) infinite" } }, "▍")));
  }

  function Orbe({ fase, aoClicar }) {
    const [sobre, setSobre] = React.useState(false);
    const estado = fase === "ouvindo" ? "listening" : fase === "pensando" ? "thinking" : "online";
    return h("button", {
      type: "button", "aria-label": "Falar com o GROOV", onClick: aoClicar,
      onPointerEnter: () => setSobre(true), onPointerLeave: () => setSobre(false),
      style: { position: "absolute", right: 14, bottom: 10, padding: 0, background: "none", border: 0, cursor: "pointer", zIndex: 6, transform: sobre ? "scale(1.05)" : "none", transition: "transform var(--dur-slow) var(--ease-out)" },
    },
      h(Reticle, { size: 130, state: estado, tone: "rose", view: sobre || fase !== "ocioso" ? "3d" : "2d", ringText: "GROOV // CORE 01" },
        h("span", { style: { font: "var(--type-display)", fontSize: "var(--fs-md)", letterSpacing: ".08em", color: "var(--fg-1)", textShadow: sobre ? "var(--text-glow-red)" : "var(--text-glow-white)", transition: "text-shadow var(--dur-slow) var(--ease-out)" } }, "GROOV")));
  }

  return { Fundo, TopoEsquerdo, TopoDireito, FaixaDeFala, Orbe };
})();
