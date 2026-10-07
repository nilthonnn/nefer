"""Los indicadores. La regla que gobierna el archivo: `None` no es cero.

Un tablero que muestra 0 % de cumplimiento cuando todavía no hay ninguna
ronda está diciendo «lo hicieron mal» cuando lo que pasa es que no hay dato.
Esa es la forma más rápida de que un tablero deje de mirarse.
"""

from __future__ import annotations

import datetime as dt

from nefer.fixmate import embeddings, fmeca, ingesta, tablero
from nefer.fixmate.activos import Activo
from nefer.fixmate.anomalia import Anomalia
from nefer.fixmate.criticidad import PRIORIDAD_EJEMPLO
from nefer.fixmate.decision import Decisiones, Respuestas
from nefer.fixmate.indice import Indice
from nefer.fixmate.rcm import Analisis, Consecuencia, Efecto, Referencia
from nefer.fixmate.tpm import Checklist, Ejecucion

RADIADOR = "TER.SOBRECALENTAMIENTO.RADIADOR"
HOY = dt.date(2026, 3, 10)


def _analisis(codigo="EX-220") -> Analisis:
    a = Analisis(Activo(codigo, "Excavadora"))
    f = a.agregar_funcion("Refrigerar", "80-95 °C con carga continua")
    ff = a.agregar_falla(f.id, "Supera 95 °C")
    m = a.agregar_modo(ff.id, "Radiador obstruido", codigo_catalogo=RADIADOR,
                       estado="validado",
                       evidencia=(Referencia("historial", "OT-1"),))
    m.efecto = Efecto(local="Sube la temperatura")
    m.consecuencias = (Consecuencia("produccion"),)
    m.evaluar_criticidad(PRIORIDAD_EJEMPLO,
                         {"severidad": 3, "frecuencia": 3, "deteccion": 2})
    o = a.agregar_modo(ff.id, "Válvula de alivio pegada", evidente=False)
    o.efecto = Efecto(local="No alivia presión")
    o.consecuencias = (Consecuencia("seguridad"),)
    return a


def _decisiones(a) -> Decisiones:
    d = Decisiones()
    d.registrar(a.modos[0], Respuestas(detectable=True, viable=True))
    d.registrar(a.modos[1], Respuestas(probable=True))
    return d


def _pauta() -> Checklist:
    c = Checklist("cl", "EX-220", "Ronda")
    c.agregar("limpiar", "Rejilla", "Sin costra", segundos=8)
    c.agregar("lubricar", "Grasera LA", "Dos golpes", segundos=8)
    return c


def _ronda(c, resultados, eid="e1") -> Ejecucion:
    e = Ejecucion(eid, c.id, c.activo_codigo, "J. Q.", fecha="2026-03-02")
    for p, r in zip(c.puntos, resultados):
        e.registrar(p.id, r, segundos=p.segundos)
    return e


# ══════════════════ None no es cero ══════════════════

def test_sin_analisis_la_completitud_es_none():
    assert tablero.rcm([]).completitud is None


def test_sin_ejecuciones_el_cumplimiento_es_none():
    assert tablero.tpm([_pauta()], []).cumplimiento is None


def test_sin_cierres_los_dias_medios_son_none():
    t = tablero.tpm([], [], [Anomalia("a", "EX-220", "x")], hoy=HOY)
    assert t.dias_medios_de_cierre is None


def test_el_dict_conserva_el_none_en_vez_de_rellenarlo():
    # Quien pinte la pantalla tiene que poder distinguir las dos cosas.
    assert tablero.rcm([]).a_dict()["completitud"] is None
    assert tablero.tpm([], []).a_dict()["cumplimiento"] is None


# ══════════════════ el tablero RCM ══════════════════

def test_cuenta_la_cadena_entera_del_analisis():
    a = _analisis()
    t = tablero.rcm([a], {"EX-220": _decisiones(a)})
    assert t.activos_analizados == 1
    assert t.funciones == 1 and t.fallas_funcionales == 1 and t.modos == 2
    assert t.modos_graves == 1 and t.modos_ocultos == 1
    assert t.modos_validados == 1


def test_el_reparto_por_estrategia_sale_de_las_decisiones():
    a = _analisis()
    t = tablero.rcm([a], {"EX-220": _decisiones(a)})
    assert t.por_estrategia["cbm"] == 1
    assert t.por_estrategia["busqueda_fallas"] == 1
    assert t.por_estrategia["operar_hasta_falla"] == 0


def test_sin_decisiones_el_analisis_no_puede_estar_completo():
    # Faltan la Q6 y la Q7.
    assert tablero.rcm([_analisis()]).analisis_completos == 0


def test_con_decisiones_el_analisis_cuenta_como_completo():
    a = _analisis()
    t = tablero.rcm([a], {"EX-220": _decisiones(a)})
    assert t.analisis_completos == 1 and t.completitud == 1.0


def test_los_modos_sin_criticidad_se_cuentan():
    a = _analisis()
    t = tablero.rcm([a], {"EX-220": _decisiones(a)})
    assert t.modos_sin_criticidad == 1     # el oculto quedó sin evaluar


def test_un_modo_sin_contrastar_no_cuenta_como_no_recurrente():
    # `frecuencia_historica is None` dice «nadie contó», no «no ocurrió».
    a = _analisis()
    assert tablero.rcm([a]).modos_recurrentes == 0
    a.modos[0].frecuencia_historica = 3
    assert tablero.rcm([a]).modos_recurrentes == 1
    a.modos[0].frecuencia_historica = 1
    assert tablero.rcm([a]).modos_recurrentes == 0


def test_el_tablero_agrega_varios_activos():
    a1, a2 = _analisis("EX-220"), _analisis("EX-330")
    t = tablero.rcm([a1, a2], {"EX-220": _decisiones(a1)})
    assert t.activos_analizados == 2 and t.modos == 4
    assert t.analisis_completos == 1 and t.completitud == 0.5


# ══════════════════ el tablero TPM ══════════════════

def test_el_cumplimiento_cuenta_rondas_completas():
    c = _pauta()
    t = tablero.tpm([c], [_ronda(c, ["ok", "ok"]),
                          _ronda(c, ["ok", "sin_acceso"], "e2")])
    assert t.ejecuciones == 2 and t.ejecuciones_completas == 1
    assert t.cumplimiento == 0.5


def test_una_ejecucion_cuya_pauta_no_esta_cargada_no_cuenta_como_fallida():
    # Restarla del denominador es más honesto que darla por fallida.
    c = _pauta()
    huerfana = Ejecucion("e9", "otra-pauta", "EX-220", "J. Q.")
    t = tablero.tpm([c], [_ronda(c, ["ok", "ok"]), huerfana])
    assert t.ejecuciones == 2
    assert t.cumplimiento == 1.0


def test_el_desglose_por_clase_responde_si_se_esta_lubricando_de_verdad():
    c = _pauta()
    t = tablero.tpm([c], [_ronda(c, ["ok", "sin_acceso"])])
    assert t.por_clase["limpiar"] == 1
    assert t.por_clase["lubricar"] == 0
    assert t.por_clase["ajustar"] == 0


def test_las_anomalias_se_cuentan_por_estado_y_por_enlace():
    abierta = Anomalia("a1", "EX-220", "Panal tapado", fecha="2026-03-01",
                       modo_falla_id="F1.1.1")
    cerrada = Anomalia("a2", "EX-220", "Fuga", fecha="2026-03-01")
    cerrada.cerrar("Cambio de manguera", hoy=dt.date(2026, 3, 5))
    t = tablero.tpm([], [], [abierta, cerrada], hoy=HOY)
    assert t.anomalias == 2 and t.anomalias_abiertas == 1
    assert t.anomalias_cerradas == 1
    assert t.anomalias_sin_enlazar == 1
    assert t.dias_medios_de_cierre == 4


# ══════════════════ confiabilidad: de prediccion, sin recalcular ══════════

def _indice_con_fallas() -> Indice:
    informes = [
        {"codigo_ot": f"OT-{i}", "codigo_equipo": "EX-220",
         "fecha": f"2026-0{i}-01", "resumen_falla": "x",
         "causa_raiz": "Radiador obstruido por tierra",
         "solucion_aplicada": "Lavado"}
        for i in (1, 2, 3)
    ]
    i = Indice(embeddings.EmbebedorLocal())
    i.agregar(ingesta.de_historial({"informes": informes}, "h.json"))
    return i


def test_el_mtbf_sale_de_prediccion_y_no_de_otra_formula():
    # Dos fórmulas para la misma pregunta dan dos números distintos, que es
    # peor que no tener ninguno.
    from nefer.fixmate import prediccion
    idx = _indice_con_fallas()
    t = tablero.confiabilidad(idx, hoy=HOY)
    assert t.equipos == 1 and t.fallas == 3
    assert t.mtbf_dias["EX-220"] == prediccion.mtbf(
        prediccion.eventos(idx, "EX-220"))


def test_el_mttr_y_la_disponibilidad_quedan_en_none_porque_no_hay_dato():
    # FixMate registra cuándo ocurrió una falla, no cuánto duró la
    # reparación. Un MTTR inventado se usa para dimensionar un taller.
    t = tablero.confiabilidad(_indice_con_fallas(), hoy=HOY)
    assert t.mttr_horas is None
    assert t.disponibilidad is None


def test_un_equipo_con_una_sola_falla_no_aparece_en_el_mtbf():
    # Con una aparición no hay intervalo, hay una fecha.
    informe = {"codigo_ot": "OT-1", "codigo_equipo": "CA-310",
               "fecha": "2026-01-01", "resumen_falla": "x",
               "causa_raiz": "Bornes sulfatados", "solucion_aplicada": "y"}
    i = Indice(embeddings.EmbebedorLocal())
    i.agregar(ingesta.de_historial({"informes": [informe]}, "h.json"))
    t = tablero.confiabilidad(i, hoy=HOY)
    assert t.equipos == 1
    assert "CA-310" not in t.mtbf_dias


# ══════════════════ los tres juntos ══════════════════

def test_el_tablero_completo_trae_las_tres_secciones():
    a = _analisis()
    c = _pauta()
    d = tablero.completo([a], {"EX-220": _decisiones(a)}, [c],
                         [_ronda(c, ["ok", "ok"])], [], _indice_con_fallas(), HOY)
    assert set(d) == {"rcm", "tpm", "confiabilidad"}
    assert d["rcm"]["modos"] == 2
    assert d["tpm"]["cumplimiento"] == 1.0
    assert d["confiabilidad"]["fallas"] == 3


def test_sin_indice_la_seccion_de_confiabilidad_es_none_y_no_ceros():
    assert tablero.completo()["confiabilidad"] is None
