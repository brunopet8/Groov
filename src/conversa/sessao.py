"""Estado da conversa: dormindo/acordando/conversando/ocioso, silêncio e a vaga de tarefa (Hermes ou laço do PC).
Sem I/O: o tempo vem do chamador."""
from enum import Enum

PAUSA_DESPERTAR = 5.0  # s sem aceitar "Hey JARVIS" depois de "tchau"/"vá embora": a despedida não acorda ele de novo
OCIOSO_APOS_S = 20.0  # s sem trabalho até ficar ocioso
DESLIGAR_APOS_S = 600.0  # s sem ninguém mexer até desligar sozinho


class Estado(str, Enum):
    DORMINDO = "dormindo"
    ACORDANDO = "acordando"
    CONVERSANDO = "conversando"
    OCIOSO = "ocioso"


class Sessao:
    def __init__(self, teto_tarefa: float = 300.0):
        self.teto_tarefa = teto_tarefa
        self.estado = Estado.DORMINDO
        self.resultado_guardado: str | None = None
        self.midia_tocando = False  # a fala captada (diálogo da série) não segura ele acordado
        self.surdo = False  # modo surdo: o microfone não chega ao Whisper; só o botão, "Hey JARVIS" ou o nome voltam
        self._ultima_atividade = 0.0
        self._tarefa_desde: float | None = None
        self._dono: str | None = None
        self._pausado = 0.0  # s de espera por resposta do usuário, fora do teto do laço
        self._pausa_desde: float | None = None
        self._acordavel_em = 0.0
        self._falando_desde: float | None = None
        self._segura_ate = 0.0
        self._ouvindo = False  # o usuário está no meio de um turno de fala

    @property
    def falando(self) -> bool:
        """O GROOV está falando (entre o início e o fim da fala no alto-falante)."""
        return self._falando_desde is not None

    def comecou_a_falar(self, agora: float) -> None:
        self._falando_desde = agora

    def parou_de_falar(self, agora: float) -> None:
        self._falando_desde = None
        if self.estado is Estado.CONVERSANDO:  # a fala dele no ocioso não zera os 10 min
            self.atividade(agora)

    def comecou_a_ouvir(self, agora: float) -> None:
        self._ouvindo = True

    def parou_de_ouvir(self, agora: float) -> None:
        self._ouvindo = False
        if self.estado is Estado.CONVERSANDO:
            self.atividade(agora)

    def acordar(self, agora: float) -> None:
        self.estado = Estado.ACORDANDO
        self._falando_desde = None  # fala sem aviso de fim da sessão anterior não segura esta
        self._ouvindo = False
        self._segura_ate = 0.0  # a segurada de um ciclo anterior não vale neste
        self._ultima_atividade = agora

    def pronto(self, agora: float) -> None:
        self.estado = Estado.CONVERSANDO
        self._ultima_atividade = agora

    def dormir(self, agora: float | None = None) -> None:
        """Com agora (pedido do usuário), o despertador fica PAUSA_DESPERTAR s surdo. Não cancela a tarefa."""
        self.estado = Estado.DORMINDO
        self._falando_desde = None
        self._ouvindo = False
        self._segura_ate = 0.0
        if agora is not None:
            self._acordavel_em = agora + PAUSA_DESPERTAR

    def ociar(self, agora: float | None = None) -> bool:
        """Só a partir de CONVERSANDO; não zera o relógio. Com agora (pedido do usuário), o despertador fica PAUSA_DESPERTAR s surdo."""
        if self.estado is not Estado.CONVERSANDO:
            return False
        self.estado = Estado.OCIOSO
        self._ouvindo = False
        if agora is not None:
            self._acordavel_em = agora + PAUSA_DESPERTAR
        return True

    def retomar(self, agora: float) -> None:
        if self.estado is Estado.OCIOSO:
            self.estado = Estado.CONVERSANDO
            self._ultima_atividade = agora

    def segurar(self, ate: float) -> None:
        self._segura_ate = ate

    def deve_ociar(self, agora: float) -> bool:
        if self._falando_desde is not None or (self._ouvindo and not self.midia_tocando):
            return False
        return (self.estado is Estado.CONVERSANDO and self._tarefa_desde is None
                and agora >= self._segura_ate and agora - self._ultima_atividade >= OCIOSO_APOS_S)

    def deve_desligar(self, agora: float) -> bool:
        return (self.estado is Estado.OCIOSO and self._tarefa_desde is None and self._falando_desde is None
                and agora >= self.desliga_em())  # falando: não corta a despedida nem o aviso de timer ao meio

    def desliga_em(self) -> float:
        return self._ultima_atividade + DESLIGAR_APOS_S

    def pode_acordar(self, agora: float) -> bool:
        return agora >= self._acordavel_em

    def atividade(self, agora: float, fala_do_usuario: bool = False) -> None:
        if not (fala_do_usuario and self.midia_tocando):
            self._ultima_atividade = agora

    @property
    def dono(self) -> str | None:
        return self._dono

    def iniciar_tarefa(self, agora: float, dono: str = "hermes") -> bool:
        if self._tarefa_desde is not None:
            return False
        self._tarefa_desde, self._dono = agora, dono
        self._pausado, self._pausa_desde = 0.0, None
        if dono == "laco":
            self.midia_tocando = False
        return True

    def pausar_relogio(self, agora: float) -> None:
        if self._pausa_desde is None:
            self._pausa_desde = agora

    def retomar_relogio(self, agora: float) -> None:
        if self._pausa_desde is not None:
            self._pausado += agora - self._pausa_desde
            self._pausa_desde = None

    def tarefa_estourou(self, agora: float) -> bool:
        if self._tarefa_desde is None:
            return False
        decorrido = agora - self._tarefa_desde
        if self._dono == "laco":  # o Hermes não pausa: relógio corrido, como sempre
            fim_da_conta = agora if self._pausa_desde is None else self._pausa_desde
            decorrido = fim_da_conta - self._tarefa_desde - self._pausado
        return decorrido >= self.teto_tarefa

    def concluir_tarefa(self, resultado: str) -> None:
        self._tarefa_desde = self._dono = None
        if self.estado is not Estado.CONVERSANDO:
            self.resultado_guardado = resultado

    def cancelar_tarefa(self) -> None:
        self._tarefa_desde = self._dono = None

    def pegar_resultado_guardado(self) -> str | None:
        resultado, self.resultado_guardado = self.resultado_guardado, None
        return resultado
