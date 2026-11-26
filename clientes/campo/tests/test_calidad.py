"""Fase 4 · calidad: accesibilidad, 30 fotos por orden y todo en modo avión."""

from __future__ import annotations

import base64
import re
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from datos_mant import EQUIPOS  # noqa: E402
from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import _contexto, _lanzar, servidor  # noqa: E402,F401

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")
AXE = (Path(__file__).parent / "recursos" / "axe.min.js").read_text(encoding="utf-8")
FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REGLAS = "{runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']}}"


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


def _axe(pg):
    pg.add_script_tag(content=AXE)
    return pg.evaluate(f"""() => axe.run(document, {REGLAS}).then(r => r.violations.map(v =>
        [v.id, v.impact, v.nodes.slice(0, 3).map(n => n.target.join(' '))]))""")


# --------------------------------------------------------------------------
# accesibilidad (WCAG 2.2 A y AA), en tema claro y oscuro
# --------------------------------------------------------------------------

@pytest.mark.parametrize("tema", ["light", "dark"])
def test_pantallas_de_mantenimiento_sin_fallas_de_accesibilidad(pw, servidor, tema):
    nav = _lanzar(pw)
    pg = nav.new_context(viewport={"width": 390, "height": 844}, color_scheme=tema,
                         has_touch=True, is_mobile=True).new_page()
    pg.add_init_script("try{localStorage.setItem('campo.orden.abierta','1')}catch(e){}")  # orden entera, todas las secciones
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["064"])
    fallas = {}
    fallas["inicio"] = _axe(pg)
    pg.click("#tab-mantenimiento")
    fallas["ordenes"] = _axe(pg)
    pg.evaluate("() => MANT.ordenes.crear('064', 'CORRECTIVO', '', '4017309000')")
    pg.click("[data-accion=bat-agregar]")
    pg.check("input[name=m-o-bat-tipo][value=LIBRE_MANTENIMIENTO]")
    pg.click("[data-estado-foto=c17][data-valor=FALLA]")
    fallas["orden"] = _axe(pg)
    pg.click("[data-firmar='ot.firmas.tecnico']")
    fallas["firma"] = _axe(pg)
    pg.click("#m-firma-cancelar")
    pg.click("#m-o-volver")
    pg.click("#m-seg-equipos")
    pg.evaluate("() => MANT.equipos.abrir('064')")
    fallas["ficha"] = _axe(pg)
    pg.click("#tab-despacho")
    fallas["despacho"] = _axe(pg)
    assert {k: v for k, v in fallas.items() if v} == {}
    nav.close()


# --------------------------------------------------------------------------
# rendimiento: 30 fotos de cámara (12 MP) en una orden
# --------------------------------------------------------------------------

CASILLAS = ["c01", "c05", "c06", "g01", "c08", "c09", "c11", "c12", "c13", "c14", "c15", "c16", "c17", "c18",
            "c19", "c20", "c21", "c22", "g03", "g04", "g05", "g06", "g07", "g08", "g09", "g11", "g12", "c23",
            "c23", "c23"]


@pytest.fixture(scope="module")
def treinta(tmp_path_factory):
    d = tmp_path_factory.mktemp("treinta")
    fuente = ImageFont.truetype(FUENTE, 160)
    rutas = []
    for i, c in enumerate(CASILLAS):
        img = Image.new("RGB", (4000, 3000), (40 + i * 6, 90, 140 - i * 3))
        dib = ImageDraw.Draw(img)
        for k in range(0, 4000, 250):          # algo de detalle, como una foto
            dib.line([(k, 0), (4000 - k, 3000)], fill=(200, 200 - i * 5, 60), width=9)
        dib.text((200, 200), f"FOTO {i + 1}", font=fuente, fill=(255, 255, 255))
        r = d / f"064_grupo_{c}_foto{i + 1:02d}_20261124-1031.jpg"
        img.save(r, "JPEG", quality=92)
        rutas.append(str(r))
    return rutas


def test_treinta_fotos_entran_se_guardan_y_vuelven(pw, servidor, treinta):
    nav = _lanzar(pw)
    ctx = _contexto(nav, movil=True)
    pg = ctx.new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["064"])
    pg.evaluate("() => MANT.ordenes.crear('064', 'PREVENTIVO', 'PM1_250', '4017309100')")
    pg.click("#tab-mantenimiento")
    pid = pg.evaluate("() => CAMPO.proyectos.actual().id")
    peso = sum(Path(r).stat().st_size for r in treinta)

    t0 = time.monotonic()
    pg.set_input_files("#m-o-fotos-varias", treinta)
    pg.wait_for_function("() => /30 fotos guardadas/.test(document.querySelector('#m-o-fotos-estado').textContent)",
                         timeout=180000)
    carga = time.monotonic() - t0
    pg.click("[data-accion=fotos-confirmar]")

    # Guardar lo tecleado no reescribe las fotos: el registro del proyecto es chico y rápido.
    pg.fill("#m-o-ot-observaciones", "Inspección con 30 fotos")
    t1 = time.monotonic()
    pg.evaluate("() => CAMPO.proyectos.volcar()")
    guardar = time.monotonic() - t1
    r = pg.evaluate("""id => CAMPO.almacen.leer(id).then(p => ({json: JSON.stringify(p).length,
        fotos: p.datos.fotos.length, ok: p.datos.fotos.filter(f => f.casilla).length}))""", pid)
    tienda = pg.evaluate("id => CAMPO.almacen.fotos.deProyecto(id).then(l => [l.length, l.reduce((a, f) => a + f.archivo.size, 0)])", pid)
    print(f"\n30 fotos ({peso / 1e6:.0f} MB originales): carga {carga:.1f} s, guardado {guardar * 1000:.0f} ms, "
          f"proyecto {r['json'] / 1024:.0f} KB, tienda {tienda[1] / 1e6:.1f} MB")
    assert r["fotos"] == 30 and r["ok"] == 30, "cada una en su casilla por el nombre"
    assert tienda[0] == 30
    assert r["json"] < 64 * 1024, "el proyecto guarda ids, no bytes"
    assert tienda[1] < peso / 3, "se reducen al guardarse"
    assert guardar < 1.0, guardar
    assert carga < 150, carga

    # PDF del anexo con las 30.
    t2 = time.monotonic()
    datos = base64.b64decode(pg.evaluate("""async () => { const b = await MANT.documentos.pdf(MANT.ordenes.actual(), ['anexo']);
      const u = new Uint8Array(await b.arrayBuffer()); let s = '';
      for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode.apply(null, u.subarray(i, i + 8192));
      return btoa(s); }"""))
    pdf = time.monotonic() - t2
    print(f"anexo PDF: {len(datos) / 1e6:.1f} MB en {pdf:.1f} s, {len(re.findall(rb'/Type /Page[^s]', datos))} hojas")
    assert len(re.findall(rb"/Subtype /Image", datos)) == 30
    assert pdf < 90, pdf

    # Se cierra la app y vuelve con las 30.
    pg.close()
    pg = ctx.new_page()
    pg.goto(servidor)
    pg.wait_for_selector("#proy-recuperado", timeout=15000)
    pg.wait_for_function("() => Array.from(document.querySelectorAll('#m-o-cuerpo img[data-foto]'))"
                         ".filter(i => i.naturalWidth > 0).length === 30", timeout=60000)
    nav.close()


# --------------------------------------------------------------------------
# todo en modo avión, de punta a punta
# --------------------------------------------------------------------------

def _texto(ruta, lineas):
    img = Image.new("RGB", (1400, 130 + 100 * len(lineas)), (245, 245, 240))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lineas):
        d.text((60, 60 + 100 * i), l, font=ImageFont.truetype(FUENTE, 64), fill=(15, 15, 15))
    img.save(ruta, "JPEG", quality=92)
    return str(ruta)


def test_jornada_completa_en_modo_avion(pw, servidor, tmp_path):
    nav = _lanzar(pw)
    ctx = nav.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True,
                          has_touch=True, is_mobile=True)
    pg = ctx.new_page()
    pg.add_init_script("try{localStorage.setItem('campo.orden.abierta','1')}catch(e){}")  # orden entera, todas las secciones
    # Con señal, una vez: la app se instala y el lector se deja listo.
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.lector")
    pg.evaluate("() => navigator.serviceWorker.ready.then(() => true)")
    assert pg.evaluate("() => MANT.lector.descargar()") is True
    pg.reload()
    pg.wait_for_function("() => navigator.serviceWorker.controller !== null")

    ctx.set_offline(True)                                   # sin señal desde aquí
    pg.reload()
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-equipos")
    pg.fill("#m-eq-tag", "064")
    pg.click("#m-eq-nuevo button[type=submit]")
    pg.wait_for_selector("#m-ficha:not([hidden])")
    pg.fill("#m-f-grupo-modelo", "C100D6")
    pg.fill("#m-f-grupo-serie", "D19I420882")
    pg.fill("#m-f-voltajeNominal", "380")
    pg.wait_for_function("() => /guardado/.test(document.querySelector('#m-f-guardado').textContent)")
    pg.click("#m-f-inspeccion")
    pg.wait_for_selector("#m-orden:not([hidden])")
    pg.click("[data-accion=confirmar]")
    pg.set_input_files("#m-o-foto-c06", _texto(tmp_path / "h.jpg", ["HOURS 6241.5"]))
    pg.click("[data-casilla=c06] [data-accion=foto-leer]")
    pg.wait_for_selector(".m-lectura", timeout=90000)
    pg.click("[data-accion=lect-usar]")
    pg.click("[data-estado-foto=c06][data-valor=OK]")
    pg.fill("#m-o-ot-ot", "4017309200")
    pg.fill("#m-o-ot-firmas-tecnico-nombre", "Técnico eléctrico")
    pg.click("[data-sn='informe.operativo'][data-valor=true]")
    with pg.expect_download() as d:
        pg.click("[data-doc=todo]")
    assert d.value.suggested_filename == "documentos-064-OT4017309200.pdf"
    assert "*HORÓMETRO:* 6241.5 hrs" in pg.input_value("#m-o-wa")
    pg.evaluate("() => CAMPO.proyectos.volcar()")

    pg.close()                                              # se cierra la app, sin señal
    pg = ctx.new_page()
    pg.goto(servidor)
    pg.wait_for_selector("#proy-recuperado", timeout=15000)
    o = pg.evaluate("() => MANT.ordenes.actual()")
    assert o["ot"]["ot"] == "4017309200" and o["ot"]["horometroSalida"] == 6241.5
    assert o["estados"]["c06"]["estado"] == "OK" and o["placaConfirmada"]
    assert o["equipo"]["grupo"]["serie"] == "D19I420882"
    nav.close()
