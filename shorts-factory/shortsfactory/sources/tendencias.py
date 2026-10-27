"""Tendencias en tiempo real: Hacker News (tecnología) y GDELT (economía en español).

Ambas APIs son públicas y sin clave. El selector descarta lo que ya se
cubrió (memoria del canal) y lo que no es de tecnología/economía.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import requests

from ..errors import ShortsError
from ..logs import obtener
from ..memory import similitud
from ..models import Tendencia
from .http import obtener_json
from .worldbank import normalizar

log = obtener("tendencias")
HN = "https://hacker-news.firebaseio.com/v0"
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"

TEMAS = (
    "ia", "inteligencia artificial", "chip", "chips", "semiconductor", "nvidia", "openai", "apple", "google",
    "inflacion", "dolar", "economia", "banco central", "tasas", "recesion", "aranceles", "bitcoin", "empleo",
    "ai", "gpu", "startup", "energy", "battery", "tariff", "inflation", "economy", "market", "rates",
)


def hackernews(n: int = 30, sesion: requests.Session | None = None) -> list[Tendencia]:
    ids = obtener_json(f"{HN}/topstories.json", sesion=sesion)[:n]
    with ThreadPoolExecutor(8) as pool:
        items = list(pool.map(lambda i: obtener_json(f"{HN}/item/{i}.json", sesion=sesion), ids))
    return [Tendencia(titulo=it["title"], url=it.get("url", ""), fuente="hackernews", puntaje=float(it.get("score", 0)))
            for it in items if isinstance(it, dict) and it.get("title")]


def gdelt(sesion: requests.Session | None = None) -> list[Tendencia]:
    consulta = '(economía OR inflación OR "banco central" OR aranceles OR "inteligencia artificial" OR semiconductores) sourcelang:spanish'
    datos = obtener_json(GDELT, params={"query": consulta, "mode": "artlist", "format": "json",
                                        "maxrecords": 50, "timespan": "1d", "sort": "hybridrel"}, sesion=sesion)
    articulos = datos.get("articles", []) if isinstance(datos, dict) else []
    n = len(articulos)
    return [Tendencia(titulo=a["title"], url=a.get("url", ""), fuente="gdelt", puntaje=float(n - i))
            for i, a in enumerate(articulos) if a.get("title")]


def relevante(t: Tendencia) -> bool:
    texto = f" {normalizar(t.titulo)} "
    return any(f" {k} " in texto for k in TEMAS)


def elegir(candidatas: list[Tendencia], cubiertos: list[str], umbral: float = 0.3) -> Tendencia:
    """La más popular que sea del nicho y no se parezca a temas ya cubiertos."""
    for t in sorted(candidatas, key=lambda t: t.puntaje, reverse=True):
        if not relevante(t):
            continue
        if any(similitud(normalizar(t.titulo), normalizar(c)) > umbral for c in cubiertos):
            log.debug("descartada (ya cubierta): %s", t.titulo)
            continue
        return t
    raise ShortsError("Ninguna tendencia nueva de tecnología/economía; usa --topic")


def buscar(cubiertos: list[str], sesion: requests.Session | None = None) -> Tendencia:
    candidatas: list[Tendencia] = []
    for nombre, fuente in (("gdelt", gdelt), ("hackernews", hackernews)):
        try:
            candidatas += fuente(sesion=sesion)
        except ShortsError as e:  # una fuente caída no detiene a la otra
            log.warning("fuente de tendencias %s no disponible: %s", nombre, e)
    if not candidatas:
        raise ShortsError("No respondió ninguna fuente de tendencias")
    return elegir(candidatas, cubiertos)
