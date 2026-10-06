"""Del dictamen RCM a la tarea ejecutable, y de vuelta a la pauta TPM.

Lo que se prueba aquí es sobre todo lo que el módulo **no rellena**. Una
tarea generada con intervalo, límite y herramienta inventados se ve
terminada y no lo está, y en campo eso se ejecuta: alguien lleva la llave
equivocada a 40 km de distancia.

De «hay una edad a la que la probabilidad sube» no sale un número: sale que
existe un número y que hay que medirlo.
"""

from __future__ import annotations

from nefer.fixmate.activos import Activo
from nefer.fixmate.decision import Decisiones, Dictamen, Respuestas
from nefer.fixmate.plan import (DISPARADORES, Tarea, aplicable, desde_dictamen,
                                falta_por_completar, generar, punto_tpm)
from nefer.fixmate.rcm import Analisis, Consecuencia

CODIGO_RADIADOR = "TER.SOBRECALENTAMIENTO.RADIADOR"


def _analisis() -> Analisis:
    a = Analisis(Activo("EX-220", "Excavadora"))
    f = a.agregar_funcion("Refrigerar", "80-95 °C con carga continua")
    ff = a.agregar_falla(f.id, "Sobrecalienta")
    a.agregar_modo(ff.id, "Radiador obstruido", codigo_catalogo=CODIGO_RADIADOR)
    a.agregar_modo(ff.id, "Rodamiento del ventilador gastado",
                   consecuencias=(Consecuencia("economica"),))
    a.agregar_modo(ff.id, "Manguera de freno fisurada",
                   consecuencias=(Consecuencia("seguridad"),))
    return a


def _decisiones(a: Analisis) -> Decisiones:
    d = Decisiones()
    d.registrar(a.modos[0], Respuestas(detectable=True, viable=True))
    d.registrar(a.modos[1], Respuestas(detectable=False, intervalo_edad=True,
                                       restaurable=False, viable=True))
    d.registrar(a.modos[2], Respuestas(detectable=False, intervalo_edad=False,
                                       costo_efectiva=False))
    return d


# ----------------------------------- el disparador lo fija la estrategia

def test_cada_estrategia_tiene_su_forma_de_dispararse():
    # Una tarea a condición con intervalo de calendario deja de ser a
    # condición: no son intercambiables.
    assert DISPARADORES["cbm"] == "condicion"
    assert DISPARADORES["restauracion"] == "intervalo"
    assert DISPARADORES["descarte"] == "intervalo"
    assert DISPARADORES["busqueda_fallas"] == "intervalo"
    assert DISPARADORES["rediseno"] == "proyecto"


def test_la_tarea_hereda_disparador_sistema_y_motivo_del_dictamen():
    a = _analisis()
    d = Dictamen("cbm", "La degradación se puede detectar con aviso suficiente")
    t = desde_dictamen(a.modos[0], d, "EX-220")
    assert t.disparador == "condicion"
    assert t.sistema == "termico"
    assert t.motivo.startswith("La degradación")
    assert t.modo_falla_id == a.modos[0].id


def test_operar_hasta_la_falla_no_genera_tarea():
    # La decisión fue NO programar nada. Una tarea vacía «para que figure»
    # devolvería al plan justo lo que el análisis sacó de él.
    d = Dictamen("operar_hasta_falla", "ninguna tarea se paga", por_defecto=True)
    assert desde_dictamen(_analisis().modos[1], d, "EX-220") is None


# ------------------------------------- lo que el módulo NO rellena

def test_una_tarea_por_intervalo_nace_sin_intervalo_y_lo_dice():
    # De «hay una edad a la que la probabilidad sube» no sale un número.
    a = _analisis()
    t = desde_dictamen(a.modos[1], Dictamen("descarte", "x" * 50), "EX-220")
    assert t.intervalo_dias is None and t.intervalo_horas is None
    assert any("cada cuanto" in f for f in falta_por_completar(t))
    assert aplicable(t) is False


def test_una_tarea_a_condicion_exige_parametro_limite_y_fuente_del_limite():
    a = _analisis()
    t = desde_dictamen(a.modos[0], Dictamen("cbm", "x" * 50), "EX-220")
    faltas = falta_por_completar(t)
    assert any("parametro" in f for f in faltas)
    assert any("OEM o de un estandar" in f for f in faltas)


def test_un_limite_sin_fuente_sigue_estando_incompleto():
    # El límite tiene que venir del OEM o de un estándar, nunca de aquí.
    t = Tarea("T1", "EX-220", "F1.1.1", "cbm", descripcion="Medir ΔT",
              disparador="condicion", parametro="ΔT sobre ambiente",
              limite="35 °C", procedimiento="Según manual")
    assert any("de donde sale el limite" in f for f in falta_por_completar(t))
    t.fuente_limite = "Manual OEM PC220-8, sección 4.3"
    assert aplicable(t) is True


def test_una_tarea_completa_se_declara_aplicable():
    t = Tarea("T1", "EX-220", "F1.1.2", "descarte",
              descripcion="Reemplazar el rodamiento del ventilador",
              disparador="intervalo", intervalo_horas=4000,
              procedimiento="Manual OEM PC220-8 §6.1")
    assert falta_por_completar(t) == ()
    assert aplicable(t) is True


def test_no_se_exigen_herramientas_ni_repuestos():
    # Hay tareas que no llevan ninguno; exigirlos haría que se rellenen con
    # cualquier cosa.
    t = Tarea("T1", "EX-220", "F1.1.1", "busqueda_fallas",
              descripcion="Probar la válvula de alivio", disparador="intervalo",
              intervalo_dias=90, procedimiento="Procedimiento del taller 12")
    assert aplicable(t) is True
    assert t.herramientas == () and t.repuestos == ()


def test_el_rediseno_no_pide_intervalo_ni_procedimiento():
    # Es un proyecto de ingeniería, no una tarea de calendario.
    t = desde_dictamen(_analisis().modos[2],
                       Dictamen("rediseno", "x" * 50, bloqueado_por_seguridad=True),
                       "EX-220")
    t.descripcion = "Reemplazar la manguera por una de mayor presión"
    assert t.disparador == "proyecto"
    assert aplicable(t) is True


# ----------------------------------------------------- el plan completo

def test_el_plan_sale_del_analisis_ya_decidido():
    a = _analisis()
    p = generar(a, _decisiones(a))
    # Tres tareas: el rediseño también lo es, de tipo proyecto. Lo único que
    # no genera tarea es «operar hasta la falla», y aquí no salió ninguno.
    assert len(p.tareas) == 3
    assert p.sin_tarea == []
    assert p.por_estrategia()["cbm"] == 1
    assert p.por_estrategia()["descarte"] == 1
    assert p.por_estrategia()["rediseno"] == 1


def test_un_modo_sin_decision_no_produce_una_tarea_en_blanco():
    # Lo denuncia la Q6 de rcm.completitud, no una tarea vacía en el plan.
    a = _analisis()
    d = Decisiones()
    d.registrar(a.modos[0], Respuestas(detectable=True, viable=True))
    assert len(generar(a, d).tareas) == 1


def test_el_plan_lista_lo_que_decidio_NO_hacer():
    # Un plan que esconde lo que decidió no hacer no se puede auditar.
    a = Analisis(Activo("EX-220", "Excavadora"))
    f = a.agregar_funcion("Refrigerar", "80-95 °C")
    ff = a.agregar_falla(f.id, "Sobrecalienta")
    m = a.agregar_modo(ff.id, "Pintura descascarada",
                       consecuencias=(Consecuencia("no-significativa"),))
    d = Decisiones()
    d.registrar(m, Respuestas(detectable=False, intervalo_edad=False,
                              costo_efectiva=False))
    p = generar(a, d)
    assert p.tareas == []
    assert p.sin_tarea == [m.id]
    assert p.por_estrategia()["operar_hasta_falla"] == 1


def test_el_plan_separa_lo_completo_de_lo_que_es_borrador():
    a = _analisis()
    p = generar(a, _decisiones(a))
    assert p.borradores and not p.completas
    t = p.tareas[0]
    t.descripcion = "Inspeccionar el panal a contraluz"
    t.parametro = "Obstrucción visible del panal"
    t.limite = "Sin zona opaca mayor al 20 %"
    t.fuente_limite = "Procedimiento del taller 08"
    t.procedimiento = "Manual OEM PC220-8 §4.3"
    assert len(p.completas) == 1


# --------------------------------- el camino de vuelta a la ronda TPM

def _tarea_cbm():
    a = _analisis()
    return a, desde_dictamen(a.modos[0], Dictamen("cbm", "x" * 50), "EX-220")


def test_solo_baja_a_la_ronda_lo_que_cumple_las_tres_condiciones():
    a, t = _tarea_cbm()
    # Sin declarar nada: no baja.
    assert punto_tpm(t, a.modos[0]) is None
    # Sensorial pero fuera del alcance declarado: no baja.
    assert punto_tpm(t, a.modos[0], "vista", alcance_operador=False) is None
    # Dentro del alcance pero con instrumento: no baja.
    assert punto_tpm(t, a.modos[0], "termografia", alcance_operador=True) is None
    # Las tres: baja.
    assert punto_tpm(t, a.modos[0], "vista", alcance_operador=True) is not None


def test_una_restauracion_no_baja_a_la_ronda_aunque_sea_sensorial():
    # Una restauración no es una ronda de treinta segundos.
    a = _analisis()
    t = desde_dictamen(a.modos[1], Dictamen("restauracion", "x" * 50), "EX-220")
    assert punto_tpm(t, a.modos[1], "vista", alcance_operador=True) is None


def test_una_busqueda_de_fallas_tampoco_baja():
    # Probar una protección no es mirarla.
    a = _analisis()
    t = desde_dictamen(a.modos[0], Dictamen("busqueda_fallas", "x" * 50),
                       "EX-220")
    assert punto_tpm(t, a.modos[0], "vista", alcance_operador=True) is None


def test_el_punto_que_baja_lleva_la_llave_hacia_rcm_y_el_criterio_vacio():
    # El análisis dice QUE hay que mirar; no dice qué significa que esté bien.
    a, t = _tarea_cbm()
    b = punto_tpm(t, a.modos[0], "oido", alcance_operador=True)
    assert b.modo_falla_id == a.modos[0].id
    assert b.codigo_catalogo == CODIGO_RADIADOR
    assert b.desde_tarea == t.id
    assert b.criterio == ""
    assert any("criterio observable" in f for f in b.falta)
    assert any("segundos" in f for f in b.falta)
