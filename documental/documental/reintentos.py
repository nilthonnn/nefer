"""Reintentos con espera exponencial y fluctuación aleatoria.

Solo se reintentan los errores marcados como transitorios. Cualquier otro
error sube de inmediato: reintentar una clave inválida solo gasta tiempo (o,
con APIs de pago, dinero).
"""

from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

from .errores import ErrorTransitorio
from .registro import obtener

T = TypeVar("T")
log = obtener("reintentos")


def reintentar(
    funcion: Callable[[], T],
    *,
    descripcion: str,
    intentos: int = 4,
    espera_inicial: float = 2.0,
    espera_maxima: float = 30.0,
    reintentables: tuple[type[BaseException], ...] = (ErrorTransitorio,),
    dormir: Callable[[float], None] = time.sleep,
) -> T:
    """Ejecuta ``funcion`` hasta ``intentos`` veces.

    Espera ``espera_inicial * 2**n`` (+ hasta un 25 % aleatorio) entre
    intentos, con tope ``espera_maxima``. ``dormir`` se inyecta en las pruebas.
    """
    if intentos < 1:
        raise ValueError("intentos debe ser >= 1")
    for n in range(intentos):
        try:
            return funcion()
        except reintentables as error:
            if n == intentos - 1:
                log.error("%s: falló tras %d intentos: %s", descripcion, intentos, error)
                raise
            espera = min(espera_maxima, espera_inicial * (2**n))
            espera += random.uniform(0, espera * 0.25)
            log.warning("%s: intento %d/%d falló (%s); reintento en %.1f s", descripcion, n + 1, intentos, error, espera)
            dormir(espera)
    raise AssertionError("inalcanzable")
