"""Módulo Equipos: la ficha de cada equipo por TAG.

Las validaciones se prueban con datos, y la pantalla se conduce como el
técnico: teclear, salir de la app, volver y encontrar la ficha como la dejó.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402

from datos_unimaq import EQUIPOS  # noqa: E402
from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import App, _contexto, _lanzar, servidor  # noqa: E402,F401

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")

APP = Path(__file__).resolve().parents[1] / "docs" / "app" / "index.html"


def _abrir(pg, servidor):
    pg.goto(servidor)
    pg.wait_for_function("() => window.UNIMAQ && UNIMAQ.equipos")
    pg.evaluate("() => UNIMAQ.equipos.listo()")


@pytest.fixture(scope="module")
def pw():
    """Una sola instancia de Playwright para todo el módulo: la API síncrona
    no admite dos abiertas a la vez."""
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="module")
def js(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    _abrir(pg, servidor)
    yield lambda codigo, arg=None: pg.evaluate(codigo, arg)
    nav.close()


VALIDAR = "([e, a]) => UNIMAQ.validaciones.validarEquipo(e, a)"


def _niveles(alertas, *niveles):
    return [a for a in alertas if a["nivel"] in niveles]


# --------------------------------------------------------------------------
# validarEquipo: avisa, no bloquea
# --------------------------------------------------------------------------

def test_los_equipos_de_referencia_no_tienen_nada_serio(js):
    for tag, e in EQUIPOS.items():
        alertas = js(VALIDAR, [e, None])
        assert _niveles(alertas, "critico", "aviso") == [], (tag, alertas)


def test_lo_que_falta_se_pide_leer_en_placa_no_se_inventa(js):
    campos = {a["campo"] for a in js(VALIDAR, [EQUIPOS["AAQ29"], None])}
    assert {"motor.serie", "frecuenciaHz"} <= campos
    assert js(VALIDAR, [EQUIPOS["064"], None]) == []


def test_serie_repetida_entre_placas(js):
    e = dict(EQUIPOS["064"], motor=dict(EQUIPOS["064"]["motor"], serie="d19i 420882"))
    a = _niveles(js(VALIDAR, [e, None]), "aviso")
    assert [x["campo"] for x in a] == ["motor.serie"]
    assert "placa equivocada" in a[0]["mensaje"]


def test_horometro_que_retrocede_es_critico(js):
    antes = dict(EQUIPOS["064"], horometro=6240.3)
    ahora = dict(EQUIPOS["064"], horometro="6.200")
    a = js(VALIDAR, [ahora, antes])
    assert [(x["nivel"], x["campo"]) for x in a] == [("critico", "horometro")]
    assert js(VALIDAR, [dict(ahora, horometro=6300), antes]) == []


@pytest.mark.parametrize("cambio,campo", [
    ({"fases": 1, "voltajeNominal": 380}, "voltajeNominal"),
    ({"fases": 3, "voltajeNominal": 127}, "voltajeNominal"),
    ({"frecuenciaHz": 55}, "frecuenciaHz"),
    ({"rpm": 1500}, "rpm"),
    ({"fases": 2}, "fases"),
])
def test_incoherencias_electricas_avisan(js, cambio, campo):
    a = _niveles(js(VALIDAR, [dict(EQUIPOS["064"], **cambio), None]), "aviso")
    assert campo in [x["campo"] for x in a], a


@pytest.mark.parametrize("cambio", [
    {"rpm": 3600}, {"rpm": 1200}, {"fases": 3, "voltajeNominal": 220},
    {"frecuenciaHz": 50, "rpm": 1500},
])
def test_combinaciones_validas_no_avisan(js, cambio):
    assert _niveles(js(VALIDAR, [dict(EQUIPOS["064"], **cambio), None]), "aviso") == []


# --------------------------------------------------------------------------
# la pantalla
# --------------------------------------------------------------------------

def _escribir(pg, ruta, valor):
    sel = "#m-f-" + ruta.replace(".", "-")
    if pg.eval_on_selector(sel, "n => n.tagName") == "SELECT":
        pg.select_option(sel, str(valor))
    else:
        pg.fill(sel, str(valor))


def _leer_guardada(pg, tag):
    return pg.evaluate("t => RDRENTA.almacen.equipos.leer(t)", tag)


def test_ficha_del_064_en_modo_avion_sobrevive_a_cerrar_la_app(pw, servidor):
    nav = _lanzar(pw)
    ctx = _contexto(nav, movil=True)
    pg = ctx.new_page()
    _abrir(pg, servidor)
    app = App(pg)
    ctx.set_offline(True)                        # modo avión desde aquí

    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-equipos")
    pg.fill("#m-eq-tag", " 064 ")
    pg.click("#m-eq-nuevo button[type=submit]")
    pg.wait_for_selector("#m-ficha:not([hidden])")
    assert pg.inner_text("#m-f-tag") == "064"

    e = EQUIPOS["064"]
    for ruta in ["ubicacion", "grupo.marca", "grupo.modelo", "grupo.serie",
                 "motor.marca", "motor.modelo", "motor.serie",
                 "alternador.marca", "alternador.modelo", "alternador.winding",
                 "controlador", "controladorModelo"]:
        valor = e
        for k in ruta.split("."):
            valor = valor[k]
        _escribir(pg, ruta, valor)
    _escribir(pg, "voltajeNominal", "380")
    _escribir(pg, "fases", 3)
    _escribir(pg, "frecuenciaHz", 60)
    _escribir(pg, "rpm", "1800")
    _escribir(pg, "horometro", "6.240,3")
    pg.wait_for_function("() => /guardado/.test(document.querySelector('#m-f-guardado').textContent)")

    guardada = _leer_guardada(pg, "064")
    assert guardada["grupo"]["serie"] == "D19I420882"
    assert guardada["voltajeNominal"] == 380 and guardada["fases"] == 3
    assert guardada["horometro"] == 6240.3

    # Se cierra la app y se vuelve a abrir, sin señal.
    pg.close()
    pg = ctx.new_page()
    pg.goto(servidor)  # el trabajador de servicio la sirve sin red
    pg.wait_for_function("() => window.UNIMAQ && UNIMAQ.equipos")
    pg.evaluate("() => UNIMAQ.equipos.listo()")
    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-equipos")
    assert pg.is_visible("#m-ficha"), "la ficha que se estaba llenando vuelve abierta"
    assert pg.input_value("#m-f-grupo-serie") == "D19I420882"
    assert pg.input_value("#m-f-horometro") == "6240.3"
    assert pg.input_value("#m-f-fases") == "3"
    assert app.errores == []
    nav.close()


def test_horometro_menor_avisa_pero_se_guarda(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav, movil=True).new_page()
    pg.on("dialog", lambda d: d.accept())
    _abrir(pg, servidor)
    pg.evaluate("e => RDRENTA.almacen.equipos.guardar(e)", dict(EQUIPOS["064"], horometro=6240))
    pg.evaluate("() => UNIMAQ.equipos.abrir('064')")
    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-equipos")

    _escribir(pg, "horometro", "6200")
    pg.wait_for_function("() => /guardado/.test(document.querySelector('#m-f-guardado').textContent)")
    assert "menor al registrado" in pg.inner_text("#m-f-alertas")
    assert "crítico" in pg.inner_text("#m-f-alertas").lower()
    assert pg.get_attribute("#m-f-horometro", "aria-invalid") == "true"
    assert _leer_guardada(pg, "064")["horometro"] == 6200, "el aviso no bloquea"
    nav.close()


def test_un_numero_ilegible_avisa_y_no_se_guarda_como_cero(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    _abrir(pg, servidor)
    pg.evaluate("() => UNIMAQ.equipos.crear('C20D6')")
    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-equipos")
    _escribir(pg, "voltajeNominal", "doscientos")
    pg.wait_for_function("() => /guardado/.test(document.querySelector('#m-f-guardado').textContent)")
    assert "no es un número" in pg.inner_text("#m-f-alertas")
    assert _leer_guardada(pg, "C20D6")["voltajeNominal"] is None
    nav.close()


def test_un_tag_repetido_abre_la_ficha_existente_sin_pisarla(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    _abrir(pg, servidor)
    pg.evaluate("e => RDRENTA.almacen.equipos.guardar(e)", EQUIPOS["AAQ29"])
    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-equipos")
    pg.evaluate("() => UNIMAQ.equipos.listo()")
    pg.fill("#m-eq-tag", "aaq29")
    pg.click("#m-eq-nuevo button[type=submit]")
    pg.wait_for_selector("#m-ficha:not([hidden])")
    assert "Ya existía la ficha de AAQ29" in pg.inner_text("#m-f-aviso")
    assert pg.input_value("#m-f-grupo-serie") == "150200062"
    assert _leer_guardada(pg, "AAQ29")["grupo"]["modelo"] == "LUX M3"

    # El TAG vacío no crea nada.
    pg.click("#m-f-volver")
    pg.fill("#m-eq-tag", "   ")
    pg.click("#m-eq-nuevo button[type=submit]")
    assert "Escriba el TAG" in pg.inner_text("#m-eq-nuevo-aviso")
    assert pg.evaluate("() => RDRENTA.almacen.equipos.listar().then(l => l.length)") == 1
    nav.close()


def test_lista_busqueda_y_borrado(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.on("dialog", lambda d: d.accept())
    _abrir(pg, servidor)
    for e in EQUIPOS.values():
        pg.evaluate("e => RDRENTA.almacen.equipos.guardar(e)", e)
    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-equipos")
    pg.fill("#m-eq-buscar", "")
    pg.wait_for_timeout(200)
    tags = pg.eval_on_selector_all("#m-eq-lista .m-tag", "n => n.map(x => x.textContent)")
    assert tags == ["064", "AAQ29", "C20D6", "C450D6"]
    pg.fill("#m-eq-buscar", "a18t")
    pg.wait_for_timeout(200)
    assert pg.eval_on_selector_all("#m-eq-lista .m-tag",
                                   "n => n.map(x => x.textContent)") == ["C450D6"]
    pg.click("#m-eq-lista [data-tag='C450D6']")
    pg.wait_for_selector("#m-ficha:not([hidden])")
    pg.click("#m-f-borrar")
    pg.wait_for_selector("#m-equipos:not([hidden])")
    assert _leer_guardada(pg, "C450D6") is None
    nav.close()


def test_todo_lo_que_se_toca_mide_48_px(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav, movil=True).new_page()
    _abrir(pg, servidor)
    pg.evaluate("e => RDRENTA.almacen.equipos.guardar(e)", EQUIPOS["064"])
    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-equipos")
    pg.evaluate("() => UNIMAQ.equipos.listo()")
    pg.wait_for_timeout(200)
    medir = """() => Array.from(document.querySelectorAll(
        '#v-mantenimiento button, #v-mantenimiento input, #v-mantenimiento select'))
      .filter(n => n.offsetParent !== null)
      .map(n => [n.id || n.className || n.textContent.trim(),
                 n.getBoundingClientRect().height])
      .filter(x => x[1] < 47.5)"""
    assert pg.evaluate(medir) == []
    pg.click("#m-eq-lista [data-tag='064']")
    pg.wait_for_selector("#m-ficha:not([hidden])")
    assert pg.evaluate(medir) == []
    # Y la barra de pestañas sigue entera con cinco.
    anchos = pg.eval_on_selector_all(".tabs button", "n => n.map(b => b.getBoundingClientRect().width)")
    assert len(anchos) == 5 and min(anchos) >= 48
    nav.close()


def test_la_app_publicada_no_lleva_datos_de_equipos_de_ejemplo():
    """Las series de referencia viven en las pruebas; la app se publica."""
    fuente = APP.read_text(encoding="utf-8")
    for serie in ["D19I420882", "A18T042328", "G18I144268", "150200062", "X17L492615"]:
        assert serie not in fuente, serie


def test_salir_de_un_campo_sin_cambiarlo_no_lo_deja_sin_guardar(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    _abrir(pg, servidor)
    pg.evaluate("() => UNIMAQ.equipos.crear('064')")
    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-equipos")
    _escribir(pg, "grupo.modelo", "C100D6")
    pg.wait_for_function("() => /guardado/.test(document.querySelector('#m-f-guardado').textContent)")
    pg.evaluate("() => document.activeElement.blur()")
    pg.wait_for_timeout(100)
    assert pg.inner_text("#m-f-guardado").startswith("guardado")
    nav.close()
