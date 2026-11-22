import pytest

from src.conversa.fala import para_fala


@pytest.mark.parametrize("escrito,falado", [
    ("Está 23°C.", "Está 23 graus."),
    ("Recife agora: 24°C, nublado.", "Recife agora: 24 graus, nublado."),
    ("Faz 23 ºC lá fora.", "Faz 23 graus lá fora."),
    ("Mínima de -3°C.", "Mínima de menos 3 graus."),
    ("Umidade de 80%.", "Umidade de 80 por cento."),
    ("Vento de 15 km/h.", "Vento de 15 quilômetros por hora."),
    ("Custa R$ 5,50.", "Custa 5,50 reais."),
    ("Fica **muito** bom & rápido.", "Fica muito bom e rápido."),
    ("Veja https://exemplo.com/a?b=1 agora.", "Veja agora."),
    ("GROOV: Senhor, está 23 graus.", "Senhor, está 23 graus."),
    ("GROOV: Sou o Groov, senhor.", "Sou o Gruv, senhor."),
    ("Jarvis: pronto.", "pronto."),
    ("Nada a mudar, senhor.", "Nada a mudar, senhor."),
])
def test_para_fala(escrito, falado):
    assert para_fala(escrito) == falado
