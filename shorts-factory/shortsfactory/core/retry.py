"""Reintentos con espera exponencial para llamadas puntuales (HTTP, subidas).

La FSM reintenta etapas completas; esto reintenta UNA llamada dentro de una
etapa, para no rehacer trabajo caro (p. ej. una subida a medias).
"""

from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

from ..errors import ErrorTransitorio
from ..logs import obtener

T = TypeVar("T")
log = obtener("retry")


def reintentar(
    fn: Callable[[], T],
    descripcion: str,
    intentos: int = 4,
    espera_inicial: float = 1.5,
    espera_maxima: float = 30.0,
    dormir: Callable[[float], None] = time.sleep,
) -> T:
    for n in range(1, intentos + 1):
        try:
            return fn()
        except ErrorTransitorio as e:
            if n == intentos:
                raise
            espera = min(espera_maxima, espera_inicial * 2 ** (n - 1))
            espera += random.uniform(0, espera * 0.25)
            log.warning("%s: intento %d/%d falló (%s); reintento en %.1f s", descripcion, n, intentos, e, espera)
            dormir(espera)
    raise AssertionError("inalcanzable")
