"use strict";
// Painel PROJETOS: workspaces e chats do Claude Code (contagem de 7 dias), um chat aberto com envio e microfone.
// O conteúdo é sempre texto, nunca HTML.
window.GroovProjetos = (function () {
  const h = React.createElement;
  const { Panel, Input, IconButton, Button, Badge } = window.ROSEHUDDesignSystem_bed3b4;

  const dois = (n) => String(n).padStart(2, "0");
  const data = (s) => { const d = new Date(s * 1000); return `${dois(d.getDate())}/${dois(d.getMonth() + 1)} ${dois(d.getHours())}:${dois(d.getMinutes())}`; };
  const linha = { display: "flex", alignItems: "center", gap: 10, padding: "7px 4px", borderTop: "1px solid var(--border-subtle)", cursor: "pointer" };
  const nome = { flex: 1, minWidth: 0, font: "var(--type-body-sm)", color: "var(--fg-1)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" };
  const dado = { font: "var(--type-data)", fontSize: "var(--fs-2xs)", color: "var(--fg-3)", flex: "none" };
  const ROTULO = { voce: "VOCÊ", claude: "CLAUDE", ferramenta: "FERRAMENTA", erro: "ERRO" };
  const COR = { voce: "var(--rose-400, var(--accent))", claude: "var(--fg-1)", ferramenta: "var(--fg-3)", erro: "var(--red-400)" };

  function Lista({ projetos, enviar }) {
    const [aberto, setAberto] = React.useState(null);
    if (!projetos) return h("p", { style: { ...dado, margin: 0 } }, "CARREGANDO...");
    if (!projetos.length) return h("p", { style: { ...dado, margin: 0 } }, "NENHUM CHAT NOS ÚLTIMOS 30 DIAS.");
    return h("div", { style: { overflowY: "auto", minHeight: 0 } }, projetos.map((w, i) => h(React.Fragment, { key: i },
      h("div", { style: { ...linha, borderTop: i ? linha.borderTop : "none" }, onClick: () => setAberto(aberto === i ? null : i) },
        h("span", { style: nome }, w.nome),
        h(Badge, { tone: w.prompts_7d ? "rose" : "neutral" }, `${w.prompts_7d} EM 7 DIAS`),
        h("span", { style: dado }, data(w.atualizado))),
      aberto === i && w.chats.map((c) => h("div", { key: c.id, style: { ...linha, paddingLeft: 18 }, onClick: () => enviar("chat", { id: c.id }) },
        h("span", { style: { ...nome, color: "var(--fg-2)" } }, c.titulo),
        h("span", { style: dado }, `${c.prompts_7d} · ${data(c.atualizado)}`))))));
  }

  function Chat({ chat, ditando, enviar, despachar }) {
    const fim = React.useRef(null);
    React.useEffect(() => { if (fim.current) fim.current.scrollIntoView({ block: "end" }); }, [chat.mensagens.length]);
    function mandar() {
      const t = chat.rascunho.trim();
      if (!t || chat.enviando) return;
      if (enviar("chat_enviar", { id: chat.id, texto: t })) despachar({ tipo: "chat_enviou", texto: t });
    }
    return h(React.Fragment, null,
      h("div", { style: { display: "flex", alignItems: "center", gap: 8 } },
        h(Button, { size: "sm", variant: "ghost", onClick: () => despachar({ tipo: "chat_voltar" }) }, "VOLTAR"),
        h("span", { style: nome }, chat.workspace || "CHAT"),
        h(Button, { size: "sm", variant: "ghost", icon: "monitor", onClick: () => { if (enviar("chat_claude", { id: chat.id })) despachar({ tipo: "claude_abrir", id: chat.id }); } }, "ABRIR NO CLAUDE CODE")),
      h("div", { style: { flex: 1, minHeight: 0, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, paddingRight: 4 } },
        chat.mensagens.map((m, i) => h("div", { key: i, style: { display: "flex", flexDirection: "column", gap: 2 } },
          h("span", { style: { ...dado, color: COR[m.quem] || "var(--fg-3)" } }, ROTULO[m.quem] || m.quem),
          h("span", { style: { font: m.quem === "ferramenta" ? "var(--type-data)" : "var(--type-body-sm)", color: m.quem === "ferramenta" ? "var(--fg-3)" : "var(--fg-2)", whiteSpace: "pre-wrap", overflowWrap: "anywhere" } }, m.texto))),
        chat.enviando && h("span", { style: dado }, "ESPERANDO A RESPOSTA..."),
        h("div", { ref: fim })),
      h("div", { style: { display: "flex", alignItems: "center", gap: 6 } },
        h(Input, {
          icon: "type", placeholder: ditando ? "FALE AGORA..." : "PROMPT PARA ESTE CHAT...", value: chat.rascunho, maxLength: 2000, style: { flex: 1 },
          onChange: (e) => despachar({ tipo: "chat_rascunho", texto: e.target.value.slice(0, 2000) }),
          onKeyDown: (e) => {
            e.stopPropagation();
            if (e.key !== "Enter" || e.nativeEvent.isComposing || e.keyCode === 229 || e.shiftKey || e.ctrlKey || e.altKey || e.metaKey) return;
            e.preventDefault();
            mandar();
          },
        }),
        h(IconButton, { icon: "mic", label: ditando ? "OUVINDO" : "DITAR", variant: ditando ? "solid" : "ghost", onClick: () => { if (!ditando && enviar("ditar", {})) despachar({ tipo: "ditar" }); } }),
        h(IconButton, { icon: "send", label: "ENVIAR", variant: "solid", onClick: mandar })));
  }

  function Painel({ estado, enviar, despachar }) {
    const { chat } = estado;
    return h(Panel, { eyebrow: "PROJETOS", meta: chat ? "CHAT" : "ÚLTIMOS 7 DIAS", interactive: false, padding: 12,
      style: { height: "100%" }, bodyStyle: { display: "flex", flexDirection: "column", gap: 10, minHeight: 0, height: "100%" } },
      chat ? h(Chat, { chat, ditando: estado.ditando, enviar, despachar }) : h(Lista, { projetos: estado.projetos, enviar }));
  }

  return { Painel };
})();
