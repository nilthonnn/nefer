#!/usr/bin/env python3
"""Rehace el codigo QR que lleva a la app publicada.

El QR es lo que convierte «instalela en el telefono» en algo que se hace en el
patio: se imprime, se pega en el taller, y cada operario lo escanea y la
instala. Se guarda ya generado en `docs/qr-app.svg` —el sitio no puede
depender de un servicio de terceros para dibujarlo, y el proyecto no tiene por
que arrastrar una dependencia para servir un dibujo que no cambia.

Solo hace falta `segno` para REGENERARLO, no para usarlo:

    pip install segno
    python herramientas/generar-qr.py

Si la direccion publicada cambia, se cambia aqui y se vuelve a ejecutar; la
prueba `test_el_qr_apunta_a_la_direccion_publicada` avisa si se olvida.
"""

from __future__ import annotations

import sys
import xml.dom.minidom
from pathlib import Path

DIRECCION = "https://nilthonnn.github.io/nefer/app/"
SALIDA = Path(__file__).resolve().parents[1] / "docs" / "qr-app.svg"
TINTA = "#16191B"


def main() -> int:
    try:
        import segno
    except ImportError:
        print("hace falta segno: pip install segno", file=sys.stderr)
        return 1

    qr = segno.make(DIRECCION, error="m")
    qr.save(str(SALIDA), scale=6, border=2, dark=TINTA, light=None)

    # El SVG lleva dentro, en texto, a donde apunta: asi se puede comprobar sin
    # tener que descodificar la imagen, y un lector de pantalla lo anuncia.
    #
    # El corte se hace sobre la etiqueta `<svg>`, no sobre el primer `>` del
    # archivo: el primero es el de la declaracion XML, y escribir ahi deja un
    # archivo que ningun navegador dibuja. Asi estuvo, y el QR impreso no se
    # veia; la prueba no lo cazo porque buscaba el titulo con una expresion
    # regular, y en un archivo mal formado el titulo sigue estando.
    svg = SALIDA.read_text(encoding="utf-8")
    abre = svg.index("<svg")
    cierra = svg.index(">", abre) + 1
    etiqueta = svg[abre:cierra].replace(
        ">", ' role="img" aria-label="Código QR de la app de campo">', 1)
    dentro = (
        f"<title>{DIRECCION}</title>"
        "<desc>Apunta a la app de campo publicada. Se regenera con "
        "herramientas/generar-qr.py</desc>"
        '<rect width="100%" height="100%" fill="#FFFFFF"/>'
    )
    SALIDA.write_text(svg[:abre] + etiqueta + dentro + svg[cierra:], encoding="utf-8")

    # Un SVG mal formado no se dibuja. Se comprueba aqui para que el fallo
    # salga al rehacerlo, y no cuando alguien escanee el papel de la pared.
    xml.dom.minidom.parse(str(SALIDA))
    print(f"{SALIDA}  ·  {DIRECCION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
