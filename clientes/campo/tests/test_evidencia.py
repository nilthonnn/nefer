"""Interpretar fotos y pruebas con evidencia, y aprender sólo con evidencia.

Lo que se tomó de los métodos de autoaprendizaje y de diagnóstico de
maquinaria, rehecho dentro de la app (sin red, sin enviar fotos a nadie):

- Lo leído pasa por un control de lo posible: un valor fuera de rango, o
  leído con poca confianza, llega sin marcar y con el motivo.
- Una corrección del técnico es primero una NOTA; sube a REGLA sólo con dos
  confirmaciones y un error de lectura con nombre. Lo desmarcado se anota
  como descarte. Nada que parezca una clave se guarda.
- La prueba con carga se lee por evidencia: medido / puede indicar /
  supuesto / verificar, con confianza, y sin dato de placa no se interpreta.
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


@pytest.fixture(scope="module")
def pagina(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.lector && MANT.ordenes")
    yield pg
    nav.close()


@pytest.fixture
def js(pagina):
    pagina.evaluate("() => localStorage.removeItem('campo.lector.aprendizaje')")
    return lambda codigo, arg=None: pagina.evaluate(codigo, arg)


REVISAR = "([p, c, o]) => MANT.lector.revisar(p, c, o)"


def test_lo_imposible_llega_sin_marcar_y_con_el_motivo(js):
    p = [{"destino": "columna", "ruta": "hz", "valor": 6.0},
         {"destino": "columna", "ruta": "hz", "valor": 60.1},
         {"destino": "orden", "ruta": "ot.horometroSalida", "valor": 9248},
         {"destino": "estado", "ruta": "probador.soh", "valor": 720}]
    r = js(REVISAR, [p, 80, {"horometroPrevio": 11825.6}])
    assert "45–65 Hz" in r[0]["duda"]
    assert "duda" not in r[1], "60,1 Hz es posible: no se toca"
    assert "no retrocede" in r[2]["duda"]
    assert "0–100 %" in r[3]["duda"]


def test_poca_confianza_se_dice(js):
    r = js(REVISAR, [[{"destino": "ficha", "ruta": "grupo.serie", "valor": "D19I420882"}], 30, {}])
    assert "baja confianza (30 %)" in r[0]["duda"]


def test_nota_regla_y_descartes(js):
    leer = lambda v: js("v => MANT.lector.ajustar([{destino:'ficha', ruta:'motor.serie', valor:v}], [], null)[0]", v)
    js("() => MANT.lector.aprender('motor.serie', '8451634B', '84516348')")
    r = leer("8451634B")
    assert r["valor"] == "8451634B" and r["antes"] == "84516348", "una vez es nota"
    js("() => MANT.lector.aprender('motor.serie', '8451634B', '84516348')")
    r = leer("8451634B")
    assert (r["valor"], r["origen"]) == ("84516348", "aprendido"), "dos veces y B/8: regla"
    c = js("() => Object.values(MANT.lector.aprendizaje().correcciones)[0]")
    assert c["etapa"] == "regla" and "confusión" in c["patron"]

    # Lo que no se parece a lo leído no es un error del lector: nunca es regla.
    for _ in range(3):
        js("() => MANT.lector.aprender('grupo.modelo', 'C20D6', 'C450D6')")
    r = js("() => MANT.lector.ajustar([{destino:'ficha', ruta:'grupo.modelo', valor:'C20D6'}], [], null)[0]")
    assert r["valor"] == "C20D6" and r["antes"] == "C450D6"

    # Dos descartes iguales: llega sin marcar y lo dice.
    js("() => MANT.lector.descartar('kva', 6825)")
    js("() => MANT.lector.descartar('kva', 6825)")
    r = js(REVISAR, [[{"destino": "ficha", "ruta": "kva", "valor": 6825}], 80, {}])
    assert "descartado antes 2 veces" in r[0]["duda"]


def test_nunca_guarda_lo_que_parece_una_clave(js):
    js("() => MANT.lector.aprender('grupo.serie', 'ghp_ABCDEF123', 'X')")
    js("() => MANT.lector.descartar('grupo.serie', 'password123')")
    a = js("() => MANT.lector.aprendizaje()")
    assert not a.get("correcciones") and not a.get("descartes")


DIAG = "([e, p]) => MANT.validaciones.diagnosticar(e, p)"


def _pruebas(vacio, carga):
    base = {"voltajeLL": None, "corrienteA": None, "hz": None, "vBateria": None,
            "presionAceitePsi": None, "tempRefrigeranteC": None, "rpm": None}
    return [dict(base, carga="inicial"), dict(base, carga=0, **vacio), dict(base, carga=25),
            dict(base, carga=50), dict(base, carga=100, **carga)]


def test_lectura_por_evidencia_de_la_prueba_con_carga(js):
    eq = dict(EQUIPOS["064"])
    eq.update(voltajeNominal=220, fases=3, frecuenciaHz=60, kva=125, rpm=1800,
              bateria={"voltaje": 24})
    r = js(DIAG, [eq, _pruebas({"hz": 60.2, "voltajeLL": 225, "presionAceitePsi": 60, "vBateria": 28.0},
                               {"hz": 57.6, "voltajeLL": 196, "corrienteA": 360, "presionAceitePsi": 30,
                                "tempRefrigeranteC": 101, "rpm": 1728})])
    temas = {d["tema"]: d for d in r}
    assert temas["Frecuencia con carga"]["confianza"] == "alta"
    assert "60.2" in temas["Frecuencia con carga"]["medido"] and "57.6" in temas["Frecuencia con carga"]["medido"]
    assert "1728" in temas["Velocidad (RPM)"]["medido"]
    assert "AVR" in temas["Regulación de voltaje"]["interpretacion"]
    assert temas["Carga"]["confianza"] == "alta" and "≈ 328 A" in temas["Carga"]["medido"]
    assert temas["Lubricación"]["confianza"] == "investigar", "no se afirma la causa"
    assert "c15" in temas["Refrigeración"]["verificar"]
    for d in r:
        assert d["medido"] and d["interpretacion"] and d["supuesto"] and d["verificar"]
    assert "no medido" in temas["Regulación de voltaje"]["supuesto"]


def test_sin_placa_no_se_interpreta(js):
    eq = {"tag": "999"}
    r = js(DIAG, [eq, _pruebas({"hz": 60.2}, {"hz": 57.0, "corrienteA": 300, "rpm": 1700, "vBateria": 12.1})])
    assert [d["tema"] for d in r] == ["Sin dato de placa"]
    assert "no se adivina" in r[0]["interpretacion"]


def test_la_orden_muestra_la_lectura_por_evidencia(pagina):
    pg = pagina
    eq = dict(EQUIPOS["064"], voltajeNominal=220, fases=3, frecuenciaHz=60, kva=125)
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", eq)
    pg.evaluate("() => MANT.ordenes.crear('064', 'INSPECCION')")
    pg.click("#tab-mantenimiento")
    pg.wait_for_selector("#m-orden:not([hidden])")
    pg.click("[data-accion=confirmar]")
    pg.wait_for_timeout(200)
    pg.evaluate("() => document.querySelectorAll('.m-columna').forEach(d => d.open = true)")
    for k, v in (("informe.pruebas.1.hz", "60.1"), ("informe.pruebas.4.hz", "57.5")):
        sel = "#" + pg.evaluate("k => 'm-o-' + k.replace(/\\./g, '-')", k)
        pg.fill(sel, v)
    pg.wait_for_timeout(300)
    texto = pg.text_content("#m-o-diag")
    assert "Frecuencia con carga" in texto and "Medido" in texto and "Verificar" in texto, texto
