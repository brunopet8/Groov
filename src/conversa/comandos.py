"""Atalhos locais (0 tokens) por intenção: hora, tchau (dormir), desligar, novidades, hoje; e filtro de alucinações do
Whisper. O que não casar segue para o cérebro (ferramentas briefing e encerrar)."""
import re
from datetime import datetime

FRASE_TCHAU = "Até logo, senhor."
FRASE_DESLIGAR = "Desligando, senhor."
FRASE_SEM_QUADRO = "Ainda não tenho o seu quadro, senhor."
FRASE_NAO_GUARDEI = "Certo, senhor. Não guardei."
FRASE_NAO_CONSEGUI_GUARDAR = "Não consegui guardar, senhor. Tente de novo em instantes."
FRASE_ENCERRO = "Encerro por hoje, senhor?"  # sem "confirma" no fim: o eco da pergunta não pode confirmar
FRASE_FICO = "Certo, senhor. Continuo aqui."
FRASE_NAO_ANOTEI = "Não anotei o timer, senhor."  # trecho com timer que chegou tarde demais para o laço
FRASE_TIMER_CANCELADO = "Timer cancelado, senhor."
FRASE_SEM_TIMER = "Não há timer armado, senhor."
FRASE_TIMER_NAO_CANCELOU = "Não consegui cancelar o timer, senhor."
FRASE_PAUSADO = "Pausado, senhor."
FRASE_NAO_ACHEI_MIDIA = "Não achei nada tocando, senhor."
FRASE_QUAL_TIMER = "Qual deles, senhor: o de desligar ou o simples?"
# resultado de Timers.cancelar -> fala
FRASE_TIMERS = {"simples": FRASE_TIMER_CANCELADO, "desligar": FRASE_TIMER_CANCELADO, "ambos": FRASE_TIMER_CANCELADO,
                "nenhum": FRASE_SEM_TIMER, "falhou": FRASE_TIMER_NAO_CANCELOU, "qual": FRASE_QUAL_TIMER}

_PONTUACAO = re.compile(r"[.,!?;:\"']")
_NOME_ANTIGO = re.compile(r"\b(?:javis|djarvis|jarviz)\b")
_GROOV = re.compile(r"\b(?:gruv|groove|grooves|grove|groves|gruve|gruvi)\b")  # grafias que o Whisper devolve para "Groov"


def normalizar(texto: str) -> str:
    texto = _PONTUACAO.sub("", texto.lower())
    return " ".join(_GROOV.sub("groov", _NOME_ANTIGO.sub("jarvis", texto)).split())


def _com_nome(*bases: str) -> set[str]:
    return {f for b in bases for n in ("jarvis", "groov") for f in (b, f"{n} {b}", f"{b} {n}")}


# Palavras que não mudam a intenção: "ok Jarvis, pode desligar agora, por favor" tem o núcleo "desligar".
# "sim" também: com "Encerro por hoje?" pendente, "Sim, desliga" tem de cair no "desliga" local.
ENCHIMENTO = {"jarvis", "groov", "pode", "por", "favor", "agora", "já", "ja", "senhor", "ok", "okay", "então", "entao", "bom",
              "tá", "ta", "aí", "ai", "ei", "oi", "hey", "hei", "sim"}


def nucleo(texto: str) -> str:
    return " ".join(p for p in normalizar(texto).split() if p not in ENCHIMENTO)


# O núcleo casa inteiro: "desliga a luz", "não vá embora" e "tchau pessoal" sobram palavras e não disparam.
_FRASES = {
    # sem "surdo" sozinho: "tá surdo?" é reclamação (revisão 14/11); "groov surdo" casa em comando_local, com o nome
    "surdo": ("fica surdo", "fique surdo", "ficar surdo", "modo surdo"),
    "hora": ("que horas são", "que horas sao", "me diz a hora", "me diga a hora", "que hora é", "me diz as horas",
             "me diga as horas", "sabe que horas são", "sabe que horas sao"),
    # sem "pode ir", "até já" e "é só isso": viram "ir", "até" e uma pergunta comum no meio da conversa (revisão
    # 28/10); como despedida, o cérebro ainda entende e chama encerrar.
    "tchau": ("tchau", "até logo", "até mais", "até daqui a pouco", "volte daqui a pouco", "volto já",
              "depois te chamo", "pode descansar", "descansa", "pode dormir", "por enquanto é só"),
    "desligar": ("desliga", "desligar", "desligue", "vá embora", "vai embora", "pode ir embora", "encerra",
                 "encerrar", "encerre", "encerra por hoje", "por hoje é só", "chega por hoje", "até amanhã", "não vou mais te usar hoje",
                 "não preciso mais de você hoje", "sai do meu pc"),
    "novidades": ("novidades", "quais as novidades", "quais são as novidades", "quais sao as novidades",
                  "alguma novidade"),
    "hoje": ("o que tenho para hoje", "o que tenho pra hoje", "o que eu tenho para hoje", "o que eu tenho pra hoje",
             "o que tem para hoje", "o que tem pra hoje"),
    # para o laço do PC; sem laço rodando, o filtro deixa seguir como hoje. Não cancela timer.
    "parar": ("para", "pare", "parar", "cancela", "cancelar", "chega"),
    # mídia direta, sem o laço nem o modelo; "para" continua sendo o cancelar do laço
    "midia_pausar": ("pausa", "pausar", "pause", "pausa a música", "pausa a série", "pausa o filme"),
    "midia_tocar": ("continua", "continuar", "dá play", "da play", "play", "despausa", "volta a tocar"),
    "midia_proxima": ("próxima", "proxima", "pula", "pular", "passa", "próxima música", "pula essa"),
    # janelas e abas, sem o laço nem o modelo (fase 6); ver JANELA_ATALHOS
    "janela_fechar_aba": ("fecha essa aba", "fecha esta aba", "fecha a aba", "fecha aba", "fechar aba", "fechar a aba"),
    "janela_fechar_chrome": ("fecha o chrome", "fechar o chrome", "fecha o google chrome", "fecha a janela do chrome",
                             "fecha o navegador", "fechar o navegador"),
    "janela_fechar": ("fecha a janela", "fechar a janela", "fecha essa janela", "fecha esta janela"),
    "janela_minimizar": ("minimiza", "minimizar", "minimize", "minimiza a janela", "minimiza essa janela"),
    "janela_minimizar_chrome": ("minimiza o chrome", "minimizar o chrome", "minimiza o navegador"),
    "cancelar_timer": tuple(f"{verbo} {t}" for t in ("o timer", "o taimer", "o temporizador", "os timers")
                            for verbo in ("cancela", "cancelar", "cancele", "tira", "tirar", "para", "desliga"))
    # o mesmo pedido dito pelo alvo: com o laço rodando não pode cair em "Não anotei o timer"
    + tuple(f"{verbo} {t} {alvo}" for t in ("o timer", "o taimer", "o temporizador")
            for verbo in ("cancela", "cancelar", "cancele", "tira", "tirar", "para")
            for alvo in ("de desligar", "para desligar", "pra desligar", "de desligamento"))
    + ("não desliga o pc", "não desligue o pc", "não desliga o computador", "não desligue o computador"),
}
# comando -> (ação, alvo) de janela_pc.agir_na_janela; alvo vazio = a janela da frente
JANELA_ATALHOS = {
    "janela_fechar_aba": ("fechar_aba", "chrome"),
    "janela_fechar_chrome": ("fechar", "chrome"),
    "janela_fechar": ("fechar", ""),
    "janela_minimizar": ("minimizar", ""),
    "janela_minimizar_chrome": ("minimizar", "chrome"),
}
# Mídia com palavra comum: sem mídia para controlar, é fala normal ("continua" depois de um briefing vai ao cérebro).
# shortcut: com uma sessão pausada esquecida (Spotify em segundo plano), "continua" ainda toca; checar quem pausou se incomodar.
MIDIA_AMBIGUAS = frozenset({"continua", "continuar", "passa", "pula", "pular"})
_NUCLEOS: dict[str, str] = {}
for _nome, _lista in _FRASES.items():
    for _frase in _lista:
        _n = nucleo(_frase)
        assert _n and _NUCLEOS.get(_n, _nome) == _nome, f"núcleo '{_n}' em dois comandos"
        _NUCLEOS[_n] = _nome

# Saídas típicas do Whisper em silêncio/ruído; não podem chegar ao LLM.
_ALUCINACOES = {normalizar(f) for f in (
    "Obrigado.", "Obrigada.", "Obrigado por assistir.",
    "Legendas pela comunidade Amara.org", "Inscreva-se no canal",
)}


_SURDO_COM_NOME = {("groov", "surdo"), ("surdo", "groov"), ("jarvis", "surdo"), ("surdo", "jarvis")}  # só o nome + surdo
_LIGA_DESLIGAR = {"de", "para", "pra"}  # "bota um timer de" [pausa] "desligar": é o timer, não o GROOV


def comando_local(texto: str, anterior: str = "", turno_fechado: bool = True) -> str | None:
    """`anterior`: o turno até aqui. "desligar" só com o turno fechado; aberto, o filtro reavalia no fechamento."""
    comando = _NUCLEOS.get(nucleo(texto))
    if comando is None and tuple(normalizar(texto).split()) in _SURDO_COM_NOME:
        return "surdo"
    ultima = normalizar(anterior).rsplit(" ", 1)[-1]
    if comando == "desligar" and (not turno_fechado or ultima in _LIGA_DESLIGAR):
        return None
    return comando


_PODE_ENVIAR = _com_nome("pode enviar")


def pode_enviar(texto: str) -> bool:
    """A frase forte: só "pode enviar" inteira. "sim", "ok" e "pode" não valem."""
    return normalizar(texto) in _PODE_ENVIAR


# Resposta a uma pergunta "Confirma?": também só a frase inteira; "sim, mas antes..." não confirma nada.
# Sem "confirma": é a última palavra da pergunta do GROOV, e o eco dela não pode confirmar sozinho.
_SIM = _com_nome("sim", "confirmo", "pode", "pode sim", "sim confirmo", "sim pode", "pode guardar")
_NAO = _com_nome("não", "nao", "cancela", "cancelar", "não não", "nao nao")


# 11/11: a resposta natural ("sim, senhor", "isso", "pode abrir", "deixa") vale pela 1ª palavra, desde que o resto seja só
# enchimento: "sim, mas antes me diz a hora" continua não sendo sim. "confirma" fica de fora (eco da pergunta).
_INICIO_SIM = frozenset({"sim", "pode", "isso", "claro", "certo", "confirmo", "ok", "okay", "positivo", "abre", "yes"})
_INICIO_NAO = frozenset({"nao", "não", "cancela", "cancelar", "deixa", "deixe", "negativo", "no"})
_ENCHIMENTO_RESPOSTA = frozenset({"senhor", "jarvis", "groov", "sim", "pode", "isso", "mesmo", "claro", "certo", "abre", "abrir", "abra",
                                  "confirmo", "por", "favor", "com", "certeza", "que", "não", "ok", "okay", "ai", "la", "lá", "pra", "para", "nao",
                                  "precisa", "obrigado", "deixa", "deixe", "esse", "cancela", "cancelar", "isso", "mesmo"})


_ACERTOU = re.compile(r"\b(?:acert\w*|pode continuar|continua tocando|deixa tocando|(?:e |é )?isso mesmo|(?:e|é) isso|ta certo|tá certo|esta certo|está certo)\b")


_NEGA_LOGO_ANTES = re.compile(r"\b(?:nao|não)\s*$")
_RECUSA_TOCOU = frozenset({"nao", "não", "errado", "errada", "errou", "outra", "outro", "pausa", "pausar", "para", "parar", "tira",
                           "troca", "trocar"})


def acertou(texto: str) -> bool:
    """Só para "Tocou X, senhor. É isso?": "não, você acertou" é sim; "não é isso" e "você não acertou" não são (negação logo
    antes). Fora daqui vale o sim_ou_nao estrito."""
    frase = normalizar(texto)
    return any(not _NEGA_LOGO_ANTES.search(frase[:m.start()]) for m in _ACERTOU.finditer(frase))


def resposta_do_que_tocou(texto: str) -> str | None:
    """"sim", "nao" ou None para a pergunta "Tocou X, senhor. É isso?". Acerto vence; qualquer palavra de recusa ("errado",
    "outra", "pausa") é não; "deixa" é deixar tocando. None: o laço deixa tocando."""
    if acertou(texto):
        return "sim"
    palavras = normalizar(texto).split()
    if set(palavras) & _RECUSA_TOCOU:
        return "nao"
    if palavras[:1] in (["deixa"], ["deixe"]):
        return "sim"
    return sim_ou_nao(texto)


def sim_ou_nao(texto: str) -> str | None:
    frase = normalizar(texto)
    if frase in _SIM:
        return "sim"
    if frase in _NAO:
        return "nao"
    palavras = frase.split()
    if palavras and set(palavras) <= _ENCHIMENTO_RESPOSTA:
        if palavras[0] in _INICIO_NAO:
            return "nao"
        # negação em qualquer lugar ("claro que não", "pode não", "ok, não") nunca é sim
        return "sim" if palavras[0] in _INICIO_SIM and not set(palavras) & _INICIO_NAO else None
    return None


def frase_hora(agora: datetime) -> str:
    h, m = agora.hour, agora.minute
    horas = f"{h} hora" if h == 1 else f"{h} horas"
    abertura = "É" if h == 1 else "São"
    if m == 0:
        return f"{abertura} {horas} em ponto, senhor."
    minutos = f"{m} minuto" if m == 1 else f"{m} minutos"
    return f"{abertura} {horas} e {minutos}, senhor."


def descartar(texto: str) -> bool:
    frase = normalizar(texto)
    return len(frase) < 2 or frase in _ALUCINACOES
