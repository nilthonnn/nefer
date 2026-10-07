"""La piel de FixMate: de donde sacan el color todas las pantallas.

FixMate tiene cuatro superficies —la pagina de entrada, la app de
diagnostico, la ronda CIL del operador y el analisis RCM de la oficina— y
hasta aqui tenia dos paletas: la de la app, clara y oscura segun el aparato,
y una azul marino propia de las dos pantallas nuevas, sin modo claro.

No es un asunto de gusto. El tecnico que diagnostica, el operador que hace la
ronda y el ingeniero que decide la estrategia hablan entre ellos de la misma
maquina; si cada pantalla parece de otro programa, la primera pregunta de
cada reunion es cual de las tres tiene el dato bueno. Y el modo claro no es
decoracion: a 4.200 m al sol, una pantalla oscura no se lee.

LA FUENTE DE VERDAD ES LA APP. Los tokens se SACAN de
`docs/fixmate/app/index.html`, entre sus marcas, y se copian a las demas. Es
la superficie que mas gente mira y la que lleva mas tiempo probada: el color
manda ahi y se obedece en las otras. Si alguien cambia la paleta de la app,
las otras pantallas cambian al regenerarlas y una prueba avisa si no se
regeneraron.

Encima de los tokens va `piel/base.css`, la capa comun de componentes
—barra, botones, tarjetas, chips, avisos—, escrita sin un solo color propio.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "docs" / "fixmate" / "app" / "index.html"
BASE = Path(__file__).resolve().parent / "piel" / "base.css"
BARRA_JS = Path(__file__).resolve().parent / "piel" / "barra.js"

INICIO = "/* fixmate:piel:inicio"
FIN = "/* fixmate:piel:fin */"


def tokens() -> str:
    """Los tokens tal como estan en la app ahora mismo."""
    html = APP.read_text(encoding="utf-8")
    m = re.search(re.escape(INICIO) + r".*?\*/(.*?)" + re.escape(FIN), html, re.S)
    if not m:
        raise SystemExit(
            f"no se encontraron las marcas de la piel en {APP.relative_to(RAIZ)}: "
            "sin ellas las demas pantallas no saben de donde copiar el color.")
    return m.group(1).strip("\n")


def base() -> str:
    return BASE.read_text(encoding="utf-8").strip("\n")


def estilos() -> str:
    """Lo que va dentro de las marcas de piel de cada pantalla."""
    return (
        "/* Generado por herramientas/piel.py desde docs/fixmate/app/index.html.\n"
        " * No editar aqui: se reescribe. */\n"
        + tokens() + "\n\n" + base()
    )


def barra_js() -> str:
    return BARRA_JS.read_text(encoding="utf-8").strip("\n")


# Las pantallas generadas reciben la piel al armarse (`espejo-ronda.py`,
# `espejo-rcm.py`). La pagina de entrada no se genera: se escribe a mano, y
# por eso la piel se le pone con esto.
DESTINOS = (RAIZ / "docs" / "fixmate" / "index.html",)

MARCA_INI = "/* piel:inicio */"
MARCA_FIN = "/* piel:fin */"


def _con_piel(texto: str, contenido: str) -> str:
    a = texto.index(MARCA_INI) + len(MARCA_INI)
    b = texto.index(MARCA_FIN)
    return texto[:a] + "\n" + contenido + "\n  " + texto[b:]


def main(argv=None) -> int:
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)
    revisar = "--revisar" in argv
    salida = 0
    for destino in DESTINOS:
        actual = destino.read_text(encoding="utf-8")
        nuevo = _con_piel(actual, tokens())
        if revisar:
            if actual != nuevo:
                print(f"{destino.relative_to(RAIZ)} NO esta al dia: corra "
                      "`python herramientas/piel.py`.", file=sys.stderr)
                salida = 1
            else:
                print(f"{destino.relative_to(RAIZ)} esta al dia.")
            continue
        destino.write_text(nuevo, encoding="utf-8")
        print(f"{destino.relative_to(RAIZ)} · piel puesta")
    return salida


if __name__ == "__main__":
    raise SystemExit(main())
