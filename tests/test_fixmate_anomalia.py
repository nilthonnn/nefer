"""La anomalía TPM y el puente automático hacia el modo de falla RCM.

La prueba que vale por todas es la de **no enlazar**. El encargo pide que la
conexión TPM → RCM sea automática «cuando exista suficiente información», y
lo que define el diseño es la última mitad de esa frase: cuando no alcanza,
la anomalía queda sin enlazar y se ve.

Una anomalía enlazada al modo equivocado contamina el MTBF por modo, la
frecuencia histórica del análisis y la decisión de estrategia que sale de
ahí. Un enlace que falta se ve; uno equivocado se suma con los demás.
"""

from __future__ import annotations

import datetime as dt

import pytest

from nefer.fixmate.activos import Activo
from nefer.fixmate.anomalia import (Anomalia, ErrorAnomalia, clasificar,
                                    desde_ejecucion, desde_item, enlazar, salud)
from nefer.fixmate.rcm import Analisis
from nefer.fixmate.tpm import Checklist, Ejecucion

HOY = dt.date(2026, 3, 2)
CODIGO_RADIADOR = "TER.SOBRECALENTAMIENTO.RADIADOR"


def _pauta() -> Checklist:
    c = Checklist("cl", "EX-220", "Ronda")
    c.agregar("limpiar", "Rejilla del radiador", "Sin costra", segundos=8)
    c.agregar("inspeccionar", "Guarda del acople", "Puesta y con sus pernos",
              alcance_operador=False, segundos=5)
    c.agregar("lubricar", "Grasera LA", "Dos golpes", segundos=8)
    return c


def _analisis() -> Analisis:
    a = Analisis(Activo("EX-220", "Excavadora"))
    f = a.agregar_funcion("Refrigerar", "80-95 °C con carga continua")
    ff = a.agregar_falla(f.id, "Sobrecalienta")
    a.agregar_modo(ff.id, "Radiador obstruido", codigo_catalogo=CODIGO_RADIADOR)
    return a


def _ronda(c, resultados) -> Ejecucion:
    e = Ejecucion("ej-1", c.id, "EX-220", "J. Quispe", fecha=HOY.isoformat())
    for p, (r, obs) in zip(c.puntos, resultados):
        e.registrar(p.id, r, obs, segundos=p.segundos)
    return e


# ------------------------------------------- qué genera anomalía y qué no

def test_solo_el_nok_genera_anomalia():
    c = _pauta()
    e = _ronda(c, [("nok", "Radiador obstruido por tierra"), ("ok", ""),
                   ("ok", "")])
    assert len(desde_ejecucion(e, c, hoy=HOY)) == 1


def test_un_sin_acceso_no_genera_anomalia():
    # No se encontró un defecto: se encontró que no se pudo mirar. Eso sale
    # por el cumplimiento, no por una anomalía colgada de un punto que nadie
    # vio.
    c = _pauta()
    e = _ronda(c, [("sin_acceso", "Guarda soldada"), ("ok", ""), ("ok", "")])
    assert desde_ejecucion(e, c, hoy=HOY) == []


def test_la_anomalia_se_cuelga_de_la_ejecucion_que_la_vio():
    c = _pauta()
    e = _ronda(c, [("nok", "Panal tapado"), ("ok", ""), ("ok", "")])
    a = desde_ejecucion(e, c, hoy=HOY)[0]
    assert a.ejecucion_id == e.id
    assert a.punto_id == c.puntos[0].id
    assert a.detectada_por == "J. Quispe"
    assert e.anomalias == [a.id]


def test_el_texto_del_operador_no_se_normaliza():
    c = _pauta()
    e = _ronda(c, [("nok", "Suena a metal cada vuelta, raro"), ("ok", ""),
                   ("ok", "")])
    assert desde_ejecucion(e, c, hoy=HOY)[0].descripcion == \
        "Suena a metal cada vuelta, raro"


def test_sin_observacion_se_usa_el_nombre_del_punto_y_no_se_inventa_texto():
    c = _pauta()
    e = _ronda(c, [("nok", ""), ("ok", ""), ("ok", "")])
    assert desde_ejecucion(e, c, hoy=HOY)[0].descripcion == "Rejilla del radiador"


def test_el_alcance_declarado_en_la_pauta_decide_la_severidad():
    # Se decidió en frío al escribir la pauta, no en campo con la máquina
    # parada y el supervisor mirando.
    c = _pauta()
    e = _ronda(c, [("nok", "Panal tapado"), ("nok", "Guarda suelta"), ("ok", "")])
    anomalias = desde_ejecucion(e, c, hoy=HOY)
    assert anomalias[0].severidad == "programable"   # alcance del operador
    assert anomalias[1].severidad == "detiene"       # fuera de su alcance


# ══════════════ el puente TPM → RCM, y cuándo NO se cruza ══════════════

def test_el_texto_libre_llega_hasta_el_modo_de_falla_rcm():
    c = _pauta()
    e = _ronda(c, [("nok", "Radiador obstruido por tierra y polvo"), ("ok", ""),
                   ("ok", "")])
    a = desde_ejecucion(e, c, _analisis(), hoy=HOY)[0]
    assert a.codigo_catalogo == CODIGO_RADIADOR
    assert a.modo_falla_id == "F1.1.1"
    assert a.enlazada is True


def test_si_el_catalogo_no_alcanza_la_anomalia_queda_sin_codigo():
    # El catálogo no adivina —no tiene «Otro» y en empate no elige—, y aquí
    # se hereda ese criterio en vez de rebajarlo.
    c = _pauta()
    e = _ronda(c, [("nok", "Algo raro"), ("ok", ""), ("ok", "")])
    a = desde_ejecucion(e, c, _analisis(), hoy=HOY)[0]
    assert a.codigo_catalogo == ""
    assert a.enlazada is False


def test_con_codigo_pero_sin_modo_que_lo_declare_no_se_enlaza_al_mas_parecido():
    # Hay un análisis RCM, pero ninguno de sus modos declara este código.
    # Elegir «el más parecido» contaminaría el MTBF por modo.
    a = Anomalia("x", "EX-220", "Filtro de aire colmatado")
    clasificar(a)
    assert a.codigo_catalogo == "ADM.RESTRICCION.FILTRO"
    enlazar(a, _analisis())      # el análisis sólo tiene el del radiador
    assert a.enlazada is False


def test_no_se_enlaza_con_el_analisis_de_otro_activo():
    a = Anomalia("x", "CA-310", "Radiador obstruido por tierra")
    clasificar(a)
    assert a.codigo_catalogo == CODIGO_RADIADOR
    enlazar(a, _analisis())      # el análisis es de EX-220
    assert a.enlazada is False


def test_con_dos_modos_que_declaran_el_mismo_codigo_no_se_elige_a_la_suerte():
    # La ambigüedad se resuelve en el análisis, no aquí.
    an = _analisis()
    an.agregar_modo("F1.1", "Radiador obstruido, otra vez",
                    codigo_catalogo=CODIGO_RADIADOR)
    a = Anomalia("x", "EX-220", "Radiador obstruido por tierra")
    clasificar(a)
    enlazar(a, an)
    assert a.enlazada is False


def test_el_codigo_declarado_en_la_pauta_gana_sobre_el_clasificador():
    # Si quien escribió la pauta ya dijo qué modo vigila ese punto, eso es
    # mejor dato que adivinarlo del texto del operador.
    c = Checklist("cl", "EX-220", "Ronda")
    c.agregar("limpiar", "Rejilla", "Sin costra", segundos=8,
              codigo_catalogo=CODIGO_RADIADOR)
    e = Ejecucion("e", c.id, "EX-220", "J. Q.", fecha=HOY.isoformat())
    e.registrar(c.puntos[0].id, "nok", "Algo raro", 9)
    a = desde_ejecucion(e, c, _analisis(), hoy=HOY)[0]
    assert a.codigo_catalogo == CODIGO_RADIADOR
    assert a.enlazada is True


def test_enlazar_sin_analisis_no_rompe_nada():
    a = Anomalia("x", "EX-220", "Radiador obstruido por tierra")
    clasificar(a)
    assert enlazar(a, None).enlazada is False


# ------------------------------------------------- ciclo de vida y cierre

def test_no_se_cierra_una_anomalia_sin_decir_que_se_hizo():
    a = Anomalia("x", "EX-220", "Panal tapado")
    with pytest.raises(ErrorAnomalia, match="sin decir que se hizo"):
        a.cerrar("   ")


def test_cerrar_anota_accion_responsable_y_fecha():
    a = Anomalia("x", "EX-220", "Panal tapado", fecha="2026-03-01")
    a.cerrar("Lavado del panal con agua a presión", "R. Mamani",
             hoy=dt.date(2026, 3, 4))
    assert a.estado == "cerrada" and a.abierta is False
    assert a.dias_abierta() == 3


def test_una_anomalia_abierta_cuenta_dias_hasta_hoy():
    a = Anomalia("x", "EX-220", "Panal tapado", fecha="2026-03-01")
    assert a.dias_abierta(dt.date(2026, 3, 10)) == 9


def test_una_severidad_inventada_se_rechaza():
    with pytest.raises(ErrorAnomalia, match="severidad"):
        Anomalia("x", "EX-220", "y", severidad="urgentisima")


def test_una_anomalia_sin_descripcion_se_rechaza():
    with pytest.raises(ErrorAnomalia, match="descripcion"):
        Anomalia("x", "EX-220", "  ")


# ----------------------------------------------------------- indicadores

def test_la_salud_mide_cerradas_y_no_abiertas():
    # Contar las abiertas mide entusiasmo del primer mes.
    abierta = Anomalia("a1", "EX-220", "Panal tapado", fecha="2026-03-01")
    cerrada = Anomalia("a2", "EX-220", "Fuga en manguera", fecha="2026-03-01")
    cerrada.cerrar("Cambio de manguera", hoy=dt.date(2026, 3, 5))
    s = salud([abierta, cerrada], hoy=dt.date(2026, 3, 10))
    assert s.total == 2 and s.abiertas == 1 and s.cerradas == 1
    assert s.dias_medios_de_cierre == 4


def test_sin_cierres_los_dias_medios_son_none():
    s = salud([Anomalia("a1", "EX-220", "x")], hoy=HOY)
    assert s.dias_medios_de_cierre is None


def test_la_salud_cuenta_las_que_no_llegaron_a_rcm():
    # Es la medida honesta de cuánto cubre el enganche automático.
    con = Anomalia("a1", "EX-220", "x", modo_falla_id="F1.1.1")
    sin = Anomalia("a2", "EX-220", "y")
    assert salud([con, sin], hoy=HOY).sin_enlazar == 1


def test_la_reincidencia_sale_por_codigo_cuando_lo_hay():
    # Repetir el mismo código es la señal de que se cerró el síntoma y no la
    # causa.
    uno = Anomalia("a1", "EX-220", "x", codigo_catalogo=CODIGO_RADIADOR)
    dos = Anomalia("a2", "EX-220", "y", codigo_catalogo=CODIGO_RADIADOR)
    otro = Anomalia("a3", "EX-220", "z", codigo_catalogo="ADM.RESTRICCION.FILTRO")
    assert salud([uno, dos, otro], hoy=HOY).reincidentes == ((CODIGO_RADIADOR, 2),)


def test_una_fecha_ilegible_ya_no_borra_la_anomalía_de_la_cuenta_de_atrasos():
    """Antes se aceptaba y `dias_abierta()` devolvía `None`.

    Una anomalía con fecha «15/03/2026» entraba al sistema, no daba error en
    ninguna parte, y desaparecía de la cuenta de días abiertos: justo la
    anomalía mal registrada era la que dejaba de pedir atención.
    """
    with pytest.raises(ErrorAnomalia, match="ISO 8601"):
        Anomalia(id="a1", activo_codigo="EX-220", descripcion="algo",
                 fecha="15/03/2026")
    with pytest.raises(ErrorAnomalia, match="ISO 8601"):
        Anomalia(id="a1", activo_codigo="EX-220", descripcion="algo",
                 fecha="2026-03-16", fecha_cierre="16/03/2026")

    buena = Anomalia(id="a1", activo_codigo="EX-220", descripcion="algo",
                     fecha="2026-03-16")
    assert buena.dias_abierta(hoy=dt.date(2026, 3, 20)) == 4
