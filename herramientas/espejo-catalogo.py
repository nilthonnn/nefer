#!/usr/bin/env python3
"""Copia el catalogo de causas de Python al JavaScript de la app.

El telefono clasifica sin red, con su propia copia del catalogo escrita en
JavaScript dentro de `docs/fixmate/app/index.html`. Dos copias que se separan
no dan error en ninguna parte: el telefono agrupa una causa y la oficina la
agrupa distinto, los dos informes se ven razonables, y nadie se entera hasta
que alguien compara dos listas que tendrian que ser la misma.

Mientras el espejo se escribio a mano, separarse era solo cuestion de tiempo:
treinta y seis entradas y doscientas pistas no se copian a mano sin errarle a
una. Asi que se genera, y `tests/test_fixmate_espejo.py` falla cuando lo que
esta en el archivo no es lo que sale de aqui.

    python herramientas/espejo-catalogo.py            # lo reescribe
    python herramientas/espejo-catalogo.py --revisar   # solo dice si esta al dia

Lo generado son los datos y los numeros; el algoritmo sigue escrito a mano en
las dos, y de que hagan lo mismo responde `tests/test_fixmate_cruce.py`, que
corre el JavaScript de la app y compara sus respuestas con las de Python.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from nefer.fixmate import catalogo as cat  # noqa: E402

APP = RAIZ / "docs" / "fixmate" / "app" / "index.html"

ABRE = "  // ---- espejo del catalogo: lo genera herramientas/espejo-catalogo.py"
CIERRA = "  // ---- fin del espejo del catalogo"

# El JSON de Python ya escapa a \uXXXX con ensure_ascii, que es justo lo que
# conviene dentro del HTML: la «ñ» de «dañados» no depende de que el servidor
# acierte con el charset.
def _js(valor) -> str:
    return json.dumps(valor, ensure_ascii=True)


def bloque() -> str:
    """El trozo de JavaScript que le corresponde al catalogo de hoy."""
    lineas = [
        ABRE,
        "  // No se edita a mano: se corre la herramienta y se vuelve a commitear.",
        f"  var CAT_MINIMO_PISTAS = {cat.MINIMO_PISTAS};",
        f"  var CAT_MINIMO_PREFIJO = {cat.MINIMO_PARA_PREFIJO};",
        f"  var CAT_PESO_INEQUIVOCA = {cat.PESO_INEQUIVOCA};",
        f"  var CAT_PESO_DE_UNA_SOLA = {cat.PESO_DE_UNA_SOLA};",
        f"  var CAT_PESO_DE_DOS = {cat.PESO_DE_DOS};",
        f"  var CAT_PESO_GENERICA = {cat.PESO_GENERICA};",
        f"  var CAT_INEQUIVOCAS = {_js(sorted(cat.INEQUIVOCAS))};",
        f"  var CAT_PLANIFICADO = {_js(list(cat.PLANIFICADO))};",
        "  var CAT_ENTRADAS = [",
    ]
    for entrada in cat.POR_DEFECTO.entradas:
        lineas.append("    [%s, %s, %s]," % (_js(entrada.codigo), _js(entrada.causa),
                                             _js(list(entrada.pistas))))
    lineas += ["  ];", CIERRA]
    return "\n".join(lineas) + "\n"


def _partes(texto: str) -> tuple[str, str]:
    """Lo de antes y lo de despues del espejo, con los marcadores fuera."""
    i = texto.find(ABRE)
    j = texto.find(CIERRA)
    if i < 0 or j < 0:
        raise SystemExit(
            f"{APP.name}: no encuentro los marcadores del espejo. Tienen que "
            f"estar, tal cual, estas dos lineas:\n{ABRE}\n{CIERRA}")
    return texto[:i], texto[j + len(CIERRA) + 1:]


def main(argv: list[str]) -> int:
    texto = APP.read_text(encoding="utf-8")
    antes, despues = _partes(texto)
    nuevo = antes + bloque() + despues
    if "--revisar" in argv:
        if nuevo == texto:
            print(f"{APP.relative_to(RAIZ)}: el espejo esta al dia.")
            return 0
        print(f"{APP.relative_to(RAIZ)}: el espejo quedo viejo. Correr "
              "«python herramientas/espejo-catalogo.py».")
        return 1
    if nuevo == texto:
        print(f"{APP.relative_to(RAIZ)}: ya estaba al dia.")
        return 0
    APP.write_text(nuevo, encoding="utf-8")
    print(f"{APP.relative_to(RAIZ)}: espejo rehecho, "
          f"{len(cat.POR_DEFECTO)} entradas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
