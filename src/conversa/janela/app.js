"use strict";
// Junta estado, conexão e telas. Com ?demo na URL não conecta: as ações vêm de window.groovDemo/groovAcao.
(function () {
  const h = React.createElement;
  const { Boot, Ocioso, Nucleo, Historico } = window.GroovTelas;
  const { Dialog, Button, Toast } = window.ROSEHUDDesignSystem_bed3b4;
  const { Fundo, TopoEsquerdo, TopoDireito, FaixaDeFala, Orbe } = window.GroovCromo;
  const { Compositor, Pergunta } = window.GroovEntrada;
  const { Grade, Sistema, JanelaApp } = window.GroovPaineis;
  const Projetos = window.GroovProjetos.Painel;
  const { fase, inicial, reduzir } = window.GroovEstado;
  const params = new URLSearchParams(location.search);
  const demo = params.has("demo");

  const hora = () => new Date().toTimeString().slice(0, 5);

  function App() {
    const [estado, despachar] = React.useReducer(reduzir, undefined, inicial);
    const enviarRef = React.useRef(() => false);
    const estadoRef = React.useRef(estado);
    estadoRef.current = estado;
    // Depois de reconectar o servidor recomeça com a telemetria desligada: a 1ª mensagem com estado reenvia o chip aceso.
    const reenviarRef = React.useRef(false);

    function aoMensagem(msg) {
      if (reenviarRef.current && msg.type === "server-message" && msg.data && msg.data.estado) {
        reenviarRef.current = false;
        if (estadoRef.current.chips.sistema) enviar("telemetria", { ligada: true });
      }
      despachar({ tipo: "rtvi", msg, hora: hora() });
    }

    React.useEffect(() => {
      if (demo) {
        window.groovEnviadas = [];
        enviarRef.current = (t, d) => { window.groovEnviadas.push({ t, d }); return !params.has("falha"); };
        window.groovAcao = (a) => { if (a.tipo === "conexao_caiu") reenviarRef.current = true; despachar(a); };
        window.groovDemo = aoMensagem;
        const s = document.createElement("script");
        s.src = "/janela/demo.js";
        s.onload = () => { const cena = window.GroovDemo.cenas[params.get("cena")]; if (cena) cena.forEach(window.groovAcao); };
        document.head.appendChild(s);
        return;
      }
      const conexao = window.GroovConexao.iniciar({
        aoMensagem,
        aoCair: () => { reenviarRef.current = true; despachar({ tipo: "conexao_caiu" }); },
        aoSubstituida: () => despachar({ tipo: "aviso", titulo: "OUTRA JANELA ASSUMIU", texto: "Recarregue esta para voltar." }),
        aoErro: () => despachar({ tipo: "aviso", titulo: "SEM MICROFONE", texto: "Verifique o microfone e o servidor." }),
      });
      enviarRef.current = conexao.enviar;
    }, []);

    // enviar devolve false com o canal fechado: o comando se perdeu e o aviso diz isso.
    function enviar(t, d) {
      const ok = enviarRef.current(t, d);
      if (!ok) despachar({ tipo: "aviso", titulo: "SEM CONEXÃO", texto: "O comando não foi enviado." });
      return ok;
    }
    const [dialogo, setDialogo] = React.useState(null);
    const fechar = () => setDialogo(null);
    const aoChip = (id) => {
      if (id === "limpar") { if (estado.turnos.length || estado.paineis.length) setDialogo("limpar"); return; }
      if (id === "sistema" && !enviar("telemetria", { ligada: !estado.chips.sistema })) return;
      if (id === "projetos" && !estado.chips.projetos && !enviar("projetos", {})) return;
      despachar({ tipo: "chip", id });
    };

    const f = fase(estado);
    // Segura a tela de boot 900 ms depois de "pronto" para o ONLINE aparecer; o relógio só roda ao "pronto" chegar.
    const pronto = estado.boot === "pronto";
    const [soltou, setSoltou] = React.useState(false);
    React.useEffect(() => {
      if (!pronto) { setSoltou(false); return; }
      const id = setTimeout(() => setSoltou(true), 900);
      return () => clearTimeout(id);
    }, [pronto]);

    const aviso = estado.aviso && h(Toast, { icon: "triangle-alert", title: estado.aviso.titulo, message: estado.aviso.texto, tone: "rose", onClose: () => despachar({ tipo: "aviso_fechar" }) });
    // Canto inferior esquerdo: SISTEMA, pergunta e aviso numa pilha só, de cima para baixo, acima da faixa de fala.
    const pilha = (...filhos) => h("div", { className: "groov-pilha", style: { position: "absolute", left: 22, bottom: 54, zIndex: 8, display: "flex", flexDirection: "column", gap: 10 } }, ...filhos);
    if (f === "boot" || (pronto && !soltou)) return h("div", { className: "groov-raiz" }, h(Boot, { marco: estado.boot }), aviso && pilha(aviso));
    const { quem, texto } = estado.faixa;
    const ativo = f !== "oculto";
    // o app encaixado fica por cima de tudo (TOPMOST): o painel dele também abre espaço para o orbe e a pilha do canto
    const comPaineis = estado.paineis.length > 0 || !!estado.claude;
    // A grade não passa por baixo da pilha do canto: abre espaço do tamanho dela.
    const larguraPilha = estado.pergunta || estado.aviso ? 360 : estado.chips.sistema ? 230 : 0;
    return h("div", { className: "groov-raiz" },
      h(Fundo),
      ativo && h(React.Fragment, null,
        h(TopoEsquerdo, { fase: f, desligaEm: estado.desligaEm }),
        h(TopoDireito, { chips: estado.chips, limpando: dialogo === "limpar", aoChip, aoDesligar: () => enviar("desligar", {}), aoMemoria: () => setDialogo("memoria"),
          surdo: estado.surdo, aoSurdo: () => enviar("surdo", { ligada: !estado.surdo }) }),
        h("div", { style: { position: "absolute", inset: "48px 22px 52px", display: "grid", gridTemplateColumns: estado.chips.historico ? "minmax(0,1fr) 250px" : "minmax(0,1fr)", gap: 14 } },
          h("div", { style: { position: "relative", minHeight: 0, minWidth: 0, paddingBottom: comPaineis || estado.chips.projetos ? 96 : 0, paddingLeft: comPaineis && larguraPilha ? larguraPilha + 16 : 0 } },
            estado.claude ? h(JanelaApp, { aoFechar: () => despachar({ tipo: "claude_fechar" }),
              // sem o aviso de SEM CONEXÃO: a área volta a cada medida e, sem conexão, o servidor já soltou o app sozinho
              aoArea: (a) => enviarRef.current("claude_area", a), aoSolto: () => enviarRef.current("claude_solto", {}) })
            : estado.chips.projetos ? h(Projetos, { estado, enviar, despachar })
            : comPaineis ? h("div", { style: { position: "relative", height: "100%" } },
              h(Grade, { paineis: estado.paineis, ativo: estado.painelAtivo, aoAtivar: (id) => despachar({ tipo: "ativar_painel", id }), aoFechar: (id) => despachar({ tipo: "fechar_painel", id }) }))
              : f === "ocioso" ? h(Ocioso) : h(Nucleo, { fase: f, texto })),
          estado.chips.historico && h("div", { style: { minHeight: 0, display: "flex", flexDirection: "column", paddingBottom: 96 } }, h(Historico, { turnos: estado.turnos }))),
        (texto || f === "ouvindo") && h(FaixaDeFala, { quem: texto ? quem : "VOCÊ", texto, falando: f === "falando" || f === "ouvindo" }),
        h(Orbe, { fase: f, aoClicar: () => enviar("acordar", {}) }),
        estado.chips.texto && h(Compositor, { aoEnviar: (t) => {
          if (!enviar("texto", { texto: t })) return false;
          despachar({ tipo: "digitou", texto: t, hora: hora() });
          return true;
        } })),
      pilha(
        ativo && estado.chips.sistema && h(Sistema, { telemetria: estado.telemetria }),
        ativo && estado.pergunta && h(Pergunta, {
          key: estado.pergunta.id, pergunta: estado.pergunta,
          // Só some se o comando saiu; "pergunta_venceu" é o que limpa o estado.
          aoResponder: (opcao) => { if (enviar("resposta", { id: estado.pergunta.id, opcao })) despachar({ tipo: "pergunta_venceu" }); },
          aoVencer: () => despachar({ tipo: "pergunta_venceu" }),
        }),
        aviso),
      h(Dialog, {
        open: dialogo === "limpar", onClose: fechar, eyebrow: "SISTEMA", title: "LIMPAR A TELA?",
        actions: h(React.Fragment, null,
          h(Button, { variant: "ghost", size: "sm", onClick: fechar }, "CANCELAR"),
          h(Button, { size: "sm", onClick: () => { despachar({ tipo: "limpar" }); fechar(); } }, "LIMPAR")),
      }, "Remove os painéis e o histórico desta tela. A conversa continua."),
      h(Dialog, {
        open: dialogo === "memoria", onClose: fechar, eyebrow: "SISTEMA", title: "ENCERRAR TUDO?",
        actions: h(React.Fragment, null,
          h(Button, { variant: "ghost", size: "sm", onClick: fechar }, "CANCELAR"),
          h(Button, { size: "sm", onClick: () => { enviar("encerrar_tudo", {}); fechar(); } }, "ENCERRAR")),
      }, "Fecha a conversa, a voz, o Whisper e esta janela. O Hey JARVIS só volta ao religar pelo atalho. O timer simples se perde; o de desligar o PC continua."));
  }

  ReactDOM.createRoot(document.getElementById("raiz")).render(h(App));
})();
