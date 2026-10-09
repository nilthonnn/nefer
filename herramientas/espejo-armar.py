#!/usr/bin/env python3
"""Copia al JavaScript de «Armar» las reglas de carga de Python, y arma la app.

Esta pantalla es la que faltaba. FixMate sabia LEER una pauta y un analisis
—validarlos, sacar la matriz FMECA, el plan de tareas, el informe de
calidad—, pero no sabia ESCRIBIRLOS: las dos pantallas de campo abren un
`.json` que hasta hoy solo podia producir alguien que conociera el esquema y
lo tecleara a mano en un editor de texto. Con eso, el unico analisis que un
usuario real podia ver era el de ejemplo, y el producto era un demo con el
formulario escondido.

De aqui sale el archivo que abren las otras dos pantallas, asi que la regla
no se negocia: ESTA PANTALLA NO PUEDE PRODUCIR UN ARCHIVO QUE EL RESTO DE
FIXMATE RECHACE. Si lo produjera, el error aparecería con la pauta ya bajada
y el operador ya en la maquina.

Lo que se genera son los DATOS: las cinco clases de punto, las frecuencias,
las clases de consecuencia, los tipos de funcion, los estados de validacion,
las fuentes de evidencia y el catalogo de fallas entero. El algoritmo
—quien acepta y quien rechaza— sigue escrito a mano en los dos lenguajes, y
de que digan lo mismo responde `tests/test_fixmate_cruce_armar.py`, que corre
este javascript con node, le hace armar el archivo y se lo da a los
cargadores de Python.

    python herramientas/espejo-armar.py            # reescribe la app
    python herramientas/espejo-armar.py --revisar  # solo dice si esta al dia
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import piel as _piel                               # noqa: E402

from nefer.fixmate import catalogo as _catalogo     # noqa: E402
from nefer.fixmate import rcm as _rcm               # noqa: E402
from nefer.fixmate import registro as _registro     # noqa: E402
from nefer.fixmate import tpm as _tpm               # noqa: E402

SALIDA = RAIZ / "docs" / "fixmate" / "armar" / "index.html"

PARTES = ("armar-head.html", "armar-reglas.js", "armar-ui.js")


def _js(valor) -> str:
    """Ordenado por clave: el catalogo son 41 entradas y un diff estable vale."""
    return json.dumps(valor, ensure_ascii=False, indent=2, sort_keys=True)


def _orden(valor) -> str:
    """Sin ordenar, para lo que lleva el orden escrito a proposito.

    Las cinco clases de punto no estan en orden alfabetico en `tpm.py`:
    «limpiar» va primera porque limpiar ES inspeccionar —la fuga y el perno
    flojo se ven cuando se quita la mugre—. Ordenarlas aqui las dejaba al
    azar en el desplegable y borraba eso.
    """
    return json.dumps(valor, ensure_ascii=False, indent=2)


def datos() -> str:
    """Las constantes, tal como estan en Python ahora mismo.

    El catalogo va entero —las 41 entradas con su causa, su sistema y su
    mecanismo— porque el codigo se ELIGE de una lista, nunca se escribe. Un
    codigo tecleado que no existe revienta en el cargador, y lo haria con el
    archivo ya bajado.
    """
    entradas = {
        e.codigo: {"causa": e.causa, "sistema": e.sistema,
                   "mecanismo": e.mecanismo}
        for e in _catalogo.POR_DEFECTO.entradas
    }
    return (
        "var CLASES = %s;\n"
        "var FRECUENCIAS = %s;\n"
        "var CLASES_CONSECUENCIA = %s;\n"
        "var CONSECUENCIAS_GRAVES = %s;\n"
        "var TIPOS_FUNCION = %s;\n"
        "var ESTADOS_VALIDACION = %s;\n"
        "var FUENTES = %s;\n"
        "var CATALOGO = %s;\n"
        "var FORMATO_FECHA = %s;"
    ) % (
        _orden(dict(_tpm.CLASES)),
        _js(list(_tpm.FRECUENCIAS)),
        _js(list(_rcm.CLASES_CONSECUENCIA)),
        _js(sorted(_rcm.CONSECUENCIAS_GRAVES)),
        _js(list(_rcm.TIPOS_FUNCION)),
        _js(list(_rcm.ESTADOS_VALIDACION)),
        _js(list(_rcm.FUENTES)),
        _js(entradas),
        _js(_registro.FORMATO),
    )


def _reemplazar(texto: str, marca: str, contenido: str) -> str:
    ini = "/* armar:%s:inicio */" % marca
    fin = "/* armar:%s:fin */" % marca
    a = texto.index(ini) + len(ini)
    b = texto.index(fin)
    return texto[:a] + "\n" + contenido + "\n" + texto[b:]


def construir(partes: Path) -> str:
    trozos = [(partes / nombre).read_text(encoding="utf-8") for nombre in PARTES]
    html = "".join(trozos)
    html = _reemplazar(html, "piel", _piel.estilos())
    html = _reemplazar(html, "arranque", _piel.arranque_js())
    html = _reemplazar(html, "datos", datos())
    return html


def _instalable(html: str) -> dict:
    """Los tres archivos de la pantalla: la pagina, el manifiesto y el
    trabajador de servicio. Los tres se generan juntos porque el nombre del
    cache lleva la huella de la pagina."""
    return {
        SALIDA: html,
        SALIDA.parent / "manifest.webmanifest": _piel.manifiesto(
            'FixMate · Armar', 'Armar',
            'Escribir la pauta de la ronda y el análisis RCM: de aquí sale el '
            'archivo que abren las otras dos pantallas.'),
        SALIDA.parent / "sw.js": _piel.trabajador('Armar', html),
    }


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    revisar = "--revisar" in argv
    partes = RAIZ / "herramientas" / "armar"

    nuevo = construir(partes)
    if revisar:
        atrasados = [r for r, c in _instalable(nuevo).items()
                     if (r.read_text(encoding="utf-8") if r.exists() else "") != c]
        if not atrasados:
            print(f"{SALIDA.parent.relative_to(RAIZ)} esta al dia.")
            return 0
        print("NO estan al dia (%s): corra `python herramientas/espejo-armar.py`."
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
