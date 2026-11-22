"use strict";
// Cenas de demonstração (?demo=1&cena=<nome>): listas de ações para o redutor, sem servidor, microfone ou placa.
window.GroovDemo = (function () {
  const rtvi = (type, data) => ({ tipo: "rtvi", msg: { type, data }, hora: "14:32" });
  const srv = (data) => rtvi("server-message", data);
  const falar = (id, text) => rtvi("bot-output", { text, segment_id: id, will_be_spoken: true });
  const conversando = srv({ estado: "conversando" });
  const painel = (p) => srv({ painel: p });
  const pergunta = (extra) => srv({ pergunta: { id: "p1", texto: "Encerro por hoje?", opcoes: ["Sim", "Não"], so_voz: false, ate: Date.now() / 1000 + 20, ...extra } });

  const telemetria = { vram_usada: 6042, vram_total: 8397, latencia_ms: 1500, voz: true, whisper: true };

  const agora = Date.now() / 1000;
  const projetosDemo = [
    { nome: "GROOV", prompts_7d: 91, atualizado: agora - 600, chats: [
      { id: "11111111-2222-3333-4444-555555555555", titulo: "Refazer a marca do GROOV", prompts_7d: 40, atualizado: agora - 600 },
      { id: "22222222-2222-3333-4444-555555555555", titulo: "Ajustar o Whisper", prompts_7d: 3, atualizado: agora - 86400 }] },
    { nome: "MeuProjeto", prompts_7d: 2, atualizado: agora - 7200, chats: [] },
    { nome: "StartUp", prompts_7d: 0, atualizado: agora - 9 * 86400, chats: [] },
  ];
  const chatDemo = { id: "11111111-2222-3333-4444-555555555555", workspace: "GROOV", mensagens: [
    { quem: "voce", texto: "Quero refazer a marca." },
    { quem: "claude", texto: "Vou começar pelo brainstorming." },
    { quem: "ferramenta", texto: "Read" },
    { quem: "claude", texto: "Pronto: o desenho está em specs/." }] };

  const turnos = [
    conversando,
    rtvi("user-input", { text: "Que horas são e como está o tempo?", final: true }),
    rtvi("bot-llm-started"), falar("a1", "São 14h32, senhor."), falar("a2", "Faz 24 graus e o céu está limpo."),
    rtvi("user-input", { text: "Abre o bloco de notas.", final: true }),
    rtvi("bot-llm-started"), falar("b1", "Abrindo agora."),
  ];

  const cenas = {
    boot: [srv({ estado: "acordando" }), srv({ boot: "inicio" }), srv({ boot: "abertura" }), srv({ boot: "whisper" })],
    boot_pronto: [srv({ estado: "acordando" }), srv({ boot: "pronto" })],
    ocioso: [srv({ estado: "ocioso", desliga_em: Date.now() / 1000 + 125 })],
    ouvindo: [conversando, rtvi("user-started-speaking")],
    pensando: [conversando, rtvi("user-started-speaking"), rtvi("user-input", { text: "Que horas são?", final: true }), rtvi("user-stopped-speaking")],
    falando: [conversando, rtvi("bot-llm-started"), rtvi("bot-started-speaking"), falar("f1", "Claro, senhor. Estou verificando isso agora.")],
    historico: [...turnos, { tipo: "chip", id: "historico" }],
    texto: [conversando, { tipo: "chip", id: "texto" }],
    boot_entrada: [srv({ estado: "acordando" }), srv({ boot: "inicio" }), { tipo: "chip", id: "texto" }, pergunta({})],
    boot_pronto_entrada: [srv({ estado: "acordando" }), srv({ boot: "pronto" }), { tipo: "chip", id: "texto" }, pergunta({})],
    pergunta_sem_opcoes: [conversando, pergunta({ opcoes: undefined })],
    pergunta: [conversando, pergunta({})],
    pergunta_voz: [conversando, pergunta({ texto: "Posso enviar a mensagem?", opcoes: [], so_voz: true })],
    paineis: [
      conversando,
      painel({ id: "pesquisa", tipo: "texto", titulo: "Pesquisa: pizzarias abertas", corpo: "Três opções abertas a esta hora, todas a menos de 2 km." }),
      painel({ id: "clima", tipo: "numero", titulo: "Clima", valor: "24", unidade: "°C", corpo: "Céu limpo, sem previsão de chuva." }),
      painel({ id: "hoje", tipo: "lista", titulo: "Hoje", itens: ["Reunião às 15h", "Comprar café", "Ligar para o contador"] }),
      painel({ id: "pc", tipo: "passos", titulo: "Abrir o bloco de notas", itens: ["abrir: bloco de notas", "esperar: janela"] }),
      painel({ id: "timer", tipo: "numero", titulo: "Timer: macarrão", fim: Date.now() / 1000 + 12 * 60 }),
    ],
    // Fronteira com o servidor: desfecho sem meta e fim não numérico.
    paineis_bordas: [
      conversando,
      painel({ id: "pc", tipo: "passos", titulo: "Abrir o bloco de notas", itens: ["abrir: bloco de notas", "esperar: janela"], corpo: "Não achei a janela." }),
      painel({ id: "t1", tipo: "numero", titulo: "Timer texto", valor: "7", unidade: "min", fim: "abc" }),
      painel({ id: "t2", tipo: "numero", titulo: "Timer sem número", fim: NaN }),
    ],
    sistema: [conversando, { tipo: "chip", id: "sistema" }, srv({ telemetria })],
    claude: [conversando, { tipo: "claude_abrir", id: "11111111-2222-3333-4444-555555555555" }],
    sistema_vazio: [conversando, { tipo: "chip", id: "sistema" }],
    sistema_nulo: [conversando, { tipo: "chip", id: "sistema" }, srv({ telemetria: { vram_usada: null, vram_total: null, latencia_ms: null, voz: false, whisper: false } })],
    // Canto inferior esquerdo cheio: SISTEMA, pergunta e aviso juntos (tudo_texto soma o compositor).
    tudo: [...turnos, { tipo: "chip", id: "historico" }, { tipo: "chip", id: "sistema" }, srv({ telemetria }), pergunta({ ate: Date.now() / 1000 + 600 }),
      painel({ id: "pesquisa", tipo: "texto", titulo: "Pesquisa: pizzarias abertas", corpo: "Três opções abertas a esta hora, todas a menos de 2 km." }),
      painel({ id: "hoje", tipo: "lista", titulo: "Hoje", itens: ["Reunião às 15h", "Comprar café", "Ligar para o contador"] }),
      // por último: qualquer mensagem do servidor apaga o aviso
      { tipo: "aviso", titulo: "SEM CONEXÃO", texto: "O comando não foi enviado." }],
    aviso: [srv({ estado: "ocioso" }), { tipo: "aviso", titulo: "SEM CONEXÃO", texto: "O comando não foi enviado." }],
    recusado: [conversando, rtvi("error-response", { error: "expirada" })],
    dialogo: turnos,
    projetos: [conversando, { tipo: "chip", id: "projetos" }, srv({ projetos: projetosDemo })],
    chat: [conversando, { tipo: "chip", id: "projetos" }, srv({ projetos: projetosDemo }), srv({ chat: chatDemo })],
    surdo: [conversando, srv({ surdo: true })],
    chat_enviando: [conversando, { tipo: "chip", id: "projetos" }, srv({ chat: chatDemo }), { tipo: "ditar" },
      { tipo: "chat_rascunho", texto: "Atualiza a lista de vagas" }],
  };

  cenas.tudo_texto = [...cenas.tudo, { tipo: "chip", id: "texto" }];

  // Cenas que precisam de clique (o diálogo vive no app, não no estado).
  const cliquesDaCena = { dialogo: ["LIBERAR A MEMÓRIA"] };

  // &clicar=A,B clica, em ordem, nos botões de mesmo nome e grava o que seria enviado em <pre id="demo-enviadas"> (prova sem humano).
  function clicar(rotulo) {
    const nome = (el) => el.getAttribute("aria-label") || el.textContent.trim();
    const dentro = document.querySelector("[role=dialog]") || document;
    const alvo = [...dentro.querySelectorAll("button,[role=button]")].find((el) => nome(el) === rotulo);
    if (alvo) alvo.click();
    else console.error("demo: botão não achado: " + rotulo);
  }
  const params = new URLSearchParams(location.search);
  const lista = [...(cliquesDaCena[params.get("cena")] || []), ...(params.get("clicar") || "").split(",").filter(Boolean)];
  // &digitar=<texto> escreve no campo do compositor como um usuário (setter nativo + input) e aperta Enter.
  function digitar(texto) {
    const campo = document.querySelector("input[placeholder^=ESCREVA]");
    if (!campo) return console.error("demo: campo de texto não achado");
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(campo, texto);
    campo.dispatchEvent(new Event("input", { bubbles: true }));
    // &tecla=composicao|shift|ctrl|alt|meta: o Enter leva esse estado e não deve enviar.
    const t = params.get("tecla");
    const init = { key: "Enter", bubbles: true, cancelable: true, isComposing: t === "composicao", keyCode: t === "composicao" ? 229 : 13, shiftKey: t === "shift", ctrlKey: t === "ctrl", altKey: t === "alt", metaKey: t === "meta" };
    setTimeout(() => campo.dispatchEvent(new KeyboardEvent("keydown", init)), 100);
  }
  if (lista.length || params.has("digitar")) {
    const passos = lista.map((r) => () => clicar(r));
    if (params.has("digitar")) passos.push(() => digitar(params.get("digitar")), () => {});
    // &reconectar=1: simula queda e a 1ª mensagem com estado da nova conexão.
    if (params.has("reconectar")) passos.push(() => { window.groovAcao({ tipo: "conexao_caiu" }); window.groovDemo({ type: "server-message", data: { estado: "ocioso" } }); });
    passos.push(() => { const pre = document.createElement("pre"); pre.id = "demo-enviadas"; pre.textContent = JSON.stringify(window.groovEnviadas); document.body.appendChild(pre); });
    passos.forEach((passo, i) => setTimeout(passo, 400 + i * 150));
  }

  return { cenas };
})();
