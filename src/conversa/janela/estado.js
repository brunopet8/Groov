"use strict";
// Redutor puro da janela do GROOV: sem DOM, sem relógio (a hora vem na ação). Carrega como <script> e com require().
(function () {
  const PAINEIS_MAX = 6;
  const TURNOS_MAX = 200;
  const RASCUNHO_MAX = 2000;  // o mesmo TEXTO_MAX que o servidor aceita
  const PROGRESSO = {
    inicio: [8, "INICIANDO SISTEMA..."], abertura: [35, "INICIANDO SISTEMA..."], whisper: [60, "CARREGANDO MÓDULOS..."],
    voz: [85, "FINALIZANDO INICIALIZAÇÃO..."], pronto: [100, "— ONLINE —"],
  };

  // vistas: segment_ids da resposta atual (cada frase chega duas vezes, "new" e "completed")
  function inicial() {
    return {
      base: "dormindo", desligaEm: null, boot: null, usuarioFalando: false, botFalando: false, pensando: false,
      faixa: { quem: "GROOV", texto: "" }, turnos: [], paineis: [], painelAtivo: null, pergunta: null, telemetria: null,
      chips: { historico: false, texto: false, projetos: false, sistema: false }, aviso: null, vistas: [],
      projetos: null, chat: null, ditando: false, surdo: false, claude: null,
    };
  }

  // Painel PROJETOS: a lista vem do servidor; o chat aberto guarda o rascunho e se está esperando resposta.
  function doChat(e, d) {
    let s = e;
    if (d.projetos) s = { ...s, projetos: d.projetos };
    if (d.chat) s = { ...s, chat: { ...d.chat, enviando: false, rascunho: s.chat && s.chat.id === d.chat.id ? s.chat.rascunho : "" } };
    if (d.chat_resposta && s.chat && s.chat.id === d.chat_resposta.id) {
      const r = d.chat_resposta;
      const linha = r.erro ? { quem: "erro", texto: r.erro } : { quem: "claude", texto: r.texto || "" };
      s = { ...s, chat: { ...s.chat, enviando: false, mensagens: [...s.chat.mensagens, linha] } };
    }
    if (typeof d.ditado === "string") {
      s = { ...s, ditando: false };
      if (s.chat) s = { ...s, chat: { ...s.chat, rascunho: [s.chat.rascunho, d.ditado.trim()].filter(Boolean).join(" ").slice(0, RASCUNHO_MAX) } };
    }
    return s;
  }

  function fase(e) {
    switch (e.base) {
      case "acordando": case "carregando": return "boot";
      case "ocioso": return "ocioso";
      case "conversando":
        return e.botFalando ? "falando" : e.usuarioFalando ? "ouvindo" : e.pensando ? "pensando" : "ouvindo";
      default: return "oculto";
    }
  }

  const cortar = (turnos) => turnos.slice(-TURNOS_MAX);
  const dormir = (e) => ({
    ...e, base: "dormindo", desligaEm: null, boot: null, usuarioFalando: false, botFalando: false, pensando: false,
    faixa: { quem: "GROOV", texto: "" }, turnos: [], paineis: [], painelAtivo: null, pergunta: null, telemetria: null, vistas: [],
    // conexão caiu ou dormiu: a resposta pendente do chat não chega mais e o microfone desarmou no servidor
    ditando: false, chat: e.chat && { ...e.chat, enviando: false },
    claude: null,  // a janela some: o servidor devolve o app ao lugar dele
  });

  function doServidor(e, d) {
    let s = e;
    if (d.estado) {
      s = d.estado === "dormindo" ? dormir(s)
        : { ...s, base: d.estado, desligaEm: d.estado === "ocioso" && d.desliga_em != null ? d.desliga_em : null };
    }
    if (d.boot) s = { ...s, boot: d.boot };
    if (d.painel) s = { ...s, paineis: [d.painel, ...s.paineis.filter((p) => p.id !== d.painel.id)].slice(0, PAINEIS_MAX) };
    if (d.painel_fechar) s = fecharPainel(s, d.painel_fechar);
    if ("pergunta" in d) s = { ...s, pergunta: d.pergunta || null };
    if (d.telemetria) s = { ...s, telemetria: d.telemetria };
    if (typeof d.surdo === "boolean") s = { ...s, surdo: d.surdo };
    return doChat(s, d);
  }

  function fecharPainel(e, id) {
    return { ...e, paineis: e.paineis.filter((p) => p.id !== id), painelAtivo: e.painelAtivo === id ? null : e.painelAtivo };
  }

  function turnoDoUsuario(e, texto, hora) {
    return { ...e, faixa: { quem: "VOCÊ", texto }, turnos: cortar([...e.turnos, { quem: "VOCÊ", hora, texto }]) };
  }

  function falaDoBot(e, d, hora) {
    if (!d.text || d.will_be_spoken === false || e.vistas.includes(d.segment_id)) return e;
    const frase = d.text.trim();
    const ultimo = e.turnos[e.turnos.length - 1];
    const continua = e.vistas.length > 0 && ultimo && ultimo.quem === "GROOV";
    const texto = continua ? `${ultimo.texto} ${frase}` : frase;
    const turnos = continua ? [...e.turnos.slice(0, -1), { ...ultimo, texto }] : cortar([...e.turnos, { quem: "GROOV", hora, texto }]);
    return { ...e, vistas: [...e.vistas, d.segment_id], faixa: { quem: "GROOV", texto }, turnos };
  }

  function doRtvi(e, msg, hora) {
    const d = msg.data || {};
    switch (msg.type) {
      case "server-message": return doServidor(e, d);
      case "user-started-speaking": return { ...e, usuarioFalando: true, pensando: false };
      case "user-stopped-speaking": return { ...e, usuarioFalando: false, pensando: true };
      case "bot-started-speaking": return { ...e, botFalando: true, pensando: false };
      case "bot-stopped-speaking": return { ...e, botFalando: false };
      // o cérebro de fato começou: é aqui que "pensando" liga para o que foi digitado
      case "bot-llm-started": return { ...e, vistas: [], faixa: { quem: "GROOV", texto: "" }, pensando: true };
      case "user-input": return d.final && d.text ? turnoDoUsuario(e, d.text, hora) : e;
      case "bot-output": return falaDoBot(e, d, hora);
      default: return e;
    }
  }

  // recusa do servidor a um comando (error-response do RTVI): o motivo vem em data.error
  function recusa(d) {
    const m = typeof d.error === "string" ? d.error.trim() : "";
    const texto = m ? m[0].toUpperCase() + m.slice(1) + (/[.!?]$/.test(m) ? "" : ".") : "O servidor não aceitou o comando.";
    return { titulo: "COMANDO RECUSADO", texto };
  }

  function reduzir(e, a) {
    switch (a.tipo) {
      // qualquer mensagem do servidor prova que a conexão voltou: some o aviso
      case "rtvi": {
        const msg = a.msg || {};
        const s = { ...doRtvi(e, msg, a.hora), aviso: msg.type === "error-response" ? recusa(msg.data || {}) : null };
        // recusa (ocupado, desligado...): o microfone e o envio do chat não ficam presos
        return msg.type === "error-response" ? { ...s, ditando: false, chat: s.chat && { ...s.chat, enviando: false } } : s;
      }
      case "chat_voltar": return { ...e, chat: null, ditando: false };
      case "chat_rascunho": return e.chat ? { ...e, chat: { ...e.chat, rascunho: a.texto } } : e;
      case "chat_enviou": return e.chat
        ? { ...e, chat: { ...e.chat, enviando: true, rascunho: "", mensagens: [...e.chat.mensagens, { quem: "voce", texto: a.texto }] } } : e;
      case "ditar": return { ...e, ditando: true };
      case "digitou": return turnoDoUsuario(e, a.texto, a.hora);
      case "chip": return { ...e, chips: { ...e.chips, [a.id]: !e.chips[a.id] } };
      case "limpar": return { ...e, turnos: [], paineis: [], painelAtivo: null, claude: null };
      // painel grande CLAUDE CODE: o servidor encaixa o app desktop sobre o corpo dele (claude_app.py)
      case "claude_abrir": return { ...e, claude: { id: a.id }, chips: { ...e.chips, projetos: false } };
      case "claude_fechar": return { ...e, claude: null };
      case "fechar_painel": return fecharPainel(e, a.id);
      case "ativar_painel": return { ...e, painelAtivo: a.id };
      case "pergunta_venceu": return { ...e, pergunta: null };
      case "aviso": return { ...e, aviso: { titulo: a.titulo, texto: a.texto } };
      case "aviso_fechar": return { ...e, aviso: null };
      // a conexão nova abre uma sessão nova no servidor, que nasce ouvindo
      case "conexao_caiu": return { ...dormir(e), surdo: false, aviso: { titulo: "SEM CONEXÃO", texto: "Tentando reconectar..." } };
      default: return e;
    }
  }

  // Retângulo (getBoundingClientRect) em frações da janela, preso nela; null se não há o que medir.
  function areaDe(r, largura, altura) {
    if (!(largura > 0 && altura > 0 && r.width > 0 && r.height > 0)) return null;
    const fr = (v) => Math.round(Math.min(Math.max(v, 0), 1) * 10000) / 10000;
    const x = fr(r.left / largura), y = fr(r.top / altura);
    return { x, y, w: fr(Math.min((r.left + r.width) / largura, 1) - x), h: fr(Math.min((r.top + r.height) / altura, 1) - y) };
  }

  const api = { PAINEIS_MAX, TURNOS_MAX, PROGRESSO, inicial, reduzir, fase, areaDe };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else window.GroovEstado = api;
})();
