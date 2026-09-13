#!/usr/bin/env python3
"""Copia la app de un clon dentro de `docs/`, que es lo unico que publica Pages.

GitHub Pages sirve la carpeta `docs/` de la raiz y nada mas: una app que vive
en `clientes/<cliente>/docs/` no llega al telefono de nadie. Este script la
deja en `docs/<cliente>/`, desde donde el sitio ya publicado la sirve sin
tocar ningun ajuste.

    python3 herramientas/publicar-clon.py

La prueba `tests/test_publicacion_clon.py` compara las dos carpetas y falla si
la publicada se queda atras. Despues de tocar la app del clon, se ejecuta esto.
"""

from __future__ import annotations

import filecmp
import pathlib
import shutil
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]

# (lo que se copia, donde se publica). La direccion publicada resultante es
# https://<usuario>.github.io/<repo>/<destino>/app/
CLONES = [("clientes/rd-renta/docs", "docs/rd-rental")]


def publicar(origen: pathlib.Path, destino: pathlib.Path) -> tuple[int, int]:
    if not origen.is_dir():
        raise SystemExit(f"no existe la carpeta del clon: {origen}")

    copiados = 0
    quiero = set()
    for archivo in sorted(origen.rglob("*")):
        if archivo.is_dir():
            continue
        relativa = archivo.relative_to(origen)
        quiero.add(relativa)
        fuera = destino / relativa
        fuera.parent.mkdir(parents=True, exist_ok=True)
        # Copiar solo lo que cambio deja el historial limpio: si nada cambio,
        # `git status` no tiene nada que decir.
        if not fuera.exists() or not filecmp.cmp(archivo, fuera, shallow=False):
            shutil.copy2(archivo, fuera)
            copiados += 1

    # Lo que ya no esta en el clon tampoco puede seguir publicado.
    sobran = 0
    if destino.is_dir():
        for archivo in sorted(destino.rglob("*"), reverse=True):
            if archivo.is_file() and archivo.relative_to(destino) not in quiero:
                archivo.unlink()
                sobran += 1
            elif archivo.is_dir() and not any(archivo.iterdir()):
                archivo.rmdir()
    return copiados, sobran


def main() -> int:
    for origen, destino in CLONES:
        copiados, sobran = publicar(RAIZ / origen, RAIZ / destino)
        print(f"{origen}  ->  {destino}  ·  {copiados} copiados, {sobran} retirados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
