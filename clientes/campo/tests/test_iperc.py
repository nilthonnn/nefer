"""IPERC continuo, como la hoja de campo (sección V).

Las seis actividades de las hojas llenadas en campo, con sus peligros,
riesgos, evaluación inicial y residual y medidas de control; las demás del
mantenimiento, marcadas «Propuesta: validar con SSOMA». El técnico elige las
actividades de hoy (o las sugeridas para el tipo de servicio), confirma que
las medidas están aplicadas (queda la hora) y puede agregar otros peligros.
Avisa, no bloquea: un residual A o S es crítico. Sale en el PDF.
"""

from __future__ import annotations

import base64
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


def _orden(pw, servidor, modo=None):
    nav = _lanzar(pw)
    pg = _contexto(nav, movil=True, modo=modo).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["064"])
    pg.evaluate("() => MANT.ordenes.crear('064', 'PREVENTIVO', 'PM1_250', '4017305001')")
    pg.click("#tab-mantenimiento")
    pg.wait_for_selector("#m-orden:not([hidden])")
    return nav, pg


def test_el_catalogo_trae_las_hojas_de_campo(pw, servidor):
    nav, pg = _orden(pw, servidor)
    f = pg.evaluate("() => MANT.modelo.filasIperc('desenergizar')")
    assert len(f) == 1 and f[0]["paso"] == "Desenergización y bloqueo del grupo electrógeno"
    assert (f[0]["inicial"], f[0]["residual"]) == ({"n": 13, "nivel": "S"}, {"n": 9, "nivel": "M"})
    assert "Colocar puesta a tierra temporal" in f[0]["medidas"] and not f[0]["propuesta"]
    assert pg.evaluate("() => MANT.modelo.filasIperc('baterias')[0].propuesta") is True
    sug = pg.evaluate("() => MANT.modelo.ipercSugerido({tipo: 'PREVENTIVO', pm: 'PM3_1000'})")
    assert "refrigerante" in sug and "aceite" in sug and "desenergizar" in sug
    nav.close()


def test_en_seguridad_elige_confirma_y_agrega(pw, servidor):
    nav, pg = _orden(pw, servidor)
    pg.click("[data-accion=g-paso][data-n='1']")
    alertas = pg.evaluate("() => MANT.ordenes.alertas().map(a => a.mensaje)")
    assert any("IPERC continuo sin actividades" in a for a in alertas)
    pg.click("[data-accion=iperc-sugerido]")
    n = pg.evaluate("() => MANT.ordenes.actual().iperc.filas.length")
    assert n >= 15
    # Quitar y volver a poner una actividad.
    pg.click("[data-iperc-act=radiador]")
    assert pg.evaluate("() => MANT.ordenes.actual().iperc.filas.some(r => r.actividad === 'radiador')") is False
    pg.click("[data-iperc-act=radiador]")
    pg.locator("[data-iperc-ok]").first.click()
    r = pg.evaluate("() => MANT.ordenes.actual().iperc.filas[0]")
    assert r["aplicadas"] and r["hora"]
    # Otro peligro, con residual significativo: aviso crítico.
    pg.click("[data-accion=iperc-otro]")
    k = pg.evaluate("() => MANT.ordenes.actual().iperc.filas.length - 1")
    pg.fill(f"#m-o-iperc-filas-{k}-peligro", "Trabajo cerca de línea energizada")
    pg.click(f"[data-iperc-nivel='{k}|residual|S']")
    crit = pg.evaluate("() => MANT.ordenes.alertas().filter(a => a.nivel === 'critico' && a.campo === 'iperc').map(a => a.mensaje)")
    assert any("Trabajo cerca de línea energizada" in c and "SIGNIFICATIVO" in c for c in crit), crit
    assert any("valídelas con SSOMA" in a for a in pg.evaluate("() => MANT.ordenes.alertas().map(a => a.mensaje)"))
    nav.close()


def test_el_iperc_sale_en_el_pdf(pw, servidor):
    nav, pg = _orden(pw, servidor)
    pg.evaluate("() => MANT.ordenes.modo('completo')")
    pg.evaluate("() => MANT.ordenes.desplegar(true)")
    pg.locator("[data-iperc-act=desenergizar]").click()
    pg.locator("[data-iperc-act=encendido]").click()
    b64 = pg.evaluate("""() => MANT.documentos.pdf(MANT.ordenes.actual(), ['iperc']).then(async b => {
        const u = new Uint8Array(await b.arrayBuffer()); let s = '';
        for (const x of u) s += String.fromCharCode(x); return btoa(s); })""")
    assert pg.is_enabled("[data-doc=iperc]")
    nav.close()
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext no esta disponible")
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        ruta = os.path.join(d, "i.pdf")
        open(ruta, "wb").write(base64.b64decode(b64))
        texto = subprocess.run(["pdftotext", "-layout", ruta, "-"], capture_output=True, text=True).stdout
    assert "IPERC CONTINUO" in texto and "MEDIDAS DE CONTROL" in texto
    assert "Desenergización" in texto and "Colocar puesta a tierra temporal" in texto
    assert "Ruido industrial" in texto and "Riesgo Significativo" in texto
