"""Plan de mantenimiento por horómetro y tablero de la flota.

Con lo que ya está en el teléfono —el horómetro de la ficha y las órdenes de
cada equipo— la app dice cuándo toca el próximo preventivo y cuál, y reúne en
un tablero lo que pide atención: equipos no aptos, avisos abiertos, PM
vencidos y próximos. No programa nada solo: el técnico decide.
"""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402

from datos_mant import EQUIPOS  # noqa: E402
from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import _contexto, _lanzar, servidor  # noqa: E402,F401

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")

PLAN = "([h, s, l]) => MANT.modelo.planPM(h, s, l)"
DIA = 864e5


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="module")
def js(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.modelo")
    yield lambda codigo, arg=None: pg.evaluate(codigo, arg)
    nav.close()


def test_el_proximo_sigue_al_ultimo_preventivo(js):
    r = js(PLAN, [11825.6, [{"pm": "PM1_250", "horometro": 11825.6}], []])
    assert (r["proximo"], r["rutina"], r["estado"]) == (12000, "PM4_2000", "al_dia")
    assert r["faltan"] == 174.4
    r = js(PLAN, [11960, [{"pm": "PM1_250", "horometro": 11825.6}], []])
    assert r["estado"] == "proximo", "a 40 h avisa"


def test_sin_historial_toca_el_siguiente_multiplo(js):
    r = js(PLAN, [11800, [], []])
    assert (r["proximo"], r["sinHistorial"]) == (12000, True)
    assert js(PLAN, [None, [], []]) is None, "sin horómetro no se planifica"


def test_vencido_y_servicios_saltados(js):
    r = js(PLAN, [11300, [{"pm": "PM2_500", "horometro": 11000}], []])
    assert (r["estado"], r["proximo"], r["rutina"]) == ("vencido", 11250, "PM1_250")
    r = js(PLAN, [10800, [{"pm": "PM4_2000", "horometro": 10000}], []])
    assert r["saltados"] == 2 and r["proximo"] == 10750, "toca el del horómetro de hoy"


def test_estima_la_fecha_con_las_horas_por_dia(js):
    r = js(PLAN, [300, [{"pm": "PM1_250", "horometro": 250}], [{"horas": 100, "fecha": 0}, {"horas": 300, "fecha": 10 * DIA}]])
    assert r["ritmo"] == 20 and r["faltan"] == 200
    assert r["estimada"] == 20 * DIA


def test_tablero_de_la_flota_y_plan_en_la_ficha(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav, movil=True).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.equipos && MANT.ordenes")
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", dict(EQUIPOS["064"], horometro=11990))
    otro = dict(EQUIPOS["064"], tag="077", horometro=500)
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", otro)
    # El 077 queda no apto en una inspección.
    pg.evaluate("() => MANT.ordenes.crear('077', 'INSPECCION')")
    pg.click("#tab-mantenimiento")
    pg.wait_for_selector("#m-orden:not([hidden])")
    pg.click("button[data-sn='informe.operativo'][data-valor=false]")
    pg.wait_for_timeout(1200)
    pg.click("#m-o-volver")
    pg.click("#m-seg-equipos")
    pg.wait_for_selector("#m-flota .m-cifras")
    pg.wait_for_function("() => /No apto desde/.test(document.querySelector('#m-flota').textContent)")
    texto = pg.text_content("#m-flota")
    assert "Estado de la flota" in texto
    assert "077" in texto and "No apto" in texto
    assert "064" in texto and "faltan 10 h" in texto, texto
    assert "PM próximo" in pg.text_content("#m-eq-lista [data-tag='064']")
    # Desde el tablero se abre la ficha y su plan crea la orden del PM.
    pg.click("#m-flota [data-tag='064']")
    pg.wait_for_selector("#m-f-plan [data-plan-pm]")
    assert "PM4 · 2000 HRS a las 12000 h" in pg.text_content("#m-f-plan")
    pg.click("#m-f-plan [data-plan-pm]")
    pg.wait_for_selector("#m-orden:not([hidden])")
    o = pg.evaluate("() => MANT.ordenes.actual().clasificacion")
    assert (o["tipo"], o["pm"]) == ("PREVENTIVO", "PM4_2000")
    nav.close()
