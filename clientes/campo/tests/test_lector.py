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


# --------------------------------------------------------------------------
# formatos reales de campo (series alteradas: los equipos son del cliente)
# --------------------------------------------------------------------------

def test_pantalla_del_controlador_en_ingles(js):
    t = ("Genset Data (1/2) Alternator Engine\nAvg Voltage 230Vac Hours 9248.0hrs\n"
         "Avg Current 74Amps Coolant Temp 183°F\nTotal kW 28kW Oil Pressure 55.1psi\n"
         "Total PF 0.96PF PCC Batt Volt 27.93Vdc\nFrequency 60.10Hz %Torq/Duty 14%")
    r = _i(js, t, "g04")
    assert r == {"ot.horometroSalida": 9248.0, "voltajeLL": 230, "corrienteA": 74, "kw": 28, "hz": 60.1,
                 "presionAceitePsi": 55.1, "tempRefrigeranteC": 83.9, "vBateria": 27.93}


def test_pantalla_del_controlador_en_espanol(js):
    r = _i(js, "Datos del Alternador (3/3)\nTension Alt 400 Vac\nkVA - Total 2.4 kVA\nFrec. Linea 60.07 Hz", "g04")
    assert r == {"voltajeLL": 400, "kva": 2.4, "hz": 60.07}
    r = _i(js, "Temperatura Refrigerante 156°F\nTens.bat. PCC 13.89Vdc\nVeloc motor 1800rpm\nHrs motor 11825.6h", "g06")
    assert r["ot.horometroSalida"] == 11825.6 and r["vBateria"] == 13.89 and r["rpm"] == 1800
    assert r["tempRefrigeranteC"] == 68.9
    assert _i(js, "Datos de Motor (2/2)\nPres. Aceite 65.8 psi", "g06") == {"presionAceitePsi": 65.8}


def test_l_l_y_l_n_por_el_voltaje_nominal(js):
    r = js("t => MANT.lector.interpretar(t, 'g04', {nominal: 380})", "Avg Voltage 221Vac")
    assert {p["ruta"]: p["valor"] for p in r} == {"voltajeLN": 221}
    r = js("t => MANT.lector.interpretar(t, 'g04', {nominal: 220})", "Avg Voltage 221Vac")
    assert {p["ruta"]: p["valor"] for p in r} == {"voltajeLL": 221}


def test_placa_del_grupo_con_secciones(js):
    t = ("Power Generation\nModelo: C300D6 N° de Serie: A18T000001\nN° de Spec: G01 Año: 2018\n"
         "POTENCIA (KW) 300 270\n(KVA) 375 338\nFRECUENCIA (Hz) 60\nBATERIA — Tensión Vcc 24Vcc\n"
         "— Capacidad (A.h) 100A.h.\nGENERADOR — Modelo: HC4E\n— Winding: WD311\n— N° de Serie: X17J000002\n"
         "MOTOR — Modelo: QSL9 G5\n— N° de Serie: 36500003\nCONTROLADOR — Modelo: PC 2.3")
    r = _i(js, t, "c05")
    assert r["grupo.modelo"] == "C300D6" and r["grupo.serie"] == "A18T000001"
    assert r["kva"] == 375 and r["frecuenciaHz"] == 60
    assert r["alternador.modelo"] == "HC4E" and r["alternador.winding"] == "311" and r["alternador.serie"] == "X17J000002"
    assert r["motor.modelo"] == "QSL9-G5" and r["motor.serie"] == "36500003"
    assert r["controladorModelo"] == "PC 2.3"
    assert r["bateria.voltaje"] == 24 and r["bateria.ah"] == 100


def test_placas_en_ingles(js):
    t = ("Generating Set ISO 8528 G2 SPEC-E\nModel Number C100D6\nSerial Number D19I000004\n"
         "Controller PC1.2\nRated Power (KVA) 125.0 113.8\nRated Voltage (V) 220 220\nRated Frequency (Hz) 60 60")
    r = _i(js, t, "c05")
    assert (r["grupo.modelo"], r["grupo.serie"], r["kva"], r["voltajeNominal"], r["frecuenciaHz"],
            r["controladorModelo"]) == ("C100D6", "D19I000004", 125, 220, 60, "PC1.2")
    t = "MODEL DE500SE0\nSERIAL NUMBER CAT00C15CLXJ00005\n625 kVA\nRATED VOLTAGE 240/139 V\nPHASE 3\nRATED R.P.M 1800"
    r = _i(js, t, "c05")
    assert (r["grupo.modelo"], r["voltajeNominal"], r["fases"], r["rpm"], r["kva"]) == ("DE500SE0", 240, 3, 1800, 625)
    assert _i(js, "Fabricante : Caterpillar\nAltitud : 3,600 msnm\nVoltaje : 480 V.", "c05") == {
        "voltajeNominal": 480, "informe.generalidades.msnm": "3600"}
    assert _i(js, "ENGINE MODEL C15\nSERIAL NUMBER *FTH00006*\nARRANGEMENT NUMBER 460-7413", "c12") == {
        "motor.modelo": "C15", "motor.serie": "FTH00006"}
    assert _i(js, "Engine Model : 6BTA5.9-G6\nRated HP : 177 @1800 RPM\nEngine Sr. No. : 84800007", "c12") == {
        "motor.modelo": "6BTA5.9-G6", "motor.serie": "84800007"}
    assert _i(js, "FRAME/CORE: UCI224G1\nWDG: 311\nSERIAL NO: G19J000008", "g01") == {
        "alternador.modelo": "UCI224G1", "alternador.winding": "311", "alternador.serie": "G19J000008"}
    assert _i(js, "FRAME WDG SERIAL Nº\nFRAME LC6114F WDG S2/4 SERIAL Nº *F6B00009*", "g01")["alternador.serie"] == "F6B00009"


def test_probador_de_baterias(js):
    r = _i(js, "GOOD BATTERY\nSOH 72% 935A\nSOC100% 13.61V\nR= 3.20mΩ", "c21")
    assert r == {"probador.soh": 72, "probador.soc": 100, "probador.voltaje": 13.61, "probador.ccaMedido": 935,
                 "probador.resistenciaMOhm": 3.2, "estados.c21": "OBS"}


def test_no_toma_rotulos_ni_numeros_pegados_por_valores(js):
    r = _i(js, "Model Number\nSerial Number\nManufacturing Order Number\nC20D6\nG18I000010", "c05")
    assert r.get("grupo.modelo") != "SERIAL" and r.get("grupo.serie") != "MANUFACTURING"
    assert "voltajeNominal" not in _i(js, "Voltaje :1480 V.", "c05"), "1480 no es un voltaje de placa"


# --------------------------------------------------------------------------
# autoaprendizaje: correcciones del técnico y fichas existentes
# --------------------------------------------------------------------------

AJUSTAR = "([p, fichas, tag]) => MANT.lector.ajustar(p, fichas, tag)"


def test_corrige_con_la_ficha_del_mismo_equipo(js):
    fichas = [{"tag": "064", "grupo": {"modelo": "C100D6", "serie": "D19I420882"}},
              {"tag": "071", "grupo": {"modelo": "C150D6", "serie": "D20I111111"}}]
    p = [{"destino": "ficha", "ruta": "grupo.modelo", "valor": "C100D8"},
         {"destino": "ficha", "ruta": "grupo.serie", "valor": "D181420882"}]
    r = js(AJUSTAR, [p, fichas, "064"])
    assert [(x["valor"], x["leido"], x["origen"]) for x in r] == [
        ("C100D6", "C100D8", "ficha 064"), ("D19I420882", "D181420882", "ficha 064")]
    r = js(AJUSTAR, [p[:1], fichas, "999"])
    assert r[0]["valor"] == "C100D8" and "origen" not in r[0], "contra otra ficha no se adivina un código corto"


def test_recuerda_la_correccion_del_tecnico_y_viaja(js):
    js("() => localStorage.removeItem('campo.lector.aprendizaje')")
    js("() => MANT.lector.aprender('alternador.modelo', 'HC.IS34E1', 'HCI534E1')")
    r = js(AJUSTAR, [[{"destino": "ficha", "ruta": "alternador.modelo", "valor": "HC.IS34E1"}], [], None])
    assert (r[0]["valor"], r[0]["origen"]) == ("HCI534E1", "aprendido")
    texto = js("() => MANT.lector.exportarAprendizaje().text()")
    js("() => localStorage.removeItem('campo.lector.aprendizaje')")
    assert js("t => MANT.lector.importarAprendizaje(t)", texto) == 1
    r = js(AJUSTAR, [[{"destino": "ficha", "ruta": "alternador.modelo", "valor": "HC.IS34E1"}], [], None])
    assert r[0]["valor"] == "HCI534E1"


def test_encuadrar_y_leer_aprende_lo_que_el_tecnico_corrige(pw, servidor, tmp_path):
    placa = _imagen(tmp_path / "alt.jpg", ["FRAME HC.IS34E1", "WDG 311"])
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.ordenes")
    pg.evaluate("() => localStorage.removeItem('campo.lector.aprendizaje')")
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["064"])
    pg.evaluate("() => MANT.ordenes.crear('064', 'INSPECCION', '', '4017303200')")
    pg.click("#tab-mantenimiento")
    pg.set_input_files("#m-o-foto-g01", str(placa))
    pg.click("[data-casilla=g01] [data-accion=foto-encuadrar]")
    pg.wait_for_selector("#editor:not([hidden])")
    pg.click("#ed-usar")
    pg.wait_for_selector(".m-lectura", timeout=90000)
    assert "(encuadre)" in pg.text_content(".m-lectura")
    k = pg.evaluate("""() => Array.from(document.querySelectorAll('.m-lectura .m-propuesta'))
        .findIndex(n => /Modelo/.test(n.textContent))""")
    pg.fill(f".m-lectura [data-valor-prop='{k}']", "HCI534E1")
    pg.click("[data-accion=lect-usar]")
    pg.wait_for_timeout(300)
    a = pg.evaluate("() => MANT.lector.aprendizaje().correcciones")
    assert any(c["usado"] == "HCI534E1" for c in a.values()), a
    nav.close()
