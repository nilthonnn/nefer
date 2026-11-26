"""Cada foto de la inspección queda también en el teléfono, y se revisa.

- En el .apk, cada foto que entra a una orden se copia sola a la galería,
  DCIM/Actas de campo/<TAG>/, con un nombre que dice qué es (TAG, casilla,
  fecha y hora): la trazabilidad no depende de la app. La orden anota dónde
  quedó la copia. Se puede apagar.
- En el navegador, que no puede escribir en la galería, un botón las guarda
  en Descargas con el mismo nombre.
- Criterios de foto técnica medidos en la foto: movida, oscura, muy clara o
  con reflejo → aviso con el consejo para repetirla. No bloquea.
"""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

from datos_mant import EQUIPOS  # noqa: E402
from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import _contexto, _lanzar, servidor  # noqa: E402,F401

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")

# Un puente de Android de mentira: guarda lo que le llega, como el de verdad.
PUENTE = """
window.__guardadas = [];
(function () {
  var abiertos = {}, n = 0;
  function nuevo(e) { var v = 'e' + (++n); abiertos[v] = e; return v; }
  window.Anfitrion = {
    version: function () { return 'prueba'; },
    abrir: function (nombre, mime) { return nuevo({ nombre: nombre, carpeta: 'Descargas/Actas de campo', bytes: 0 }); },
    abrirFoto: function (nombre, mime, sub) { return nuevo({ nombre: nombre, carpeta: 'DCIM/Actas de campo/' + sub, bytes: 0, mime: mime }); },
    trozo: function (v, b64) { abiertos[v].bytes += atob(b64).length; return ''; },
    cerrar: function (v) { var e = abiertos[v]; delete abiertos[v]; window.__guardadas.push(e); return 'OK:' + e.carpeta + '/' + e.nombre; },
    cancelar: function (v) { delete abiertos[v]; }
  };
})();
"""


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="module")
def fotos(tmp_path_factory):
    d = tmp_path_factory.mktemp("fotos-tel")
    nitida = Image.new("RGB", (1600, 1200), (200, 200, 200))
    g = ImageDraw.Draw(nitida)
    for k in range(0, 1600, 40):
        g.line([(k, 0), (k, 1200)], fill=(20, 20, 20), width=3)
        g.text((k + 5, 600), "C100D6", fill=(0, 0, 0))
    nitida.save(d / "placa.jpg", "JPEG", quality=90)
    nitida.filter(ImageFilter.GaussianBlur(12)).save(d / "movida.jpg", "JPEG", quality=90)
    Image.new("RGB", (1600, 1200), (15, 15, 15)).save(d / "oscura.jpg", "JPEG", quality=90)
    return d


def _orden(pg):
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["064"])
    pg.evaluate("() => MANT.ordenes.crear('064', 'INSPECCION')")
    pg.click("#tab-mantenimiento")
    pg.wait_for_selector("#m-orden:not([hidden])")


def test_en_el_apk_cada_foto_va_a_la_galeria_del_equipo(pw, servidor, fotos):
    nav = _lanzar(pw)
    pg = _contexto(nav, movil=True).new_page()
    pg.add_init_script(PUENTE)
    pg.goto(servidor)
    _orden(pg)
    assert pg.is_checked("[data-copia-fotos]"), "por omisión se copia"
    pg.set_input_files("#m-o-foto-c05", str(fotos / "placa.jpg"))
    pg.wait_for_function("() => window.__guardadas.length === 1")
    g = pg.evaluate("() => window.__guardadas[0]")
    assert g["carpeta"] == "DCIM/Actas de campo/064"
    assert g["nombre"].startswith("064_grupo_c05_") and g["nombre"].endswith(".jpg")
    assert g["bytes"] > 1000 and g["mime"].startswith("image/")
    pg.wait_for_selector("text=Copia en el teléfono: DCIM/Actas de campo/064/")
    f = pg.evaluate("() => MANT.ordenes.actual().fotos[0]")
    assert f["copia"]["ruta"].startswith("DCIM/Actas de campo/064/064_grupo_c05_")

    # Apagado, no se copia.
    pg.uncheck("[data-copia-fotos]")
    pg.set_input_files("#m-o-foto-c06", str(fotos / "placa.jpg"))
    pg.wait_for_function("() => MANT.ordenes.actual().fotos.length === 2")
    pg.wait_for_timeout(500)
    assert pg.evaluate("() => window.__guardadas.length") == 1
    nav.close()


def test_en_el_navegador_se_guardan_a_mano_con_nombre_trazable(pw, servidor, fotos):
    nav = _lanzar(pw)
    pg = _contexto(nav, descargas=True).new_page()
    pg.goto(servidor)
    _orden(pg)
    assert pg.locator("[data-copia-fotos]").count() == 0, "el navegador no escribe en la galería"
    pg.set_input_files("#m-o-foto-c05", str(fotos / "placa.jpg"))
    pg.wait_for_selector("[data-accion=fotos-al-telefono]")
    with pg.expect_download() as d:
        pg.click("[data-accion=fotos-al-telefono]")
    assert d.value.suggested_filename.startswith("064_grupo_c05_")
    pg.wait_for_selector("text=Copia en el teléfono: Descargas/064_grupo_c05_")
    nav.close()


def test_avisa_si_la_foto_salio_movida_u_oscura(pw, servidor, fotos):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    _orden(pg)
    pg.set_input_files("#m-o-foto-c05", str(fotos / "placa.jpg"))
    pg.set_input_files("#m-o-foto-c12", str(fotos / "movida.jpg"))
    pg.set_input_files("#m-o-foto-c06", str(fotos / "oscura.jpg"))
    # Tres tomas seguidas, sin esperar: ninguna se pierde aunque la pantalla
    # se repinte mientras la cámara está abierta.
    pg.wait_for_function("() => MANT.ordenes.actual().fotos.filter(f => f.calidad).length === 3")
    cal = {f["casilla"]: f["calidad"]["avisos"] for f in pg.evaluate("() => MANT.ordenes.actual().fotos")}
    assert cal["c05"] == [], cal
    assert "borrosa" in cal["c12"]
    assert "oscura" in cal["c06"]
    texto = pg.text_content("[data-casilla=c12]")
    assert "Parece movida" in texto and "usted decide" in texto
    assert "Cómo tomarla" in pg.text_content("[data-casilla=c05]")
    nav.close()


# --------------------------------------------------------------------------
# Lo que salió usando la app como técnico, una jornada completa
# --------------------------------------------------------------------------

def test_el_lector_siempre_deja_salir(pw, servidor, fotos):
    """Leyendo o fallado, el panel tiene botón: no se queda pegado en la foto."""
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    _orden(pg)
    pg.evaluate("() => { MANT.lector.leerFoto = () => new Promise(() => {}); }")
    pg.set_input_files("#m-o-foto-c05", str(fotos / "placa.jpg"))
    pg.wait_for_selector("[data-casilla=c05] [data-accion=foto-leer]")
    pg.click("[data-casilla=c05] [data-accion=foto-leer]")
    pg.wait_for_selector(".m-lectura-estado")
    pg.click("[data-casilla=c05] [data-accion=lect-cerrar]")
    assert pg.locator(".m-lectura-estado").count() == 0
    nav.close()


def test_el_nombre_de_la_orden_sigue_a_la_clasificacion(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    _orden(pg)
    pg.check("input[name=m-o-tipo][value=PREVENTIVO]")
    pg.wait_for_timeout(300)
    pg.fill("#m-o-ot-ot", "4017305000")
    pg.wait_for_timeout(1500)
    pg.click("#m-o-volver")
    pg.wait_for_timeout(500)
    texto = pg.inner_text("#m-ot-lista")
    assert "OT 4017305000 · 064 · Preventivo" in texto, texto
    # El que escribió el técnico no se toca.
    pg.locator("#m-ot-lista [data-retomar], #m-ot-lista button:has-text('Continuar')").first.click()
    pg.fill("#m-proy-nombre", "Mi orden de prueba")
    pg.wait_for_timeout(300)
    pg.check("input[name=m-o-tipo][value=CORRECTIVO]")
    pg.wait_for_timeout(1500)
    pg.click("#m-o-volver")
    pg.wait_for_timeout(500)
    assert "Mi orden de prueba" in pg.inner_text("#m-ot-lista")
    nav.close()


def test_el_historial_de_la_ficha_abierta_se_actualiza(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.equipos")
    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-equipos")
    pg.fill("#m-eq-tag", "077")
    pg.click("#m-eq-nuevo button[type=submit]")
    pg.wait_for_selector("#m-ficha:not([hidden])")
    assert "Sin órdenes" in pg.inner_text("#m-f-hist-lista")
    pg.click("#m-f-inspeccion")
    pg.wait_for_selector("#m-orden:not([hidden])")
    pg.wait_for_timeout(1200)
    pg.click("#m-seg-equipos")
    pg.wait_for_function("() => !/Sin órdenes/.test(document.querySelector('#m-f-hist-lista').innerText)")
    nav.close()
