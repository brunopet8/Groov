"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const E = require("../../src/conversa/janela/estado.js");

const congelar = (o) => { Object.values(o).forEach((v) => v && typeof v === "object" && congelar(v)); return Object.freeze(o); };
const rtvi = (type, data, hora = "10:00") => ({ tipo: "rtvi", msg: { type, data }, hora });
const srv = (data, hora) => rtvi("server-message", data, hora);
const aplicar = (acoes, e = E.inicial()) => acoes.reduce((s, a) => E.reduzir(s, a), e);
const painel = (id, extra = {}) => srv({ painel: { id, tipo: "texto", titulo: id, ...extra } });

test("constantes", () => {
  assert.equal(E.PAINEIS_MAX, 6);
  assert.equal(E.TURNOS_MAX, 200);
  assert.deepEqual(E.PROGRESSO.pronto, [100, "— ONLINE —"]);
  assert.deepEqual(E.PROGRESSO.inicio, [8, "INICIANDO SISTEMA..."]);
});

test("estado inicial", () => {
  const e = E.inicial();
  assert.equal(e.base, "dormindo");
  assert.equal(e.desligaEm, null);
  assert.deepEqual(e.faixa, { quem: "GROOV", texto: "" });
  assert.deepEqual(e.turnos, []);
  assert.deepEqual(e.paineis, []);
  assert.deepEqual(e.chips, { historico: false, texto: false, projetos: false, sistema: false });
  assert.equal(e.pergunta, null);
  assert.equal(e.telemetria, null);
  assert.equal(e.aviso, null);
  assert.equal(e.projetos, null);
  assert.equal(e.chat, null);
  assert.equal(e.ditando, false);
});

const ID = "11111111-2222-3333-4444-555555555555";
const abrirChat = () => srv({ chat: { id: ID, workspace: "Proj", mensagens: [{ quem: "voce", texto: "oi" }] } });

test("projetos e chat chegam do servidor", () => {
  const e = aplicar([srv({ projetos: [{ nome: "Proj", chats: [] }] }), abrirChat()]);
  assert.deepEqual(e.projetos, [{ nome: "Proj", chats: [] }]);
  assert.deepEqual(e.chat, { id: ID, workspace: "Proj", mensagens: [{ quem: "voce", texto: "oi" }], enviando: false, rascunho: "" });
});

test("enviar no chat: mensagem entra, espera a resposta, resposta entra", () => {
  let e = aplicar([abrirChat(), { tipo: "chat_rascunho", texto: "faz X" }, { tipo: "chat_enviou", texto: "faz X" }]);
  assert.equal(e.chat.enviando, true);
  assert.equal(e.chat.rascunho, "");
  assert.deepEqual(e.chat.mensagens.at(-1), { quem: "voce", texto: "faz X" });
  e = aplicar([srv({ chat_resposta: { id: ID, texto: "Feito." } })], e);
  assert.equal(e.chat.enviando, false);
  assert.deepEqual(e.chat.mensagens.at(-1), { quem: "claude", texto: "Feito." });
});

test("resposta com erro vira linha de erro", () => {
  const e = aplicar([abrirChat(), { tipo: "chat_enviou", texto: "x" }, srv({ chat_resposta: { id: ID, erro: "falhou" } })]);
  assert.deepEqual(e.chat.mensagens.at(-1), { quem: "erro", texto: "falhou" });
  assert.equal(e.chat.enviando, false);
});

test("resposta de outro chat é ignorada", () => {
  const antes = aplicar([abrirChat(), { tipo: "chat_enviou", texto: "x" }]);
  const depois = aplicar([srv({ chat_resposta: { id: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", texto: "y" } })], antes);
  assert.deepEqual(depois.chat, antes.chat);
});

test("ditado vai para o rascunho e desliga o microfone", () => {
  const e = aplicar([abrirChat(), { tipo: "chat_rascunho", texto: "corrige" }, { tipo: "ditar" }, srv({ ditado: "o login" })]);
  assert.equal(e.chat.rascunho, "corrige o login");
  assert.equal(e.ditando, false);
});

test("ditado sem chat aberto é ignorado", () => {
  const e = aplicar([{ tipo: "ditar" }, srv({ ditado: "x" })]);
  assert.equal(e.chat, null);
});

test("recusa do servidor solta o microfone e o envio", () => {
  const e = aplicar([abrirChat(), { tipo: "chat_enviou", texto: "x" }, { tipo: "ditar" }, rtvi("error-response", { error: "ocupado" })]);
  assert.equal(e.ditando, false);
  assert.equal(e.chat.enviando, false);
});

test("conexão caiu: microfone e envio do chat soltam", () => {
  const e = aplicar([abrirChat(), { tipo: "chat_enviou", texto: "x" }, { tipo: "ditar" }, { tipo: "conexao_caiu" }]);
  assert.equal(e.ditando, false);
  assert.equal(e.chat.enviando, false);
});

test("ditado longo não passa de 2000", () => {
  const e = aplicar([abrirChat(), srv({ ditado: "a".repeat(2500) })]);
  assert.equal(e.chat.rascunho.length, 2000);
});

test("chat_voltar fecha o chat", () => {
  assert.equal(aplicar([abrirChat(), { tipo: "chat_voltar" }]).chat, null);
});

test("fase por estado base", () => {
  const com = (base, extra = {}) => ({ ...E.inicial(), base, ...extra });
  assert.equal(E.fase(com("dormindo")), "oculto");
  assert.equal(E.fase(com("acordando")), "boot");
  assert.equal(E.fase(com("carregando")), "boot");
  assert.equal(E.fase(com("ocioso")), "ocioso");
  assert.equal(E.fase(com("conversando")), "ouvindo");
  assert.equal(E.fase(com("conversando", { pensando: true })), "pensando");
  assert.equal(E.fase(com("conversando", { pensando: true, usuarioFalando: true })), "ouvindo");
  assert.equal(E.fase(com("conversando", { usuarioFalando: true, botFalando: true })), "falando");
});

test("desligaEm entra em ocioso e some em conversando", () => {
  let e = aplicar([srv({ estado: "ocioso", desliga_em: 123.5 })]);
  assert.equal(e.base, "ocioso");
  assert.equal(e.desligaEm, 123.5);
  e = aplicar([srv({ estado: "conversando" })], e);
  assert.equal(e.desligaEm, null);
});

test("boot guarda o marco", () => {
  assert.equal(aplicar([srv({ boot: "whisper" })]).boot, "whisper");
});

test("dormindo zera tudo", () => {
  let e = aplicar([
    srv({ estado: "conversando" }), painel("a"), srv({ pergunta: { id: "1", texto: "?", opcoes: [], so_voz: false, ate: 1 } }),
    srv({ telemetria: { vram_usada: 1 } }), rtvi("user-started-speaking"), rtvi("bot-started-speaking"),
    { tipo: "digitou", texto: "oi", hora: "10:01" },
  ]);
  assert.equal(e.turnos.length, 1);
  e = aplicar([srv({ estado: "dormindo" })], e);
  assert.equal(e.base, "dormindo");
  assert.deepEqual([e.turnos, e.paineis, e.pergunta, e.telemetria], [[], [], null, null]);
  assert.deepEqual([e.usuarioFalando, e.botFalando, e.pensando], [false, false, false]);
});

test("painel repetido substitui e vai para a frente", () => {
  const e = aplicar([painel("a"), painel("b"), painel("a", { titulo: "novo" })]);
  assert.deepEqual(e.paineis.map((p) => p.id), ["a", "b"]);
  assert.equal(e.paineis[0].titulo, "novo");
});

test("o 7o painel derruba o mais velho", () => {
  const e = aplicar(["1", "2", "3", "4", "5", "6", "7"].map((i) => painel(i)));
  assert.equal(e.paineis.length, 6);
  assert.deepEqual(e.paineis.map((p) => p.id), ["7", "6", "5", "4", "3", "2"]);
});

test("painel_fechar e fechar_painel / ativar_painel", () => {
  let e = aplicar([painel("a"), painel("b"), { tipo: "ativar_painel", id: "a" }]);
  assert.equal(e.painelAtivo, "a");
  e = aplicar([srv({ painel_fechar: "a" })], e);
  assert.deepEqual(e.paineis.map((p) => p.id), ["b"]);
  assert.equal(e.painelAtivo, null);
  e = aplicar([{ tipo: "fechar_painel", id: "b" }], e);
  assert.deepEqual(e.paineis, []);
});

test("pergunta abre, fecha com null e vence", () => {
  const p = { id: "1", texto: "?", opcoes: ["Sim", "Não"], so_voz: false, ate: 5 };
  const e = aplicar([srv({ pergunta: p })]);
  assert.deepEqual(e.pergunta, p);
  assert.equal(aplicar([srv({ pergunta: null })], e).pergunta, null);
  assert.equal(aplicar([{ tipo: "pergunta_venceu" }], e).pergunta, null);
});

test("telemetria", () => {
  assert.deepEqual(aplicar([srv({ telemetria: { voz: true } })]).telemetria, { voz: true });
});

test("sinais de fala", () => {
  let e = aplicar([rtvi("user-started-speaking")]);
  assert.equal(e.usuarioFalando, true);
  e = aplicar([rtvi("user-stopped-speaking")], e);
  assert.deepEqual([e.usuarioFalando, e.pensando], [false, true]);
  e = aplicar([rtvi("bot-started-speaking")], e);
  assert.deepEqual([e.botFalando, e.pensando], [true, false]);
  e = aplicar([rtvi("bot-stopped-speaking")], e);
  assert.equal(e.botFalando, false);
});

test("bot-output repetido com o mesmo segment_id conta uma vez", () => {
  const out = (id, text) => rtvi("bot-output", { text, segment_id: id, will_be_spoken: true });
  const e = aplicar([rtvi("bot-llm-started"), out("s1", "Olá."), out("s1", "Olá.")]);
  assert.equal(e.turnos.length, 1);
  assert.equal(e.turnos[0].texto, "Olá.");
  assert.deepEqual(e.faixa, { quem: "GROOV", texto: "Olá." });
});

test("duas frases da mesma resposta viram um turno so", () => {
  const out = (id, text) => rtvi("bot-output", { text, segment_id: id }, "10:05");
  const e = aplicar([rtvi("bot-llm-started"), out("s1", "Olá."), out("s2", " Tudo bem?")]);
  assert.equal(e.turnos.length, 1);
  assert.deepEqual(e.turnos[0], { quem: "GROOV", hora: "10:05", texto: "Olá. Tudo bem?" });
});

test("nova resposta abre novo turno; will_be_spoken false e ignorado", () => {
  const out = (id, text, extra = {}) => rtvi("bot-output", { text, segment_id: id, ...extra });
  const e = aplicar([
    rtvi("bot-llm-started"), out("a", "Um."), rtvi("bot-llm-started"), out("a", "Dois."), out("b", "mudo", { will_be_spoken: false }),
  ]);
  assert.deepEqual(e.turnos.map((t) => t.texto), ["Um.", "Dois."]);
});

test("user-input nao final e ignorado; final vira turno VOCE", () => {
  let e = aplicar([rtvi("user-input", { text: "ol", final: false })]);
  assert.deepEqual(e.turnos, []);
  e = aplicar([rtvi("user-input", { text: "olá", final: true }, "10:02")], e);
  assert.deepEqual(e.turnos, [{ quem: "VOCÊ", hora: "10:02", texto: "olá" }]);
  assert.deepEqual(e.faixa, { quem: "VOCÊ", texto: "olá" });
});

test("digitou cria turno VOCE", () => {
  const e = aplicar([{ tipo: "digitou", texto: "que horas", hora: "09:30" }]);
  assert.deepEqual(e.turnos, [{ quem: "VOCÊ", hora: "09:30", texto: "que horas" }]);
});

test("TURNOS_MAX corta os mais velhos", () => {
  const acoes = Array.from({ length: E.TURNOS_MAX + 5 }, (_, i) => ({ tipo: "digitou", texto: `t${i}`, hora: "10:00" }));
  const e = aplicar(acoes);
  assert.equal(e.turnos.length, E.TURNOS_MAX);
  assert.equal(e.turnos[0].texto, "t5");
});

test("limpar esvazia turnos e paineis e mantem base", () => {
  let e = aplicar([srv({ estado: "conversando" }), painel("a"), { tipo: "digitou", texto: "x", hora: "10:00" }]);
  e = aplicar([{ tipo: "limpar" }], e);
  assert.deepEqual([e.turnos, e.paineis, e.base], [[], [], "conversando"]);
});

test("chip alterna, aviso abre e fecha, conexao_caiu volta a dormir", () => {
  let e = aplicar([{ tipo: "chip", id: "texto" }]);
  assert.equal(e.chips.texto, true);
  e = aplicar([{ tipo: "chip", id: "texto" }], e);
  assert.equal(e.chips.texto, false);
  e = aplicar([{ tipo: "aviso", titulo: "T", texto: "x" }], e);
  assert.deepEqual(e.aviso, { titulo: "T", texto: "x" });
  e = aplicar([{ tipo: "aviso_fechar" }], e);
  assert.equal(e.aviso, null);
  e = aplicar([srv({ estado: "conversando" }), { tipo: "conexao_caiu" }]);
  assert.equal(e.base, "dormindo");
});

test("reduzir nao muda o objeto recebido", () => {
  const acoes = [
    srv({ estado: "ocioso", desliga_em: 1 }), srv({ boot: "voz" }), painel("a"), painel("b"), srv({ painel_fechar: "a" }),
    srv({ pergunta: { id: "1" } }), srv({ telemetria: { a: 1 } }), rtvi("user-started-speaking"), rtvi("user-stopped-speaking"),
    rtvi("bot-started-speaking"), rtvi("bot-stopped-speaking"), rtvi("bot-llm-started"),
    rtvi("bot-output", { text: "a", segment_id: "x" }), rtvi("user-input", { text: "b", final: true }),
    { tipo: "digitou", texto: "c", hora: "1" }, { tipo: "chip", id: "historico" }, { tipo: "ativar_painel", id: "b" },
    { tipo: "fechar_painel", id: "b" }, { tipo: "pergunta_venceu" }, { tipo: "aviso", titulo: "t", texto: "x" },
    { tipo: "aviso_fechar" }, { tipo: "limpar" }, { tipo: "conexao_caiu" }, srv({ estado: "dormindo" }),
  ];
  let e = E.inicial();
  for (const a of acoes) e = E.reduzir(congelar(structuredClone(e)), congelar(structuredClone(a)));
});

test("aviso de conexao some quando chega mensagem do servidor", () => {
  let e = aplicar([srv({ estado: "conversando" }), { tipo: "conexao_caiu" }]);
  assert.deepEqual(e.aviso, { titulo: "SEM CONEXÃO", texto: "Tentando reconectar..." });
  e = aplicar([srv({ estado: "ocioso" })], e);
  assert.equal(e.aviso, null);
  e = aplicar([{ tipo: "aviso", titulo: "T", texto: "x" }, rtvi("bot-llm-started")]);
  assert.equal(e.aviso, null);
});

test("digitou nao liga pensando; bot-llm-started liga; fala do bot desliga", () => {
  let e = aplicar([{ tipo: "digitou", texto: "oi", hora: "10:00" }]);
  assert.equal(e.pensando, false);
  e = aplicar([rtvi("bot-llm-started")], e);
  assert.equal(e.pensando, true);
  e = aplicar([rtvi("bot-started-speaking")], e);
  assert.equal(e.pensando, false);
});

test("error-response vira aviso COMANDO RECUSADO e sobrevive a esta mesma mensagem", () => {
  let e = aplicar([{ tipo: "conexao_caiu" }, rtvi("error-response", { error: "expirada" })]);
  assert.deepEqual(e.aviso, { titulo: "COMANDO RECUSADO", texto: "Expirada." });
  e = aplicar([rtvi("error-response", { error: "está desligado" })]);
  assert.equal(e.aviso.texto, "Está desligado.");
  e = aplicar([rtvi("error-response", { error: "falhou." })]);
  assert.equal(e.aviso.texto, "Falhou.");
  for (const d of [undefined, {}, { error: 5 }, { error: "" }]) {
    assert.equal(aplicar([rtvi("error-response", d)]).aviso.texto, "O servidor não aceitou o comando.");
  }
  e = aplicar([rtvi("error-response", { error: "expirada" }), rtvi("bot-llm-started")]);
  assert.equal(e.aviso, null);
});

test("aviso fecha pela acao aviso_fechar mesmo sem servidor", () => {
  const e = aplicar([{ tipo: "conexao_caiu" }, { tipo: "aviso_fechar" }]);
  assert.equal(e.aviso, null);
});

test("modo surdo vem do servidor e cai com a conexao", () => {
  assert.equal(E.inicial().surdo, false);
  assert.equal(aplicar([srv({ estado: "conversando" }), srv({ surdo: true })]).surdo, true);
  assert.equal(aplicar([srv({ surdo: true }), srv({ surdo: false })]).surdo, false);
  assert.equal(aplicar([srv({ surdo: true }), { tipo: "conexao_caiu" }]).surdo, false);
  assert.equal(aplicar([srv({ surdo: true }), srv({ estado: "dormindo" })]).surdo, true);  // dormir nao tira do surdo
});

// ---- painel grande CLAUDE CODE (14/11): o app desktop é encaixado por cima pelo servidor ----

test("claude_abrir abre o painel grande e fecha o PROJETOS", () => {
  const e = aplicar([{ tipo: "chip", id: "projetos" }, { tipo: "claude_abrir", id: ID }]);
  assert.deepEqual(e.claude, { id: ID });
  assert.equal(e.chips.projetos, false);
  assert.equal(E.inicial().claude, null);
});

test("claude some ao fechar, limpar, dormir e cair a conexão", () => {
  const aberto = [srv({ estado: "conversando" }), { tipo: "claude_abrir", id: ID }];
  assert.equal(aplicar([...aberto, { tipo: "claude_fechar" }]).claude, null);
  assert.equal(aplicar([...aberto, { tipo: "limpar" }]).claude, null);
  assert.equal(aplicar([...aberto, srv({ estado: "dormindo" })]).claude, null);
  assert.equal(aplicar([...aberto, { tipo: "conexao_caiu" }]).claude, null);
  assert.deepEqual(aplicar([...aberto, srv({ estado: "ocioso" })]).claude, { id: ID });  // ocioso a tela segue
});

test("areaDe: retângulo do corpo em frações da janela, preso em [0, 1]", () => {
  assert.deepEqual(E.areaDe({ left: 192, top: 108, width: 960, height: 540 }, 1920, 1080), { x: 0.1, y: 0.1, w: 0.5, h: 0.5 });
  assert.deepEqual(E.areaDe({ left: -10, top: 0, width: 2000, height: 1080 }, 1920, 1080), { x: 0, y: 0, w: 1, h: 1 });
  assert.equal(E.areaDe({ left: 0, top: 0, width: 0, height: 10 }, 1920, 1080), null);
  assert.equal(E.areaDe({ left: 0, top: 0, width: 10, height: 10 }, 0, 1080), null);
});
