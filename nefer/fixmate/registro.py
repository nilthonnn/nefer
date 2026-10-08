"""Lo que hace que un registro sea un registro, y no una nota.

Un solo asunto por ahora, y es el que mas vale: la fecha.

«03/04/2026» en Lima es el 3 de abril y en Houston el 4 de marzo, y dos años
despues nadie puede decir cual era. Peor: una fecha que el programa no sabe
leer no da error, da SILENCIO —`dias_abierta()` devolvia `None` y la anomalia
desaparecia de la cuenta de atrasos sin que nadie se enterara—. Aqui se exige
ISO 8601 (AAAA-MM-DD) o nada: un dato faltante se ve, uno ambiguo no.

Vive aparte porque la necesitan los tres registros del sistema —el analisis
RCM, la ejecucion de la ronda y la anomalia— y cada uno lanza su propio
error. La regla es una sola; el error, el de quien llama.
"""

from __future__ import annotations

import re
from datetime import date as _date

FORMATO = "AAAA-MM-DD"
_PATRON = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def fecha(valor: str, donde: str, error: type = ValueError) -> str:
    """La fecha, en ISO 8601, o vacia. Cualquier otra cosa es un error.

    Vacia se admite a proposito: es «no se declaro», que es informacion
    honesta y que los informes de calidad cuentan. Lo que no se admite es
    «15/03/2026», que parece una fecha y no se puede auditar.
    """
    valor = str(valor or "").strip()
    if not valor:
        return ""
    if not _PATRON.match(valor):
        raise error(
            f"{donde}: la fecha «{valor}» no esta en formato ISO 8601 "
            f"({FORMATO}). Una fecha ambigua en un registro no se puede "
            "auditar despues.")
    try:
        _date.fromisoformat(valor)
    except ValueError as exc:
        raise error(f"{donde}: la fecha «{valor}» no existe ({exc}).") from exc
    return valor
