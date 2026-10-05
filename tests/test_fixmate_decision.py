"""La matriz de decisión: de modo de falla a estrategia, sin «preventivo» a secas.

La prueba central de este archivo es una sola y vale por todas las demás:

    con consecuencia de seguridad o ambiental, «operar hasta la falla» no
    puede salir NUNCA, en ninguna combinación de respuestas.

Se comprueba por fuerza bruta sobre las 3⁶ combinaciones posibles. Un árbol
de decisión que permita cerrar un modo de falla de seguridad con «operar
hasta la falla» es peor que no tener árbol, porque firma la omisión.
"""

from __future__ import annotations

import itertools

import pytest

from nefer.fixmate.decision import (ESTRATEGIAS, POR_DEFECTO, PROACTIVAS,
                                    Decisiones, Respuestas, decidir, resumen)
from nefer.fixmate.rcm import Analisis, Consecuencia, Efecto, ModoFalla
from nefer.fixmate.activos import Activo

TRI = (True, False, None)


def modo(clase="produccion", evidente=True, mid="m1") -> ModoFalla:
    return ModoFalla(mid, "F1.1", "Un modo de falla", evidente=evidente,
                     consecuencias=(Consecuencia(clase),))


def todas_las_respuestas():
    campos = ("detectable", "intervalo_edad", "restaurable", "viable",
              "costo_efectiva", "probable")
    for combo in itertools.product(TRI, repeat=len(campos)):
        yield Respuestas(**dict(zip(campos, combo)))


# ══════════════════ la guarda que no se negocia ══════════════════

@pytest.mark.parametrize("clase", ["seguridad", "ambiental"])
def test_con_consecuencia_grave_nunca_sale_operar_hasta_la_falla(clase):
    m = modo(clase)
    for r in todas_las_respuestas():
        d = decidir(m, r)
        assert d.estrategia != "operar_hasta_falla", (
            f"{clase} + {r.a_dict()} devolvió «operar hasta la falla»")


@pytest.mark.parametrize("clase", ["seguridad", "ambiental"])
def test_con_consecuencia_grave_y_falla_oculta_tampoco(clase):
    m = modo(clase, evidente=False)
    for r in todas_las_respuestas():
        assert decidir(m, r).estrategia != "operar_hasta_falla"


def test_sin_tarea_proactiva_y_con_seguridad_el_rediseno_es_obligatorio():
    d = decidir(modo("seguridad"),
                Respuestas(detectable=False, intervalo_edad=False,
                           costo_efectiva=False))
    assert d.estrategia == "rediseno"
    assert d.bloqueado_por_seguridad is True
    assert "no es una salida legal" in d.motivo


def test_solo_se_marca_bloqueado_cuando_de_verdad_se_iba_a_operar_hasta_fallar():
    # Un modo grave que sí tiene tarea a condición no está bloqueado por nada:
    # se decidió por su propio mérito.
    d = decidir(modo("seguridad"), Respuestas(detectable=True, viable=True))
    assert d.estrategia == "cbm"
    assert d.bloqueado_por_seguridad is False


# ══════════════════ evidente u oculta, primero ══════════════════

def test_la_falla_oculta_verificable_va_a_busqueda_de_fallas():
    d = decidir(modo("seguridad", evidente=False), Respuestas(probable=True))
    assert d.estrategia == "busqueda_fallas"
    assert d.por_defecto is True
    assert "falla multiple" in d.motivo


def test_la_falla_oculta_no_verificable_va_a_rediseno():
    d = decidir(modo("produccion", evidente=False), Respuestas(probable=False))
    assert d.estrategia == "rediseno"


def test_lo_oculto_se_decide_antes_que_todo_lo_demas():
    # Aunque la degradación sea detectable y haya intervalo de edad: si la
    # pérdida de función no es evidente, el riesgo es la falla múltiple.
    d = decidir(modo("produccion", evidente=False),
                Respuestas(detectable=True, intervalo_edad=True,
                           restaurable=True, viable=True, probable=True))
    assert d.estrategia == "busqueda_fallas"
    assert d.camino[0].respuesta == "no"


# ══════════════════ el orden de preferencia de RCM ══════════════════

def test_cbm_gana_cuando_la_degradacion_es_detectable():
    # Primera en el orden porque aprovecha la vida útil y no abre una máquina
    # que está sana.
    d = decidir(modo(), Respuestas(detectable=True, intervalo_edad=True,
                                   restaurable=True, viable=True))
    assert d.estrategia == "cbm"


def test_sin_deteccion_pero_con_edad_y_restaurable_va_a_restauracion():
    d = decidir(modo(), Respuestas(detectable=False, intervalo_edad=True,
                                   restaurable=True, viable=True))
    assert d.estrategia == "restauracion"


def test_con_edad_pero_sin_restaurar_va_a_descarte():
    d = decidir(modo(), Respuestas(detectable=False, intervalo_edad=True,
                                   restaurable=False, viable=True))
    assert d.estrategia == "descarte"


def test_una_tarea_inviable_no_se_elige_aunque_aplique():
    d = decidir(modo(), Respuestas(detectable=True, viable=False,
                                   intervalo_edad=False, costo_efectiva=False))
    assert d.estrategia == "operar_hasta_falla"


# ══════════════════ el 89 % de Nowlan y Heap ══════════════════

def test_sin_intervalo_de_edad_se_avisa_que_un_limite_por_horas_no_previene():
    d = decidir(modo(), Respuestas(detectable=False, intervalo_edad=False,
                                   costo_efectiva=False))
    assert any("89 %" in a for a in d.avisos)
    assert any("Nowlan" in a for a in d.avisos)


def test_el_aviso_del_89_no_aparece_cuando_si_hay_intervalo_de_edad():
    d = decidir(modo(), Respuestas(detectable=False, intervalo_edad=True,
                                   restaurable=True, viable=True))
    assert not any("89 %" in a for a in d.avisos)


# ══════════════════ no inventar economía ══════════════════

def test_sin_datos_economicos_se_dice_y_no_se_declara_ahorro():
    d = decidir(modo(), Respuestas(detectable=False, intervalo_edad=False,
                                   costo_efectiva=None))
    assert any("Informacion economica insuficiente" in a for a in d.avisos)
    assert not any("ahorr" in a.lower() and "no se declara" not in a
                   for a in d.avisos)


def test_el_aviso_economico_no_aparece_cuando_si_hay_dato():
    d = decidir(modo(), Respuestas(detectable=False, intervalo_edad=False,
                                   costo_efectiva=False))
    assert not any("economica insuficiente" in a for a in d.avisos)


# ══════════════════ auditabilidad ══════════════════

def test_toda_decision_lleva_motivo_escrito():
    for clase in ("seguridad", "ambiental", "produccion", "economica",
                  "no-significativa", "operacional"):
        for evidente in (True, False):
            for r in todas_las_respuestas():
                d = decidir(modo(clase, evidente), r)
                assert len(d.motivo) > 40, (clase, evidente, r.a_dict())


def test_toda_decision_deja_el_camino_que_la_produjo():
    d = decidir(modo(), Respuestas(detectable=False, intervalo_edad=True,
                                   restaurable=True, viable=True))
    assert len(d.camino) >= 3
    assert all(p.pregunta and p.respuesta and p.consecuencia for p in d.camino)
    assert d.camino[0].pregunta.startswith("¿La perdida de funcion es evidente")


def test_nunca_devuelve_una_estrategia_fuera_del_catalogo():
    for r in todas_las_respuestas():
        for clase in ("seguridad", "produccion"):
            assert decidir(modo(clase), r).estrategia in ESTRATEGIAS


def test_sin_evaluar_no_es_lo_mismo_que_no():
    # `None` significa «nadie se lo preguntó». La decisión sale del lado
    # conservador y se marca incompleta.
    sin = decidir(modo(), Respuestas())
    assert sin.incompleta is True
    assert any("del lado conservador" in a for a in sin.avisos)
    con = decidir(modo(), Respuestas(detectable=False, intervalo_edad=False,
                                     restaurable=False, viable=True,
                                     costo_efectiva=False, probable=False))
    assert con.incompleta is False


def test_las_acciones_por_defecto_se_marcan_como_tales():
    # Es lo que la Q7 de JA1011 pide justificar aparte.
    proactiva = decidir(modo(), Respuestas(detectable=True, viable=True))
    assert proactiva.por_defecto is False
    assert proactiva.proactiva is True
    rtf = decidir(modo(), Respuestas(detectable=False, intervalo_edad=False,
                                     costo_efectiva=False))
    assert rtf.por_defecto is True
    assert rtf.estrategia in POR_DEFECTO


def test_las_proactivas_son_exactamente_las_tres_tareas_programables():
    assert PROACTIVAS == {"cbm", "restauracion", "descarte"}
    assert PROACTIVAS.isdisjoint(POR_DEFECTO)
    assert PROACTIVAS | POR_DEFECTO == set(ESTRATEGIAS)


# ══════════════════ el registro y su resumen ══════════════════

def test_el_registro_cuenta_por_estrategia():
    a = Analisis(Activo("EX-220", "Excavadora"))
    f = a.agregar_funcion("Refrigerar", "80-95 °C")
    ff = a.agregar_falla(f.id, "Sobrecalienta")
    m1 = a.agregar_modo(ff.id, "Radiador obstruido")
    m2 = a.agregar_modo(ff.id, "Manguera de freno fisurada",
                        consecuencias=(Consecuencia("seguridad"),))
    d = Decisiones()
    d.registrar(m1, Respuestas(detectable=True, viable=True))
    d.registrar(m2, Respuestas(detectable=False, intervalo_edad=False,
                               costo_efectiva=False))
    assert d.reparto()["cbm"] == 1
    assert d.reparto()["rediseno"] == 1
    assert d.reparto()["operar_hasta_falla"] == 0

    r = resumen(a, d)
    assert r["modos"] == 2 and r["decididos"] == 2
    assert r["graves"] == 1
    assert r["rediseños_obligatorios"] == 1
