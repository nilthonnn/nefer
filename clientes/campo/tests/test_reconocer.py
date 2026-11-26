"""Reconocer el equipo (QR o TAG escrito) y su historial de mantenimiento."""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from datos_mant import EQUIPOS  # noqa: E402
from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import _contexto, _lanzar, servidor  # noqa: E402,F401

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")
FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# El detector nativo de códigos (Android, macOS) no está en el Chromium de
# Linux: se simula uno que devuelve lo que diga window.__qr.
DETECTOR = """
window.__qr = null;
window.BarcodeDetector = class { constructor() {} detect() {
  return Promise.resolve(window.__qr ? [{ rawValue: window.__qr }] : []); } };
"""


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


def _pagina(pw, servidor, detector=False):
    nav = _lanzar(pw)
    ctx = _contexto(nav, movil=True)
    if detector:
        ctx.add_init_script(DETECTOR)
    pg = ctx.new_page()
    pg.on("dialog", lambda d: d.accept("Registrada por error") if d.type == "prompt" else d.accept())
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.reconocer && MANT.equipos")
    for e in EQUIPOS.values():
        pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", e)
    return nav, pg


def _foto(ruta, texto):
    img = Image.new("RGB", (1200, 400), (240, 240, 235))
    ImageDraw.Draw(img).text((80, 120), texto, font=ImageFont.truetype(FUENTE, 120), fill=(10, 10, 10))
    img.save(ruta, "JPEG", quality=92)
    return str(ruta)


def test_la_etiqueta_qr_lleva_el_tag(pw, servidor, tmp_path):
    nav, pg = _pagina(pw, servidor)
    assert pg.evaluate("() => MANT.reconocer.contenido(' 064 ')") == "EQUIPO:064"
    assert pg.evaluate("() => MANT.reconocer.tagDe('EQUIPO:aaq29', [])") == "AAQ29"
    assert pg.evaluate("() => MANT.reconocer.tagDe('064', ['064'])") == "064"
    assert pg.evaluate("() => MANT.reconocer.tagDe('cualquier cosa', ['064'])") is None
    svg = pg.evaluate("() => MANT.reconocer.etiqueta('064', 'T9 – Plataforma')")
    assert svg.startswith("<svg") and "<path d=\"M" in svg and ">064</text>" in svg
    # Que el QR se lee se comprobó al escribir esto, decodificando la captura
    # de la etiqueta con OpenCV («EQUIPO:064»). No queda en la suite: OpenCV
    # pesa demasiado para traerlo sólo para esto, y una prueba que se salta
    # cuando falta cuenta aquí como fallo.
    n = svg.count("h8v8h-8z")
    assert n > 200, n
    nav.close()


def test_escanear_el_qr_abre_la_ficha(pw, servidor, tmp_path):
    nav, pg = _pagina(pw, servidor, detector=True)
    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-equipos")
    pg.evaluate("() => { window.__qr = 'EQUIPO:AAQ29'; }")
    pg.set_input_files("#m-eq-escanear", _foto(tmp_path / "qr.jpg", "QR"))
    pg.wait_for_selector("#m-ficha:not([hidden])")
    assert pg.inner_text("#m-f-tag") == "AAQ29"
    assert "código QR" in pg.inner_text("#m-eq-escaneo")
    nav.close()


def test_sin_detector_lee_el_tag_escrito(pw, servidor, tmp_path):
    nav, pg = _pagina(pw, servidor)
    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-ordenes")
    pg.set_input_files("#m-ot-escanear", _foto(tmp_path / "tag.jpg", "C450D6"))
    pg.wait_for_function("() => document.querySelector('#m-ot-tag').value === 'C450D6'", timeout=90000)
    assert "TAG leído en la foto" in pg.inner_text("#m-ot-escaneo")
    nav.close()


def test_el_historial_del_equipo(pw, servidor):
    nav, pg = _pagina(pw, servidor)
    pg.evaluate("""async () => {
      await MANT.ordenes.crear('064', 'PREVENTIVO', 'PM2_500', '4017304000');
      let m = MANT.ordenes.actual();
      await CAMPO.proyectos.volcar();
      await MANT.ordenes.volver();
      await MANT.ordenes.crear('064', 'CORRECTIVO', '', '4017304001');
      await CAMPO.proyectos.volcar();
      const id2 = CAMPO.proyectos.actual().id;
      await MANT.ordenes.volver();
      await CAMPO.proyectos.anular(id2, 'OT duplicada en SAP', 'Supervisor');
      await MANT.ordenes.crear('AAQ29', 'INSPECCION', '', '4017304002');
      await CAMPO.proyectos.volcar();
      await MANT.ordenes.volver();
    }""")
    h = pg.evaluate("() => MANT.equipos.historial('064')")
    assert sorted(x["ot"] for x in h) == ["4017304000", "4017304001"], "sólo las de este TAG"
    anulada = [x for x in h if x["ot"] == "4017304001"][0]
    assert anulada["estado"] == "anulado" and anulada["anulacion"]["motivo"] == "OT duplicada en SAP"

    pg.evaluate("() => MANT.equipos.abrir('064')")
    pg.click("#tab-mantenimiento")
    pg.wait_for_selector("#m-f-hist-lista .m-hist")
    texto = pg.inner_text("#m-f-hist-lista")
    assert "Preventivo PM2 · OT 4017304000" in texto
    assert "ANULADA: OT duplicada en SAP" in texto
    pg.click("#m-f-hist-lista [data-hist-abrir]")
    pg.wait_for_selector("#m-orden:not([hidden])")
    assert pg.inner_text("#m-o-tag") == "064"
    nav.close()
