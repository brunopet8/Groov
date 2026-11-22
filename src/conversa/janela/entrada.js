"use strict";
// Campo de texto e cartão de pergunta: o que o usuário faz sem falar.
window.GroovEntrada = (function () {
  const h = React.createElement;
  const { Input, IconButton, Panel, Button, Badge, Progress } = window.ROSEHUDDesignSystem_bed3b4;

  // aoEnviar(texto) devolve true se o comando saiu; só então o campo esvazia.
  function Compositor({ aoEnviar }) {
    const [valor, setValor] = React.useState("");
    const caixa = React.useRef(null);
    function enviar() {
      const t = valor.trim();
      if (!t) return;
      if (!aoEnviar(t)) return;
      setValor("");
      const campo = caixa.current && caixa.current.querySelector("input");
      if (campo) campo.focus();
    }
    return h("div", { ref: caixa, style: { position: "absolute", left: "50%", bottom: 54, width: 440, transform: "translateX(-50%)", display: "flex", alignItems: "center", gap: 6, zIndex: 6 } },
      h(Input, {
        icon: "type", placeholder: "ESCREVA PARA O GROOV...", value: valor, maxLength: 2000, autoFocus: true, style: { flex: 1 },
        // Teclas só digitam: Enter envia e nada sobe para a janela.
        onChange: (e) => setValor(e.target.value.slice(0, 2000)),
        onKeyDown: (e) => {
          e.stopPropagation();
          if (e.key !== "Enter") return;
          // Enter que confirma composição (IME, keyCode 229) ou com modificador não envia e fica intacto.
          if (e.nativeEvent.isComposing || e.keyCode === 229 || e.shiftKey || e.ctrlKey || e.altKey || e.metaKey) return;
          e.preventDefault();
          enviar();
        },
      }),
      h(IconButton, { icon: "send", label: "ENVIAR", variant: "solid", onClick: enviar }));
  }

  // ate é segundos de relógio; a barra esvazia do aparecimento até ate e então chama aoVencer uma vez.
  function Pergunta({ pergunta, aoResponder, aoVencer }) {
    const { texto, so_voz: soVoz, ate } = pergunta;
    const opcoes = Array.isArray(pergunta.opcoes) ? pergunta.opcoes : [];
    const [inicio] = React.useState(() => Date.now() / 1000);
    const [agora, setAgora] = React.useState(() => Date.now() / 1000);
    const vencida = agora >= ate;
    React.useEffect(() => {
      if (vencida) { aoVencer(); return; }
      const id = setInterval(() => setAgora(Date.now() / 1000), 250);
      return () => clearInterval(id);
    }, [vencida]);
    if (vencida) return null;
    const valor = Math.max(0, Math.min(100, ((ate - agora) / Math.max(ate - inicio, 0.001)) * 100));
    // Dentro da pilha do canto (.groov-pilha) o groov.css sobrepõe esta posição (static !important).
    return h("div", { style: { position: "absolute", left: 22, bottom: 54, width: 360, zIndex: 6 } },
      h(Panel, { eyebrow: "PERGUNTA", interactive: false, padding: 12, footer: h(Progress, { value: valor, size: "sm", showValue: false, width: "100%" }) },
        h("div", { style: { font: "var(--type-body)", color: "var(--fg-1)", marginBottom: 12 } }, texto),
        soVoz
          ? h(Badge, { tone: "rose", dot: true }, "CONFIRME POR VOZ")
          : h("div", { style: { display: "flex", flexWrap: "wrap", gap: 8 } },
            opcoes.map((o, i) => h(Button, { key: i, size: "sm", variant: i === 0 ? "primary" : "ghost", onClick: () => aoResponder(o) }, o)))));
  }

  return { Compositor, Pergunta };
})();
