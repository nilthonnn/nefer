#!/usr/bin/env python3
"""Copia al JavaScript de la pantalla RCM lo que decide Python, y la arma.

La pantalla de analisis RCM vive en `docs/fixmate/rcm/index.html` y es
trabajo de oficina: se abre un analisis, el equipo contesta el arbol de
decision de SAE JA1011 y la pantalla muestra a donde lleva cada respuesta.
Decide tres cosas por su cuenta: la estrategia de cada modo de falla, el
informe de completitud de las siete preguntas y el resumen del tablero. Las
mismas tres las deciden `nefer/fixmate/decision.py` y `rcm.py` cuando el
archivo vuelve a la oficina.

    python herramientas/espejo-rcm.py            # reescribe la pantalla
    python herramientas/espejo-rcm.py --revisar  # solo dice si esta al dia

Lo que se genera son los DATOS y los TEXTOS LARGOS: las seis estrategias,
cuales son acciones por defecto, las clases de consecuencia, las siete
preguntas de la norma y los tres avisos. El arbol sigue escrito a mano en los
dos lenguajes, y de que decida lo mismo responde
`tests/test_fixmate_cruce_rcm.py`, que corre este javascript sobre las 729
combinaciones de respuestas por cada clase de consecuencia —evidente y
oculta— y compara dictamen por dictamen.

Aqui el cruce importa mas que en ninguna otra parte de FixMate. Un arbol que
se separa no da error en ningun lado: la pantalla dice «operar hasta la
falla» y la oficina dice «rediseño obligatorio» sobre el mismo modo de falla
de seguridad, las dos se ven razonables, y la que queda firmada es la que
alguien imprimio primero.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from nefer.fixmate import criticidad as _criticidad  # noqa: E402
from nefer.fixmate import decision as _decision      # noqa: E402
from nefer.fixmate import rcm as _rcm                # noqa: E402

SALIDA = RAIZ / "docs" / "fixmate" / "rcm" / "index.html"
ANALISIS_EJEMPLO = RAIZ / "ejemplos" / "rcm-tpm" / "analisis-ex220.json"

PARTES = ("rcm-head.html", "rcm-reglas.js", "rcm-ui.js")


def _js(valor, ordenar: bool = False) -> str:
    return json.dumps(valor, ensure_ascii=False, indent=2, sort_keys=ordenar)


def datos() -> str:
    """Las constantes, tal como estan en Python ahora mismo.

    `ESTRATEGIAS` y `PREGUNTAS` salen SIN ordenar a proposito: el orden de las
    seis estrategias y el de las siete preguntas es informacion, no detalle de
    serializacion. Las pertenencias (`POR_DEFECTO`, `PROACTIVAS`, `CRITICAS`)
    son conjuntos en Python y salen ordenadas para que el archivo generado no
    cambie de una corrida a otra.
    """
    return (
        "var ESTRATEGIAS = %s;\n"
        "var POR_DEFECTO = %s;\n"
        "var PROACTIVAS = %s;\n"
        "var CLASES_CONSECUENCIA = %s;\n"
        "var CONSECUENCIAS_GRAVES = %s;\n"
        "var PREGUNTAS = %s;\n"
        "var CRITICAS = %s;\n"
        "var SIN_DATOS_ECONOMICOS = %s;\n"
        "var AVISO_SIN_EVALUAR = %s;\n"
        "var AVISO_89 = %s;\n"
        "var ADVERTENCIA_RPN = %s;"
    ) % (
        _js(dict(_decision.ESTRATEGIAS)),
        _js(sorted(_decision.POR_DEFECTO)),
        _js(sorted(_decision.PROACTIVAS)),
        _js(list(_rcm.CLASES_CONSECUENCIA)),
        _js(sorted(_rcm.CONSECUENCIAS_GRAVES)),
        _js([{"numero": p.numero, "clave": p.clave, "texto": p.texto,
              "responde": p.responde} for p in _rcm.PREGUNTAS]),
        _js(sorted(_rcm.CRITICAS)),
        _js(_decision.SIN_DATOS_ECONOMICOS),
        _js(_decision.AVISO_SIN_EVALUAR),
        _js(_decision.AVISO_89),
        _js(_criticidad.ADVERTENCIA_RPN),
    )


def demo() -> str:
    """El analisis de ejemplo, embutido. Va detras de un boton que dice que el
    equipo es inventado: un analisis RCM que se ve completo sobre una maquina
    que no existe es exactamente la clase de documento que alguien firma."""
    analisis = json.loads(ANALISIS_EJEMPLO.read_text(encoding="utf-8"))
    return "var ANALISIS_DEMO = %s;" % _js(analisis)


def _reemplazar(texto: str, marca: str, contenido: str) -> str:
    ini = "/* rcm:%s:inicio */" % marca
    fin = "/* rcm:%s:fin */" % marca
    a = texto.index(ini) + len(ini)
    b = texto.index(fin)
    return texto[:a] + "\n" + contenido + "\n" + texto[b:]


def construir(partes: Path) -> str:
    """La pantalla entera, con los datos puestos."""
    trozos = [(partes / nombre).read_text(encoding="utf-8") for nombre in PARTES]
    html = "".join(trozos)
    html = _reemplazar(html, "datos", datos())
    html = _reemplazar(html, "demo", demo())
    return html


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    revisar = "--revisar" in argv
    partes = RAIZ / "herramientas" / "rcm"

    nuevo = construir(partes)
    if revisar:
        actual = SALIDA.read_text(encoding="utf-8") if SALIDA.exists() else ""
        if actual == nuevo:
            print(f"{SALIDA.relative_to(RAIZ)} esta al dia.")
            return 0
        print(f"{SALIDA.relative_to(RAIZ)} NO esta al dia: corra "
              "`python herramientas/espejo-rcm.py`.", file=sys.stderr)
        return 1

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(nuevo, encoding="utf-8")
    print(f"{SALIDA.relative_to(RAIZ)} · {len(nuevo) / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
