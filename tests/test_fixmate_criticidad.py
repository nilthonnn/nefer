"""Criticidad configurable: la escala es de la empresa, no de la herramienta.

La prueba que más importa de este archivo es la del RPN. No comprueba que el
cálculo esté bien: comprueba que el defecto conocido del RPN **se reproduce**,
y que el código lo advierte. Si algún día alguien «arregla» el RPN para que
dos riesgos distintos den números distintos, habrá inventado una escala que
no es el RPN, y esta prueba tiene que caerse.
"""

from __future__ import annotations

import pytest

from nefer.fixmate import criticidad as c
from nefer.fixmate.criticidad import (ErrorCriticidad, Factor, Metodo, Nivel,
                                      NO_EVALUADA, evaluar)


# ------------------------------------------------ sin método no hay número

def test_sin_metodo_la_criticidad_es_no_evaluada_y_no_cero():
    # Cero se lee como «bajo riesgo»; «no evaluada» se lee como lo que es.
    r = evaluar(None, {"severidad": 5})
    assert r.etiqueta == NO_EVALUADA
    assert r.valor is None
    assert r.evaluada is False


def test_el_modulo_no_expone_ninguna_escala_por_defecto():
    # Si apareciera un `POR_DEFECTO`, la herramienta estaría decidiendo el
    # apetito de riesgo de un cliente que no conoce.
    assert not hasattr(c, "POR_DEFECTO")
    assert not hasattr(c, "METODO_POR_DEFECTO")
    # Lo que sí hay va rotulado.
    assert all("EJEMPLO" in nombre for nombre in c.EJEMPLOS)


def test_un_metodo_a_medio_responder_no_da_numero():
    with pytest.raises(ErrorCriticidad, match="falta responder"):
        evaluar(c.PRIORIDAD_EJEMPLO, {"severidad": 3})


def test_un_nivel_fuera_de_la_escala_se_rechaza_con_los_permitidos():
    with pytest.raises(ErrorCriticidad, match="permitidos"):
        evaluar(c.PRIORIDAD_EJEMPLO,
                {"severidad": 9, "frecuencia": 1, "deteccion": 1})


# --------------------------------------------- el defecto del RPN, fijado

def test_el_rpn_da_el_mismo_numero_a_dos_riesgos_muy_distintos():
    # 2×3×5 = 30 y 5×3×2 = 30. El segundo es severidad crítica: mata gente.
    # Esto NO es un error del código: es el defecto del RPN, y está aquí para
    # que nadie lo «arregle» creyendo que lo mejora.
    molesto = evaluar(c.RPN_EJEMPLO,
                      {"severidad": 2, "frecuencia": 3, "deteccion": 5})
    mortal = evaluar(c.RPN_EJEMPLO,
                     {"severidad": 5, "frecuencia": 3, "deteccion": 2})
    assert molesto.valor == mortal.valor == 30
    assert molesto.etiqueta == mortal.etiqueta


def test_el_rpn_viaja_siempre_con_su_advertencia():
    r = evaluar(c.RPN_EJEMPLO, {"severidad": 2, "frecuencia": 3, "deteccion": 5})
    assert "ordinales" in r.advertencia
    assert "AIAG-VDA" in r.advertencia


def test_la_tabla_de_prioridad_si_distingue_esos_dos_casos():
    # Lo que el RPN confunde, la tabla lo separa: pondera severidad primero
    # y no multiplica nada. Es la razón por la que AIAG-VDA la adoptó.
    molesto = evaluar(c.PRIORIDAD_EJEMPLO,
                      {"severidad": 2, "frecuencia": 3, "deteccion": 5})
    mortal = evaluar(c.PRIORIDAD_EJEMPLO,
                     {"severidad": 5, "frecuencia": 3, "deteccion": 2})
    assert molesto.etiqueta != mortal.etiqueta
    assert mortal.etiqueta == "alta"


def test_la_severidad_critica_manda_salvo_que_sea_remota_y_evidente():
    alta = evaluar(c.PRIORIDAD_EJEMPLO,
                   {"severidad": 5, "frecuencia": 2, "deteccion": 1})
    assert alta.etiqueta == "alta"
    baja = evaluar(c.PRIORIDAD_EJEMPLO,
                   {"severidad": 5, "frecuencia": 1, "deteccion": 1})
    assert baja.etiqueta == "baja"


def test_la_tabla_de_prioridad_no_tiene_huecos():
    # Una tabla con huecos decide por omisión, que es lo que no se quiere.
    for s in range(1, 6):
        for f in range(1, 6):
            for d in range(1, 6):
                r = evaluar(c.PRIORIDAD_EJEMPLO,
                            {"severidad": s, "frecuencia": f, "deteccion": d})
                assert r.etiqueta in ("alta", "media", "baja")


# --------------------------------------- un método propio del taller

def _metodo_propio() -> Metodo:
    gravedad = Factor("gravedad", "Gravedad", (
        Nivel(1, "Leve"), Nivel(2, "Seria"), Nivel(3, "Grave")))
    return Metodo(nombre="Matriz del taller norte", version="2024-1",
                  factores=(gravedad,), combinacion="maximo",
                  umbrales=((3, "A"), (2, "B"), (1, "C")))


def test_una_planta_puede_traer_su_propia_escala():
    r = evaluar(_metodo_propio(), {"gravedad": 3})
    assert r.etiqueta == "A"
    assert r.metodo == "Matriz del taller norte"
    assert r.version == "2024-1"


def test_el_metodo_y_la_version_viajan_con_el_resultado():
    # Sin esto no hay forma de saber si un «12» de hace dos años es comparable
    # con un «12» de hoy. Lo normal es que no lo sea.
    r = evaluar(c.RPN_EJEMPLO, {"severidad": 1, "frecuencia": 1, "deteccion": 1})
    d = r.a_dict()
    assert d["metodo"] and d["version"]
    assert d["valores"] == {"severidad": 1, "frecuencia": 1, "deteccion": 1}


def test_una_tabla_con_hueco_se_niega_en_vez_de_elegir():
    metodo = Metodo(nombre="incompleta", version="1",
                    factores=(Factor("x", "X", (Nivel(1, "uno"), Nivel(2, "dos"))),),
                    combinacion="matriz", tabla={(1,): "baja"})
    assert evaluar(metodo, {"x": 1}).etiqueta == "baja"
    with pytest.raises(ErrorCriticidad, match="no esta en la tabla"):
        evaluar(metodo, {"x": 2})


def test_una_combinacion_desconocida_no_se_adivina():
    metodo = Metodo(nombre="rara", version="1",
                    factores=(Factor("x", "X", (Nivel(1, "uno"),)),),
                    combinacion="promedio_ponderado")
    with pytest.raises(ErrorCriticidad, match="desconocida"):
        evaluar(metodo, {"x": 1})
