#!/usr/bin/env python3
"""Arma el demo descargable: la app entera en un solo archivo.

Con el índice de ejemplo dentro, para que la pestaña de diagnóstico funcione
en el archivo suelto: es lo que se manda por WhatsApp, y sin índice esa
pestaña sólo sabría pedir uno que el que lo recibe no tiene.

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
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
APP = RAIZ / "docs" / "app" / "index.html"
CORPUS = RAIZ / "ejemplos" / "fixmate"


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


def indice_de_ejemplo() -> str:
    """El corpus de ejemplo, ya indexado, listo para incrustar.

    Se arma aquí en vez de guardarlo hecho en el repositorio: un índice
    guardado se queda atrás del corpus sin que nadie lo note, y además lleva
    dentro las rutas de la máquina que lo armó, que no son las de nadie más.
    """
    sys.path.insert(0, str(RAIZ))
    from nefer.fixmate import Indice, Motor, actualizar

    indice = Indice()
    actualizar(indice, [CORPUS])
    indice.medicion = Motor(indice).medicion()

    datos = {
        "version": 1,
        "embebedor": indice.embebedor.nombre,
        "dimension": indice.embebedor.dimension,
        "medicion": indice.medicion,
        # Sin las rutas de esta máquina: el archivo tiene que salir igual se
        # arme donde se arme, y una prueba compara los bytes.
        "fuentes": {},
        "fragmentos": [],
    }
    for fragmento in indice.fragmentos:
        d = fragmento.a_dict()
        d["metadatos"] = {k: v for k, v in d["metadatos"].items()
                          if not k.startswith("_")}
        datos["fragmentos"].append(d)
    return json.dumps(datos, ensure_ascii=False, separators=(",", ":"))


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

    # El índice va dentro de la etiqueta que la app ya declara vacía: el
    # navegador no la ejecuta y la pestaña de diagnóstico lo encuentra ahí
    # cuando no hay ninguno guardado.
    indice = indice_de_ejemplo()
    hueco = '<script type="application/json" id="fixmate-indice-demo"></script>'
    if hueco not in html:
        raise SystemExit("la app ya no declara la etiqueta del índice de ejemplo")
    html = html.replace(
        hueco,
        '<script type="application/json" id="fixmate-indice-demo">'
        + indice + "</script>", 1)

    destino.write_text(html, encoding="utf-8")
    print(f"{destino}  ·  {destino.stat().st_size / 1024:.0f} KB"
          f"  ·  {cuantas} tipografías incrustadas"
          f"  ·  índice de ejemplo de {len(indice) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
