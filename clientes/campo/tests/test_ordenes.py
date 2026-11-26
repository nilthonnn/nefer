"""Órdenes de trabajo de mantenimiento: clasificación, trazabilidad y aptitud.

El criterio de aceptación es el de la obra: llenar una OT completa del 064
en modo avión, cerrar la app, reabrirla y encontrarla intacta.
"""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402

from datos_mant import EQUIPOS  # noqa: E402
from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import App, _contexto, _lanzar, servidor  # noqa: E402,F401

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")

DESC_064 = "INSP. RUTINARIA T9_PLATAFORMA_064"


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


def _abrir(pg, servidor):
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.ordenes")


@pytest.fixture(scope="module")
def js(pw, servidor):
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    _abrir(pg, servidor)
    yield lambda codigo, arg=None: pg.evaluate(codigo, arg)
    nav.close()


# --------------------------------------------------------------------------
# clasificación y rutina por horómetro
# --------------------------------------------------------------------------

@pytest.mark.parametrize("horas,pm,objetivo", [
    (250, "PM1_250", 250), (500, "PM2_500", 500), (750, "PM1_250", 750),
    (1000, "PM3_1000", 1000), (2000, "PM4_2000", 2000), (6240, "PM1_250", 6250),
    (6490, "PM2_500", 6500), (7990, "PM4_2000", 8000), (3010, "PM3_1000", 3000),
    (40, "PM1_250", 250),
])
def test_rutina_sugerida_por_horometro(js, horas, pm, objetivo):
    r = js("h => MANT.modelo.sugerirPM(h)", horas)
    assert (r["pm"], r["objetivo"]) == (pm, objetivo)


def test_sin_horometro_no_hay_sugerencia(js):
    assert js("() => MANT.modelo.sugerirPM(null)") is None
    assert js("() => MANT.modelo.sugerirPM('')") is None


def test_clasificar_marca_una_sola_casilla_del_informe(js):
    r = js("""() => {
      const M = MANT.modelo, m = M.mantenimiento('064');
      M.clasificar(m, 'PREVENTIVO', 'PM2_500');
      const a = [m.clasificacion, Object.assign({}, m.informe.servicio)];
      M.clasificar(m, 'CORRECTIVO', 'PM2_500');
      return a.concat([m.clasificacion, m.informe.servicio]);
    }""")
    assert r[0] == {"tipo": "PREVENTIVO", "pm": "PM2_500"}
    assert r[1] == {"2.1": False, "2.2": True, "2.3": False, "2.4": False}
    assert r[2] == {"tipo": "CORRECTIVO", "pm": ""}, "el correctivo no lleva rutina"
    assert r[3]["2.4"] is True and r[3]["2.2"] is False


# --------------------------------------------------------------------------
# validarMantenimiento y validarOT
# --------------------------------------------------------------------------

VALIDAR = "([m, ctx]) => MANT.validaciones.validarMantenimiento(m, ctx)"


def _m(js, tag="064", tipo="PREVENTIVO", pm="PM1_250", **cambios):
    m = js("([t, ti, p]) => MANT.modelo.clasificar(MANT.modelo.mantenimiento(t), ti, p)",
           [tag, tipo, pm])
    m["placaConfirmada"] = {"fecha": "hoy", "tecnico": "T"}
    m["equipo"] = dict(js("e => MANT.modelo.normalizar.equipo(e)", EQUIPOS[tag]))
    m["ot"]["ot"] = "4017300492"
    # Una orden en regla lleva su IPERC continuo con las medidas confirmadas.
    filas = js("() => MANT.modelo.filasIperc('area')")
    for f in filas:
        f.update(aplicadas=True, hora="hoy")
    m["iperc"] = {"actividades": ["area"], "filas": filas, "fecha": "hoy"}
    for k, v in cambios.items():
        m[k] = v
    return m


def _campos(alertas, *niveles):
    return [(a["nivel"], a["campo"]) for a in alertas if not niveles or a["nivel"] in niveles]


def test_rutina_que_no_corresponde_al_horometro_avisa(js):
    m = _m(js, pm="PM3_1000")
    m["ot"]["horometroSalida"] = 6240
    a = js(VALIDAR, [m, {}])
    assert ("aviso", "clasificacion.pm") in _campos(a)
    m["clasificacion"]["pm"] = "PM1_250"
    assert ("aviso", "clasificacion.pm") not in _campos(js(VALIDAR, [m, {}]))


def test_la_orden_que_nombra_otro_tag_es_critica(js):
    m = _m(js)
    m["ot"]["descripcion"] = "INSP. RUTINARIA T9_SALVEANI_AAQ29"
    a = js(VALIDAR, [m, {}])
    assert ("critico", "ot.descripcion") in _campos(a)
    assert "un informe = un TAG" in [x for x in a if x["campo"] == "ot.descripcion"][0]["mensaje"]
    m["ot"]["descripcion"] = DESC_064
    assert ("critico", "ot.descripcion") not in _campos(js(VALIDAR, [m, {}]))
    m["ot"]["descripcion"] = "Limpieza de radiador"          # sin guion bajo: no se adivina
    assert ("critico", "ot.descripcion") not in _campos(js(VALIDAR, [m, {}]))


def test_la_misma_ot_en_dos_proyectos(js):
    m = _m(js)
    m["ot"]["ot"] = "4017300492"
    otro = {"id": "p2", "vista": "mantenimiento", "estado": "borrador", "nombre": "Otra",
            "datos": {"tag": "064", "ot": {"ot": "4017300492"}}}
    a = js(VALIDAR, [m, {"id": "p1", "otros": [otro]}])
    assert ("aviso", "ot.ot") in _campos(a)
    otro["datos"]["tag"] = "AAQ29"
    assert ("critico", "ot.ot") in _campos(js(VALIDAR, [m, {"id": "p1", "otros": [otro]}]))
    otro["estado"] = "anulado"
    assert _campos(js(VALIDAR, [m, {"id": "p1", "otros": [otro]}]), "aviso", "critico") == []


def test_placa_sin_confirmar_y_ficha_cambiada(js):
    m = _m(js)
    m["placaConfirmada"] = None
    ficha = EQUIPOS["064"]
    assert ("aviso", "placaConfirmada") in _campos(js(VALIDAR, [m, {"ficha": ficha}]))
    m = _m(js)
    cambiada = dict(ficha, motor=dict(ficha["motor"], serie="99999999"))
    a = js(VALIDAR, [m, {"ficha": cambiada}])
    assert ("aviso", "placaConfirmada") in _campos(a)
    assert _campos(js(VALIDAR, [m, {"ficha": ficha}]), "aviso", "critico") == []


def test_correctivo_apto_necesita_accion_y_pruebas(js):
    m = _m(js, tipo="CORRECTIVO", pm="")
    m["informe"]["operativo"] = True
    a = _campos(js(VALIDAR, [m, {}]), "aviso")
    assert ("aviso", "correctivo.falla") in a
    assert ("aviso", "correctivo.accion") in a
    assert ("aviso", "informe.operativo") in a
    m["correctivo"] = {"falla": "No arranca", "causa": "Relé de arranque", "accion": "Cambio de relé",
                       "pruebas": "Arranque y 30 min en vacío"}
    m["aptitud"] = {"por": "Supervisor", "fecha": "hoy"}
    # Sólo queda el dato de las fotos obligatorias, que es otro asunto.
    assert [x for x in js(VALIDAR, [m, {}]) if x["campo"] != "fotos"] == []


def test_no_apto_y_tarea_completa_pide_aviso(js):
    m = _m(js, tipo="INSPECCION", pm="")
    m["informe"]["operativo"] = False
    m["aptitud"]["por"] = "T"
    m["ot"]["tareaCompleta"] = True
    m["ot"]["firmas"]["tecnico"]["nombre"] = "T"
    assert ("aviso", "ot.crearAviso") in _campos(js(VALIDAR, [m, {}]))


@pytest.mark.parametrize("op,nivel", [
    ({"inicio": "2026-11-20T07:00", "fin": "2026-11-20T09:00", "horasHombre": 2, "personas": 1}, None),
    ({"inicio": "2026-11-20T07:00", "fin": "2026-11-20T09:00", "horasHombre": 4, "personas": 2}, None),
    ({"inicio": "2026-11-20T07:00", "fin": "2026-11-20T09:00", "horasHombre": 2, "personas": 2}, "info"),
    ({"inicio": "2026-11-20T09:00", "fin": "2026-11-20T07:00", "horasHombre": 2, "personas": 1}, "critico"),
    ({"inicio": "2026-11-20T07:00", "fin": "", "horasHombre": None, "personas": 1}, None),
])
def test_horas_hombre(js, op, nivel):
    ot = js("() => MANT.modelo.ordenTrabajo()")
    ot["ot"] = "1"
    ot["operaciones"][0].update(op)
    a = [x for x in js("o => MANT.validaciones.validarOT(o, null)", ot)
         if x["campo"].startswith("ot.operaciones.0")]
    assert [x["nivel"] for x in a] == ([nivel] if nivel else [])


def test_crear_aviso_sin_texto_y_horometro_que_retrocede(js):
    ot = js("() => MANT.modelo.ordenTrabajo()")
    ot.update(ot="1", crearAviso=True, horometroSalida=6200)
    a = _campos(js("o => MANT.validaciones.validarOT(o, 6240)", ot))
    assert ("aviso", "ot.textoAviso") in a
    assert ("critico", "ot.horometroSalida") in a


# --------------------------------------------------------------------------
# la pantalla
# --------------------------------------------------------------------------

def _pagina(pw, servidor, movil=True):
    nav = _lanzar(pw)
    ctx = _contexto(nav, movil=movil)
    pg = ctx.new_page()
    pg.on("dialog", lambda d: d.accept("Registrada dos veces") if d.type == "prompt" else d.accept())
    _abrir(pg, servidor)
    return nav, ctx, pg


def _guardado(pg):
    pg.wait_for_function(
        "() => /guardado/.test(document.querySelector('#m-o-guardado').textContent)")


def _f(pg, ruta, valor):
    pg.fill("#m-o-" + ruta.replace(".", "-"), str(valor))


def _crear(pg, tag, tipo, numero, pm=None):
    pg.click("#tab-mantenimiento")
    pg.click("#m-seg-ordenes")
    pg.fill("#m-ot-tag", tag)
    pg.dispatch_event("#m-ot-tag", "change")
    pg.check(f"input[name=m-ot-tipo][value={tipo}]")
    if pm:
        pg.check(f"input[name=m-ot-pm][value={pm}]")
    pg.fill("#m-ot-numero", numero)
    pg.click("#m-ot-nueva button[type=submit]")
    pg.wait_for_selector("#m-orden:not([hidden])")


def test_ot_completa_del_064_en_modo_avion_sobrevive_a_cerrar_la_app(pw, servidor):
    nav, ctx, pg = _pagina(pw, servidor)
    app = App(pg)
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", dict(EQUIPOS["064"], horometro=6240))
    ctx.set_offline(True)                                   # modo avión

    _crear(pg, "064", "PREVENTIVO", "4017300492")
    assert pg.is_checked("input[name=m-o-pm][value=PM1_250]"), "la rutina sugerida queda marcada"
    assert "PREVENTIVO · PM1" in pg.inner_text("#m-o-clase")

    pg.fill("#m-o-confirma", "Técnico eléctrico")
    pg.click("[data-accion=confirmar]")
    assert "Placa confirmada por Técnico eléctrico" in pg.inner_text("#m-o-cuerpo")

    # Lo que exige el aviso antes de tocar el equipo.
    for ruta in ["seguridad.items.bloqueo", "seguridad.items.iperc", "seguridad.items.hira",
                 "seguridad.items.bateria", "seguridad.herramientas.mecanica",
                 "seguridad.herramientas.dielectrica"]:
        pg.click(f"[data-estado='{ruta}'][data-valor=OK]")
    for ruta, valor in [("ot.descripcion", DESC_064), ("ot.aviso", "17360944"),
                        ("ot.ubicacionTecnica", "40020102.30.10.01"),
                        ("ot.puestoTrabajo", "QI3SS-MANTENIMIENTO EQUIPOS SOPORTE"),
                        ("ot.operaciones.0.descripcion", "LIMPIEZA RAD T9_PLATAFORMA_064"),
                        ("ot.operaciones.0.inicio", "2026-11-20T07:00"),
                        ("ot.operaciones.0.fin", "2026-11-20T09:00"),
                        ("ot.operaciones.0.horasHombre", "2"), ("ot.operaciones.0.empleado", "1001"),
                        ("ot.operaciones.1.inicio", "2026-11-20T07:00"),
                        ("ot.operaciones.1.fin", "2026-11-20T09:00"),
                        ("ot.operaciones.1.horasHombre", "2"), ("ot.operaciones.1.empleado", "1002"),
                        ("ot.observaciones", "Inspección y limpieza de radiador; arranque en vacío OK."),
                        ("ot.defectoReco", "Sin defecto detectado"),
                        ("ot.horometroSalida", "6.241,5"),
                        ("ot.textoAviso", "064: tapa de combustible sin seguro"),
                        ("aptitud.por", "Supervisor de turno"),
                        ("ot.firmas.tecnico.nombre", "Técnico eléctrico"),
                        ("ot.firmas.supervisor.nombre", "Supervisor de turno")]:
        _f(pg, ruta, valor)
    pg.click("[data-accion=agregar-demora]")
    pg.select_option("#m-o-ot-demoras-0-tipo", "Demora: Traslado y sin transp.")
    _f(pg, "ot.demoras.0.duracion", "0,5")
    pg.click("[data-sn='ot.crearAviso'][data-valor=true]")
    pg.click("[data-sn='informe.operativo'][data-valor=true]")
    pg.click("[data-sn='ot.tareaCompleta'][data-valor=true]")
    pg.click("[data-estado='seguridad.items.desbloqueo'][data-valor=OK]")
    # IPERC continuo: la desenergización, con sus medidas confirmadas.
    pg.click("[data-iperc-act=desenergizar]")
    pg.click("[data-iperc-ok='0']")
    _guardado(pg)
    pg.wait_for_timeout(900)
    _guardado(pg)

    serias = [a for a in pg.evaluate("() => MANT.ordenes.alertas()") if a["nivel"] != "info"]
    assert serias == [], serias

    pid = pg.evaluate("() => CAMPO.proyectos.actual().id")
    pg.close()                                              # se cierra la app
    pg = ctx.new_page()
    _abrir(pg, servidor)                                    # sin red: la sirve la caché
    pg.wait_for_selector("#proy-recuperado", timeout=8000)
    assert pg.evaluate("() => CAMPO.proyectos.actual().id") == pid
    assert pg.is_visible("#m-orden")
    assert pg.input_value("#m-o-ot-ot") == "4017300492"
    assert pg.input_value("#m-o-ot-descripcion") == DESC_064
    assert pg.input_value("#m-o-ot-operaciones-1-empleado") == "1002"
    assert pg.input_value("#m-o-ot-horometroSalida") == "6241.5"
    assert pg.input_value("#m-o-ot-demoras-0-tipo") == "Demora: Traslado y sin transp."
    for sn in ["ot.crearAviso", "informe.operativo", "ot.tareaCompleta"]:
        assert pg.get_attribute(f"[data-sn='{sn}'][data-valor=true]", "aria-pressed") == "true", sn
    assert "Placa confirmada" in pg.inner_text("#m-o-cuerpo")
    assert pg.get_attribute("[data-estado='seguridad.items.bloqueo'][data-valor=OK]", "aria-pressed") == "true"
    guardado = pg.evaluate("id => CAMPO.almacen.leer(id)", pid)
    assert guardado["datos"]["seguridad"]["horas"]["bloqueo"], "la marca guarda su hora"
    assert guardado["datos"]["equipo"]["grupo"]["serie"] == "D19I420882"
    assert guardado["datos"]["informe"]["servicio"]["2.2"] is True
    assert app.errores == []
    nav.close()


def test_correctivo_registra_aptitud_y_la_revision_de_avisos(pw, servidor):
    nav, ctx, pg = _pagina(pw, servidor)
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["C450D6"])
    _crear(pg, "C450D6", "CORRECTIVO", "4017300500")
    assert pg.is_visible("#m-o-correctivo-falla")
    _f(pg, "ot.firmas.tecnico.nombre", "Técnico mecánico")
    pg.click("[data-sn='informe.operativo'][data-valor=true]")
    texto = pg.inner_text("#m-o-alertas")
    assert "Se declara apto sin pruebas registradas" in texto
    assert "Correctivo sin la falla reportada" in texto

    pg.click("#m-o-alertas [data-revisar*='informe.operativo']")
    _guardado(pg)
    pg.wait_for_timeout(900)
    datos = pg.evaluate("() => CAMPO.almacen.leer(CAMPO.proyectos.actual().id).then(p => p.datos)")
    d = [x for x in datos["decisiones"] if x["campo"] == "informe.operativo"]
    assert d and d[0]["por"] == "Técnico mecánico"
    assert datos["informe"]["operativo"] is True and datos["aptitud"]["fecha"]
    assert "revisado" in pg.inner_text("#m-o-alertas")
    nav.close()


def test_una_ot_repetida_ofrece_abrir_la_existente(pw, servidor):
    nav, ctx, pg = _pagina(pw, servidor)
    _crear(pg, "064", "INSPECCION", "4017300492")
    primero = pg.evaluate("() => CAMPO.proyectos.actual().id")
    pg.click("#m-o-volver")
    _crear(pg, "064", "INSPECCION", "4017300492")           # confirm → abre la que hay
    assert pg.evaluate("() => CAMPO.proyectos.actual().id") == primero
    n = pg.evaluate("() => CAMPO.proyectos.listar().then(l => l.filter(p => p.vista === 'mantenimiento').length)")
    assert n == 1, "sin duplicidades"
    nav.close()


def test_pasar_por_despacho_no_duplica_la_orden(pw, servidor):
    nav, ctx, pg = _pagina(pw, servidor)
    _crear(pg, "064", "INSPECCION", "4017300600")
    _guardado(pg)
    App(pg).despacho()
    pg.click("#d-datos summary")
    pg.fill("#d-cliente", "OTRO CLIENTE")
    pg.evaluate("() => CAMPO.proyectos.volcar()")
    pg.click("#tab-mantenimiento")
    _f(pg, "ot.observaciones", "seguimos")
    pg.wait_for_timeout(1200)
    l = pg.evaluate("() => CAMPO.proyectos.listar().then(l => l.map(p => [p.vista, p.datos.ot ? p.datos.ot.observaciones : null]))")
    mant = [x for x in l if x[0] == "mantenimiento"]
    assert mant == [["mantenimiento", "seguimos"]], l
    assert [x[0] for x in l].count("despacho") == 1
    nav.close()


def test_anular_una_orden_desde_su_lista(pw, servidor):
    nav, ctx, pg = _pagina(pw, servidor)
    _crear(pg, "064", "VISITA", "4017300700")
    _guardado(pg)
    pid = pg.evaluate("() => CAMPO.proyectos.actual().id")
    pg.click("#m-o-volver")
    pg.wait_for_selector(f"#m-ot-lista [data-anular='{pid}']")
    pg.click(f"#m-ot-lista [data-anular='{pid}']")
    pg.wait_for_selector(f"#m-ot-lista .anulada[data-id='{pid}']")
    assert "Registrada dos veces" in pg.inner_text("#m-ot-lista")
    assert pg.evaluate("id => CAMPO.almacen.leer(id).then(p => p.estado)", pid) == "anulado"
    nav.close()


def test_la_orden_se_toca_con_guantes(pw, servidor):
    nav, ctx, pg = _pagina(pw, servidor)
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["064"])
    _crear(pg, "064", "CORRECTIVO", "4017300800")
    pg.click("[data-accion=agregar-demora]")
    chicos = pg.evaluate("""() => Array.from(document.querySelectorAll(
        '#m-orden button, #m-orden input:not([type=radio]):not([type=file]), #m-orden select, #m-orden textarea, #m-orden .m-opciones label, #m-orden label.boton'))
      .filter(n => n.offsetParent !== null)
      .map(n => [n.id || n.textContent.trim().slice(0, 30), n.getBoundingClientRect().height])
      .filter(x => x[1] < 47.5)""")
    assert chicos == []
    nav.close()


# --------------------------------------------------------------------------
# seguridad antes de iniciar (lo que exige el aviso)
# --------------------------------------------------------------------------

def _con_inicio(js, **items):
    m = _m(js, tipo="INSPECCION", pm="")
    m["ot"]["operaciones"][0]["inicio"] = "2026-11-20T07:00"
    m["seguridad"]["items"].update(items)
    return m


def test_trabajo_iniciado_sin_bloqueo_es_critico(js):
    a = _campos(js(VALIDAR, [_con_inicio(js), {}]))
    assert ("critico", "seguridad.items.bloqueo") in a
    assert ("aviso", "seguridad.items.iperc") in a
    assert ("aviso", "seguridad.items.hira") in a
    assert ("aviso", "seguridad.herramientas.dielectrica") in a, "la 0010 es eléctrica"


def test_con_bloqueo_iperc_hira_y_dielectrica_no_hay_avisos_de_seguridad(js):
    m = _con_inicio(js, bloqueo="OK", iperc="OK", hira="OK")
    m["seguridad"]["herramientas"]["dielectrica"] = "OK"
    assert [x for x in _campos(js(VALIDAR, [m, {}])) if x[1].startswith("seguridad")] == []


def test_sin_iniciar_no_se_exige_nada_todavia(js):
    m = _m(js, tipo="INSPECCION", pm="")
    assert [x for x in _campos(js(VALIDAR, [m, {}])) if x[1].startswith("seguridad")] == []


def test_tarea_completa_sin_desbloqueo_y_calibracion_vencida(js):
    m = _con_inicio(js, bloqueo="OK", iperc="OK", hira="OK")
    m["seguridad"]["herramientas"]["dielectrica"] = "OK"
    m["ot"]["tareaCompleta"] = True
    m["seguridad"]["instrumentos"][2].update(serie="MM-123", calibracion="2020-01-31", estado="OK")
    a = _campos(js(VALIDAR, [m, {}]))
    assert ("aviso", "seguridad.items.desbloqueo") in a
    assert ("aviso", "seguridad.instrumentos.2.calibracion") in a
    m["seguridad"]["instrumentos"][2]["calibracion"] = "2099-12-31"
    m["seguridad"]["items"]["desbloqueo"] = "OK"
    assert [x for x in _campos(js(VALIDAR, [m, {}])) if x[1].startswith("seguridad")] == []


def test_los_instrumentos_del_aviso_vienen_en_la_lista(js):
    r = js("() => MANT.modelo.mantenimiento('064').seguridad.instrumentos.map(i => i.nombre)")
    assert r == ["Pirómetro", "Pinza amperimétrica", "Multímetro", "Revelador de tensión"]


# --------------------------------------------------------------------------
# parámetros de operación y prueba (sección 6) · validarPrueba
# --------------------------------------------------------------------------

PRUEBA = "([eq, p]) => MANT.validaciones.validarPrueba(eq, p)"


def test_441_v_sobre_380_es_critico(js):
    a = js(PRUEBA, [EQUIPOS["064"], {"carga": 50, "voltajeLL": 441}])
    assert [(x["nivel"], x["campo"]) for x in a] == [("critico", "voltajeLL")]
    assert "16,1 %" in a[0]["mensaje"]


def test_384_y_222_no_alertan(js):
    assert js(PRUEBA, [EQUIPOS["064"], {"carga": 50, "voltajeLL": 384, "voltajeLN": 222}]) == []


@pytest.mark.parametrize("vll,nivel", [(390, "aviso"), (370, "aviso"), (389, None), (420, "critico")])
def test_tolerancia_de_voltaje(js, vll, nivel):
    a = [x["nivel"] for x in js(PRUEBA, [EQUIPOS["064"], {"carga": 25, "voltajeLL": vll}])]
    assert a == ([nivel] if nivel else [])


def test_otros_parametros_del_panel(js):
    p = {"carga": 100, "voltajeLL": 380, "voltajeLN": 200, "hz": 61, "presionAceitePsi": 15,
         "tempRefrigeranteC": 104, "vBateria": 12.0}
    c = {(x["nivel"], x["campo"]) for x in js(PRUEBA, [EQUIPOS["064"], p])}
    assert c == {("aviso", "voltajeLN"), ("aviso", "hz"), ("critico", "presionAceitePsi"),
                 ("critico", "tempRefrigeranteC"), ("aviso", "vBateria")}


def test_sin_placa_confirmada_no_compara(js):
    a = js(PRUEBA, [{}, {"carga": 0, "voltajeLL": 441}])
    assert [x["nivel"] for x in a] == ["info"]


def test_la_tabla_en_la_orden_avisa_el_441(pw, servidor):
    nav, ctx, pg = _pagina(pw, servidor)
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["C450D6"])
    _crear(pg, "C450D6", "INSPECCION", "4017302000")
    pg.click("[data-accion=confirmar]")
    pg.evaluate("() => document.querySelectorAll('.m-columna').forEach(d => d.open = true)")
    _f(pg, "informe.generalidades.voltaje", "441")
    _f(pg, "informe.pruebas.1.voltajeLL", "441")
    _f(pg, "informe.pruebas.1.hz", "60")
    texto = pg.inner_text("#m-o-alertas")
    assert "Voltaje 441 V (vacío) fuera de ±10 % de 380 V" in texto
    assert "Generalidades: voltaje 441 V y la placa dice 380 V" in texto
    assert pg.get_attribute("#m-o-informe-pruebas-1-voltajeLL", "aria-invalid") == "true"
    nav.close()
