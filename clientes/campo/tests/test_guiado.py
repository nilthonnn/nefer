"""Inspección guiada: la orden recorrida en seis pasos.

Equipo → Seguridad → Fotos → Mediciones → Hallazgos → Cierre. Una tarea por
pantalla, barra de avance y un botón que dice qué sigue. La ronda de fotos usa
la cámara de la app; en placas y pantallas muestra un marco guía, recorta lo
que queda dentro y empieza a leerlo sola. Los avisos se revisan en Hallazgos,
no al abrir. «Formulario completo» muestra la misma orden entera.
"""

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


def _guiada(pw, servidor):
    nav = _lanzar(pw, camara=True)
    pg = _contexto(nav, movil=True, camara=True, modo=None).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", dict(EQUIPOS["064"], horometro=11800))
    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-equipos")
    pg.locator("#m-eq-lista [data-tag='064']").click()
    pg.click("#m-f-inspeccion")
    pg.wait_for_selector("#m-orden.guiado")
    return nav, pg


def _paso(pg):
    return pg.text_content(".g-titulo").strip()


def test_seis_pasos_con_una_tarea_cada_uno(pw, servidor):
    nav, pg = _guiada(pw, servidor)
    assert _paso(pg) == "Equipo"
    assert pg.is_hidden("#m-o-revisar"), "los avisos no salen al abrir"
    assert pg.evaluate("() => getComputedStyle(document.querySelector('#v-mantenimiento > .encab')).display") == "none"
    pg.click("[data-accion=confirmar]")
    pg.fill("#m-o-ot-ot", "4017305001")
    pg.click(".g-nav .primary")
    assert _paso(pg) == "Seguridad"
    pg.click("[data-accion=g-seguridad-ok]")
    s = pg.evaluate("() => MANT.ordenes.actual().seguridad")
    assert all(v == "OK" for v in s["items"].values() if v) and len(s["horas"]) >= 4
    pg.click(".g-nav .primary")
    assert _paso(pg) == "Fotos"
    assert "Foto 1 de 25" in pg.text_content(".g-contador")
    # Sin foto también se avanza: avisa, no bloquea.
    pg.click(".g-nav .primary")
    assert "Foto 2 de 25" in pg.text_content(".g-contador")
    pg.click("[data-accion=g-paso][data-n='3']")
    assert _paso(pg) == "Mediciones" and pg.is_visible("#m-o-diag")
    pg.click(".g-nav .primary")
    assert _paso(pg) == "Hallazgos" and pg.is_visible("#m-o-revisar"), "aquí se revisan los avisos"
    pg.click(".g-nav .primary")
    assert _paso(pg) == "Cierre"
    assert pg.locator("[data-firmar]").count() >= 2 and pg.is_visible("[data-doc=todo]")
    pg.click("[data-accion=g-terminar]")
    pg.wait_for_selector("#m-ordenes:not([hidden])")
    nav.close()


def test_ronda_de_fotos_con_la_camara_y_el_marco(pw, servidor):
    nav, pg = _guiada(pw, servidor)
    pg.click("[data-accion=g-paso][data-n='2']")
    # Vista frontal: cámara sin marco, la foto entra directa (sin editor).
    pg.click("[data-accion=g-camara]")
    pg.wait_for_selector("#camara:not([hidden])")
    assert pg.is_hidden("#cam-marco")
    pg.wait_for_function("() => document.querySelector('#cam-video').videoWidth > 0")
    pg.click("#cam-disparar")
    pg.wait_for_function("() => MANT.ordenes.actual().fotos.length === 1")
    assert pg.is_hidden("#camara") and pg.is_hidden("#editor")
    assert pg.evaluate("() => MANT.ordenes.actual().fotos[0].casilla") == "c01"
    pg.click("[data-estado-foto=c01][data-valor=OK]")
    pg.click(".g-nav .primary")
    # Placa del equipo: con marco, y la lectura empieza sola.
    assert "Placa de datos" in pg.text_content(".g-casilla")
    pg.click("[data-accion=g-camara]")
    pg.wait_for_selector("#camara:not([hidden])")
    assert pg.is_visible("#cam-marco")
    pg.wait_for_function("() => document.querySelector('#cam-video').videoWidth > 0")
    pg.click("#cam-disparar")
    pg.wait_for_function("() => MANT.ordenes.actual().fotos.length === 2")
    pg.wait_for_selector("[data-casilla=c05] .m-lectura-estado, [data-casilla=c05] .m-lectura", timeout=20000)
    assert pg.evaluate("() => MANT.ordenes.actual().fotos[1].casilla") == "c05"
    nav.close()


def test_formulario_completo_y_vuelta(pw, servidor):
    nav, pg = _guiada(pw, servidor)
    pg.click("[data-accion=g-modo]")
    pg.wait_for_selector("details.m-grupo")
    assert pg.evaluate("() => localStorage.getItem('campo.orden.modo')") == "completo"
    assert pg.is_visible("#m-o-revisar")
    pg.click("[data-accion=g-modo]")
    pg.wait_for_selector(".g-titulo")
    assert pg.evaluate("() => localStorage.getItem('campo.orden.modo')") == "guiado"
    nav.close()


def test_hallazgos_pide_texto_solo_a_lo_observado(pw, servidor):
    nav, pg = _guiada(pw, servidor)
    pg.click("[data-accion=g-paso][data-n='2']")
    pg.click("[data-estado-foto=c01][data-valor=OBS]")
    pg.click(".g-nav .primary")
    pg.click("[data-estado-foto=c05][data-valor=OK]")
    pg.click("[data-accion=g-paso][data-n='4']")
    hall = pg.locator(".g-hallazgo")
    assert hall.count() == 1 and "Vista frontal" in hall.text_content()
    hall.locator("textarea").fill("Puerta lateral descuadrada.")
    pg.wait_for_timeout(300)
    assert pg.evaluate("() => MANT.ordenes.actual().estados.c01.nota") == "Puerta lateral descuadrada."
    assert "1 componentes marcados OK" in pg.text_content(".g-cuerpo")
    nav.close()
