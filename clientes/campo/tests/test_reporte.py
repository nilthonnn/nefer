"""Reporte para el grupo de WhatsApp: texto, PDF y Excel con lo mismo."""

from __future__ import annotations

import base64
import io
import shutil
import subprocess

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402

from datos_mant import EQUIPOS  # noqa: E402
from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import _contexto, _lanzar, servidor  # noqa: E402,F401

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="module")
def js(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.reporte")
    yield lambda codigo, arg=None: pg.evaluate(codigo, arg)
    nav.close()


ARMAR = """([eq, tipo, pm]) => {
  const M = MANT.modelo, m = M.clasificar(M.mantenimiento('064'), tipo, pm);
  if (eq) { m.equipo = M.normalizar.equipo(eq); m.placaConfirmada = {fecha: 'hoy', tecnico: 'T'}; }
  m.ot.ot = '4017300492';
  m.ot.horometroSalida = 6241.5;
  m.ot.observaciones = 'Inspección y limpieza de radiador\\nArranque en vacío; parámetros normales';
  m.ot.crearAviso = true;
  m.ot.textoAviso = 'Tapa de combustible sin seguro';
  m.informe.operativo = true;
  m.ot.firmas.tecnico.nombre = 'Técnico eléctrico';
  return m;
}"""


def test_el_texto_tiene_el_formato_del_grupo(js):
    eq = dict(EQUIPOS["064"], kva=100)
    m = js(ARMAR, [eq, "PREVENTIVO", "PM2_500"])
    assert js("m => MANT.reporte.texto(m)", m) == "\n".join([
        "*REPORTE DE MANTENIMIENTO PREVENTIVO PM2 (500 H) – GRUPO ELECTRÓGENO*",
        "",
        "*TAG:* 064",
        "*UBICACIÓN:* T9 – Plataforma Generadores",
        "*HORÓMETRO:* 6241.5 hrs",
        "*GRUPO:* Cummins C100D6 – Serie D19I420882",
        "*MOTOR:* Cummins 6BTA5.9-G6",
        "*VOLTAJE:* 380 Vac / 60 Hz / 100 kVA",
        "*O.T.:* 4017300492",
        "",
        "*ACTIVIDAD:*",
        "• Inspección y limpieza de radiador",
        "• Arranque en vacío",
        "• parámetros normales",
        "",
        "*OBSERVACIONES:*",
        "• Aviso: Tapa de combustible sin seguro",
        "",
        "*ESTADO DE EQUIPO:* Operativo con observaciones",
        "",
        "*Reportado por:* Técnico eléctrico",
    ])


def test_sin_placa_confirmada_no_se_inventa(js):
    m = js(ARMAR, [None, "INSPECCION", ""])
    t = js("m => MANT.reporte.texto(m)", m)
    assert t.startswith("*REPORTE DE INSPECCIÓN – GRUPO ELECTRÓGENO*")
    assert "*GRUPO:* [ leer en equipo ]" in t
    assert "*VOLTAJE:* [ leer en equipo ]" in t


@pytest.mark.parametrize("operativo,aviso,estado", [
    (True, False, "Operativo"), (True, True, "Operativo con observaciones"),
    (False, False, "Inoperativo"), (None, False, "Por confirmar"),
])
def test_estado_del_equipo_sale_de_la_aptitud(js, operativo, aviso, estado):
    m = js(ARMAR, [EQUIPOS["064"], "CORRECTIVO", ""])
    m["informe"]["operativo"] = operativo
    m["ot"]["crearAviso"] = aviso
    assert js("m => MANT.reporte.estado(MANT.modelo.normalizar.mantenimiento(m))", m) == estado


def _bytes(js, expr, m):
    b64 = js(f"""async m => {{ const b = await Promise.resolve({expr}(m));
      const u = new Uint8Array(await b.arrayBuffer()); let s = '';
      for (let i = 0; i < u.length; i++) s += String.fromCharCode(u[i]); return btoa(s); }}""", m)
    return base64.b64decode(b64)


def test_pdf_y_excel_dicen_lo_mismo(js, tmp_path):
    m = js(ARMAR, [EQUIPOS["064"], "PREVENTIVO", "PM2_500"])
    pdf = _bytes(js, "MANT.reporte.pdf", m)
    assert pdf.startswith(b"%PDF-") and pdf.rstrip().endswith(b"%%EOF")
    if shutil.which("pdftotext"):
        ruta = tmp_path / "r.pdf"
        ruta.write_bytes(pdf)
        texto = subprocess.run(["pdftotext", str(ruta), "-"], capture_output=True, text=True).stdout
        for esperado in ("PREVENTIVO PM2", "064", "D19I420882", "Operativo con observaciones",
                         "Tapa de combustible"):
            assert esperado in texto, esperado

    openpyxl = pytest.importorskip("openpyxl")
    libro = openpyxl.load_workbook(io.BytesIO(_bytes(js, "MANT.reporte.xlsx", m)))
    filas = {r[0]: r[1] for r in libro.active.iter_rows(values_only=True)}
    assert filas["Campo"] == "Valor"
    assert filas["TAG"] == "064"
    assert filas["O.T."] == "4017300492"
    assert filas["ESTADO DE EQUIPO"] == "Operativo con observaciones"
    assert filas["OBSERVACIÓN 1"] == "Aviso: Tapa de combustible sin seguro"
    assert js("m => MANT.reporte.nombre(m, 'pdf')", m) == "reporte-064-OT4017300492.pdf"


def test_en_la_orden_se_copia_y_se_descarga(pw, servidor):
    nav = _lanzar(pw)
    ctx = nav.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True,
                          permissions=["clipboard-read", "clipboard-write"])
    pg = ctx.new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["064"])
    pg.evaluate("() => MANT.ordenes.crear('064', 'INSPECCION', '', '4017300900')")
    pg.click("#tab-mantenimiento")
    pg.wait_for_selector("#m-orden:not([hidden])")
    assert pg.input_value("#m-o-wa").startswith("*REPORTE DE INSPECCIÓN")
    pg.fill("#m-o-ot-firmas-tecnico-nombre", "Técnico mecánico")
    assert "*Reportado por:* Técnico mecánico" in pg.input_value("#m-o-wa"), "se actualiza al escribir"

    pg.click("[data-accion=wa-copiar]")
    pg.wait_for_function("() => /Copiado/.test(document.querySelector('#m-o-wa-estado').textContent)")
    assert pg.evaluate("() => navigator.clipboard.readText()") == pg.input_value("#m-o-wa")

    for accion, ext in (("wa-pdf", ".pdf"), ("wa-excel", ".xlsx")):
        with pg.expect_download() as d:
            pg.click(f"[data-accion={accion}]")
        assert d.value.suggested_filename == "reporte-064-OT4017300900" + ext
    nav.close()
