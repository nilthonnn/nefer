"""El código QR que lleva a la app publicada.

El QR es lo que convierte «instálela en el teléfono» en algo que se hace en la
playa de faenado: se imprime, se pega, y cada quien lo escanea. Se guarda ya
generado porque el sitio no puede depender de un servicio de terceros para
dibujarlo, y el proyecto no tiene por qué arrastrar una dependencia para servir
un dibujo que no cambia.

Sólo hace falta `segno` para REHACERLO, no para usarlo:

    pip install segno
    python3 demos/camal/qr.py
"""

from __future__ import annotations

import sys
from pathlib import Path

DIRECCION = "https://nilthonnn.github.io/nefer/camal/"
SALIDA = Path(__file__).resolve().parents[2] / "docs" / "camal" / "qr.svg"
TINTA = "#12151B"


def anotar(svg: str) -> str:
    """Mete título y descripción DENTRO de la etiqueta `<svg>`.

    Se busca el cierre de esa etiqueta y no el primer `>` del archivo: el
    primero es el de la declaración XML, y escribir ahí deja un archivo que
    ningún navegador abre. Así salió el primer intento, y el QR no se veía.
    """
    abre = svg.index("<svg")
    cierra = svg.index(">", abre) + 1
    dentro = (
        f"<title>{DIRECCION}</title>"
        "<desc>Apunta a la app de pesaje del camal. Se rehace con "
        "demos/camal/qr.py</desc>"
        '<rect width="100%" height="100%" fill="#FFFFFF"/>'
    )
    etiqueta = svg[abre:cierra].replace(
        ">", ' role="img" aria-label="Código QR de la app del camal">', 1)
    return svg[:abre] + etiqueta + dentro + svg[cierra:]


def main() -> int:
    try:
        import segno
    except ImportError:
        print("hace falta segno: pip install segno", file=sys.stderr)
        return 1

    segno.make(DIRECCION, error="m").save(
        str(SALIDA), scale=6, border=2, dark=TINTA, light=None)
    SALIDA.write_text(anotar(SALIDA.read_text(encoding="utf-8")), encoding="utf-8")

    # Un SVG mal formado no se ve, y eso no se nota hasta que alguien escanea.
    import xml.dom.minidom
    xml.dom.minidom.parse(str(SALIDA))

    print(f"{SALIDA}  ·  {DIRECCION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
