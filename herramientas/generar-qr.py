#!/usr/bin/env python3
"""Rehace los codigos QR de lo publicado.

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
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TINTA = "#16191B"

# Cada QR con su direccion, su archivo y como se anuncia a un lector de
# pantalla. El de la app se imprime y se pega en el taller; el de FixMate va
# en la propia pagina, para pasar de la laptop al telefono de quien mira.
CODIGOS = [
    ("https://nilthonnn.github.io/nefer/app/",
     RAIZ / "docs" / "qr-app.svg",
     "Código QR de la app de campo",
     "Apunta a la app de campo publicada."),
    ("https://nilthonnn.github.io/nefer/fixmate/",
     RAIZ / "docs" / "fixmate" / "qr-fixmate.svg",
     "Código QR de la demo de FixMate",
     "Apunta a la demo de FixMate publicada."),
]

# Se conserva el nombre de antes: hay codigo y pruebas que lo nombran.
DIRECCION, SALIDA = CODIGOS[0][0], CODIGOS[0][1]


def main() -> int:
    try:
        import segno
    except ImportError:
        print("hace falta segno: pip install segno", file=sys.stderr)
        return 1

    for direccion, salida, etiqueta, descripcion in CODIGOS:
        salida.parent.mkdir(parents=True, exist_ok=True)
        qr = segno.make(direccion, error="m")
        qr.save(str(salida), scale=6, border=2, dark=TINTA, light=None)

        # El SVG lleva dentro, en texto, a donde apunta: asi se puede
        # comprobar sin descodificar la imagen, y un lector de pantalla lo
        # anuncia.
        svg = salida.read_text(encoding="utf-8")
        abre = '<svg xmlns="http://www.w3.org/2000/svg"'
        cierra = svg.index(">", svg.index(abre)) + 1
        cabecera = svg[:cierra].replace(
            ">",
            f' role="img" aria-label="{etiqueta}">'
            f"<title>{direccion}</title>"
            f"<desc>{descripcion} Se regenera con "
            "herramientas/generar-qr.py</desc>"
            '<rect width="100%" height="100%" fill="#FFFFFF"/>',
            1,
        )
        salida.write_text(cabecera + svg[cierra:], encoding="utf-8")
        print(f"{salida}  ·  {direccion}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
