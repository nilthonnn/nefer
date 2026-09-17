#!/usr/bin/env python3
"""FixMate en un solo archivo, para mandarlo por WhatsApp.

La app de campo vive en `docs/fixmate/app/`. Esto la deja en un `.html`
suelto con el indice de ejemplo dentro, para que quien lo reciba abra y vea
algo funcionando sin preparar nada.

Dos diferencias con el demo de las actas, y las dos a favor:

- **No lleva tipografia incrustada.** La app de actas aloja Barlow porque
  una portada de acta impresa tiene que salir igual en cualquier maquina.
  Aqui lo que importa es leer una causa raiz con guantes y a contraluz, y
  para eso la tipografia del propio telefono es tan buena y cuesta cero
  bytes. El archivo baja de 600 KB a menos de 200.
- **El indice de ejemplo no se carga solo.** Va dentro, pero detras de un
  boton que dice que es un taller inventado. Mezclado con el historial de
  verdad hacia que el tecnico leyera una orden que no existio nunca.

El archivo tiene que salir igual se arme donde se arme: una prueba compara
los bytes con uno recien hecho, y si alguien cambia la app y se olvida de
rehacerlo, se pone roja.
"""

from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
APP = RAIZ / "docs" / "fixmate" / "app" / "index.html"
CORPUS = RAIZ / "ejemplos" / "fixmate"

AVISO = """<!-- FixMate en un solo archivo, armado con
     herramientas/empaquetar-fixmate.py.

     Abralo con doble clic: no necesita internet, ni instalar nada, ni
     servidor. Trae dentro un taller de ejemplo, detras de un boton y
     rotulado como inventado; lo suyo se carga desde «Agregar historiales
     y manuales», se lee en este mismo aparato y queda guardado. -->
"""


def indice_de_ejemplo() -> str:
    """El indice del corpus de ejemplo, armado ahora y no guardado aparte.

    Guardado aparte se queda atras del corpus sin que nadie lo note, y ademas
    lleva dentro las rutas de la maquina que lo armo, que no son las de nadie.
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
    destino = (pathlib.Path(sys.argv[1]) if len(sys.argv) > 1
               else RAIZ / "docs" / "fixmate-app.html")
    html = APP.read_text(encoding="utf-8")
    if "@font-face" in html:
        raise SystemExit(
            "la app de FixMate empezo a alojar tipografia: o se incrusta "
            "aqui, o el archivo suelto se abre sin ella")

    html = html.replace("<style>", AVISO + "<style>", 1)

    hueco = '<script type="application/json" id="fixmate-indice-demo"></script>'
    if hueco not in html:
        raise SystemExit("la app ya no declara la etiqueta del indice de ejemplo")
    indice = indice_de_ejemplo()
    html = html.replace(
        hueco,
        '<script type="application/json" id="fixmate-indice-demo">'
        + indice + "</script>", 1)

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    print(f"{destino}  ·  {destino.stat().st_size / 1024:.0f} KB"
          f"  ·  indice de ejemplo de "
          f"{len(indice.encode('utf-8')) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
