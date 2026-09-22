"""Los codigos QR que llevan la app al telefono tienen que poder dibujarse.

Un SVG mal cerrado no da error en ninguna parte: el navegador simplemente no lo
pinta, y lo que queda en la pagina es un hueco en blanco donde deberia estar el
codigo. Nadie se entera hasta que un operario intenta escanear la hoja pegada
en el taller.

Se rehacen con `python herramientas/generar-qr.py`.
"""

from __future__ import annotations

import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SVG = "{http://www.w3.org/2000/svg}"


# Cada proyecto hace sus codigos con su propia herramienta; aqui se comprueban
# todos, porque todos acaban impresos en la misma pared del taller.
HERRAMIENTAS = [
    RAIZ / "herramientas" / "generar-qr.py",
    RAIZ / "clientes" / "rd-renta" / "herramientas" / "generar-qr.py",
]


def _codigos():
    todos = []
    for ruta in HERRAMIENTAS:
        spec = importlib.util.spec_from_file_location("generar_qr_" + ruta.parent.parent.name, ruta)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        base = ruta.parent.parent.relative_to(RAIZ)
        for direccion, relativa, que_es in modulo.CODIGOS:
            todos.append((direccion, str(base / relativa) if str(base) != "." else relativa,
                          que_es))
    return todos


@pytest.mark.parametrize("direccion,relativa,que_es", _codigos())
def test_el_codigo_qr_es_un_dibujo_valido(direccion, relativa, que_es):
    archivo = RAIZ / relativa
    assert archivo.is_file(), f"falta {relativa}"

    # Si esto levanta, el navegador tampoco lo dibuja.
    raiz = ET.parse(archivo).getroot()
    assert raiz.tag == SVG + "svg"

    # Y tiene que decir, en texto, a donde lleva: se comprueba sin descodificar
    # la imagen, y un lector de pantalla lo anuncia en vez de callarse.
    titulos = [t.text for t in raiz.iter(SVG + "title")]
    assert direccion in titulos, f"{relativa} no declara {direccion}"
    assert raiz.get("role") == "img"
    assert raiz.get("aria-label")


def test_la_pagina_del_clon_ensena_los_codigos_que_existen():
    """Un `<img>` a un archivo que no esta deja el mismo hueco en blanco."""
    portada = RAIZ / "clientes" / "rd-renta" / "docs" / "index.html"
    texto = portada.read_text(encoding="utf-8")
    for nombre in ("qr-app.svg", "qr-apk.svg"):
        assert f'src="{nombre}"' in texto, f"la portada no ensena {nombre}"
        assert (portada.parent / nombre).is_file(), f"falta {nombre}"
