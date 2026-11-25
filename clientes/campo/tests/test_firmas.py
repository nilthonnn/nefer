"""Firma dibujada en pantalla: se guarda con la orden y se reemplaza sin dejar restos."""

from __future__ import annotations

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


def _dibujar(pg):
    caja = pg.locator("#m-firma-lienzo").bounding_box()
    x, y = caja["x"] + 30, caja["y"] + caja["height"] / 2
    pg.mouse.move(x, y)
    pg.mouse.down()
    for k in range(1, 12):
        pg.mouse.move(x + k * 20, y + (15 if k % 2 else -15))
    pg.mouse.up()


def test_firmar_reemplazar_y_quitar(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["064"])
    pg.evaluate("() => MANT.ordenes.crear('064', 'INSPECCION', '', '4017306000')")
    pg.click("#tab-mantenimiento")
    pid = pg.evaluate("() => CAMPO.proyectos.actual().id")
    pg.fill("#m-o-ot-firmas-tecnico-nombre", "Técnico eléctrico")

    # Guardar sin trazo no firma nada.
    pg.click("[data-firmar='ot.firmas.tecnico']")
    pg.click("#m-firma-guardar")
    assert "Firme dentro del recuadro" in pg.text_content("#m-firma-titulo")
    _dibujar(pg)
    pg.click("#m-firma-guardar")
    pg.wait_for_selector("#m-firma", state="hidden")
    pg.wait_for_function("() => { const i = document.querySelector('img.m-firma-ver'); return i && i.naturalWidth > 0; }")
    f = pg.evaluate("() => MANT.ordenes.actual().ot.firmas.tecnico")
    assert f["imagen"] and f["fecha"], f
    reg = pg.evaluate("id => CAMPO.almacen.fotos.leer(id).then(r => [r.proyecto, r.archivo.type, r.archivo.size])", f["imagen"])
    assert reg[0] == pid and reg[1] == "image/png" and reg[2] > 500

    # Volver a firmar reemplaza: la anterior desaparece de la tienda.
    primera = f["imagen"]
    pg.click("[data-firmar='ot.firmas.tecnico']")
    _dibujar(pg)
    pg.click("#m-firma-guardar")
    pg.wait_for_selector("#m-firma", state="hidden")
    segunda = pg.evaluate("() => MANT.ordenes.actual().ot.firmas.tecnico.imagen")
    assert segunda != primera
    assert pg.evaluate("id => CAMPO.almacen.fotos.leer(id)", primera) is None

    # Firmas del informe (dos por lado) y del check-list.
    assert pg.is_visible("[data-firmar='informe.firmas.cliente.1']")
    pg.click("[data-accion=bat-agregar]")
    assert pg.is_visible("[data-firmar='baterias.0.supervisor']")

    pg.click("[data-firma-quitar='ot.firmas.tecnico']")
    pg.wait_for_timeout(300)
    assert pg.evaluate("() => MANT.ordenes.actual().ot.firmas.tecnico.imagen") is None
    assert pg.evaluate("id => CAMPO.almacen.fotos.leer(id)", segunda) is None
    nav.close()
