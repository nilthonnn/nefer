"""La app genera el Excel y el PDF dentro del telefono.

Es una segunda implementacion del mismo formato que produce `nefer construir`.
Dos implementaciones se separan con el tiempo, asi que aqui se comprueban las
dos cosas: que la geometria copiada siga coincidiendo con la de layout.py, y
que los archivos que salen del navegador los abran los lectores de verdad.
"""

from __future__ import annotations

import io
import json
import os
import re
import zipfile
from pathlib import Path

import pytest

from nefer import build, layout

APP = Path(__file__).resolve().parents[1] / "docs" / "app" / "index.html"
FUENTE = APP.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# que las dos implementaciones no se separen
# --------------------------------------------------------------------------

def _constante_js(nombre: str) -> str:
    m = re.search(rf"\b{nombre}:\s*([^,\n]+)", FUENTE)
    assert m, f"no se encontro {nombre} en la app"
    return m.group(1).strip().strip('"')


def _var_js(nombre: str) -> str:
    """Lee `var X = 11` o `var A = 1, X = 11, B = 2`, que asi estan declaradas."""
    m = re.search(rf"\b{nombre}\s*=\s*([0-9.]+)", FUENTE)
    assert m, f"no se encontro {nombre} en la app"
    return m.group(1)


def test_geometria_compartida_con_layout():
    """Las cifras que la app copio de layout.py siguen siendo las mismas."""
    assert int(_constante_js("BLOQUES_FOTO_POR_PAGINA")) == build.BLOQUES_FOTO_POR_PAGINA
    assert int(_constante_js("BLOQUES_CONSUMIBLE_POR_PAGINA")) == \
        build.BLOQUES_CONSUMIBLE_POR_PAGINA
    assert _constante_js("CODIGO_FORMATO") == layout.CODIGO_FORMATO
    assert _constante_js("VERSION_FORMATO") == layout.VERSION_FORMATO
    assert _constante_js("TITULO_COMPARATIVO") == layout.TITULO_COMPARATIVO
    assert _constante_js("TITULO_DANOS") == layout.TITULO_DANOS

    assert int(_var_js("FILA_INICIO_FOTOS")) == layout.FILA_INICIO_FOTOS
    assert int(_var_js("ALTO_BLOQUE_FOTO")) == layout.ALTO_BLOQUE_FOTO
    assert int(_var_js("FILAS_IMAGEN")) == layout.FILAS_IMAGEN
    assert float(_var_js("ALTO_FILA_ESTANDAR")) == layout.ALTO_FILA_ESTANDAR
    assert float(_var_js("ALTO_FILA_ROTULO")) == layout.ALTO_FILA_ROTULO
    assert float(_var_js("ALTO_FILA_SEPARADOR")) == layout.ALTO_FILA_SEPARADOR


def test_anchos_de_columna_compartidos():
    bloque = re.search(r"var ANCHOS_COLUMNA = \{(.*?)\};", FUENTE, re.S)
    assert bloque, "no se encontro la tabla de anchos en la app"
    leidos = {c: float(v) for c, v in re.findall(r"([A-Z]):([\d.]+)", bloque.group(1))}
    assert leidos == layout.ANCHOS_COLUMNA


def test_paneles_compartidos():
    assert re.search(r'var PANEL_IZQ = \["A", "L"\]', FUENTE)
    assert re.search(r'PANEL_DER = \["M", "Z"\]', FUENTE)
    assert layout.PANEL_IZQ == ("A", "L")
    assert layout.PANEL_DER == ("M", "Z")


# --------------------------------------------------------------------------
# los archivos que salen del navegador
# --------------------------------------------------------------------------

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402

CHROME = next(
    (r for r in (
        os.environ.get("NEFER_CHROMIUM"),
        "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    ) if r and Path(r).exists()),
    None,
)


@pytest.fixture(scope="module")
def entregables(tmp_path_factory):
    """Arma el acta de ejemplo y descarga el PDF y el Excel, una sola vez."""
    if CHROME is None:
        pytest.skip("no hay Chromium disponible")
    destino = tmp_path_factory.mktemp("entregables")
    salida = {}
    fallos: list[str] = []

    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=CHROME)
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True,
                              accept_downloads=True, permissions=[])
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fallos.append(str(e)))
        pg.goto(APP.as_uri())
        pg.wait_for_timeout(600)
        pg.click("#btn-demo")
        pg.wait_for_timeout(2500)
        assert pg.eval_on_selector_all("#d-grid .slot.lleno", "n => n.length") == 10

        for boton, clave in (("#d-pdf", "pdf"), ("#d-xlsx", "xlsx")):
            with pg.expect_download(timeout=60000) as espera:
                pg.click(boton)
            bajado = espera.value
            ruta = destino / bajado.suggested_filename
            bajado.save_as(ruta)
            salida[clave] = ruta
        nav.close()

    assert fallos == [], fallos
    return salida


def test_el_pdf_es_valido_y_lleva_el_acta(entregables):
    datos = entregables["pdf"].read_bytes()
    assert datos.startswith(b"%PDF-")
    assert datos.rstrip().endswith(b"%%EOF")

    # Ocho fotos por pagina: diez fotos y un accesorio caben en dos.
    assert datos.count(b"/Type /Page\n") or datos.count(b"/Type /Page ")
    paginas = len(re.findall(rb"/Type /Page[^s]", datos))
    assert paginas == 2, paginas

    # Cada foto entra como JPEG incrustado, sin recodificar en el lector.
    assert len(re.findall(rb"/Subtype /Image", datos)) == 10

    texto = _texto_de_pdf(entregables["pdf"])
    if texto is None:
        pytest.skip("pdftotext no esta disponible")
    for esperado in ("REPORTE FOTOGRÁFICO", "004-001155", "MINERA EJEMPLO S.A.C.",
                     "GE-0142", "1548.7", "VISTA LATERAL IZQUIERDA", "HORÓMETRO"):
        assert esperado in texto, esperado


def _texto_de_pdf(ruta: Path):
    import shutil
    import subprocess
    if not shutil.which("pdftotext"):
        return None
    return subprocess.run(["pdftotext", str(ruta), "-"],
                          capture_output=True, text=True).stdout


def test_el_excel_lo_abre_openpyxl_con_sus_fotos(entregables):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(entregables["xlsx"])
    ws = wb.active

    assert ws.title == "REPORTE"
    assert len(ws._images) == 10

    assert ws[layout.CELDA_ACTA].value == "004-001155"
    assert ws[layout.CELDA_CLIENTE].value == "MINERA EJEMPLO S.A.C."
    assert ws[layout.CELDA_CODIGO].value == "GE-0142"

    # Los rotulos caen en las filas que dicta layout.bloque_foto.
    esperados = ["VISTA FRONTAL", "VISTA POSTERIOR", "VISTA LATERAL IZQUIERDA",
                 "VISTA LATERAL DERECHA"]
    leidos = []
    for franja in range(2):
        fila = layout.bloque_foto(franja)["fila_rotulo"]
        leidos.append(ws[f"{layout.PANEL_IZQ[0]}{fila}"].value)
        leidos.append(ws[f"{layout.PANEL_DER[0]}{fila}"].value)
    assert leidos == esperados


def test_el_excel_pagina_como_el_formato(entregables):
    """Sin saltos, Excel imprime la hoja entera escalada y el formato se pierde."""
    with zipfile.ZipFile(entregables["xlsx"]) as z:
        hoja = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    cortes = [int(m) for m in re.findall(r'<brk id="(\d+)"', hoja)]
    # Diez fotos son cinco franjas: un corte tras la cuarta.
    esperado = layout.FILA_INICIO_FOTOS + \
        layout.ALTO_BLOQUE_FOTO * build.BLOQUES_FOTO_POR_PAGINA - 1
    assert cortes == [esperado], cortes


def test_el_excel_lo_abre_libreoffice(entregables, tmp_path):
    """El lector que usa la oficina: si LibreOffice no lo abre, no sirve."""
    import shutil
    import subprocess
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        pytest.skip("LibreOffice no esta instalado")

    perfil = tmp_path / "perfil"
    r = subprocess.run(
        [soffice, "-env:UserInstallation=file://" + str(perfil), "--headless",
         "--convert-to", "pdf", "--outdir", str(tmp_path), str(entregables["xlsx"])],
        capture_output=True, text=True, timeout=180)
    salida = tmp_path / (entregables["xlsx"].stem + ".pdf")
    assert salida.exists(), r.stdout + r.stderr
    assert salida.stat().st_size > 20_000
