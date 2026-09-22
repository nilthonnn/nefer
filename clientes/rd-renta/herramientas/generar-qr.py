#!/usr/bin/env python3
"""Rehace los codigos QR que llevan la app al telefono.

El QR es lo que convierte «instalela en el telefono» en algo que se hace en el
patio: se imprime, se pega en el taller, y cada operario lo escanea. Se guardan
ya generados —el sitio no puede depender de un servicio de terceros para
dibujarlos, y el proyecto no tiene por que arrastrar una dependencia para
servir un dibujo que no cambia.

Solo hace falta `segno` para REGENERARLOS, no para usarlos:

    pip install segno
    python herramientas/generar-qr.py

Si una direccion cambia, se cambia en la tabla de abajo y se vuelve a
ejecutar; las pruebas avisan si se olvida.
"""

from __future__ import annotations

import sys
import xml.dom.minidom
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TINTA = "#16191B"

# (direccion, archivo, que es). El archivo va dentro de `docs/`; de ahi lo
# recoge publicar-clon.py del proyecto de origen.
CODIGOS = [
    ("https://nilthonnn.github.io/nefer/rd-rental/app/",
     "docs/qr-app.svg",
     "la app de campo de RD RENTAL publicada"),
    ("https://github.com/nilthonnn/nefer/releases/download/android/rd-rental-actas.apk",
     "docs/qr-apk.svg",
     "la aplicacion de Android de RD RENTAL, para descargar e instalar"),
]


def anotar(svg: str, direccion: str, que_es: str) -> str:
    """Mete dentro del dibujo, en texto, a donde apunta.

    Asi se puede comprobar sin descodificar la imagen, y un lector de pantalla
    lo anuncia en vez de callarse.

    Ojo con donde se corta: el archivo empieza por la declaracion `<?xml ...?>`,
    que tambien acaba en `>`. Lo que hay que abrir es la etiqueta `<svg`, y no
    la primera que aparezca.
    """
    abre = svg.index("<svg")
    cierra = svg.index(">", abre)
    etiqueta_svg = svg[abre:cierra]          # sin el `>` final
    return (
        svg[:abre]
        + etiqueta_svg
        + f' role="img" aria-label="Código QR de {que_es}">'
        + f"<title>{direccion}</title>"
        + f"<desc>Apunta a {que_es}. Se regenera con "
        + "herramientas/generar-qr.py</desc>"
        + '<rect width="100%" height="100%" fill="#FFFFFF"/>'
        + svg[cierra + 1:]
    )


def main() -> int:
    try:
        import segno
    except ImportError:
        print("hace falta segno: pip install segno", file=sys.stderr)
        return 1

    for direccion, relativa, que_es in CODIGOS:
        salida = RAIZ / relativa
        salida.parent.mkdir(parents=True, exist_ok=True)
        # Correccion media: la hoja impresa se arruga y se mancha, y un QR con
        # margen de error corto deja de leerse a la primera.
        qr = segno.make(direccion, error="m")
        qr.save(str(salida), scale=6, border=2, dark=TINTA, light=None)

        salida.write_text(
            anotar(salida.read_text(encoding="utf-8"), direccion, que_es),
            encoding="utf-8")

        # Un SVG mal cerrado no da error: simplemente no se dibuja, y nadie se
        # entera hasta que un operario se queda mirando un hueco en blanco.
        xml.dom.minidom.parse(str(salida))
        print(f"{relativa}  ·  {direccion}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
