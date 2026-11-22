import pytest

from src import clima
from src.clima import SEM_LOCAL, Mar, Tempo, mar, tempo_do_dia, temperatura_agora


def falso(resposta, urls=None, timeouts=None):
    def buscar(url, timeout=None):
        if urls is not None:
            urls.append(url)
        if timeouts is not None:
            timeouts.append(timeout)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta

    return buscar


def nunca(url, timeout=None):
    raise AssertionError("sem config não pode sair nada do PC")


@pytest.fixture
def recife(monkeypatch):
    monkeypatch.setenv("GROOV_CIDADE", "Recife")
    monkeypatch.setenv("GROOV_LAT", "-8.05")
    monkeypatch.setenv("GROOV_LON", "-34.9")
    monkeypatch.setenv("GROOV_MAR", "Boa Viagem;-8.13;-34.9")


def test_local_e_mar_local_leem_a_config(recife):
    assert clima.local() == ("Recife", -8.05, -34.9)
    assert clima.mar_local() == ("Boa Viagem", -8.13, -34.9)


@pytest.mark.parametrize("nome,valor", [("GROOV_LAT", "abc"), ("GROOV_LON", ""), ("GROOV_CIDADE", " ")])
def test_cidade_incompleta_ou_quebrada_vira_none(recife, monkeypatch, nome, valor):
    monkeypatch.setenv(nome, valor)
    assert clima.local() is None


@pytest.mark.parametrize("valor", ["Boa Viagem;-8.13", "Boa Viagem;x;-34.9", ";-8.13;-34.9", ""])
def test_mar_quebrado_vira_none(monkeypatch, valor):
    monkeypatch.setenv("GROOV_MAR", valor)
    assert clima.mar_local() is None


def test_tempo_do_dia_le_atual_e_diario(recife):
    urls = []
    resposta = {"current": {"temperature_2m": 23.6, "weather_code": 2},
                "daily": {"temperature_2m_max": [28.7], "temperature_2m_min": [20.6],
                          "precipitation_probability_max": [30]}}
    assert tempo_do_dia(buscar=falso(resposta, urls)) == Tempo(24, "parcialmente nublado", 29, 21, 30)
    assert "daily=temperature_2m_max" in urls[0] and "latitude=-8.05" in urls[0] and "longitude=-34.9" in urls[0]


def test_mar_le_a_onda_do_lugar_da_config(recife):
    urls = []
    assert mar(buscar=falso({"current": {"wave_height": 1.58}}, urls)) == Mar(1.58, "Boa Viagem")
    assert urls[0].startswith("https://marine-api.open-meteo.com/v1/marine") and "latitude=-8.13" in urls[0]


def test_sem_config_nada_sai_do_pc():
    assert tempo_do_dia(buscar=nunca) is None and mar(buscar=nunca) is None
    assert temperatura_agora(buscar=nunca) == SEM_LOCAL
    assert "GROOV_CIDADE" in SEM_LOCAL and "privado/.env" in SEM_LOCAL


@pytest.mark.parametrize("resposta", [OSError("sem rede"), {}, {"current": {"wave_height": None}},
                                      {"current": {"temperature_2m": None, "weather_code": 1}, "daily": {}}])
def test_tempo_e_mar_sem_rede_ou_json_estranho_viram_none(recife, resposta):
    assert tempo_do_dia(buscar=falso(resposta)) is None and mar(buscar=falso(resposta)) is None


def test_timeout_chega_ao_buscar(recife):
    timeouts = []
    tempo_do_dia(buscar=falso({}, timeouts=timeouts))
    mar(buscar=falso({}, timeouts=timeouts))
    assert timeouts == [3, 3]


def test_resume_temperatura_e_condicao(recife):
    resposta = {"current": {"temperature_2m": 24.36, "weather_code": 3}}
    texto = temperatura_agora(buscar=lambda url: resposta)
    assert texto == "Recife agora: 24°C, nublado."


def test_codigo_desconhecido_mostra_so_temperatura(recife):
    resposta = {"current": {"temperature_2m": 19.5, "weather_code": 999}}
    assert temperatura_agora(buscar=lambda url: resposta) == "Recife agora: 20°C."


def test_api_fora_do_ar_da_mensagem_clara(recife):
    def falha(url):
        raise OSError("timeout")

    assert temperatura_agora(buscar=falha) == "Não consegui consultar o clima agora (timeout)."


def test_url_pede_dados_atuais_das_coordenadas(recife):
    urls = []
    temperatura_agora(buscar=lambda url: urls.append(url) or {"current": {"temperature_2m": 1, "weather_code": 0}})
    assert "latitude=-8.05" in urls[0] and "longitude=-34.9" in urls[0]
    assert "current=temperature_2m,weather_code" in urls[0]
