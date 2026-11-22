"""Turno do usuário acumulado: o VAD de 0,14 s corta a fala em trechos, e o pedido é o turno inteiro. Sem pipecat."""

import time

from .comandos import _com_nome, normalizar

JUNTAR_TURNO_S = 3  # s em que um trecho tardio ainda entra no pedido: depois do início do laço ou do fim do turno
CONFIRMACAO_VALE_S = 60  # s em que "pode" ainda se refere ao pedido anterior que o cérebro não levou ao pc
_CONFIRMACOES = _com_nome("sim", "pode", "pode sim", "pode ir", "isso", "isso mesmo", "confirmo", "confirma", "claro",
                            "faz", "faz isso", "manda", "ok", "beleza", "quero")


class Turno:
    def __init__(self):
        self._trechos: list[str] = []
        self._inicio: float | None = None
        self._voz: float | None = None  # início do trecho de áudio que gerou o ÚLTIMO trecho adicionado
        self._aberto = False
        self._novo = True  # o próximo abrir ou trecho começa um turno do zero (ou junta ao anterior)
        self._fechado_em: float | None = None  # None também depois de consumir: o pedido já foi
        self._desde = 0  # primeiro trecho deste turno, sem o anterior juntado
        self._anterior: tuple[str, float] | None = None  # pedido não consumido (texto, hora) que um turno novo substituiu

    def _comecar(self, agora: float) -> None:
        if not self._novo:
            return
        # o Smart Turn fecha em "...na Netflix" e o usuário segue falando antes de o cérebro chamar pc: é o mesmo pedido
        if self._fechado_em is None or agora - self._fechado_em >= JUNTAR_TURNO_S:
            # o cérebro perguntou "confirma?" em vez de chamar pc: o "pode" seguinte tem de achar este pedido
            if self._trechos and not self._confirmacao(self.texto()):
                self._anterior = (self.texto(), self._fechado_em if self._fechado_em is not None else self._inicio)
            self._trechos, self._inicio = [], agora
        self._desde, self._novo = len(self._trechos), False

    def abrir(self, agora: float) -> None:
        self._comecar(agora)  # sem VAD o pipecat abre o turno pela transcrição, que já passou pelo filtro
        self._aberto = True

    def adicionar(self, texto: str, agora: float, inicio_trecho: float | None = None) -> None:
        """`inicio_trecho`: quando o áudio que o Whisper transcreveu começou (o STT carrega no frame); sem ele, None."""
        self._comecar(agora)
        self._voz = inicio_trecho  # None: o STT não marcou; `inicio_da_voz` devolve None e quem julga decide
        self._trechos.append(texto.strip())

    def texto(self) -> str:
        return " ".join(self._trechos)

    def desde_abrir(self) -> str:
        """Só os trechos deste turno: "desligar" vale pelo que o usuário disse agora, não pelo turno juntado."""
        return " ".join(self._trechos[self._desde:])

    def inicio(self) -> float | None:
        return self._inicio

    def inicio_da_voz(self) -> float | None:
        """Quando começou a voz que gerou o último trecho: a resposta a uma pergunta do laço compara com ESTE, não com `inicio()` (o turno
        do eco da pergunta, juntado em menos de JUNTAR_TURNO_S, deixava `inicio()` antes do fim da fala e engolia a resposta)."""
        return self._voz

    def fechar(self, agora: float) -> None:
        """O texto fica: a ferramenta pc o lê depois do fim do turno, com `consumir`."""
        self._aberto, self._novo, self._fechado_em = False, True, agora

    @staticmethod
    def _confirmacao(texto: str) -> bool:
        return normalizar(texto) in _CONFIRMACOES

    def consumir(self, agora: float | None = None) -> str:
        """Quem inicia o pc leva o pedido; o próximo turno não junta a ele. "Pode"/"sim" leva o pedido anterior."""
        texto = self.texto()
        anterior, self._anterior = self._anterior, None
        if anterior and self._confirmacao(texto):
            agora = time.monotonic() if agora is None else agora
            if agora - anterior[1] <= CONFIRMACAO_VALE_S:
                texto = anterior[0]
        self._trechos, self._inicio, self._fechado_em, self._desde, self._novo = [], None, None, 0, True
        return texto

    def aberto(self) -> bool:
        return self._aberto

    def juntar_ao_laco(self, texto: str, agora: float, inicio_laco: float | None) -> bool:
        return bool(texto.strip()) and inicio_laco is not None and agora - inicio_laco <= JUNTAR_TURNO_S
