from src.conversa.contexto import cortar_historico


def u(n): return {"role": "user", "content": f"u{n}"}
def a(n): return {"role": "assistant", "content": f"a{n}"}
def chamada(n): return {"role": "assistant", "tool_calls": [{"id": f"c{n}"}]}
def resultado(n): return {"role": "tool", "tool_call_id": f"c{n}", "content": "{}"}


def test_historico_curto_fica_igual():
    mensagens = [u(1), a(1), u(2), a(2)]
    assert cortar_historico(mensagens, 8) == mensagens


def test_corta_nas_ultimas_oito_comecando_num_turno_do_usuario():
    mensagens = [u(1), a(1), u(2), a(2), u(3), a(3), u(4), a(4), u(5), a(5)]
    assert cortar_historico(mensagens, 8) == mensagens[2:]


def test_nao_separa_chamada_de_ferramenta_do_resultado():
    mensagens = [u(1), chamada(1), resultado(1), a(1), u(2), a(2), u(3), a(3)]
    cortado = cortar_historico(mensagens, 7)  # o recorte cairia no meio de u1/chamada/resultado
    assert cortado[0]["role"] == "user" and cortado == mensagens[4:]


def test_sem_usuario_no_recorte_volta_ao_ultimo_usuario():
    mensagens = [u(1)] + [a(i) for i in range(10)]
    assert cortar_historico(mensagens, 4) == mensagens


def test_nao_altera_a_lista_original():
    mensagens = [u(1), a(1), u(2), a(2), u(3), a(3), u(4), a(4), u(5), a(5)]
    copia = list(mensagens)
    cortar_historico(mensagens, 4)
    assert mensagens == copia
