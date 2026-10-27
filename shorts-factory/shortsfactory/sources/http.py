"""GET HTTP con clasificación de errores (transitorio vs definitivo) y reintentos."""

from __future__ import annotations

from typing import Any

import requests

from ..core.retry import reintentar
from ..errors import ErrorConfiguracion, ErrorTransitorio

AGENTE = "ShortsFactory/0.1 (+https://github.com/)"


def obtener_json(url: str, params: dict | None = None, headers: dict | None = None,
                 sesion: requests.Session | None = None, timeout: float = 20) -> Any:
    cliente = sesion or requests.Session()

    def una_vez() -> Any:
        try:
            r = cliente.get(url, params=params, headers={"User-Agent": AGENTE, **(headers or {})}, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as e:
            raise ErrorTransitorio(f"sin conexión con {url.split('/')[2]}: {type(e).__name__}") from e
        host = url.split("/")[2]
        if r.status_code in (408, 429) or r.status_code >= 500:
            raise ErrorTransitorio(f"{host} respondió {r.status_code}")
        if r.status_code in (401, 403):
            raise ErrorConfiguracion(f"{host} rechazó la credencial ({r.status_code})")
        if r.status_code != 200:
            raise ErrorConfiguracion(f"{host} respondió {r.status_code}: {r.text[:200]}")
        try:
            return r.json()
        except ValueError as e:
            raise ErrorTransitorio(f"{host} devolvió JSON incompleto") from e

    return reintentar(una_vez, f"GET {url.split('?')[0]}")
