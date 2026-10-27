"""Paginación de subtítulos cinéticos (estilo "Hormozi").

Se muestran 1–3 palabras a la vez; la palabra que se está diciendo se
resalta y las palabras de énfasis llevan el color de acento. Una página
nunca cruza un punto ni un silencio largo, y nunca se solapa con la
siguiente (dos páginas a la vez se leen como ruido).
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from ..models import PalabraT


class Pagina(BaseModel):
    inicio: float
    fin: float
    palabras: list[PalabraT]


def paginar(palabras: list[PalabraT], por_pagina: int, hueco: float = 0.35) -> list[Pagina]:
    paginas: list[list[PalabraT]] = []
    actual: list[PalabraT] = []
    for p in palabras:
        if actual and (len(actual) >= por_pagina or p.inicio - actual[-1].fin > hueco):
            paginas.append(actual)
            actual = []
        actual.append(p)
        if re.search(r"[.!?…:]$", p.texto):
            paginas.append(actual)
            actual = []
    if actual:
        paginas.append(actual)

    salida: list[Pagina] = []
    for i, grupo in enumerate(paginas):
        fin = grupo[-1].fin + 0.12
        if i + 1 < len(paginas):
            fin = min(fin, paginas[i + 1][0].inicio)
        # Redondeo de ambos extremos: si no, 0.8999… > 0.9 y dos páginas se solapan.
        salida.append(Pagina(inicio=round(grupo[0].inicio, 3), fin=round(fin, 3), palabras=grupo))
    return salida
