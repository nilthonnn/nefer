"""Guiones editoriales: escritos por una persona, con las cifras ligadas a la serie real.

Es la vía más sólida ante la revisión del YPP: el ángulo y las frases son
de autoría humana, y los números no se teclean a mano, los pone la serie
(así nunca quedan desactualizados ni mal copiados). El archivo JSON es un
``Guion`` normal con dos añadidos:

- ``datos``: ``{"indicador": "TX.VAL.TECH.MF.ZS", "pais": "WLD"}`` fija la serie
  (si falta, se elige por el tema como siempre);
- huecos en el texto que se rellenan con la serie:
  ``{primero} {anio_primero} {ultimo} {anio_ultimo} {maximo} {anio_maximo}
  {minimo} {anio_minimo} {cambio} {verbo} {pais} {indicador}``.

El resultado pasa por las MISMAS heurísticas que un guion de LLM.
"""

from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Any

from ..errors import ErrorContenido
from ..models import Guion, Serie

HUECOS = ("primero", "anio_primero", "ultimo", "anio_ultimo", "maximo", "anio_maximo",
          "minimo", "anio_minimo", "cambio", "verbo", "pais", "indicador")


def leer(ruta: Path) -> dict[str, Any]:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ErrorContenido(f"No se pudo leer el guion editorial {ruta}: {e}") from e
    if not isinstance(datos, dict) or "frases" not in datos:
        raise ErrorContenido(f"{ruta}: falta 'frases'")
    return datos


def cifra(valor: float) -> str:
    """Como lo diría el guion: 1 decimal, coma decimal, sin ceros sobrantes."""
    return f"{valor:.1f}".rstrip("0").rstrip(".").replace(".", ",")


def valores(serie: Serie) -> dict[str, str]:
    p0, p1 = serie.puntos[0], serie.ultimo
    alto = max(serie.puntos, key=lambda p: p.valor)
    bajo = min(serie.puntos, key=lambda p: p.valor)
    cambio = abs((p1.valor - p0.valor) / p0.valor * 100) if p0.valor else 0.0
    return {
        "primero": cifra(p0.valor), "anio_primero": str(p0.anio),
        "ultimo": cifra(p1.valor), "anio_ultimo": str(p1.anio),
        "maximo": cifra(alto.valor), "anio_maximo": str(alto.anio),
        "minimo": cifra(bajo.valor), "anio_minimo": str(bajo.anio),
        "cambio": cifra(cambio),
        "verbo": "subió" if p1.valor > p0.valor else "bajó" if p1.valor < p0.valor else "se mantuvo",
        "pais": serie.pais_nombre, "indicador": serie.indicador.lower(),
    }


def construir(datos: dict[str, Any], serie: Serie) -> Guion:
    v = valores(serie)

    def rellenar(texto: str) -> str:
        usados = {n for _, n, _, _ in string.Formatter().parse(texto) if n}
        desconocidos = usados - set(HUECOS)
        if desconocidos:
            raise ErrorContenido(f"Huecos desconocidos en el guion: {sorted(desconocidos)}; válidos: {', '.join(HUECOS)}")
        return texto.format(**v)

    crudo = {k: val for k, val in datos.items() if k != "datos"}
    crudo["titulo"] = rellenar(crudo.get("titulo", ""))
    crudo["descripcion"] = rellenar(crudo.get("descripcion", ""))
    crudo["frases"] = [{**f, "texto": rellenar(f["texto"]), "enfasis": [rellenar(e) for e in f.get("enfasis", [])]}
                       for f in crudo["frases"]]
    crudo["generador"] = "editorial"
    try:
        return Guion.model_validate(crudo)
    except ValueError as e:
        raise ErrorContenido(f"El guion editorial no cumple el esquema: {e}") from e
