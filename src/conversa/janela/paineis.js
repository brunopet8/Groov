"use strict";
// Painéis de resultado (grade solta no centro) e o painel SISTEMA do canto. O conteúdo é sempre texto, nunca HTML.
window.GroovPaineis = (function () {
  const h = React.createElement;
  const { Panel, Stat, Progress, StatusDot } = window.ROSEHUDDesignSystem_bed3b4;

  const dois = (n) => String(n).padStart(2, "0");
  const ROTULOS = { texto: "RESPOSTA", lista: "LISTA", numero: "MEDIDA", passos: "TAREFA" };
  const corpoTxt = { margin: 0, font: "var(--type-body-sm)", color: "var(--fg-2)", textWrap: "pretty", overflowWrap: "anywhere" };

  // Segundos inteiros até fim (epoch s), parando em 0; relógio de parede, então sobrevive a aba em segundo plano.
  const restante = (fim) => Math.max(0, Math.ceil(fim - Date.now() / 1000));
  const mmss = (s) => `${dois(Math.floor(s / 60))}:${dois(s % 60)}`;

  function Contagem({ fim, ...resto }) {
    const [resta, setResta] = React.useState(() => restante(fim));
    React.useEffect(() => {
      setResta(restante(fim));
      const id = setInterval(() => { const r = restante(fim); setResta(r); if (r === 0) clearInterval(id); }, 1000);
      return () => clearInterval(id);
    }, [fim]);
    return h(Stat, { value: mmss(resta), size: "lg", animate: false, tone: resta === 0 ? "red" : "white", ...resto });
  }

  function Passos({ itens, aberto }) {
    return h("ol", { style: { margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column" } },
      itens.map((t, i) => {
        const atual = aberto && i === itens.length - 1;
        return h("li", { key: i, style: { display: "flex", gap: 8, padding: "5px 0", borderTop: i ? "1px solid var(--border-subtle)" : "none", font: "var(--type-data)", fontSize: "var(--fs-2xs)", color: atual ? "var(--red-400)" : "var(--fg-2)" } },
          h("span", { style: { color: atual ? "var(--red-400)" : "var(--fg-3)", flex: "none" } }, dois(i + 1)),
          h("span", { style: { minWidth: 0, overflowWrap: "anywhere" } }, t));
      }));
  }

  function Lista({ itens }) {
    return h("ul", { style: { margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column" } },
      itens.map((t, i) => h("li", { key: i, style: { ...corpoTxt, color: "var(--fg-1)", padding: "5px 0", borderTop: i ? "1px solid var(--border-subtle)" : "none" } }, t)));
  }

  function Cartao({ p, i, ativo, aoAtivar, aoFechar }) {
    const itens = Array.isArray(p.itens) ? p.itens : [];
    const passos = p.tipo === "passos";
    const contagem = p.tipo === "numero" && Number.isFinite(p.fim);
    const rodape = passos && (p.meta || p.corpo) ? h("span", { style: { ...corpoTxt, font: "var(--type-micro)", color: "var(--fg-2)" } }, [p.meta, p.corpo].filter(Boolean).join(" · ")) : undefined;
    const corpo = p.corpo && !passos && p.tipo !== "numero" ? h("p", { style: corpoTxt }, p.corpo) : null;
    return h("div", {
      // O × está dentro do painel e o clique sobe: botões não ativam.
      onClick: (e) => { if (!e.target.closest("button")) aoAtivar(p.id); },
      style: { minWidth: 0, animation: `groov-fade-up var(--dur-slow) var(--ease-out) ${i * 50}ms both` },
    },
      h(Panel, {
        eyebrow: contagem ? "CONTAGEM" : ROTULOS[p.tipo], meta: passos ? undefined : p.meta, title: p.titulo,
        active: ativo, enter: false, onClose: () => aoFechar(p.id), footer: rodape, style: { cursor: "default" },
      },
        corpo,
        p.tipo === "lista" && h(Lista, { itens }),
        passos && h(Passos, { itens, aberto: !(p.meta || p.corpo) }),
        p.tipo === "numero" && (contagem
          ? h(Contagem, { fim: p.fim, caption: p.corpo })
          : h(Stat, { value: p.valor || "—", suffix: p.unidade, size: "lg", animate: false, caption: p.corpo }))));
  }

  // Grade solta: colunas de 260 a 320 px, vão de 16, rola dentro de si quando 6 painéis não cabem.
  function Grade({ paineis, ativo, aoAtivar, aoFechar }) {
    return h("div", { style: { position: "absolute", inset: 0, overflowY: "auto", display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 320px))", gridAutoRows: "min-content", gap: 16, justifyContent: "safe center", alignContent: "safe center", padding: "4px 8px" } },
      paineis.map((p, i) => h(Cartao, { key: p.id, p, i, ativo: ativo === p.id, aoAtivar, aoFechar })));
  }

  const num = (v) => typeof v === "number" && Number.isFinite(v);
  const virgula = (n) => n.toFixed(1).replace(".", ",");
  const gb = (mib) => virgula(mib / 1024);

  function Sistema({ telemetria }) {
    const t = telemetria || {};
    const memoria = num(t.vram_usada) && num(t.vram_total) && t.vram_total > 0;
    const pct = memoria ? Math.max(0, Math.min(100, (t.vram_usada / t.vram_total) * 100)) : 0;
    const linha = { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 };
    const rotulo = { font: "var(--type-micro)", letterSpacing: "var(--tracking-wider)", color: "var(--fg-3)" };
    const dado = { font: "var(--type-data)", fontSize: "var(--fs-2xs)", color: "var(--fg-1)", fontVariantNumeric: "tabular-nums" };
    return h("div", { style: { width: 230 } },
      h(Panel, { eyebrow: "SISTEMA", meta: "CORE 01", interactive: false, padding: 10, bodyStyle: { gap: 10 } },
        h("div", { style: { display: "flex", flexDirection: "column", gap: 4 } },
          h("div", { style: linha }, h("span", { style: rotulo }, "VRAM"), h("span", { style: dado }, memoria ? `${gb(t.vram_usada)} / ${gb(t.vram_total)} GB` : "—")),
          h(Progress, { value: pct, size: "sm", showValue: false, width: "100%" })),
        h("div", { style: linha }, h("span", { style: rotulo }, "LATÊNCIA"), h("span", { style: dado }, num(t.latencia_ms) ? `${virgula(t.latencia_ms / 1000)} s` : "—")),
        h(StatusDot, { tone: t.voz ? "online" : "idle", label: "VOZ", size: 5 }),
        h(StatusDot, { tone: t.whisper ? "online" : "idle", label: "WHISPER", size: 5 })));
  }

  // Painel grande CLAUDE CODE: o corpo fica vazio e o servidor encaixa a janela do app desktop por cima dele (claude_app.py).
  // Manda a área ao montar e a cada mudança de tamanho; ao sumir (fechou, dormiu, trocou de tela) manda "solto".
  function JanelaApp({ aoFechar, aoArea, aoSolto }) {
    const corpo = React.useRef(null);
    const avisos = React.useRef({ aoArea, aoSolto });
    avisos.current = { aoArea, aoSolto };
    React.useEffect(() => {
      let ultima = "";
      const medir = () => {
        const a = corpo.current && window.GroovEstado.areaDe(corpo.current.getBoundingClientRect(), window.innerWidth, window.innerHeight);
        const chave = JSON.stringify(a);
        if (!a || chave === ultima) return;
        ultima = chave;
        avisos.current.aoArea(a);
      };
      medir();
      const observador = new ResizeObserver(medir);
      observador.observe(corpo.current);
      window.addEventListener("resize", medir);
      return () => { observador.disconnect(); window.removeEventListener("resize", medir); avisos.current.aoSolto(); };
    }, []);
    return h(Panel, { eyebrow: "APP", title: "CLAUDE CODE", meta: "DESKTOP", interactive: false, enter: false, padding: 12, onClose: aoFechar,
      style: { height: "100%" }, bodyStyle: { display: "flex", flexDirection: "column", minHeight: 0, height: "100%" } },
      h("div", { ref: corpo, style: { flex: 1, minHeight: 0, display: "grid", placeItems: "center", border: "1px dashed var(--border-subtle)" } },
        h("p", { style: { ...corpoTxt, font: "var(--type-micro)", color: "var(--fg-3)" } }, "ABRINDO O CLAUDE... SE ELE NÃO APARECER (OU FOI FECHADO), FECHE ESTE PAINEL E ABRA DE NOVO.")));
  }

  return { Grade, Sistema, JanelaApp };
})();
