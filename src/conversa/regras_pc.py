"""Regras locais do controle do PC: funções puras que valem mesmo com o modelo enganado (spec 2026-11-07-controle-do-pc).
Sem pipecat. O modelo só propõe; aqui o PC decide se uma URL, uma navegação ou um host pode ser usado."""
import re
import unicodedata

from src import config
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit


@dataclass(frozen=True)
class Decisao:
    tipo: str  # "ok", "perguntar", "recusar", "parar", "forte" (frase forte) ou "anunciar" (mídia escolhida por ele)
    motivo: str = ""
    valor: str = ""


@dataclass(frozen=True)
class Site:
    chave: str
    dominio: str
    leitura: bool = False  # site de leitura: link no mesmo host não passa pela lista sem volta


SITES: dict[str, Site] = {s.chave: s for s in (
    Site("netflix", "netflix.com"),
    Site("g1", "g1.globo.com", leitura=True),
    Site("github", "github.com"),
    Site("google", "www.google.com"),
    Site("youtube", "youtube.com"),
)}

# Moldes de URL com caminho, todos constantes; só eles fogem da regra "só a raiz do host".
MOLDES: dict[str, str] = {
    "github_estrelas": "https://github.com/search?q=stars%3A%3E1&s=stars&o=desc&type=repositories",
}

# Descrição curta de cada molde, para o modelo saber que existem (mesmas chaves de MOLDES).
DESCRICAO_MOLDES: dict[str, str] = {
    "github_estrelas": "repositórios com mais estrelas do GitHub",
}

# Moldes de busca por site (mesmas chaves de SITES); {q} só recebe palavras do usuário (o laço confere).
BUSCAS: dict[str, str] = {
    "netflix": "https://www.netflix.com/search?q={q}",
    "youtube": "https://www.youtube.com/results?search_query={q}",
    "google": "https://www.google.com/search?q={q}",
    "github": "https://github.com/search?q={q}&type=repositories",
    "g1": "https://g1.globo.com/busca/?q={q}",
}


def busca_de(url: str) -> tuple[str, str] | None:
    """(site, termo decodificado) se a URL for exatamente um molde de BUSCAS; qualquer desvio devolve None."""
    try:
        p = urlsplit(url.strip())
    except ValueError:
        return None
    if p.scheme != "https" or p.fragment:
        return None
    pares = parse_qsl(p.query, keep_blank_values=True)
    for chave, molde in BUSCAS.items():
        m = urlsplit(molde)
        if (p.netloc, p.path) != (m.netloc, m.path):
            continue
        fixos = dict(x.split("=", 1) for x in m.query.split("&"))
        campo = next(k for k, v in fixos.items() if v == "{q}")
        if sorted(k for k, _ in pares) != sorted(fixos):
            return None
        valores = dict(pares)
        if any(valores[k] != v for k, v in fixos.items() if k != campo):
            return None
        termo = valores[campo].strip()
        return (chave, termo) if termo else None
    return None


# Hosts de e-mail e o app WhatsApp: só se o pedido citar e-mail ou WhatsApp.
PESSOAIS: frozenset[str] = frozenset({"mail.google.com", "outlook.live.com", "outlook.office.com", "mail.yahoo.com",
                                      "whatsapp"})
_CITA_EMAIL = frozenset({"email", "emails", "gmail", "outlook"})
_CITA_WHATSAPP = frozenset({"whatsapp", "zap"})

# Sem "vai": "e depois vai dormir" não é destino.
_GATILHOS = frozenset({"abre", "abrir", "abra", "entra", "entrar", "entre", "ir", "site"})
PALAVRAS_COMUNS = frozenset({
    "o", "a", "os", "as", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das", "no", "na", "nos", "nas", "em",
    "pra", "pro", "para", "por", "pelo", "pela", "favor", "me", "mim", "meu", "minha", "meus", "minhas", "seu", "sua",
    "e", "ou", "que", "com", "sem", "pagina", "ai", "la", "ali", "aqui", "agora", "ja", "so", "isso", "esse", "essa",
    "este", "esta", "embora", "ver", "lo", "ele", "ela", "voce", "senhor", "jarvis", "groov", "hey", "ei", "aba", "janela",
    "navegador", "chrome", "google", "internet", "app", "aplicativo", "programa", "tambem", "depois", "entao",
    "email", "emails",
})

# Bloqueio: domínios (host igual ou subdomínio), nomes distintivos (trecho do host) e categorias (trecho do host).
BLOQUEIO_HOSTS = frozenset({
    "itau.com.br", "itau.com", "bradesco.com.br", "santander.com.br", "bb.com.br", "caixa.gov.br",
    "nubank.com.br", "bancointer.com.br", "inter.co", "c6bank.com.br", "xpi.com.br", "xp.com.br", "btgpactual.com",
    "rico.com.vc", "clear.com.br", "paypal.com", "mercadopago.com.br", "mercadopago.com", "picpay.com", "wise.com",
    "binance.com", "1password.com", "bitwarden.com", "lastpass.com", "passwords.google.com", "pay.google.com",
    "payments.google.com", "myaccount.google.com", "web.whatsapp.com",
})
_BLOQUEIO_NOMES = ("itau", "bradesco", "santander", "nubank", "bancointer", "c6bank", "btgpactual", "paypal",
                   "mercadopago", "picpay", "binance", "1password", "bitwarden", "lastpass")
_BLOQUEIO_CATEGORIAS = ("banco", "bank", "pix", "corretora", "invest", "wallet")  # errar para mais é o lado seguro
# No título, só nomes próprios (palavra inteira); "Caixa", "Inter", "Rico" sozinhos são palavras comuns.
_BLOQUEIO_TITULO = ("banco do brasil", "caixa economica", "c6",
                    "itau", "bradesco", "santander", "nubank", "banco inter", "xp investimentos",
                    "btg pactual", "rico investimentos", "clear corretora", "paypal", "mercado pago", "picpay",
                    "binance", "1password", "bitwarden", "lastpass")

_ROTULO = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
# TLD só de letras (ou punycode): mata IP em qualquer grafia (127.1, 192.168.0.10) e host sem ponto.
_HOST = re.compile(rf"(?:{_ROTULO}\.)+(?:[a-z]{{2,63}}|xn--[a-z0-9-]{{1,59}})")
_SUFIXOS_LOCAIS = (".localhost", ".local", ".lan", ".internal", ".intranet", ".home.arpa", ".localdomain")


def _palavras(texto: str) -> list[str]:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\be[\s-]+mail", "email", texto)
    return re.findall(r"[a-z0-9]+", texto)


def _citadas(pedido: str) -> set[str]:
    """Palavras do pedido mais pares colados, para o Whisper que separa ("Git Hub", "Net flix", "G 1")."""
    p = _palavras(pedido)
    return {*p, *(a + b for a, b in zip(p, p[1:]))}


def _casa(host: str, dominio: str) -> bool:
    return host == dominio or host.endswith("." + dominio)


def host_de(url: str) -> str | None:
    """Host em minúsculas, ou None se a URL não for http/https limpa para um host público com nome."""
    url = url.strip()
    if not url or "\\" in url or any(ord(c) <= 32 for c in url):
        return None
    if "://" not in url:
        url = "https://" + url  # a barra do Chrome costuma mostrar o endereço sem esquema
    try:
        partes = urlsplit(url)
    except ValueError:
        return None
    host = partes.netloc.lower()
    if partes.scheme.lower() not in ("http", "https") or "@" in host or ":" in host or "[" in host:
        return None
    if not _HOST.fullmatch(host) or host.endswith(_SUFIXOS_LOCAIS):
        return None
    return host


def _pessoal(host: str) -> bool:
    return any(_casa(host, p) for p in PESSOAIS)


def cita_pessoal(alvo: str, pedido: str) -> bool:
    """O pedido cita o pessoal em questão: WhatsApp para o app, e-mail para os hosts de e-mail."""
    citadas = _citadas(pedido)
    return bool(citadas & (_CITA_WHATSAPP if alvo == "whatsapp" else _CITA_EMAIL))


def _destinos(pedido: str, sites: dict[str, Site]) -> set[str]:
    """Palavras citadas como destino: a primeira palavra incomum depois de abre/entra/site. Chave da tabela, sozinha
    ou colada à seguinte ("git hub"), não vale: o site dela já decide, e g1.com.br ou git.com.br não são o site."""
    p = _palavras(pedido)
    achadas = set()
    for i, palavra in enumerate(p):
        if palavra in _GATILHOS:
            j = next((j for j in range(i + 1, len(p)) if p[j] not in PALAVRAS_COMUNS and p[j] not in _GATILHOS), None)
            if j is not None and p[j] not in sites and "".join(p[j:j + 2]) not in sites:
                achadas.add(p[j])
    return achadas


_DOMINIO_DITO = re.compile(r"(?<![a-z0-9.-])((?:[a-z0-9-]+\.)+[a-z]{2,})(?![a-z0-9-])")
_SUFIXOS_GENERICOS = frozenset({"com", "org", "net", "gov", "edu", "co"})  # "com.br" sozinho não é um site


def _cita_dominio(host: str, pedido: str) -> bool:
    """O usuário disse o domínio ("globo.com", "www.globo.com"): vale ele, com ou sem www., e os subdomínios dele."""
    nu = host.removeprefix("www.")
    for d in _DOMINIO_DITO.findall(pedido.lower()):
        d = d.removeprefix("www.")
        if d.count(".") == 1 and d.split(".")[0] in _SUFIXOS_GENERICOS:
            continue
        if _casa(nu, d):
            return True
    return False


def _avaliar_host(host: str | None, pedido: str, alcancados: frozenset[str], sites: dict[str, Site],
                  extras: frozenset[str] = frozenset()) -> Decisao:
    if host is None:
        return Decisao("recusar", "endereço inválido")
    if bloqueado(host, "", extras):
        return Decisao("parar", "site bloqueado")
    if _pessoal(host):
        # alcançado não vale aqui: chegar num e-mail sem o pedido citar é sinal de engano
        return Decisao("ok") if cita_pessoal(host, pedido) else Decisao("recusar", "pessoal não citado")
    citadas = _citadas(pedido)
    if host in alcancados or any(s.chave in citadas and _casa(host, s.dominio) for s in sites.values()):
        return Decisao("ok")
    if _cita_dominio(host, pedido):  # 11/11: "abre o globo.com" parou em www.globo.com
        return Decisao("ok")
    nu = host.removeprefix("www.")  # 11/11: "abre o globo.com" e o modelo escreve www.globo.com
    if any(nu in (f"{p}.com", f"{p}.com.br") for p in _destinos(pedido, sites)):
        return Decisao("ok")
    return Decisao("perguntar", "host não citado", host)


def avaliar_url(url: str, pedido: str, alcancados: frozenset[str], sites: dict[str, Site] = SITES,
                extras: frozenset[str] = frozenset()) -> Decisao:
    """Decide `abrir_site(url)`: só a raiz do host, ou um molde constante, e só para host citado, alcançado ou aprovado."""
    host = host_de(url)
    if host is not None and url.strip() not in MOLDES.values():
        partes = urlsplit(url.strip() if "://" in url else "https://" + url.strip())
        if partes.path not in ("", "/") or partes.query or partes.fragment:
            return Decisao("recusar", "caminho fora de molde")
    return _avaliar_host(host, pedido, alcancados, sites, extras)


def avaliar_navegacao(host_novo: str, pedido: str, alcancados: frozenset[str],
                      extras: frozenset[str] = frozenset()) -> Decisao:
    """Decide o host em que um clique caiu (o PC relê o endereço depois de cada ação no Chrome). 11/11: navegar para outro host
    é livre; só bloqueado, login e pessoal não citado (e-mail, WhatsApp) param."""
    host = host_de(host_novo)
    if host is None:
        return Decisao("parar", "endereço ilegível")  # a navegação já aconteceu: recusar não desfaz nada
    if bloqueado(host, "", extras) or _login(host):
        return Decisao("parar", "site bloqueado")
    if _pessoal(host) and not cita_pessoal(host, pedido):
        return Decisao("recusar", "pessoal não citado")
    return Decisao("ok")


def bloqueado(host: str | None, titulo: str, extras: frozenset[str] = frozenset()) -> bool:
    """Banco, corretora, pagamento e senhas: base versionada mais os extras de privado/. Título só por nome próprio,
    e nunca em host da tabela de sites, onde o host já decide (manchete "Caixa paga..." no G1 não bloqueia)."""
    if host:
        host = host.lower()
        if any(_casa(host, d) for d in BLOQUEIO_HOSTS | extras):
            return True
        if any(t in host for t in _BLOQUEIO_NOMES + _BLOQUEIO_CATEGORIAS):
            return True
        if any(_casa(host, s.dominio) for s in SITES.values()):
            return False
    frase = f" {' '.join(_palavras(titulo))} "
    return any(f" {nome} " in frase for nome in _BLOQUEIO_TITULO)


def carregar_extras(caminho: Path) -> frozenset[str]:
    """Hosts extras de bloqueio, um por linha (# comenta). Ausente ou ilegível: vazio, e a base continua valendo."""
    try:
        linhas = caminho.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return frozenset()
    limpas = (linha.strip().lower() for linha in linhas)
    return frozenset(host_de(linha) or linha for linha in limpas if linha and not linha.startswith("#"))


# --- Classificação sem volta, campos e mídia (Task 2) ---

@dataclass(frozen=True)
class Elemento:
    id: int
    nome: str
    tipo: str  # ControlType da UIA, sem prefixo: Button, Hyperlink, Edit, ComboBox, ListItem...
    papel: str = ""  # papel ARIA (searchbox...)
    texto_interno: str = ""
    ancestrais: tuple[str, ...] = ()  # nomes dos ancestrais até o Document ou a janela
    senha: bool = False  # IsPassword da UIA
    runtime_id: str = ""
    host_do_link: str | None = None


def _ar(radical: str, radical_e: str = "") -> tuple[str, ...]:
    """Formas de um verbo regular em -ar; `radical_e` para pagu-e, publiqu-e, apagu-e."""
    e = radical_e or radical
    return (*(radical + s for s in ("ar", "a", "o", "as", "am", "ou", "ando", "ado", "ada")),
            *(e + s for s in ("e", "es", "em", "ei")))


# Botões que mudam a conta (prova 5, Spotify: "Salvar X na Sua Biblioteca", "Seguir X"). Decisão provisória
# (a revisar): sem "curta", "curtida(s)" e "curtido", que são "Curta-metragem" e "Músicas Curtidas".
_SOCIAIS = (*_ar("salv"), "seguir", "siga", "segue", "sigo", "seguiu", "seguindo", "curtir", "curte", "curti", "curtiu",
            "save", "follow", "following", "unfollow", "like", "likes", "unlike")
FAMILIAS: dict[str, tuple[str, ...]] = {
    "enviar": (*_ar("envi"), "envios", *_ar("mand"), *_ar("encaminh"),
               "responder", "responda", "responde", "respondo", "respondeu", "respondido",
               "send", "sends", "sent", "reply", "replies", "forward", "submit"),
    "dinheiro": (*_ar("compr"), "compras", *_ar("pag", "pagu"), "pagamento", "pagamentos", *_ar("assin"), "assinatura",
                 "transferir", "transfere", "transfira", "transferiu", "transferido", "transferencia",
                 "pix", "dinheiro", "money",  # "Enviar Pix" no app WhatsApp, que o bloqueio de host não cobre
                 "finalizar compra", "buy", "pay", "payment", "place order", "checkout", "check out", "purchase",
                 "subscribe", "subscription", "transfer"),
    "destruir": (*_ar("apag", "apagu"), *_ar("delet"), "excluir", "exclua", "exclui", "excluido", "exclusao",
                 "remover", "remova", "remove", "removido", "remocao", "cancelar plano", "cancelar assinatura",
                 "cancelamento", *_ar("desinstal"), "delete", "uninstall", "cancel plan", "cancel membership",
                 "cancel subscription"),
    "publicar": (*_ar("public", "publiqu"), *_ar("post"), *_ar("compartilh"), *_ar("instal"),
                 "adicionar extensao", "adicionar ao chrome", "publish", "post", "share", "install", "add to chrome"),
    "estado": ("tornar publico", "tornar publica", "change visibility", "make public", "change to public",
               "alterar senha", "alterar email", "mudar senha", "change password", "change email", *_SOCIAIS,
               "adicionar a playlist", "adicionar a musicas curtidas", "add to playlist"),
}
# Consentimento genérico vale só como rótulo inteiro: "Continuar assistindo" é outro rótulo.
_CONSENTIMENTO = frozenset({"permitir", "permita", "permite", "permito", *_ar("autoriz"), *_ar("confirm"),
                            *_ar("aceit"), "sim", "ok", "okay", "allow", "authorize", "confirm",
                            "yes", "accept", "agree", "concordo"})
_COMPLEMENTO_CONSENTIMENTO = frozenset({"todos", "todas", "tudo", "all", "sempre", "always", "e", "and", "os", "cookies"})
FAMILIAS["consentimento"] = tuple(sorted(_CONSENTIMENTO))
# 11/11, a pedido do usuário, retirados por serem regras de PRECISÃO que travavam pedido bom: "continuar" como consentimento;
# a escolha do item de mídia pelo nome (decidir_midia e o laço que a usava); a pergunta de `www.` e a parada ao navegar para
# outro host; `texto_permitido` (o modelo pode digitar texto que ele não ditou); "abriu janela nova" como parada.
# Ficam as de SEGURANÇA: bloqueio, login e senha, pessoal só se citado, cliques sem volta, janelas proibidas, confirmação forte.

# Valores provisórios do "Resultado das provas" (07/11), decisão provisória (a revisar); Netflix logada pendente.
# Controles de navegação isentos da comparação com o pedido e do consentimento genérico, por origem. O play do
# título já casado ("Tocar <nome>" no Spotify; nome do botão da Netflix pendente) é isento pelo laço, não aqui.
ISENTOS: dict[str, tuple[str, ...]] = {
    "netflix": (),  # + o perfil de GROOV_PERFIL_NETFLIX (isentos())
    "spotify": ("Buscar", "O que você quer ouvir?"),
}


def isentos(origem: str | None) -> tuple[str, ...]:
    fixos = ISENTOS.get(origem or "", ())
    perfil = config.valor("GROOV_PERFIL_NETFLIX").strip() if origem == "netflix" else ""
    return fixos + (perfil,) if perfil else fixos
# Nome real do campo de busca por app, quando ele não diz busca, pesquisa ou search (prova 5: ComboBox do Spotify).
CAMPOS_BUSCA: dict[str, tuple[str, ...]] = {
    "spotify": ("O que você quer ouvir?",),
}
# "ControlType/LocalizedControlType" de cartão e faixa por origem; só o tipo quando o texto não foi medido.
ITENS_DE_MIDIA: dict[str, tuple[str, ...]] = {
    "spotify": ("DataItem/linha", "DataItem/item"),
    "netflix": ("Hyperlink",),  # sonda antiga: cartão é link com o nome do título
}
# Caminho do player por origem: fora dele o play não vale (prova da Netflix 08/11: a prévia do modal /browse?jbv= toca).
PLAYER: dict[str, str] = {"netflix": "watch"}  # segmento do caminho; aceita país antes ("/br/watch/81")
# Razão do difflib sem acento e pontuação: "zora no kanta" 0,89 passa, "Sora no Kanata Rising" 0,80 pergunta.
# O nome antes do subtítulo (":", " - ", "(") também conta (casa_alvo); duas temporadas na tela continuam perguntando.
LIMIAR_ALVO: float = 0.85

VERBOS_MIDIA = ("bota", "botar", "coloca", "põe", "toca", "tocar", "assistir", "ouvir")
# Formas faladas além da lista literal do spec, para o pedido de mídia e o corte do título.
_VERBOS_MIDIA_FALADOS = frozenset({*_palavras(" ".join(VERBOS_MIDIA)), "coloque", "toque", "bote", "assiste",
                                   "assista", "ouve", "ouca", "escuta", "escutar", "play", "reproduz", "reproduzir"})
# Apps com regras próprias de mídia (11/11: abrir app não depende mais disto). Sem "whatsapp": a UIA só vê a moldura do app
# (prova 5, WebView2 sem filhos). Decisão provisória (a revisar, repetindo a prova com o WhatsApp aberto na hora no monitor 1).
APPS = ("spotify",)
# Teclas que o laço pode apertar (nome → VK). Sem alt/ctrl/win: nada de fechar, trocar de app nem colar. Sem enter e tab
# (revisão 14/11): enter depois de digitar manda a mensagem e tab+enter aperta o botão focado, sem passar pelas regras do
# clique nem pela frase forte. A sonda repete a tabela.
ORIGENS_DE_PLAYER = ("netflix", "youtube", "spotify")  # onde clicar num ponto sem texto (o vídeo) faz sentido
TECLAS: dict[str, int] = {
    "espaco": 0x20, "esc": 0x1B, "cima": 0x26, "baixo": 0x28, "esquerda": 0x25,
    "direita": 0x27, "pagina_cima": 0x21, "pagina_baixo": 0x22, "k": 0x4B, "j": 0x4A, "l": 0x4C, "f": 0x46, "m": 0x4D,
    "play_pause": 0xB3, "proxima": 0xB0, "anterior": 0xB1, "volume_mais": 0xAF, "volume_menos": 0xAE, "mudo": 0xAD,
}

_BUSCA = ("busca", "buscar", "pesquis", "procur", "search")  # prefixos de palavra
_NAO_BUSCA = ("mensag", "comentar", "comentario", "respost", "message", "reply", "comment")
_SENSIVEIS = ("senha", "password", "pin", "cvv", "cvc", "cpf", "cnpj", "rg", "cartao", "card", "documento",
              "codigo", "code", "token", "otp", "validade", "expiry", "security code", "passcode")
_LOGIN = ("accounts.", "login.", "signin.", "auth.", "sso.")
# Palavras que separam o título no pedido ("bota X na netflix e depois bota um timer"): verbos e o timer.
_TIMER = frozenset({"timer", "timers", "taimer", "taimers", "taymer", "tymer", "temporizador"})  # com o Whisper
_SEPARADORES = frozenset({*_VERBOS_MIDIA_FALADOS, *_GATILHOS, *_TIMER, "le", "ler", "leia", "mostre", "mostra",
                          "mostrar", "quero"})
_ENCHIMENTO_ALVO = PALAVRAS_COMUNS | {"eu", "mais", "hoje"}
# Pedido que descreve em vez de nomear: ele escolhe e anuncia.
_DESCRITORES = frozenset({"musica", "musicas", "cancao", "som", "algo", "alguma", "algum", "coisa", "reportagem",
                          "noticia", "materia", "repositorio", "filme", "serie", "video", "episodio", "playlist",
                          "album", "podcast", "anime", "desenho", "documentario"})


def _frase(texto: str) -> str:
    return f" {' '.join(_palavras(texto))} "


def _tem(texto: str, formas) -> bool:
    frase = _frase(texto)
    return any(_frase(f) in frase for f in formas)


def _familias(texto: str) -> set[str]:
    """Todas as famílias sem volta do texto, por palavra inteira sem acento; consentimento só como rótulo inteiro."""
    achadas = {nome for nome, formas in FAMILIAS.items() if nome != "consentimento" and _tem(texto, formas)}
    p = set(_palavras(texto))
    if p & _CONSENTIMENTO and p <= _CONSENTIMENTO | _COMPLEMENTO_CONSENTIMENTO:
        achadas.add("consentimento")
    return achadas


def familia(texto: str) -> str | None:
    """Uma família do texto; enviar só se for a única ("Enviar pagamento" é dinheiro)."""
    achadas = _familias(texto)
    return next((f for f in FAMILIAS if f in achadas and f != "enviar"), "enviar" if achadas else None)


def _login(host: str | None) -> bool:
    # shortcut: só olha o host, "/authorize" no caminho fica de fora porque Elemento não traz o caminho do link
    return bool(host) and (host.startswith(_LOGIN) or "oauth" in host or "authorize" in host)


def _isento(nome: str, origem: str | None) -> bool:
    return _frase(nome) in {_frase(i) for i in isentos(origem)}


_CAMINHOS_LOGIN = frozenset({"login", "signin", "sign-in", "logon", "entrar", "auth", "oauth", "authorize", "sso"})


def pagina_de_login(endereco: str | None, elementos) -> bool:
    """Página de login ou com campo de senha: o laço para. Prova 5: `netflix.com/br/login` está em host permitido e
    a regra de host de login não pegava."""
    if any(e.senha or (e.tipo == "Edit" and _tem(e.nome, ("senha", "password"))) for e in elementos):
        return True
    if not endereco:
        return False
    partes = urlsplit(endereco.strip() if "://" in endereco else "https://" + endereco.strip())
    return _login(partes.hostname) or any(seg in _CAMINHOS_LOGIN or seg.startswith(("login", "signin"))
                                          for seg in partes.path.lower().split("/"))


def classificar_clique(el: Elemento, host: str | None, pedido: str, origem: str | None) -> Decisao:
    """Decide um clique só no PC: `ok`, `forte` (só enviar, com forma de enviar no pedido) ou `parar`."""
    if _login(host) or _login(el.host_do_link):
        return Decisao("parar", "login")
    site = SITES.get(origem or "")
    if site and site.leitura and host and el.host_do_link and _casa(host, site.dominio) \
            and _casa(el.host_do_link, site.dominio):
        return Decisao("ok")  # manchete "Caixa paga..." no G1 não para a cena
    familias = set().union(*(_familias(t) for t in (el.nome, el.texto_interno, *el.ancestrais)))
    if _isento(el.nome, origem):
        familias.discard("consentimento")
    if not familias:
        return Decisao("ok")
    if familias == {"enviar"} and _tem(pedido, FAMILIAS["enviar"]):
        return Decisao("forte")
    return Decisao("parar", "sem volta: " + ", ".join(sorted(familias)))


def tecla_permitida(tecla: str) -> bool:
    return tecla in TECLAS


def alvo_visual(rotulo: str, descricao: str, host: str | None, pedido: str, origem: str | None, midia: bool) -> Decisao:
    """Clique achado pela visão (OCR ou Claude): as mesmas regras do clique pela árvore, com o rótulo lido E a descrição
    pedida como nomes. Sem rótulo (ícone, vídeo) só vale em pedido de mídia dentro de um player; senão não há o que conferir.
    `midia` vem do laço (pedido_de_midia com o site herdado, nunca com o app aberto)."""
    if not rotulo.strip() and not (midia and origem in ORIGENS_DE_PLAYER):
        return Decisao("parar", "alvo sem nome")
    nomes = [n.strip() for n in (rotulo, descricao) if n.strip()]
    decisoes = [classificar_clique(Elemento(id=-1, nome=n, tipo="Button"), host, pedido, origem) for n in nomes]
    return next((d for d in decisoes if d.tipo == "parar"), None) or next((d for d in decisoes if d.tipo == "forte"),
                                                                          Decisao("ok"))


def e_campo_sensivel(el: Elemento) -> bool:
    return el.senha or _tem(el.nome, _SENSIVEIS)


_JANELA_LOGIN = ("login", "log in", "entrar", "sign in", "signin", "senha", "password")
EDITORES_DE_TEXTO = frozenset({"notepad", "notepad++", "wordpad"})  # processos de editor de texto puro (nunca o Chrome: "Rich text editor" de página de login)
_NOMES_EDITOR = ("editor de texto", "text editor")  # nome do campo do Bloco de Notas (medido 11/11)


def e_nome_de_editor(nome: str) -> bool:
    return _frase(nome) in {_frase(n) for n in _NOMES_EDITOR}
_CAMPO_USUARIO = ("usuario", "user", "username", "email", "e-mail", "e mail")


def janela_de_login(titulo: str, texto: str) -> bool:
    """Janela de app que pede login: título ou o começo do texto visível. Nela, todo campo de texto é sensível."""
    return _tem(f"{titulo} {texto[:500]}", _JANELA_LOGIN)


def digitacao_bloqueada(el: Elemento, titulo: str, texto: str, processo: str = "") -> bool:
    """Não escrever em campo sensível, nem em qualquer campo de uma janela de login que não seja claramente usuário/e-mail."""
    if e_campo_sensivel(el):
        return True
    if processo in EDITORES_DE_TEXTO and e_nome_de_editor(el.nome):  # o título do Bloco de Notas é o nome do arquivo ("senha.txt"): editor de texto nunca é janela de login
        return False
    return janela_de_login(titulo, texto) and not _tem(el.nome, _CAMPO_USUARIO)


def e_campo_de_busca(el: Elemento, origem: str | None) -> bool:
    if el.tipo not in ("Edit", "ComboBox") or e_campo_sensivel(el):
        return False
    palavras = _palavras(el.nome)
    if any(p.startswith(_NAO_BUSCA) for p in palavras) or any(familia(t) for t in (el.nome, *el.ancestrais)):
        return False
    return (el.papel.lower() == "searchbox" or any(p.startswith(_BUSCA) for p in palavras)
            or _frase(el.nome) in {_frase(n) for n in CAMPOS_BUSCA.get(origem or "", ())})


# Outros navegadores: o laço não os abre nem age neles (as regras de host, login e bloqueio de sites só valem no Chrome).
NAVEGADORES_RECUSADOS = frozenset({"msedge", "edge", "microsoftedge", "firefox", "mozillafirefox", "opera", "operagx", "brave",
                                   "bravebrowser", "vivaldi", "iexplore", "internetexplorer", "safari", "tor", "torbrowser"})
PROCESSOS_NAVEGADOR = ("msedge", "firefox", "opera", "brave", "vivaldi", "iexplore", "safari", "tor")  # nomes de processo
FRASE_SO_CHROME = "no navegador eu só uso o Chrome"


def e_outro_navegador(nome: str) -> bool:
    return "".join(_palavras(nome)) in NAVEGADORES_RECUSADOS


def apps_citados(pedido: str) -> frozenset[str]:
    """Só os apps com regras próprias (APPS): para mídia e timer. Qualquer outro app: `nome_de_app_citado`."""
    return frozenset(a for a in APPS if a in _citadas(pedido))


def nome_de_app_citado(nome: str, pedido: str) -> bool:
    """O nome do app está na fala do usuário (palavras inteiras, sem acento; "bloco de notas", "visual studio code")."""
    palavras = _palavras(nome)
    return (len("".join(palavras)) >= 2 and not set(palavras) <= PALAVRAS_COMUNS
            and (_frase(nome) in _frase(pedido) or "".join(palavras) in _citadas(pedido)))


def cita_destino(texto: str) -> bool:
    """O pedido cita app da lista ou site (da tabela ou "abre X"): quem arma o timer é o laço, no fim."""
    return bool(apps_citados(texto) or set(SITES) & _citadas(texto) or _destinos(texto, SITES))


def pedido_de_midia(pedido: str, origem: str | None = None) -> bool:
    """`origem`: site ou app herdado da continuação, que conta como citado."""
    citadas = _citadas(pedido)
    origem_citada = bool(origem) or bool(apps_citados(pedido)) or any(chave in citadas for chave in SITES)
    return origem_citada and bool(set(_palavras(pedido)) & (_VERBOS_MIDIA_FALADOS | _COISAS_DE_TOCAR))


# 14/11: "…, música no YouTube" veio sem verbo (transcrição ruim) e não contou como mídia. "vídeo(s)" fica de fora: "pesquisa
# vídeos de X" pede a lista, não o play.
_COISAS_DE_TOCAR = frozenset({"musica", "musicas", "clipe", "playlist", "episodio", "filme", "serie"})


def _fora_do_alvo(palavra: str, origem: str = "") -> bool:
    return palavra in SITES or palavra in APPS or palavra == origem


def alvo_nomeado(pedido: str, origem: str) -> str | None:
    """O primeiro trecho do pedido entre verbos, site e app, sem enchimento nas pontas; None se só descreve."""
    trechos, atual = [], []
    for p in _palavras(pedido):
        if p in _SEPARADORES or _fora_do_alvo(p, origem):
            trechos.append(atual)
            atual = []
        else:
            atual.append(p)
    trechos.append(atual)
    for t in trechos:
        while t and t[0] in _ENCHIMENTO_ALVO:
            t = t[1:]
        while t and t[-1] in _ENCHIMENTO_ALVO:
            t = t[:-1]
        if t:
            return None if t[0] in _DESCRITORES else " ".join(t)
    return None


_SUBTITULO = re.compile(r":|\s[-–—]\s|\(")


def casa_alvo(nome: str, pedido: str) -> float:
    """Semelhança de 0 a 1 entre o nome e o título que o pedido nomeia; 0 se o pedido não nomeia. Vale a melhor entre
    o nome inteiro e o nome antes do subtítulo: "Sora no Kanata: The Fighting!" casa "Sora no Kanata" (0,68 inteiro)."""
    alvo = alvo_nomeado(pedido, "")
    if not alvo:
        return 0.0
    return max(SequenceMatcher(None, " ".join(_palavras(n)), alvo).ratio() for n in (nome, _SUBTITULO.split(nome, 1)[0]))


def _citados_sem_alvo(pedido: str) -> set[str]:
    """O que o pedido cita além de verbo, site e descrição ("kalue" em "uma música do Kaluê"), antes do timer
    ("hora" de "timer de uma hora" não escolhe "Hora de Aventura")."""
    palavras = _palavras(pedido)
    palavras = palavras[:next((i for i, p in enumerate(palavras) if p in _TIMER), len(palavras))]
    return {p for p in palavras
            if p not in _ENCHIMENTO_ALVO | _SEPARADORES | _DESCRITORES and not _fora_do_alvo(p)}


# --- Texto digitado (buscar, digitar) e fala do modelo (perguntar, desistir, responder) ---
_SEGREDOS = frozenset({"senha", "senhas", "codigo", "codigos", "token", "tokens", "pin", "pins", "cpf", "cartao",
                       "cartoes", "pix", "password", "passwords", "passcode", "code", "codes", "card", "cards", "otp",
                       "cvv", "cvc"})
_PODE = frozenset({"pode", "posso", "podemos", "can"})
# Enchimento depois de "pode" que não muda o pedido: "pode confirmar agora, senhor?" ainda é só consentimento.
_ENCHIMENTO_PODE = frozenset({"agora", "ja", "senhor", "por", "favor", "gentileza", "please", "now", "sir", "you"})
_CPF = re.compile(r"\b\d{3}[.\s-]?\d{3}[.\s-]?\d{3}[.\s/-]?\d{2}\b")
_CORRIDA_CARTAO = re.compile(r"\d(?:[ -]?\d){12,}")


def _distancia(a: str, b: str) -> int:
    linha = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        anterior, linha[0] = linha[0], i
        for j, cb in enumerate(b, 1):
            anterior, linha[j] = linha[j], min(linha[j] + 1, linha[j - 1] + 1, anterior + (ca != cb))
    return linha[-1]


def _tolerancia(palavra: str) -> int:
    # Fora do spec (≤ 1 até 5 letras): palavra de 1-2 letras ou com dígito é exata, senão "4 8 2 9" passaria por "o".
    if len(palavra) <= 2 or any(c.isdigit() for c in palavra):
        return 0
    return 1 if len(palavra) <= 5 else 2


def _casa_palavra(a: str, b: str) -> bool:
    """Igual ou com a folga de `_tolerancia`: o Whisper ouve "Kalui" e o Spotify toca "Kaluê"."""
    return a == b or _distancia(a, b) <= min(_tolerancia(a), _tolerancia(b))


def casa_alguma(citados, palavras) -> bool:
    return any(_casa_palavra(a, b) for a in citados for b in palavras)


def _luhn(digitos: str) -> bool:
    soma = sum(d if i % 2 == 0 else (d * 2 - 9 if d > 4 else d * 2) for i, d in enumerate(map(int, reversed(digitos))))
    return soma % 10 == 0


def _formato_sensivel(texto: str) -> bool:
    """CPF, cartão válido por Luhn ou 6+ dígitos seguidos."""
    if _CPF.search(texto) or re.search(r"\d{6,}", texto):
        return True
    for corrida in _CORRIDA_CARTAO.findall(texto):
        d = re.sub(r"\D", "", corrida)
        if any(_luhn(d[i:i + n]) for n in range(13, 20) for i in range(len(d) - n + 1)):
            return True
    return False


def _pede_segredo_ou_imita_confirmacao(texto: str) -> bool:
    p = _palavras(texto)
    if set(p) & _SEGREDOS or _tem(texto, ("para confirmar", "pra confirmar", "to confirm")):
        return True
    # depois de "pode", até o fim da oração: família sem volta em qualquer palavra; consentimento só se for o resto todo
    # ("posso continuar procurando?" passa, "posso confirmar agora?" não)
    for oracao in re.split(r"[.?!;\n]+", texto):
        o = [w for w in _palavras(oracao) if w not in _SOCIAIS]  # "Posso seguir procurando?" é pergunta comum
        for i, w in enumerate(o):
            if w in _PODE:
                resto = " ".join(x for x in o[i + 1:] if x not in _ENCHIMENTO_PODE)
                if _familias(resto) or _familias(" ".join(o[i + 1:])) - {"consentimento"}:
                    return True
    return False


_DADO_TECNICO = frozenset({"id", "link", "url", "endereco", "codigo"})


def pede_dado_tecnico(texto: str) -> bool:
    """A pergunta pede ao usuário um id, link, URL, endereço ou código: ele não sabe, o modelo deve achar sozinho."""
    return bool(set(_palavras(texto)) & _DADO_TECNICO)


def fala_permitida(texto: str, tipo: str) -> bool:
    """`responder` recusa por formato (notícia sobre Pix passa); `perguntar` e `desistir` também por palavra."""
    if tipo not in {"perguntar", "desistir", "responder"} or _formato_sensivel(texto):
        return False
    return tipo == "responder" or not _pede_segredo_ou_imita_confirmacao(texto)


# ---- Timers: lidos só da transcrição do usuário, nunca do modelo ----

@dataclass(frozen=True)
class PedidoTimer:
    minutos: int | None  # None: sem número claro, quem chama pergunta ou avisa
    desligar: bool
    ambiguo: bool  # "desligar" perto de timer sem casar a forma: perguntar, nunca armar calado


_DESLIGAR = frozenset({"desligar", "desliga", "desligue", "desligamento", "desligando"})
_LIGA_DESLIGAR = frozenset({"de", "para", "pra", "pro"})
_NEGACAO = frozenset({"nao", "nem", "nunca", "sem"})
_PERTO = 3  # palavras em volta do timer
_PC = (("o", "pc"), ("o", "computador"), ("pc",), ("computador",))
_ARTIGOS = frozenset({"o", "a", "os", "as"})
_DURACAO = frozenset({"de", "em", "por", "daqui", "dentro", "apos", "durante", "com"})
_FIM_DE_FRASE = frozenset({"e", "senhor", "jarvis", "groov", "ai", "agora", "favor"})
_UNIDADES = {"minuto": 1, "minutos": 1, "min": 1, "hora": 60, "horas": 60, "h": 60}
_NUMEROS = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7,
    "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
    "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20, "trinta": 30,
    "quarenta": 40, "cinquenta": 50, "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90, "cem": 100,
}


def _numero(p: list[str], i: int) -> tuple[int, int] | None:
    """(valor, palavras usadas) em p[i]: dígitos ou extenso até "noventa e nove"."""
    if i >= len(p):
        return None
    if p[i].isdigit():
        return int(p[i]), 1
    if p[i] not in _NUMEROS:
        return None
    valor = _NUMEROS[p[i]]
    if valor in range(20, 100, 10) and i + 2 < len(p) and p[i + 1] == "e" and _NUMEROS.get(p[i + 2], 10) < 10:
        return valor + _NUMEROS[p[i + 2]], 3
    return valor, 1


def _duracoes(p: list[str]) -> list[tuple[int, int, int]]:
    """(minutos, índice do início, índice logo depois) de cada duração com unidade: "uma hora e meia", "meia hora",
    "1 hora e 15 minutos", "45 minutos"."""
    achadas, i = [], 0
    while i < len(p):
        if p[i] == "meia" and i + 1 < len(p) and p[i + 1] == "hora":
            achadas.append((30, i, i + 2))
            i += 2
            continue
        n = _numero(p, i)
        if n is None or i + n[1] >= len(p) or p[i + n[1]] not in _UNIDADES:
            i += 1
            continue
        k = i + n[1] + 1
        total = n[0] * _UNIDADES[p[k - 1]]
        if _UNIDADES[p[k - 1]] == 60 and k + 1 < len(p) and p[k] == "e":
            if p[k + 1] == "meia":
                total, k = total + 30, k + 2
            elif (resto := _numero(p, k + 1)) is not None:
                total, k = total + resto[0], k + 1 + resto[1]
                if k < len(p) and _UNIDADES.get(p[k]) == 1:  # "e 15 minutos" é a mesma duração
                    k += 1
        achadas.append((total, i, k))
        i = k
    return achadas


def _depois_do_pc(p: list[str], k: int) -> int:
    for pc in _PC:
        if tuple(p[k:k + len(pc)]) == pc:
            return k + len(pc)
    return k


def _outro_objeto(p: list[str], k: int) -> bool:
    """Em p[k] começa um objeto de "desligar" que não é o PC ("o forno")."""
    return k < len(p) and p[k] in _ARTIGOS and _depois_do_pc(p, k) == k


def ler_timer(transcricao: str) -> PedidoTimer | None:
    """Timer pedido na transcrição. "timer de/para/pra desligar" seguido só de fim de frase, duração ou "o PC" desliga
    o PC; outro objeto ("o forno") é timer simples; negação até 3 palavras antes anula. Negação logo depois, duas
    durações ou dois timers ("de uma hora, não, de duas") viram ambíguo: perguntar, nunca armar."""
    p = re.sub(r"(\d)([a-z])", r"\1 \2", " ".join(_palavras(transcricao))).split()  # "30min", "1h"
    # "time de desligar": erro do Whisper; só antes de de/para/pra + desligar, senão "meu time" viraria timer
    p = ["timer" if w == "time" and p[j + 1:j + 2] and p[j + 1] in _LIGA_DESLIGAR and p[j + 2:j + 3]
         and p[j + 2] in _DESLIGAR else w for j, w in enumerate(p)]
    timers = [j for j, w in enumerate(p) if w in _TIMER]
    if not timers or _NEGACAO & set(p[max(0, timers[0] - _PERTO):timers[0]]):
        return None
    i = timers[0]
    duracoes = _duracoes(p[i + 1:])
    minutos = (duracoes[0][0] or None) if duracoes else None
    fim = i + 1 + (duracoes[0][2] if duracoes else 0)
    # "timer de desligar de uma hora" ou, com a duração colada ao timer, "timer de uma hora pra desligar"
    colada = bool(duracoes) and all(w in _DURACAO for w in p[i + 1:i + 1 + duracoes[0][1]])
    liga = next((j for j in (i + 1, fim if colada else i + 1)
                 if j + 1 < len(p) and p[j] in _LIGA_DESLIGAR and p[j + 1] in _DESLIGAR), None)
    if liga is not None:
        k = _depois_do_pc(p, liga + 2)
        resto = p[k:]
        if not resto or resto[0] in _DURACAO | _FIM_DE_FRASE | _NEGACAO or _numero(p, k) is not None:
            desligar = True
        elif _outro_objeto(p, k):  # "desligar o forno": o objeto não é o PC
            desligar, k = False, k + 2
        else:
            return PedidoTimer(None, False, True)
        fim = max(fim, k)
    elif _DESLIGAR & set(p[max(0, i - _PERTO):i + _PERTO + 1] + p[fim:fim + _PERTO]):  # perto do timer ou da duração
        return PedidoTimer(None, False, True)
    else:
        desligar = False
    if len(timers) > 1 or len(duracoes) > 1 or _NEGACAO & set(p[i + 1:fim + _PERTO]):
        return PedidoTimer(None, desligar or (len(timers) > 1 and bool(_DESLIGAR & set(p[timers[1]:]))), True)
    return PedidoTimer(minutos, desligar, False)


_CANCELA_AMBOS = ("os dois", "as duas", "todos", "todas", "ambos", "timers", "temporizadores")


def cita_desligar(transcricao: str) -> bool:
    """Cita desligar, PC ou computador: o cancelamento roda `shutdown /a` sempre, mesmo sem registro."""
    p = _palavras(transcricao)
    return bool(_objetos_desligar(p) or {"pc", "computador"} & set(p))


def _objetos_desligar(p: list[str]) -> list[int]:
    """Índices depois de cada "desligar" que é o assunto; "desliga o timer" é só o verbo sobre o timer."""
    return [j + 1 for j, w in enumerate(p) if w in _DESLIGAR and not _TIMER & set(p[j + 1:j + 3])]


def qual_timer(transcricao: str) -> str | None:
    """Que timer um pedido de cancelar cita: "ambos", "desligar" (desligar, PC ou computador), "simples" (só
    desligar outro objeto, "o forno", pela regra de `ler_timer`) ou None (não disse)."""
    if _tem(transcricao, _CANCELA_AMBOS):
        return "ambos"
    if "simples" in _palavras(transcricao):  # a resposta que a pergunta "qual timer" ensina
        return "simples"
    if not cita_desligar(transcricao):
        return None
    p = _palavras(transcricao)
    objetos = _objetos_desligar(p)
    outro = objetos and not {"pc", "computador"} & set(p) and all(
        _outro_objeto(p, k) and p[k + 1:k + 2] and p[k + 1] not in _TIMER for k in objetos)
    return "simples" if outro else "desligar"


# --- Janelas e abas (fase 6): fechar e minimizar por comando direto ---
ACOES_JANELA = ("fechar", "fechar_aba", "minimizar")


def decidir_janela(acao: str, processo: str, abas: int, groov: bool, proibidos, confirmado: bool = False) -> Decisao:
    """`processo` vazio = a sonda não leu a janela. Qualquer app, menos os `proibidos` (sistema) e o GROOV; Chrome com mais
    de uma aba pergunta antes de fechar a janela inteira (fechar uma aba só não precisa)."""
    if acao not in ACOES_JANELA or groov or not processo or processo.lower() in {p.lower() for p in proibidos}:
        return Decisao("recusar", "janela proibida")
    chrome = processo.lower() == "chrome"
    if acao == "fechar_aba" and not chrome:
        return Decisao("recusar", "só aba do Chrome")
    if acao == "fechar" and chrome and abas > 1 and not confirmado:
        return Decisao("perguntar", "várias abas", str(abas))
    return Decisao("ok")
