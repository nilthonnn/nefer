"""Lo que se vio usando la app como un técnico, ya corregido.

- La orden de mantenimiento no cabía en el teléfono (unos 26 000 px): ahora
  cada sección, y cada parte de las fotos, se pliega y dice cuánto lleva.
- En recepción las fotos del retorno quedaban todas en la tira (0 / 10) y el
  paquete .zip se negaba: ahora se proponen en las vistas vacías, como en el
  despacho, y se corrigen tocando la casilla.
"""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402
from PIL import Image  # noqa: E402

from datos_mant import EQUIPOS  # noqa: E402
from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import _contexto, _lanzar, servidor  # noqa: E402,F401

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="module")
def retorno(tmp_path_factory):
    d = tmp_path_factory.mktemp("retorno")
    rutas = []
    for i, color in enumerate([(40, 60, 90), (90, 60, 40), (60, 90, 40)]):
        r = d / f"IMG_2026112{i}_1030{i}.jpg"
        Image.new("RGB", (1600, 1200), color).save(r, "JPEG", quality=85)
        rutas.append(str(r))
    return rutas


def _orden(pg):
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["064"])
    pg.evaluate("() => MANT.ordenes.crear('064', 'INSPECCION')")
    pg.click("#tab-mantenimiento")
    pg.wait_for_selector("#m-orden:not([hidden])")


def test_la_orden_se_abre_plegada_y_corta(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav, movil=True, plegada=True).new_page()
    pg.goto(servidor)
    _orden(pg)
    abiertos = pg.eval_on_selector_all(
        "#m-o-cuerpo details.m-grupo[open]", "l => l.map(d => d.dataset.grupo)")
    assert abiertos == ["Clasificación", "Fotos de la inspección"]
    assert pg.eval_on_selector_all("#m-o-cuerpo details.m-subgrupo[open]", "l => l.length") == 0
    alto = pg.evaluate("() => document.querySelector('#m-o-cuerpo').getBoundingClientRect().height")
    assert alto < 6000, f"la orden plegada mide {alto:.0f} px"
    resumen = pg.inner_text("details[data-grupo='Fotos de la inspección'] > summary")
    assert "0 / " in resumen, "el resumen dice cuántas obligatorias lleva"

    # Abrir una sección: se recuerda al repintar.
    pg.click("details[data-grupo='Check-list de baterías'] > summary")
    pg.click("[data-accion=bat-agregar]")
    assert pg.is_visible("input[name=m-o-bat-tipo]"), "sigue abierta tras repintar"

    # «Abrir todas» abre todo y queda recordado en el teléfono.
    pg.click("[data-accion=abrir-todo]")
    assert pg.eval_on_selector_all("#m-o-cuerpo :is(.m-grupo,.m-subgrupo):not([open])", "l => l.length") == 0
    assert pg.evaluate("() => localStorage.getItem('campo.orden.abierta')") == "1"
    pg.click("[data-accion=abrir-todo]")
    abiertos = pg.eval_on_selector_all("#m-o-cuerpo :is(.m-grupo,.m-subgrupo)[open]", "l => l.map(d => d.dataset.grupo)")
    assert abiertos == ["Clasificación", "Fotos de la inspección"], "plegar vuelve a lo de inicio"
    nav.close()


def test_recepcion_propone_las_fotos_del_retorno(pw, servidor, retorno):
    nav = _lanzar(pw)
    pg = _contexto(nav, movil=True, descargas=True).new_page()
    pg.goto(servidor)
    pg.click("#tab-recepcion")
    pg.click("#r-empezar")
    pg.set_input_files("#r-f3", retorno)
    pg.wait_for_function("() => document.querySelector('#r-t-vistas').textContent.trim().startsWith('3 /')")
    assert pg.text_content("#r-t-tira").strip() == "0"
    assert pg.eval_on_selector_all("#r-vistas .slot.propuesto", "l => l.length") == 3
    # Tocar una propuesta la devuelve a la tira; ponerla a mano ya no es propuesta.
    pg.click("#r-vistas .slot.lleno >> nth=0")
    pg.wait_for_function("() => document.querySelector('#r-t-vistas').textContent.trim().startsWith('2 /')")
    assert pg.text_content("#r-t-tira").strip() == "1"
    # Con fotos colocadas, el paquete .zip sale.
    with pg.expect_download() as d:
        pg.click("#r-zip")
    assert d.value.suggested_filename.endswith(".zip")
    nav.close()
