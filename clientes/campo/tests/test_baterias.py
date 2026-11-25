"""Check-list de baterías dentro de la orden, como el formato en papel."""

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


def test_check_list_completo(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav, movil=True).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    eq = dict(EQUIPOS["064"], horometro=500)
    eq["bateria"] = {"marca": "ETNA", "modelo": "SU-1217 PRO LM", "voltaje": 12, "ah": 124, "cca": 810, "cantidad": 2}
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", eq)
    pg.evaluate("() => MANT.ordenes.crear('064', 'PREVENTIVO', 'PM2_500', '4017305000')")
    pg.click("#tab-mantenimiento")
    pg.wait_for_selector("#m-orden:not([hidden])")

    pg.click("[data-accion=bat-agregar]")
    assert pg.is_checked("input[name=m-o-bat-frec][value=PM2_500]"), "la rutina sale de la orden"
    assert "Check-list de baterías sin tipo" in pg.inner_text("#m-o-alertas")

    pg.check("input[name=m-o-bat-tipo][value=LIBRE_MANTENIMIENTO]")
    assert pg.is_visible("[data-estado='baterias.0.items.14']")
    assert not pg.is_visible("[data-estado='baterias.0.items.3']"), "sólo los ítems de su tipo"
    m = pg.evaluate("() => MANT.ordenes.actual()")
    assert all(m["baterias"][0]["items"][str(i)] == "NA" for i in range(1, 11))
    assert "Verificación de estados de alerta del indicador" in pg.text_content("#m-o-cuerpo")

    pg.click("[data-accion=bat-ficha]")
    assert pg.input_value("#m-o-baterias-0-bateria-modelo") == "SU-1217 PRO LM"
    assert pg.input_value("#m-o-baterias-0-bateria-cantidad") == "2"

    for i in range(11, 19):
        pg.click(f"[data-estado='baterias.0.items.{i}'][data-valor=OK]")
    assert "ítems sin marcar 19" in pg.inner_text("#m-o-alertas")
    pg.click("[data-estado='baterias.0.items.19'][data-valor=NA]")

    # Probador con SOH 65 %: crítico, y pide decidir el reemplazo (ítem 19).
    pg.fill("#m-o-probador-soh", "65")
    t = pg.inner_text("#m-o-alertas")
    assert "SOH 65 % → evaluar reemplazo" in t
    assert "el ítem 19 (reemplazar baterías) no está marcado OK" in t

    pg.fill("#m-o-baterias-0-personal-0-nombre", "Técnico eléctrico")
    pg.fill("#m-o-baterias-0-supervisor-nombre", "Supervisor de turno")
    pg.evaluate("() => CAMPO.proyectos.volcar()")
    d = pg.evaluate("() => CAMPO.almacen.leer(CAMPO.proyectos.actual().id).then(p => p.datos)")
    c = d["baterias"][0]
    assert c["tipo"] == "LIBRE_MANTENIMIENTO" and c["frecuencia"] == "PM2_500" and c["ot"] == "4017305000"
    assert c["items"]["14"] == "OK" and c["items"]["19"] == "NA" and c["items"]["1"] == "NA"
    assert c["personal"][0]["nombre"] == "Técnico eléctrico"

    # Cambiar de tipo: el otro bloque pasa a NA y el elegido se limpia.
    pg.check("input[name=m-o-bat-tipo][value=PLOMO_ACIDO]")
    c = pg.evaluate("() => MANT.ordenes.actual().baterias[0]")
    assert c["items"]["1"] is None and c["items"]["14"] == "NA"
    k = pg.evaluate("() => MANT.modelo.aKit(MANT.ordenes.actual()).baterias[0].probador.soh")
    assert k == 65, "el kit recibe el probador de la orden"
    nav.close()
