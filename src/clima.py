"""Tempo e mar pelo Open-Meteo (grátis, sem chave, dados CC BY 4.0). Só as coordenadas saem do PC."""
import json
import sys
import urllib.request
from dataclasses import dataclass

from src import config

URL = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
       "&current=temperature_2m,weather_code&timezone=America%2FSao_Paulo")
URL_DIA = URL + "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&forecast_days=1"
# a célula de onda mais perto fica ~6 km mar adentro: na areia a onda tende a ser menor
URL_MAR = ("https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}"
           "&current=wave_height&timezone=America%2FSao_Paulo")

# Códigos WMO usados pelo Open-Meteo, agrupados.
CONDICOES = {0: "céu limpo", 1: "poucas nuvens", 2: "parcialmente nublado", 3: "nublado",
             45: "neblina", 48: "neblina"}
CONDICOES |= {c: "garoa" for c in range(51, 58)}
CONDICOES |= {c: "chuva" for c in range(61, 68)}
CONDICOES |= {c: "pancadas de chuva" for c in (80, 81, 82)}
CONDICOES |= {c: "trovoada" for c in (95, 96, 99)}


@dataclass(frozen=True)
class Tempo:
    temperatura: int
    condicao: str | None
    maxima: int
    minima: int
    chuva: int  # chance máxima do dia, em %


@dataclass(frozen=True)
class Mar:
    altura: float  # altura significativa das ondas agora, em metros
    lugar: str = ""  # praia de GROOV_MAR; sem ela o briefing não fala do mar


FALHA_DO_CLIMA = "Não consegui consultar o clima agora"  # ferramentas.py reconhece a falha por ele
SEM_LOCAL = "Não sei sua cidade: preencha GROOV_CIDADE, GROOV_LAT e GROOV_LON no privado/.env."


def _lugar(nome: str, lat: str, lon: str) -> tuple[str, float, float] | None:
    try:
        return (nome.strip(), float(lat), float(lon)) if nome.strip() else None
    except ValueError:
        return None


def local() -> tuple[str, float, float] | None:
    """(cidade, lat, lon) de GROOV_CIDADE/LAT/LON; None se faltar ou não for número."""
    return _lugar(config.valor("GROOV_CIDADE"), config.valor("GROOV_LAT"), config.valor("GROOV_LON"))


def mar_local() -> tuple[str, float, float] | None:
    """(praia, lat, lon) de GROOV_MAR = "nome;lat;lon"; None se faltar ou estiver quebrada."""
    partes = config.valor("GROOV_MAR").split(";")
    return _lugar(*partes) if len(partes) == 3 else None


def _buscar_json(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def tempo_do_dia(buscar=_buscar_json, timeout: float = 3) -> Tempo | None:
    """Agora + máxima, mínima e chance de chuva de hoje; None sem cidade na config ou se a rede ou a resposta falharem."""
    lugar = local()
    if lugar is None:
        return None
    try:
        dados = buscar(URL_DIA.format(lat=lugar[1], lon=lugar[2]), timeout=timeout)
        atual, dia = dados["current"], dados["daily"]
        return Tempo(round(atual["temperature_2m"]), CONDICOES.get(atual.get("weather_code")),
                     round(dia["temperature_2m_max"][0]), round(dia["temperature_2m_min"][0]),
                     round(dia["precipitation_probability_max"][0]))
    except Exception:  # rede, timeout, chave faltando ou valor None
        return None


def mar(buscar=_buscar_json, timeout: float = 3) -> Mar | None:
    praia = mar_local()
    if praia is None:
        return None
    try:
        altura = buscar(URL_MAR.format(lat=praia[1], lon=praia[2]), timeout=timeout)["current"]["wave_height"]
        return Mar(float(altura), praia[0])
    except Exception:
        return None


def temperatura_agora(buscar=_buscar_json):
    lugar = local()
    if lugar is None:
        return SEM_LOCAL
    cidade, lat, lon = lugar
    try:
        atual = buscar(URL.format(lat=lat, lon=lon))["current"]
    except Exception as erro:  # rede, timeout ou JSON inesperado: o relatório não pode quebrar
        return f"{FALHA_DO_CLIMA} ({erro})."
    texto = f"{cidade} agora: {round(atual['temperature_2m'])}°C"
    condicao = CONDICOES.get(atual.get("weather_code"))
    return f"{texto}, {condicao}." if condicao else f"{texto}."


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(temperatura_agora())
