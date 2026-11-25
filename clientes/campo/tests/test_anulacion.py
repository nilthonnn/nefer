"""Anular un acta de despacho o recepción registrada por error.

Anular no es borrar: el acta se queda, con motivo, fecha y quién, y deja de
poder continuarse o sobrescribirse. La trazabilidad es eso: que dentro de un
mes se pueda explicar por qué hay un N° de acta que no vale.
"""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402

from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import App, _contexto, _lanzar, servidor  # noqa: E402,F401

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


def _pagina(pw, servidor, respuestas=None):
    """Una página cuyos diálogos se contestan en orden con `respuestas`."""
    nav = _lanzar(pw)
    pg = _contexto(nav, movil=True).new_page()
    cola = list(respuestas or [])

    def contestar(d):
        if d.type == "prompt":
            v = cola.pop(0) if cola else None
            d.dismiss() if v is None else d.accept(v)
        else:
            d.accept()
    pg.on("dialog", contestar)
    pg.goto(servidor)
    pg.wait_for_function("() => window.CAMPO && window.MANT")
    return nav, pg, cola


def _despacho(pg, equipo, acta, nombre):
    App(pg).despacho()
    pg.click("#d-proy-nuevo")
    pg.click("#d-datos summary")
    pg.fill("#d-equipo", equipo)
    pg.fill("#d-acta", acta)
    pg.click("#d-datos summary")
    pg.fill("#d-proy-nombre", nombre)
    pg.click("#d-proy-guardar")
    pg.wait_for_function("() => !/sin guardar/.test(document.querySelector('#d-proy-estado').textContent)")
    return pg.evaluate("() => CAMPO.proyectos.actual().id")


def _fila(pg, pid):
    return pg.locator(f".proy-fila[data-id='{pid}']")


def _lista(pg):
    pg.click("[data-ir='inicio']")
    pg.evaluate("() => CAMPO.proyectosUI.refrescar()")
    pg.wait_for_timeout(150)


def _registro(pg, pid):
    return pg.evaluate("id => CAMPO.almacen.leer(id)", pid)


def test_anular_deja_constancia_y_no_borra(pw, servidor):
    nav, pg, cola = _pagina(pw, servidor, ["Se registró el equipo equivocado", "Supervisor de turno"])
    pid = _despacho(pg, "GE-074", "ACTA-0001", "Despacho errado")
    _lista(pg)
    _fila(pg, pid).locator("[data-anular]").click()
    pg.wait_for_selector(f".proy-fila.anulada[data-id='{pid}']")

    fila = _fila(pg, pid)
    texto = fila.inner_text()
    assert "ANULADA" in texto and "Se registró el equipo equivocado" in texto
    assert "Supervisor de turno" in texto
    assert fila.locator("[data-abrir]").count() == 0, "una anulada no se continúa"
    assert fila.locator("[data-borrar]").count() == 0, "una anulada no se borra"
    assert fila.locator("[data-anular]").count() == 0

    r = _registro(pg, pid)
    assert r["estado"] == "anulado"
    assert r["anulacion"]["motivo"] == "Se registró el equipo equivocado"
    h = r["historial"][-1]
    assert h["accion"] == "anulado" and h["estadoPrevio"] == "borrador"
    assert r["datos"]["campos"]["d-equipo"] == "GE-074", "los datos se conservan"
    nav.close()


def test_el_acta_abierta_se_suelta_y_el_autoguardado_no_la_reescribe(pw, servidor):
    nav, pg, _ = _pagina(pw, servidor, ["Duplicada por error", ""])
    pid = _despacho(pg, "GE-074", "ACTA-0002", "Abierta y anulada")
    _lista(pg)
    _fila(pg, pid).locator("[data-anular]").click()
    pg.wait_for_selector(f".proy-fila.anulada[data-id='{pid}']")

    assert pg.evaluate("() => CAMPO.proyectos.actual().id") != pid
    App(pg).despacho()
    pg.click("#d-datos summary")
    assert pg.input_value("#d-equipo") == "", "la pantalla quedó libre"
    pg.fill("#d-equipo", "OTRO")
    pg.evaluate("() => CAMPO.proyectos.volcar()")
    pg.wait_for_timeout(300)
    assert _registro(pg, pid)["estado"] == "anulado"
    assert _registro(pg, pid)["datos"]["campos"]["d-equipo"] == "GE-074"

    err = pg.evaluate(f"() => CAMPO.proyectos.abrir('{pid}').then(() => null, e => e.message)")
    assert "anulada" in err
    nav.close()


def test_sin_motivo_no_se_anula(pw, servidor):
    nav, pg, _ = _pagina(pw, servidor, ["   "])
    pid = _despacho(pg, "GE-074", "ACTA-0003", "Sin motivo")
    _lista(pg)
    _fila(pg, pid).locator("[data-anular]").click()
    pg.wait_for_timeout(300)
    assert _registro(pg, pid)["estado"] != "anulado"
    err = pg.evaluate(f"() => CAMPO.proyectos.anular('{pid}', '').then(() => null, e => e.message)")
    assert "motivo" in err
    nav.close()


def test_duplicados_se_marcan_y_anular_uno_los_limpia(pw, servidor):
    nav, pg, _ = _pagina(pw, servidor, ["Registro duplicado", "Técnico"])
    a = _despacho(pg, "GE-074", "ACTA-0010", "Primera")
    b = _despacho(pg, "ge-074", " acta-0010 ", "Segunda")
    c = _despacho(pg, "GE-074", "ACTA-0011", "Otra acta")
    _lista(pg)
    assert "POSIBLE DUPLICADO" in _fila(pg, a).inner_text()
    assert "Segunda" in _fila(pg, a).inner_text()
    assert "POSIBLE DUPLICADO" in _fila(pg, b).inner_text()
    assert "POSIBLE DUPLICADO" not in _fila(pg, c).inner_text()

    _fila(pg, b).locator("[data-anular]").click()
    pg.wait_for_selector(f".proy-fila.anulada[data-id='{b}']")
    assert "POSIBLE DUPLICADO" not in _fila(pg, a).inner_text()
    nav.close()


def test_duplicar_una_anulada_da_un_borrador_trazable(pw, servidor):
    nav, pg, _ = _pagina(pw, servidor, ["Datos del cliente errados", ""])
    pid = _despacho(pg, "GE-074", "ACTA-0020", "Para rehacer")
    _lista(pg)
    _fila(pg, pid).locator("[data-anular]").click()
    pg.wait_for_selector(f".proy-fila.anulada[data-id='{pid}']")
    _fila(pg, pid).locator("[data-duplicar]").click()
    pg.wait_for_timeout(400)
    copia = pg.evaluate(f"""() => CAMPO.proyectos.listar()
        .then(l => l.find(p => p.historial && p.historial[0].de === '{pid}'))""")
    assert copia["estado"] == "borrador"
    assert copia["historial"][0]["estadoDe"] == "anulado"
    assert pg.evaluate(f"() => CAMPO.proyectos.abrir('{copia['id']}').then(p => p.estado)") == "borrador"
    nav.close()


def test_una_recepcion_tambien_se_anula_y_viaja_anulada(pw, servidor):
    nav, pg, _ = _pagina(pw, servidor)
    pg.click("#tab-recepcion")
    pg.click("#r-proy-nuevo")
    pg.evaluate("""() => { document.querySelector('#r-acta').value = 'R-0001';
                          document.querySelector('#r-acta').dispatchEvent(new Event('input', {bubbles: true})); }""")
    pg.fill("#r-proy-nombre", "Recepción errada")
    pg.click("#r-proy-guardar")
    pg.wait_for_function("() => !/sin guardar/.test(document.querySelector('#r-proy-estado').textContent)")
    pid = pg.evaluate("() => CAMPO.proyectos.actual().id")
    pg.evaluate(f"() => CAMPO.proyectos.anular('{pid}', 'Equipo no llegó', 'Almacén')")
    r = pg.evaluate(f"""async () => {{
      const P = CAMPO.proyectos;
      const paquete = await P.empaquetar('{pid}');
      const nuevo = await P.importar(paquete.blob);
      return [nuevo.estado, nuevo.anulacion.motivo, nuevo.historial.length];
    }}""")
    assert r == ["anulado", "Equipo no llegó", 1]
    nav.close()
