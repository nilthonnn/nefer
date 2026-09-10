#!/usr/bin/env python3
"""Arma el demo descargable: la app entera en un solo archivo.

La versión servida trae la tipografía en archivos aparte, que es lo correcto
—se guardan en caché una vez y no se vuelven a pedir—. Pero un archivo suelto
no puede llevar vecinos: si se descarga `index.html` a solas, esas rutas no
resuelven y el texto sale con la tipografía del sistema.

Aquí se incrustan como `data:` para que el demo se vea exactamente igual que
la app publicada. Cuesta un tercio más de peso, y sólo lo paga quien descarga
el archivo para probar.

    python3 herramientas/empaquetar-demo.py [destino.html]
"""

from __future__ import annotations

import base64
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
APP = RAIZ / "docs" / "app" / "index.html"


def incrustar(html: str, carpeta: pathlib.Path) -> tuple[str, int]:
    """Cambia cada src:url("tipografia/x.woff2") por su contenido en base64."""
    incrustados = 0

    def reemplazo(m: re.Match) -> str:
        nonlocal incrustados
        archivo = carpeta / m.group(1)
        if not archivo.exists():
            raise SystemExit(f"falta la tipografía: {archivo}")
        b64 = base64.b64encode(archivo.read_bytes()).decode("ascii")
        incrustados += 1
        return f'src:url("data:font/woff2;base64,{b64}") format("woff2")'

    html = re.sub(r'src:url\("(tipografia/[^"]+)"\) format\("woff2"\)',
                  reemplazo, html)
    return html, incrustados


def main() -> None:
    destino = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "nefer-app.html"
    html = APP.read_text(encoding="utf-8")
    html, cuantas = incrustar(html, APP.parent)
    if not cuantas:
        raise SystemExit("no se incrustó ninguna tipografía: ¿cambiaron las rutas?")

    aviso = ("<!-- Demo de un solo archivo, armado con herramientas/"
             "empaquetar-demo.py.\n     La tipografía va incrustada porque un "
             "archivo suelto no lleva vecinos.\n     Ojo: desde un archivo "
             "local el navegador DENIEGA el permiso de cámara\n     y no hay "
             "forma de concederlo; la app lo avisa en pantalla. Galería,\n"
             "     cámara del sistema y los entregables sí funcionan. -->\n")
    html = html.replace("<style>", aviso + "<style>", 1)

    destino.write_text(html, encoding="utf-8")
    print(f"{destino}  ·  {destino.stat().st_size / 1024:.0f} KB"
          f"  ·  {cuantas} tipografías incrustadas")


if __name__ == "__main__":
    main()
