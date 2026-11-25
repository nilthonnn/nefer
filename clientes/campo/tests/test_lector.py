"""Lector de fotos: leer valores de placa, panel, batería y horómetro.

El reconocimiento corre en el navegador (Tesseract en WebAssembly) con los
archivos de docs/app/lector: ninguna foto sale del teléfono. Lo leído es
siempre una propuesta que el técnico corrige y elige.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from datos_mant import EQUIPOS  # noqa: E402
from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import _contexto, _lanzar, servidor  # noqa: E402,F401

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")

APP = Path(__file__).resolve().parents[1] / "docs" / "app"
FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="module")
def js(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.lector")
    yield lambda codigo, arg=None: pg.evaluate(codigo, arg)
    nav.close()


def _i(js, texto, casilla, tags=None):
    return {p["ruta"]: p["valor"] for p in
            js("([t, c, g]) => MANT.lector.interpretar(t, c, {tags: g})", [texto, casilla, tags or []])}


# --------------------------------------------------------------------------
# interpretar: el texto leído → los campos que pide la ficha
# --------------------------------------------------------------------------

def test_horometro(js):
    assert _i(js, "HOURS 6241.5", "c06") == {"ot.horometroSalida": 6241.5}
    assert _i(js, "000624 h", "c06") == {"ot.horometroSalida": 624}
    assert _i(js, "Engine hours\n12 34\n6241,5", "c06") == {"ot.horometroSalida": 6241.5}


def test_placa_del_grupo(js):
    t = ("GENERATOR SET\nMODEL: C100D6\nSERIAL NO. D19I420882\n100 KVA 80 KW\n"
         "380/220 V 60 HZ 3 PHASE 1800 RPM")
    assert _i(js, t, "c05") == {"grupo.modelo": "C100D6", "grupo.serie": "D19I420882", "kva": 100,
                                "voltajeNominal": 380, "frecuenciaHz": 60, "fases": 3, "rpm": 1800}


def test_placas_de_motor_y_alternador(js):
    assert _i(js, "ENGINE MODEL 6BTA5.9-G6  ESN 84862783  CPL 2911", "c12") == {
        "motor.modelo": "6BTA5.9-G6", "motor.serie": "84862783", "motor.cpl": "2911"}
    assert _i(js, "FRAME PI144E1 SERIAL X17L492615 WDG 311", "g01") == {
        "alternador.modelo": "PI144E1", "alternador.serie": "X17L492615", "alternador.winding": "311"}


def test_bateria_y_probador(js):
    assert _i(js, "12V 124AH 810CCA", "c19") == {"bateria.voltaje": 12, "bateria.ah": 124, "bateria.cca": 810}
    r = _i(js, "SOH: 65%  SOC 80%  12.58V  690CCA  4.12mΩ", "c21")
    assert r == {"probador.soh": 65, "probador.soc": 80, "probador.voltaje": 12.58,
                 "probador.ccaMedido": 690, "probador.resistenciaMOhm": 4.12, "estados.c21": "FALLA"}
    assert _i(js, "SOH 98%", "c21")["estados.c21"] == "OK"
    assert _i(js, "SOH 80%", "c21")["estados.c21"] == "OBS"


def test_pantallas_del_tablero(js):
    assert _i(js, "L1-L2 384 V  L1-N 222 V  I1 45 A", "g04") == {
        "voltajeLL": 384, "voltajeLN": 222, "corrienteA": 45}
    assert _i(js, "60.0 Hz 1800 RPM", "g05") == {"hz": 60, "rpm": 1800}
    assert _i(js, "OIL 310 kPa  COOLANT 82 C", "g06") == {"presionAceitePsi": 45, "tempRefrigeranteC": 82}
    assert _i(js, "OIL 45 PSI  WATER 180 F", "g06") == {"presionAceitePsi": 45, "tempRefrigeranteC": 82.2}
    assert _i(js, "BATTERY 27.6 V", "g07") == {"vBateria": 27.6}


def test_reconoce_el_equipo_por_su_tag(js):
    tags = ["064", "AAQ29", "C450D6"]
    assert _i(js, "UNIDAD AAQ29 PLATAFORMA", "c01", tags) == {"tag": "AAQ29"}
    assert _i(js, "TORRE AAQ290", "c01", tags) == {}, "sólo el TAG entero"
    assert _i(js, "sin nada", "c01", tags) == {}


# --------------------------------------------------------------------------
# batería: los criterios de aceptación
# --------------------------------------------------------------------------

def test_validar_bateria_soh_65_critico_y_98_ok(js):
    a = js("() => MANT.validaciones.validarBateria({tipo: 'LIBRE_MANTENIMIENTO', probador: {soh: 65, soc: 90}})")
    assert ("critico", "probador.soh") in [(x["nivel"], x["campo"]) for x in a]
    b = js("() => MANT.validaciones.validarBateria({tipo: 'LIBRE_MANTENIMIENTO', probador: {soh: 98, soc: 90}})")
    assert [x for x in b if x["nivel"] != "info"] == [], "98 % es OK: sólo quedan ítems sin marcar"


# --------------------------------------------------------------------------
# lectura de verdad: imagen → Tesseract en el navegador → propuesta
# --------------------------------------------------------------------------

def _imagen(ruta: Path, lineas: list[str]):
    fuente = ImageFont.truetype(FUENTE, 64)
    img = Image.new("RGB", (1400, 130 + 100 * len(lineas)), (245, 245, 240))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lineas):
        d.text((60, 60 + 100 * i), l, font=fuente, fill=(15, 15, 15))
    img.save(ruta, "JPEG", quality=92)
    return ruta


def test_el_lector_viaja_con_la_app():
    for f in ("tesseract.min.js", "worker.min.js", "tesseract-core-simd-lstm.wasm.js", "eng.traineddata.gz", "LEEME.md"):
        assert (APP / "lector" / f).is_file(), f
    assert 'var LECTOR = "campo-lector-7.0.0"' in (APP / "sw.js").read_text()


def test_lee_el_horometro_y_la_placa_y_pide_confirmar(pw, servidor, tmp_path):
    horo = _imagen(tmp_path / "horometro.jpg", ["HOURS 6241.5"])
    placa = _imagen(tmp_path / "placa.jpg", ["MODEL C100D6", "SERIAL NO D19I420882", "380 V 60 HZ"])
    nav = _lanzar(pw)
    ctx = _contexto(nav, movil=True)
    pg = ctx.new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", dict(EQUIPOS["064"], horometro=6200))
    pg.evaluate("() => MANT.ordenes.crear('064', 'INSPECCION', '', '4017303000')")
    pg.click("#tab-mantenimiento")
    pg.wait_for_selector("#m-orden:not([hidden])")
    pg.click("[data-accion=confirmar]")

    pg.set_input_files("#m-o-foto-c06", str(horo))
    pg.wait_for_selector("[data-casilla=c06] [data-accion=foto-leer]")
    pg.click("[data-casilla=c06] [data-accion=foto-leer]")
    pg.wait_for_selector(".m-lectura", timeout=90000)
    assert pg.input_value(".m-lectura [data-valor-prop='0']") == "6241.5"
    assert "HOURS" in pg.text_content(".m-lectura .m-texto")
    assert pg.evaluate("() => MANT.ordenes.actual().ot.horometroSalida") is None, "nada se escribe sin elegir"
    pg.click("[data-accion=lect-usar]")
    o = pg.evaluate("() => MANT.ordenes.actual()")
    assert o["ot"]["horometroSalida"] == 6241.5
    assert o["lecturas"][0]["casilla"] == "c06" and o["lecturas"][0]["aplicadas"][0]["valor"] == 6241.5

    # Placa: el técnico corrige un valor antes de usarlo; va a la ficha y la
    # orden pide volver a confirmar la placa.
    ctx.set_offline(True)                     # el lector ya está guardado: sin señal
    pg.set_input_files("#m-o-foto-c05", str(placa))
    pg.click("[data-casilla=c05] [data-accion=foto-leer]")
    pg.wait_for_selector(".m-lectura", timeout=90000)
    props = pg.evaluate("() => Array.from(document.querySelectorAll('.m-lectura .m-propuesta')).map(n => n.innerText)")
    assert any("Modelo" in t for t in props) and any("serie" in t for t in props)
    pg.fill(".m-lectura [data-valor-prop='1']", "D19I420882")
    pg.click("[data-accion=lect-usar]")
    pg.wait_for_timeout(400)
    ficha = pg.evaluate("() => CAMPO.almacen.equipos.leer('064')")
    assert ficha["grupo"]["modelo"] == "C100D6" and ficha["grupo"]["serie"] == "D19I420882"
    assert ficha["voltajeNominal"] == 380 and ficha["frecuenciaHz"] == 60
    nav.close()


def test_una_foto_de_otro_equipo_se_avisa(pw, servidor, tmp_path):
    foto = _imagen(tmp_path / "frente.jpg", ["UNIDAD AAQ29"])
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    for e in (EQUIPOS["064"], EQUIPOS["AAQ29"]):
        pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", e)
    pg.evaluate("() => MANT.ordenes.crear('064', 'INSPECCION', '', '4017303100')")
    pg.click("#tab-mantenimiento")
    pg.set_input_files("#m-o-foto-c01", str(foto))
    pg.click("[data-casilla=c01] [data-accion=foto-leer]")
    pg.wait_for_selector(".m-lectura", timeout=90000)
    assert "la foto es de otro equipo: esta orden es del 064" in pg.inner_text(".m-lectura")
    nav.close()
