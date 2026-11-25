#!/usr/bin/env python3
"""Mide el lector de fotos de la app contra fotos reales de campo.

Corre el MISMO lector que usa el teléfono (Tesseract en el navegador, con los
archivos de docs/app/lector) sobre una carpeta de fotos, y compara lo que
propone con lo que de verdad dice cada foto.

    python herramientas/medir-lector.py CARPETA [--salida DIR]

CARPETA tiene las fotos, nombradas NN_<casilla>.jpg (p. ej. 03_c21.jpg, la
casilla del probador), y un verdad.json:

    {"_tags": ["064", "CE5760"],                 # TAG que tienen ficha
     "_fichas": [{"tag": "064", "grupo": {"modelo": "C100D6", "serie": "…"}}],  # opcional
     "_tag_de": {"09_c05.jpg": "064"},            # opcional: de qué equipo es cada foto
     "03_c21.jpg": {"probador.soh": 72, "probador.soc": 100}}

Sin `_fichas` se mide el lector solo; con ellas, también el autoaprendizaje
que corrige lo leído contra las fichas del teléfono.

Las fotos son del cliente: la carpeta se queda en la computadora, NUNCA en el
repositorio. Lo que sí va al repositorio son los casos de prueba en texto
(tests/test_lector.py), con los números de serie alterados.
"""

from __future__ import annotations

import argparse
import base64
import functools
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tests"))


def igual(a, b):
    if isinstance(b, (int, float)) and a is not None:
        try:
            return abs(float(a) - float(b)) < 0.06
        except (TypeError, ValueError):
            return False
    return str(a).replace(" ", "").upper() == str(b).replace(" ", "").upper()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("carpeta", type=Path)
    ap.add_argument("--salida", type=Path, help="deja aquí el texto leído de cada foto")
    a = ap.parse_args()

    from playwright.sync_api import sync_playwright
    from navegador import opciones

    verdad = json.loads((a.carpeta / "verdad.json").read_text(encoding="utf-8"))
    tags = verdad.pop("_tags", [])
    fichas = verdad.pop("_fichas", [])
    tag_de = verdad.pop("_tag_de", {})
    manejador = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(RAIZ / "docs" / "app"))
    manejador.log_message = lambda *x, **k: None
    srv = socketserver.TCPServer(("127.0.0.1", 0), manejador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    total = aciertos = 0
    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        pg = nav.new_page()
        pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/")
        pg.wait_for_function("() => window.MANT && MANT.lector")
        for nombre, esperado in verdad.items():
            casilla = nombre.split("_", 1)[1].split(".")[0]
            b64 = base64.b64encode((a.carpeta / nombre).read_bytes()).decode()
            r = pg.evaluate("""async ([b64, casilla, tags, fichas, tag]) => {
                const bin = atob(b64), u = new Uint8Array(bin.length);
                for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
                const t0 = performance.now();
                const l = await MANT.lector.leerFoto(new Blob([u], {type: 'image/jpeg'}), casilla, {tags, fichas, tag});
                return {texto: l.texto, giro: l.giro, ms: Math.round(performance.now() - t0),
                        props: l.propuestas.map(p => [p.ruta, p.valor])};
            }""", [b64, casilla, tags, fichas, tag_de.get(nombre)])
            propuestas = dict(r["props"])
            bien = [k for k, v in esperado.items() if igual(propuestas.get(k), v)]
            total += len(esperado)
            aciertos += len(bien)
            print(f"{nombre:14} {len(bien)}/{len(esperado)}  giro {r['giro']:>3}°  {r['ms'] / 1000:4.1f} s")
            for k, v in esperado.items():
                if k not in bien:
                    print(f"{'':16}✗ {k}: esperado {v!r}, propuso {propuestas.get(k)!r}")
            if a.salida:
                a.salida.mkdir(parents=True, exist_ok=True)
                (a.salida / (nombre + ".txt")).write_text(r["texto"], encoding="utf-8")
        nav.close()
    srv.shutdown()
    print(f"\nTOTAL {aciertos}/{total} campos ({100 * aciertos / max(total, 1):.0f} %)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
