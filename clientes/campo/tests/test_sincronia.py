"""Compartir fichas y órdenes entre teléfonos, sin servidor ni nube.

Dos teléfonos (dos contextos del navegador, cada uno con su almacén): uno
exporta su paquete, el otro lo importa y se UNEN — lo vacío no borra lo
escrito, el horómetro es el mayor, las órdenes van por su id, una anulación
siempre viaja, las fotos llegan, y dos órdenes con el mismo TAG y OT se
señalan como posible duplicado. Importar dos veces no duplica nada.
"""

from __future__ import annotations

import base64

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


def _anular(pg, motivo, por):
    respuestas = [motivo, por]
    def responder(d):
        d.accept(respuestas.pop(0) if respuestas else "")
    pg.on("dialog", responder)
    pg.locator("#m-ot-lista [data-anular]").first.click()
    pg.wait_for_timeout(700)
    pg.remove_listener("dialog", responder)


def _telefono(nav, servidor):
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.sincronia && MANT.ordenes")
    return pg


def _orden(pg, tag, tipo, pm, ot, foto=None, anular=False):
    pg.evaluate("([t, ti, p, o]) => MANT.ordenes.crear(t, ti, p, o)", [tag, tipo, pm, ot])
    pg.click("#tab-mantenimiento")
    pg.wait_for_selector("#m-orden:not([hidden])")
    if foto:
        pg.set_input_files("#m-o-foto-c05", str(foto))
        pg.wait_for_function("() => MANT.ordenes.actual().fotos.length === 1")
    pg.wait_for_timeout(1200)
    pg.click("#m-o-volver")
    pg.wait_for_timeout(500)
    if anular:
        _anular(pg, "registrada por error", "Técnico A")


def test_dos_telefonos_se_unen_sin_duplicar(pw, servidor, tmp_path):
    foto = tmp_path / "placa.jpg"
    Image.new("RGB", (800, 600), (120, 130, 140)).save(foto, "JPEG")
    nav = _lanzar(pw)

    # Teléfono A: una orden anulada, y luego un PM1 con foto, OT 111.
    a = _telefono(nav, servidor)
    a.evaluate("e => CAMPO.almacen.equipos.guardar(e)",
               dict(EQUIPOS["064"], horometro=11800, actualizado=2000, ubicacion="Patio norte"))
    _orden(a, "064", "INSPECCION", "", "", anular=True)
    _orden(a, "064", "PREVENTIVO", "PM1_250", "111", foto=foto)
    a.evaluate("() => MANT.sincronia.nombrarTelefono('Técnico A')")
    r = a.evaluate("""() => MANT.sincronia.exportar({fotos: true}).then(async r => {
        const b = new Uint8Array(await r.blob.arrayBuffer()); let s = '';
        for (const x of b) s += String.fromCharCode(x);
        return {nombre: r.nombre, b64: btoa(s), resumen: r.resumen}; })""")
    assert r["nombre"].startswith("flota-tecnico-a-") and r["nombre"].endswith(".nefer-flota")
    assert r["resumen"] == {"equipos": 1, "ordenes": 2, "fotos": 1}
    paquete = tmp_path / r["nombre"]
    paquete.write_bytes(base64.b64decode(r["b64"]))

    # Teléfono B: la misma ficha con otro dato y más horas; su propia OT 111.
    b = _telefono(nav, servidor)
    b.evaluate("e => CAMPO.almacen.equipos.guardar(e)",
               dict(EQUIPOS["064"], horometro=11900, actualizado=1000, ubicacion="",
                    motor=dict(EQUIPOS["064"]["motor"], cpl="CPL-9")))
    _orden(b, "064", "PREVENTIVO", "PM1_250", "111")
    b.click("#m-seg-equipos")
    b.click("#m-sinc summary")
    b.set_input_files("#m-sinc-archivo", str(paquete))
    b.wait_for_function("() => /Órdenes:/.test(document.querySelector('#m-sinc-estado').textContent)")
    texto = b.text_content("#m-sinc-estado")
    assert "Desde: Técnico A" in texto
    assert "Órdenes: 2 nuevas" in texto
    assert "Fotos recibidas: 1" in texto
    assert "Posible duplicado 064 · OT 111" in texto, texto

    e = b.evaluate("() => CAMPO.almacen.equipos.leer('064')")
    assert e["horometro"] == 11900, "el horómetro es el mayor"
    assert e["ubicacion"] == "Patio norte", "lo vacío se completa"
    assert e["motor"]["cpl"] == "CPL-9", "lo escrito aquí no se pierde"

    ordenes = b.evaluate("() => CAMPO.almacen.listar().then(l => l.filter(p => p.vista === 'mantenimiento'))")
    assert len(ordenes) == 3
    anulada = [o for o in ordenes if o["estado"] == "anulado"]
    assert len(anulada) == 1 and anulada[0]["anulacion"]["motivo"] == "registrada por error"
    pm1 = [o for o in ordenes if o["datos"]["ot"]["ot"] == "111" and o["estado"] != "anulado"]
    assert len(pm1) == 2
    venida = [o for o in pm1 if o["datos"]["fotos"]][0]
    assert venida["historial"][-1]["accion"] == "sincronizada"
    fid = venida["datos"]["fotos"][0]["foto"]
    assert b.evaluate("id => CAMPO.almacen.fotos.leer(id).then(f => !!(f && f.archivo))", fid)

    # Importar otra vez no duplica nada.
    b.set_input_files("#m-sinc-archivo", str(paquete))
    b.wait_for_function("() => /0 nuevas, 0 actualizadas/.test(document.querySelector('#m-sinc-estado').textContent)")
    assert b.evaluate("() => CAMPO.almacen.listar().then(l => l.filter(p => p.vista === 'mantenimiento').length)") == 3

    # El historial y la flota de B ya cuentan el PM1 que hizo A.
    hist = b.evaluate("() => MANT.equipos.historial('064')")
    assert sum(1 for h in hist if h["pm"] == "PM1_250") == 2
    nav.close()


def test_una_anulacion_siempre_viaja(pw, servidor, tmp_path):
    nav = _lanzar(pw)
    a = _telefono(nav, servidor)
    a.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["064"])
    _orden(a, "064", "INSPECCION", "", "222")
    exp = lambda pg: pg.evaluate("""() => MANT.sincronia.exportar({}).then(async r => {
        const b = new Uint8Array(await r.blob.arrayBuffer()); let s = '';
        for (const x of b) s += String.fromCharCode(x); return btoa(s); })""")
    p1 = tmp_path / "uno.nefer-flota"
    p1.write_bytes(base64.b64decode(exp(a)))
    b = _telefono(nav, servidor)
    imp = lambda pg, f: pg.evaluate("""async b64 => { const s = atob(b64), u = new Uint8Array(s.length);
        for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);
        return MANT.sincronia.importar(new Blob([u])); }""", base64.b64encode(f.read_bytes()).decode())
    assert imp(b, p1)["ordenesNuevas"] == 1
    # A la anula; B recibe la anulación aunque B la haya tocado después.
    _anular(a, "OT equivocada", "Técnico A")
    b.evaluate("""() => CAMPO.almacen.listar().then(l => { const p = l[0]; p.modificado = Date.now() + 9e7;
        return CAMPO.almacen.guardar(p); })""")
    p2 = tmp_path / "dos.nefer-flota"
    p2.write_bytes(base64.b64decode(exp(a)))
    i = imp(b, p2)
    assert i["anulacionesRecibidas"] == 1
    assert b.evaluate("() => CAMPO.almacen.listar().then(l => l[0].estado)") == "anulado"
    # Y de vuelta, la anulada de B no se des-anula con una copia vieja.
    assert imp(b, p1)["sinCambios"] == 1
    assert b.evaluate("() => CAMPO.almacen.listar().then(l => l[0].estado)") == "anulado"
    nav.close()
