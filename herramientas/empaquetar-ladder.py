#!/usr/bin/env python3
"""Arma las descargas de LadderLab a partir de `docs/ladder/`.

Salen dos archivos en `docs/ladder/descargas/`:

- **LadderLab.html** — la app entera en UN archivo: lecciones, simulador,
  estilos e icono van dentro. Es la que se abre en Android. Un HTML que llega
  al teléfono se abre desde Descargas como `content://`, y desde ahí Chrome
  no puede cargar los archivos de al lado (`lecciones.js`, `energia.js`): la
  versión en carpeta se queda en blanco. En un solo archivo no hay nada al
  lado que cargar.
- **LadderLab-demo.zip** — para computadora: la carpeta de la app con el
  manual, el archivo único, el manual en PDF y un LEEME.

Las dos salidas son reproducibles: con las mismas fuentes dan los mismos bytes
(el zip lleva fecha fija). Así la integración puede volver a armarlas y exigir
que coincidan con las del repositorio, y una descarga vieja no pasa inadvertida.

El PDF del manual no se genera aquí, porque hace falta un navegador. Se toma
el que está en `descargas/` (`tests/test_ladder_android.py` comprueba que
existe).
"""

from __future__ import annotations

import base64
import re
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "docs" / "ladder"
DESCARGAS = APP / "descargas"
PDF = DESCARGAS / "Manual-de-uso-LadderLab.pdf"
WEB = "https://nilthonnn.github.io/nefer/ladder/"
FECHA_FIJA = (2026, 11, 7, 0, 0, 0)

# Lo que forma la app en carpeta. El trabajador de servicio va igual: en una
# computadora con servidor local sirve; abierto como archivo no se registra.
PIEZAS = ["index.html", "lecciones.js", "energia.js", "manifest.webmanifest",
          "sw.js", "icono.svg", "icono-192.png", "icono-512.png",
          "AUDITORIA-FUNCIONAL.md", "AUDITORIA-ANDROID.md"]

LEEME = """LadderLab - Ladder (LAD) para TIA Portal, con ruta de grupos electrogenos y mineria
====================================================================================

EN UN CELULAR ANDROID
  Opcion 1 - instalar la app (recomendada): descarga el APK desde
     https://github.com/nilthonnn/nefer/releases?q=ladderlab&expanded=true
     abre el archivo .apk y acepta "instalar desde esta fuente".
  Opcion 2 - sin instalar: abre "LadderLab.html" (esta en la raiz de este .zip)
     desde Archivos o Descargas, y elige Chrome si pregunta con que abrirlo.
     Es la app entera en un solo archivo.
  NO abras "LadderLab/index.html" en el celular: Android no deja que esa pagina
  cargue los archivos de al lado y se queda en blanco.

EN UNA COMPUTADORA (Windows, Mac o Linux)
  1. Descomprime todo este .zip en una carpeta (no lo abras desde dentro del .zip).
  2. Haz doble clic en "LadderLab.html", o en "LadderLab/index.html".
  3. Se abre en tu navegador (Chrome, Edge, Firefox o Safari). No necesita internet.

EN LINEA
  {web}  (en Chrome, menu > "Instalar app" o "Agregar a pantalla de inicio")

QUE TRAE
  - 24 lecciones: basico, intermedio, avanzado y "Grupos y mineria".
  - PLC simulado con ciclo de scan de 10 ms, editor grafico de segmentos LAD y HMI.
  - 20 retos que se corrigen solos, 9 de ellos contra un modelo de planta.
  - Laboratorio libre (exporta e importa programas .json) y referencia de instrucciones.

DOCUMENTOS
  - Manual-de-uso-LadderLab.pdf ...... manual completo con capturas.
  - LadderLab/manual/index.html ...... el mismo manual, para leer en el navegador.
  - LadderLab/AUDITORIA-FUNCIONAL.md . auditoria contra normas internacionales.

TU PROGRESO
  Se guarda en el navegador, en este equipo. No se envia a ningun servidor.
  Abierto desde un archivo en Android puede no guardarse entre visitas: para
  conservar el progreso usa el APK o la version en linea instalada.

TIA Portal, SIMATIC y S7 son marcas de Siemens AG. LadderLab es una herramienta de
estudio independiente: no reemplaza a TIA Portal ni a S7-PLCSIM.
""".format(web=WEB)


def _en_linea(js: str) -> str:
    """Un script para ir dentro de <script>: que no lo cierre antes de tiempo."""
    if re.search(r"</script", js, re.I):
        js = re.sub(r"</(script)", r"<\\/\1", js, flags=re.I)
    return js


def archivo_unico() -> str:
    html = (APP / "index.html").read_text(encoding="utf-8")

    def cambiar(viejo: str, nuevo: str) -> None:
        nonlocal html
        if viejo not in html:
            sys.exit(f"empaquetar-ladder: no encuentro en index.html: {viejo[:60]!r}")
        html = html.replace(viejo, nuevo)

    for js in ("lecciones.js", "energia.js"):
        codigo = _en_linea((APP / js).read_text(encoding="utf-8"))
        cambiar(f'<script src="{js}"></script>', f"<script>\n{codigo}\n</script>")
    svg = base64.b64encode((APP / "icono.svg").read_bytes()).decode("ascii")
    cambiar('<link rel="icon" href="icono.svg" type="image/svg+xml">',
            f'<link rel="icon" href="data:image/svg+xml;base64,{svg}" type="image/svg+xml">')
    # El manifiesto y el icono de iOS son archivos de al lado: aquí no existen.
    cambiar('<link rel="manifest" href="manifest.webmanifest">\n', "")
    cambiar('<link rel="apple-touch-icon" href="icono-192.png">\n', "")
    # El manual no viaja dentro: se abre en línea.
    html = html.replace('href="manual/index.html"', f'href="{WEB}manual/index.html"')
    cambiar("const UN_ARCHIVO = false;", "const UN_ARCHIVO = true;")
    # Los enlaces a `descargas/` siguen en el texto, pero UN_ARCHIVO los oculta.
    for resto in ('src="lecciones.js"', 'src="energia.js"', 'href="manual/', 'href="icono'):
        if resto in html:
            sys.exit(f"empaquetar-ladder: quedó una referencia a un archivo de al lado: {resto}")
    return html


def _agregar(z: zipfile.ZipFile, nombre: str, datos: bytes) -> None:
    info = zipfile.ZipInfo(nombre, FECHA_FIJA)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, datos)


def main() -> int:
    DESCARGAS.mkdir(exist_ok=True)
    unico = archivo_unico().encode("utf-8")
    (DESCARGAS / "LadderLab.html").write_bytes(unico)

    if not PDF.exists():
        sys.exit(f"empaquetar-ladder: falta {PDF.relative_to(RAIZ)}")
    raiz = "LadderLab-demo/"
    with zipfile.ZipFile(DESCARGAS / "LadderLab-demo.zip", "w") as z:
        _agregar(z, raiz + "LEEME.txt", LEEME.encode("utf-8"))
        _agregar(z, raiz + "LadderLab.html", unico)
        _agregar(z, raiz + PDF.name, PDF.read_bytes())
        for pieza in PIEZAS:
            _agregar(z, raiz + "LadderLab/" + pieza, (APP / pieza).read_bytes())
        for img in sorted((APP / "manual").iterdir()):
            _agregar(z, raiz + "LadderLab/manual/" + img.name, img.read_bytes())

    for f in ("LadderLab.html", "LadderLab-demo.zip"):
        print(f"{f}: {(DESCARGAS / f).stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
