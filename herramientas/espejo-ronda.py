#!/usr/bin/env python3
"""Copia al JavaScript de la ronda lo que decide Python, y arma la app.

La app de la ronda CIL vive en `docs/fixmate/ronda/index.html` y corre en el
telefono del operador, sin red. Decide dos cosas por su cuenta: si la ronda
quedo completa y que anomalia sale de cada punto NOK. Las mismas dos cosas
las decide `nefer/fixmate/tpm.py` cuando la oficina recibe el archivo.

Dos copias que se separan no dan error en ninguna parte: el telefono dice
que la ronda esta completa, la oficina dice que no, las dos pantallas se ven
razonables, y nadie se entera hasta que alguien compara dos listas que
tendrian que ser la misma.

    python herramientas/espejo-ronda.py            # reescribe la app
    python herramientas/espejo-ronda.py --revisar  # solo dice si esta al dia

Tambien se copia aqui LA PIEL —los tokens de color de la app de
diagnostico y la capa comun de componentes—, para que las cuatro superficies
de FixMate se vean como un solo producto y esta tenga modo claro: a 4.200 m
al sol, una pantalla oscura no se lee. Ver `herramientas/piel.py`.

Lo que se genera son los DATOS y los NUMEROS: las clases, los resultados,
las severidades, la fraccion de sospecha y la pauta de ejemplo. El
algoritmo sigue escrito a mano en los dos lenguajes, y de que hagan lo
mismo responde `tests/test_fixmate_cruce_ronda.py`, que corre este
javascript y compara sus respuestas con las de Python.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import piel as _piel                              # noqa: E402

from nefer.fixmate import anomalia as _anomalia  # noqa: E402
from nefer.fixmate import tpm as _tpm            # noqa: E402

SALIDA = RAIZ / "docs" / "fixmate" / "ronda" / "index.html"
PAUTA_EJEMPLO = RAIZ / "ejemplos" / "rcm-tpm" / "pauta-ex220.json"

PARTES = ("ronda-head.html", "ronda-reglas.js", "ronda-ui.js")


def _js(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, indent=2, sort_keys=True)


def datos() -> str:
    """Las constantes, tal como estan en Python ahora mismo."""
    return (
        "var CLASES = %s;\n"
        "var RESULTADOS = %s;\n"
        "var SEVERIDADES = %s;\n"
        "var FRACCION_SOSPECHOSA = %s;"
    ) % (
        _js(dict(_tpm.CLASES)),
        _js({k: v for k, v in _tpm.RESULTADOS.items()}),
        _js(dict(_anomalia.SEVERIDADES)),
        json.dumps(_tpm.FRACCION_SOSPECHOSA),
    )


def demo() -> str:
    """La pauta de ejemplo, embutida. Va detras de un boton que dice que el
    taller es inventado: mezclada con una pauta de verdad, hacia que el
    operador registrara una ronda sobre una maquina que no existe."""
    pauta = json.loads(PAUTA_EJEMPLO.read_text(encoding="utf-8"))
    return "var PAUTA_DEMO = %s;" % _js(pauta)


def _reemplazar(texto: str, marca: str, contenido: str) -> str:
    ini = "/* ronda:%s:inicio */" % marca
    fin = "/* ronda:%s:fin */" % marca
    a = texto.index(ini) + len(ini)
    b = texto.index(fin)
    return texto[:a] + "\n" + contenido + "\n" + texto[b:]


def construir(partes: Path) -> str:
    """La app entera, con los datos puestos."""
    trozos = [(partes / nombre).read_text(encoding="utf-8") for nombre in PARTES]
    html = "".join(trozos)
    html = _reemplazar(html, "piel", _piel.estilos())
    html = _reemplazar(html, "arranque", _piel.arranque_js())
    html = _reemplazar(html, "datos", datos())
    html = _reemplazar(html, "demo", demo())
    return html


def _instalable(html: str) -> dict:
    """Los tres archivos de la pantalla: la pagina, el manifiesto y el
    trabajador de servicio. Los tres se generan juntos porque el nombre del
    cache lleva la huella de la pagina: sueltos, el telefono se quedaria con
    una version y el sitio serviria otra."""
    return {
        SALIDA: html,
        SALIDA.parent / "manifest.webmanifest": _piel.manifiesto(
            'FixMate · Ronda CIL', 'Ronda CIL', 'La ronda de limpieza, inspección y lubricación del operador: un punto a la vez, medio minuto, y sin señal.', 'portrait-primary'),
        SALIDA.parent / "sw.js": _piel.trabajador('Ronda CIL', html),
    }


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    revisar = "--revisar" in argv
    partes = RAIZ / "herramientas" / "ronda"

    nuevo = construir(partes)
    if revisar:
        atrasados = [r for r, c in _instalable(nuevo).items()
                     if (r.read_text(encoding="utf-8") if r.exists() else "") != c]
        if not atrasados:
            print(f"{SALIDA.parent.relative_to(RAIZ)} esta al dia.")
            return 0
        print("NO estan al dia (%s): corra `python herramientas/espejo-ronda.py`."
              % ", ".join(str(r.relative_to(RAIZ)) for r in atrasados),
              file=sys.stderr)
        return 1

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    for ruta, contenido in _instalable(nuevo).items():
        ruta.write_text(contenido, encoding="utf-8")
    print(f"{SALIDA.relative_to(RAIZ)} · {len(nuevo) / 1024:.1f} KB · "
          "con manifiesto y trabajador de servicio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
