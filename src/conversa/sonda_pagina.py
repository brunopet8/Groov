"""Terceira sonda do controle do PC: o Playwright MCP (Microsoft, Apache-2.0, 0.0.83) com a extensão no Chrome logado do usuário lê e
age nos SITES da lista pelo conteúdo da página (snapshot de acessibilidade com referências), em vez da árvore da UIA do Chrome.
Não decide nada: as regras são de regras_pc/laco. Mídia, som, envio, trazer/fechar/minimizar, e tudo que não for aba
de site da lista, continuam na sonda de baixo (a `Sonda`, ou a `SondaComposta` da 9.5).

A aba é achada pelo título da janela do Chrome (a aba ativa dá o título da janela): se não houver uma aba só da lista com aquele
título, a janela fica com a sonda de baixo. O log guarda só o nome da operação e o motivo fixo, nunca o conteúdo da página.
"""
import ctypes
import json
import logging
import re
import shutil
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from urllib.parse import urljoin

from src.conversa.ajudante import ambiente_sem
from src.conversa.mcp_stdio import ClienteMCP, ErroFerramenta
from src.conversa.pc import TEXTO_MAX, ErroSonda, Leitura
from src.conversa.regras_pc import SITES, Elemento, host_de
from src.conversa.sonda_ad import processo_da_janela

log = logging.getLogger("groov.sonda_pagina")

SONDA_PAGINA = True  # padrão desde 11/11 (pedido do usuário): leitura por página nos sites da lista; False volta à UIA. Sem node, servidor ou token cai na UIA
SITES_PAGINA = tuple(s.dominio for s in SITES.values())  # só os sites que o laço já usa hoje (regras_pc.SITES)
RAIZ = Path(__file__).resolve().parents[2]
SERVIDOR_JS = RAIZ / "ferramentas" / "navegador" / "node_modules" / "@playwright" / "mcp" / "cli.js"  # npm ci em ferramentas/navegador
# --snapshot-mode none: as ações não devolvem a página inteira (a leitura é o browser_snapshot, que a traz sempre). O 0.0.83 não tem
# --background: a primeira conexão abre a aba de conexão da extensão no Chrome (uma vez por sessão do GROOV).
ARGS_SERVIDOR = ("--extension", "--snapshot-mode", "none")
TOKEN_EXTENSAO = "PLAYWRIGHT_MCP_EXTENSION_TOKEN"  # em privado/.env; dispensa a aprovação da aba a cada conexão
TETO_PAGINA_S = 15.0
PAUSA_FALHA_S = 180.0  # depois de uma falha do servidor/extensão, a janela fica na sonda atual por este tempo (sem esperar o teto a cada passo)
PREFIXOS_CONEXAO = ("chrome-extension://", "about:blank")  # abas da conexão da extensão: podem ser reaproveitadas para o site
TETO_CONEXAO_S = 40.0  # a primeira chamada espera a extensão conectar (o servidor desiste em 30 s)
# ControlType da UIA que o regras_pc espera, por papel ARIA do snapshot; papel fora da tabela não vira Elemento.
TIPOS = {"button": "Button", "link": "Hyperlink", "textbox": "Edit", "searchbox": "Edit", "combobox": "ComboBox",
         "listitem": "ListItem", "option": "ListItem", "checkbox": "CheckBox", "radio": "RadioButton", "menuitem": "MenuItem",
         "tab": "TabItem"}
CAMPOS = ("textbox", "searchbox", "combobox")  # o valor digitado nunca vira texto da página
# O snapshot não distingue <input type=password> (papel textbox, sem valor): pelo rótulo aqui e, antes de digitar, pelo tipo real.
# Resposta do browser_evaluate que libera escrever; qualquer outra (password, vazia, inesperada) recusa.
JS_TIPO_CAMPO = "(el) => el.isContentEditable ? 'editable' : el.tagName === 'TEXTAREA' ? 'textarea' : el.tagName === 'INPUT' ? el.type : ''"
# Valor atual do campo (input/textarea: value; editor rico: innerText). Só `""` libera escrever em modo acrescentar.
JS_VALOR_CAMPO = "(el) => el.isContentEditable ? el.innerText : (el.value ?? '')"
# Clique recusado porque outro elemento cobre o botão (Netflix: modal/prévia): nunca clica por baixo (11/11 abriu a série errada); o laço recebe `coberto`.
CATEGORIA_COBERTO = "intercepta_ponteiro"
BANNER_MAX = 6  # controles: diálogo com até isto e sem marca [modal] é banner (cookies) e não esconde os controles da página
PAPEIS_DIALOGO = ("dialog", "alertdialog")  # com um aberto, só vale o que está dentro dele (o modal da Netflix cobre a página; 11/11 o laço clicou atrás dele)
TIPOS_ESCRITA = frozenset({"text", "search", "email", "url", "tel", "textarea", "editable"})
PALAVRAS_SENHA = ("senha", "password", "passcode", "palavra-passe", "contraseña")


@dataclass
class _No:
    papel: str
    nome: str = ""
    ref: str = ""
    valor: str = ""
    url: str = ""
    placeholder: str = ""
    modal: bool = False
    filhos: list = field(default_factory=list)


_CHAVE = re.compile(r'^(?P<papel>[\w/-]+)(?: (?P<nome>"(?:[^"\\]|\\.)*"))?(?P<marcas>(?: \[[^\]]*\])*)$')
_REF = re.compile(r"\[ref=([^\]]+)\]")
_LINHA = re.compile(r"^( *)- (.*)$")
_ABA = re.compile(r"^- (\d+):( \(current\))? \[(.*)\]\((\S*)\)(?: \[crashed\])?$")


def _texto(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] == '"':
        try:
            return json.loads(s)
        except ValueError:
            return s[1:-1]
    return s


def _separar(resto: str) -> tuple[str, str | None]:
    """Chave e valor de uma linha do YAML do snapshot. A chave inteira vem entre aspas simples quando tem `: ` etc."""
    if resto.startswith("'"):
        i, buf = 1, []
        while i < len(resto):
            if resto[i] == "'":
                if resto[i + 1:i + 2] == "'":
                    buf.append("'")
                    i += 2
                    continue
                break
            buf.append(resto[i])
            i += 1
        chave, cauda = "".join(buf), resto[i + 1:]
    else:
        m = re.search(r":( |$)", resto)
        chave, cauda = (resto[:m.start()], resto[m.start():]) if m else (resto, "")
    return chave, _texto(cauda[2:]) if cauda.startswith(": ") else None


def _arvore(yaml: str) -> _No:
    raiz = _No("root")
    pilha = [(-1, raiz)]
    for linha in yaml.splitlines():
        m = _LINHA.match(linha)
        if not m:
            continue
        nivel = len(m[1]) // 2
        while pilha[-1][0] >= nivel:
            pilha.pop()
        pai = pilha[-1][1]
        chave, valor = _separar(m[2])
        if chave == "/url":
            pai.url = valor or ""
        elif chave == "/placeholder":
            pai.placeholder = valor or ""
        elif chave == "text":
            pai.filhos.append(_No("text", nome=valor or ""))
        elif k := _CHAVE.match(chave):
            r = _REF.search(k["marcas"])
            no = _No(k["papel"], nome=_texto(k["nome"] or ""), ref=r[1] if r else "", valor=valor or "", modal="[modal]" in k["marcas"])
            pai.filhos.append(no)
            pilha.append((nivel, no))
    return raiz


def _em_ordem(no: _No):
    yield no
    for f in no.filhos:
        yield from _em_ordem(f)


def _dialogo_aberto(raiz: _No) -> _No | None:
    """O diálogo mais de cima: o último na ordem do documento (modais entram no fim do body). shortcut: o snapshot não traz z-index;
    trocar se aparecer site que abre o modal por baixo de outro."""
    return next((n for n in reversed(list(_em_ordem(raiz))) if n.papel in PAPEIS_DIALOGO), None)


def _mencao_senha(*textos: str) -> bool:
    return any(p in t.lower() for t in textos for p in PALAVRAS_SENHA)


def _percorrer(no: _No, ancestrais: tuple[str, ...], elementos: list, textos: list, base: str) -> str:
    """Desce a árvore. Nó com referência e papel da tabela vira Elemento; os outros nomes alimentam o texto da página. Devolve o
    texto dos descendentes, que vira o `texto_interno` do pai."""
    if no.papel == "text":
        textos.append(no.nome)
        return no.nome
    elemento = bool(no.ref) and no.papel in TIPOS
    senha = elemento and no.papel in CAMPOS and _mencao_senha(no.nome, no.placeholder)
    tipo = TIPOS.get(no.papel, "")
    papel_aria = "searchbox" if no.papel == "searchbox" else ""
    if senha:  # só o Elemento marcado (o nome é o rótulo), sem texto interno nem valor, para o regras_pc recusar escrever nele
        elementos.append(Elemento(id=len(elementos), nome=no.nome, tipo=tipo, papel=papel_aria, texto_interno="",
                                  ancestrais=ancestrais, senha=True, runtime_id=no.ref, host_do_link=None))
        return ""
    lugar = len(elementos)
    if elemento:
        elementos.append(None)  # reserva a posição: o pai vem antes dos filhos, o texto interno só depois
    elif no.nome:
        textos.append(no.nome)
    partes = [] if no.papel in CAMPOS or not no.valor else [no.valor]
    if partes:
        textos.append(no.valor)
    filhos_anc = (*ancestrais, no.nome) if no.nome else ancestrais
    partes += [f for c in no.filhos if (f := _percorrer(c, filhos_anc, elementos, textos, base))]
    dentro = " ".join(partes)
    if elemento:
        host = host_de(urljoin(base, no.url)) if no.papel == "link" and no.url else None
        elementos[lugar] = Elemento(id=lugar, nome=no.nome, tipo=tipo, papel=papel_aria, texto_interno=dentro,
                                    ancestrais=ancestrais, senha=False, runtime_id=no.ref, host_do_link=host)
    return " ".join(x for x in (no.nome, dentro) if x)


def ler_snapshot(resposta: str, hwnd: int) -> Leitura:
    """`Leitura` do texto que o browser_snapshot devolve (seções `### Page` e `### Snapshot`). Sem a seção do snapshot: ErroSonda."""
    secoes = {}
    for bloco in re.split(r"^### ", resposta, flags=re.M)[1:]:
        titulo, _, corpo = bloco.partition("\n")
        secoes[titulo.strip()] = corpo
    if "Snapshot" not in secoes:
        raise ErroSonda("ler: sem snapshot")
    pagina = secoes.get("Page", "")
    url = (re.search(r"^- Page URL: (.+)$", pagina, re.M) or [None, ""])[1].strip()
    titulo = (re.search(r"^- Page Title: (.*)$", pagina, re.M) or [None, ""])[1].strip()
    elementos, textos = [], []
    raiz = _arvore(secoes["Snapshot"])
    _percorrer(raiz, (), elementos, textos, url)  # o TEXTO da página fica inteiro; só os controles podem ser limitados ao diálogo
    if dialogo := _dialogo_aberto(raiz):
        refs = {n.ref for n in _em_ordem(dialogo) if n.ref}
        dentro = [e for e in elementos if e.runtime_id in refs]
        if dialogo.modal or len(dentro) > BANNER_MAX:  # com modal de verdade, o resto da página não existe para o laço (11/11 Netflix)
            elementos = [replace(e, id=i) for i, e in enumerate(dentro)]
    texto = " ".join(textos)
    return Leitura(hwnd=hwnd, endereco=url or None, titulo=titulo, texto=texto[:TEXTO_MAX], elementos=tuple(elementos),
                   cortado=len(texto) > TEXTO_MAX)


@dataclass(frozen=True)
class _Aba:
    indice: int
    atual: bool
    titulo: str
    url: str


def titulo_da_janela_win(hwnd: int) -> str:
    if sys.platform != "win32":
        return ""
    u = ctypes.WinDLL("user32")
    buf = ctypes.create_unicode_buffer(512)
    u.GetWindowTextW(ctypes.c_void_p(hwnd), buf, 512)
    return buf.value


class SondaPagina:
    def __init__(self, cliente: ClienteMCP, sites: tuple[str, ...] = SITES_PAGINA, titulo_de=titulo_da_janela_win,
                 processo_de=processo_da_janela, relogio=time.monotonic):
        self.cliente, self.sites, self.titulo_de, self.processo_de = cliente, sites, titulo_de, processo_de
        self.relogio, self._pausa_ate = relogio, 0.0
        self.coberto = False  # o último clique falhou por outro elemento cobrir o alvo
        self._aberta: tuple[int, str] | None = None  # (índice, url) da última aba que o laço abriu

    def _permitido(self, url: str) -> bool:
        host = host_de(url)
        return bool(host) and any(host == d or host.endswith("." + d) for d in self.sites)

    async def _abas(self) -> list[_Aba]:
        """As abas da sessão do servidor. Falha de conexão: a leitura por página fica desligada até reiniciar (e a falha sobe)."""
        try:
            lista = await self.cliente.chamar("browser_tabs", {"action": "list"})
        except ErroSonda:
            if self._pausa_ate != float("inf"):  # 1ª falha de conexão da sessão: a leitura por página fica desligada até reiniciar
                log.warning("página: servidor ou extensão não responde: desligada nesta sessão, usando a sonda atual")
            self._pausa_ate = float("inf")
            raise
        return [_Aba(int(m[1]), bool(m[2]), m[3], m[4]) for linha in lista.splitlines() if (m := _ABA.match(linha.strip()))]

    async def _aba(self, hwnd: int) -> _Aba | None:
        """A aba de site da lista cujo título casa com o da janela do Chrome ("<aba> - Google Chrome - perfil"); com várias de mesmo
        título (cada abrir_site abre uma aba nova), a que o próprio laço acabou de abrir, senão a ativa e, sem ela, a mais recente (maior índice). Nenhuma: None."""
        if self.processo_de(hwnd) != "chrome":
            return None
        if self.relogio() < self._pausa_ate:
            return None
        janela = self.titulo_de(hwnd)
        achadas = [a for a in await self._abas()
                   if a.titulo and self._permitido(a.url) and (janela == a.titulo or janela.startswith(a.titulo + " - "))]
        return max(achadas, key=lambda a: ((a.indice, a.url) == self._aberta, a.atual, a.indice), default=None)

    async def abrir(self, url: str) -> bool:
        """Abre o site numa aba DA SESSÃO do servidor (a extensão só vê as abas do seu grupo): reaproveita a aba de conexão se for a
        única, senão aba nova. True se abriu; qualquer falha, pausa ou site fora da lista é False e quem chama usa a sonda atual."""
        if not self._permitido(url) or self.relogio() < self._pausa_ate:
            return False
        try:
            abas = await self._abas()
            if len(abas) == 1 and abas[0].url.startswith(PREFIXOS_CONEXAO):
                await self.cliente.chamar("browser_navigate", {"url": url})
            else:
                await self.cliente.chamar("browser_tabs", {"action": "new", "url": url})
        except ErroSonda as e:
            log.warning("sonda_pagina abrir: %s", e)
            return False
        try:  # o site já abriu: daqui em diante falhar não pode virar uma segunda abertura (fora do grupo) pela sonda atual
            nova = next((a for a in await self._abas() if a.atual), None)
            if nova is not None:
                self._aberta = (nova.indice, nova.url)
            if nova is not None:  # o select traz a janela da aba para a frente: a janela_da_aba do laço pega a da frente primeiro
                await self.cliente.chamar("browser_tabs", {"action": "select", "index": nova.indice})
        except ErroSonda as e:
            log.warning("sonda_pagina abrir (depois de abrir): %s", e)
        return True

    async def aceita(self, hwnd: int) -> bool:
        try:
            return await self._aba(hwnd) is not None
        except ErroSonda as e:
            log.warning("sonda_pagina %s", e)
            return False

    async def _preparar(self, hwnd: int, op: str) -> _Aba:
        aba = await self._aba(hwnd)
        if aba is None:
            raise ErroSonda(f"{op}: aba_nao_identificada")
        if not aba.atual:  # o select traz a aba para a frente: só quando ela não é a atual do servidor
            await self.cliente.chamar("browser_tabs", {"action": "select", "index": aba.indice})
        return aba

    async def ler(self, hwnd: int) -> Leitura:
        await self._preparar(hwnd, "ler")
        try:
            leitura = ler_snapshot(await self.cliente.chamar("browser_snapshot"), hwnd)
        except ErroSonda:  # mesmo disjuntor do browser_tabs: o servidor falhou, pausa e a composição cai na sonda de baixo
            self._pausa_ate = self.relogio() + PAUSA_FALHA_S
            raise
        if not self._permitido(leitura.endereco or ""):
            raise ErroSonda("ler: site_fora_da_lista")
        return leitura

    async def _agir(self, hwnd: int, endereco: str | None, op: str, ferramenta: str, args: dict, campo: bool = False,
                    vazio: bool = False) -> bool:
        """Ação: qualquer falha é "não agiu" (o laço relê), como nas outras sondas. `endereco` é o da leitura: se a aba já mudou, não age.
        `campo`: confere no navegador que o alvo não é um campo de senha antes de escrever nele."""
        self.coberto = False
        try:
            aba = await self._preparar(hwnd, op)
            if endereco and aba.url != endereco:
                log.info("sonda_pagina %s: aba_mudou", op)
                return False
            if campo:
                tipo = re.search(r'"([^"\n]*)"', await self.cliente.chamar(
                    "browser_evaluate", {"target": args["target"], "function": JS_TIPO_CAMPO}))
                if not tipo or tipo[1].lower() not in TIPOS_ESCRITA:  # falha fechada: só escreve em tipo conhecido
                    log.info("sonda_pagina %s: campo_nao_confirmado", op)
                    return False
            if vazio:  # o fill troca o valor inteiro (WhatsApp Web, Docs): com texto já no campo, não escreve
                atual = await self.cliente.chamar("browser_evaluate", {"target": args["target"], "function": JS_VALOR_CAMPO})
                if atual.partition("### Result")[2].strip().splitlines()[:1] != ['""']:
                    log.info("sonda_pagina %s: campo_com_texto", op)
                    return False
            try:
                await self.cliente.chamar(ferramenta, args)
            except ErroFerramenta as e:
                self.coberto = e.categoria == CATEGORIA_COBERTO
                raise
        except ErroSonda as e:
            log.warning("sonda_pagina %s", e)
            return False
        return True

    async def clicar(self, hwnd: int, el: Elemento, endereco: str | None) -> bool:
        return bool(el.runtime_id) and await self._agir(
            hwnd, endereco, "clicar", "browser_click", {"target": el.runtime_id})

    async def digitar(self, hwnd: int, el: Elemento, texto: str, endereco: str | None, acrescentar: bool = True) -> bool:
        # shortcut: o browser_type troca o valor do campo, então `acrescentar` só escreve em campo vazio; acrescentar de verdade
        # num editor rico exigiria colar no fim, o que não é seguro por fill.
        return bool(el.runtime_id) and await self._agir(hwnd, endereco, "digitar", "browser_type",
                                                        {"target": el.runtime_id, "text": texto}, campo=True, vazio=acrescentar)

    async def buscar(self, hwnd: int, el: Elemento, texto: str, endereco: str | None) -> bool:
        return bool(el.runtime_id) and await self._agir(hwnd, endereco, "buscar", "browser_type",
                                                        {"target": el.runtime_id, "text": texto, "submit": True}, campo=True)

    async def rolar(self, hwnd: int, direcao: str) -> bool:
        # shortcut: rola a janela (não um painel interno da página); a roda do mouse do servidor pede --caps=vision. Trocar se a Fase 10 mostrar página que rola por dentro.
        sinal = -1 if direcao in ("cima", "up") else 1
        return await self._agir(hwnd, None, "rolar", "browser_evaluate",
                                {"function": f"() => window.scrollBy(0, {sinal} * 0.8 * window.innerHeight)"})

    async def voltar(self, hwnd: int) -> bool:
        return await self._agir(hwnd, None, "voltar", "browser_navigate_back", {})


class SondaPaginaComposta:
    """O que a Fase 8 entrega ao laço: leitura e ações da SondaPagina na aba de site da lista da janela do Chrome; todo o resto
    (mídia, som, envio, trazer/fechar/minimizar e as outras janelas) vai para a sonda de baixo, como hoje."""

    def __init__(self, atual, pagina: SondaPagina):
        self.atual, self.pagina = atual, pagina

    def __getattr__(self, nome):  # só chega aqui o que não está definido abaixo
        return getattr(self.atual, nome)

    @property
    def coberto(self) -> bool:
        return self.pagina.coberto

    async def abrir_site(self, url: str) -> None:
        """Site da lista com a sonda de página ativa: abre na aba da sessão do servidor (só ela é lida); senão, como sempre. O laço
        acha a janela depois (`janela_da_aba`, que lê pelo título/endereço, já pela sonda de página quando a aba é dela)."""
        if not await self.pagina.abrir(url):
            await self.atual.abrir_site(url)

    async def _por(self, hwnd: int):
        return self.pagina if await self.pagina.aceita(hwnd) else self.atual

    async def ler(self, hwnd: int) -> Leitura:
        sonda = await self._por(hwnd)
        try:
            return await sonda.ler(hwnd)
        except ErroSonda:
            if sonda is self.pagina and self.pagina.relogio() < self.pagina._pausa_ate:  # o snapshot falhou: lê pela atual
                return await self.atual.ler(hwnd)
            raise

    async def clicar(self, hwnd: int, el: Elemento, endereco: str | None) -> bool:
        return await (await self._por(hwnd)).clicar(hwnd, el, endereco)

    async def digitar(self, hwnd: int, el: Elemento, texto: str, endereco: str | None, acrescentar: bool = True) -> bool:
        return await (await self._por(hwnd)).digitar(hwnd, el, texto, endereco, acrescentar)

    async def buscar(self, hwnd: int, el: Elemento, texto: str, endereco: str | None) -> bool:
        return await (await self._por(hwnd)).buscar(hwnd, el, texto, endereco)

    async def rolar(self, hwnd: int, direcao: str) -> bool:
        return await (await self._por(hwnd)).rolar(hwnd, direcao)

    async def voltar(self, hwnd: int) -> bool:
        return await (await self._por(hwnd)).voltar(hwnd)


def escolher_sonda_pagina(atual, segredos: frozenset[str], token: str | None, ligada: bool | None = None, procurar=shutil.which,
                          servidor: Path = SERVIDOR_JS):
    """Backend do laço pela constante, por cima da sonda `atual` (que pode ser a SondaComposta da 9.5). Sem node, sem o servidor
    instalado ou sem o token: fica a sonda atual e avisa (sem conteúdo) no log. O token vai só para o ambiente do servidor."""
    if not (SONDA_PAGINA if ligada is None else ligada):
        return atual
    node = procurar("node")
    if not (node and servidor.exists() and token):
        log.warning("página: faltou node, servidor ou token: usando a sonda atual")
        return atual
    cliente = ClienteMCP([node, str(servidor), *ARGS_SERVIDOR], {**ambiente_sem(segredos), TOKEN_EXTENSAO: token},
                         TETO_PAGINA_S, TETO_CONEXAO_S)
    return SondaPaginaComposta(atual, SondaPagina(cliente))
