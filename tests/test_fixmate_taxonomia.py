"""Los nueve niveles de ISO 14224, y qué llena FixMate en cada uno.

Esto cierra la OBS-02 de la auditoría. La observación no decía «faltan
niveles»: decía que **nadie podía responder si la jerarquía mapea a la
norma sin abrir el código**. Se cierra con un mapeo explícito, probado, y
con las ausencias declaradas y justificadas — no ampliando la jerarquía por
si acaso, que es como se llena un sistema de niveles que nadie usa.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from nefer.fixmate import cargador, taxonomia  # noqa: E402
from nefer.fixmate.activos import Activo, Ubicacion  # noqa: E402

EJEMPLO = RAIZ / "ejemplos" / "rcm-tpm" / "analisis-ex220.json"


def test_la_taxonomía_tiene_los_nueve_niveles_en_orden():
    assert len(taxonomia.NIVELES) == 9
    assert [n.numero for n in taxonomia.NIVELES] == list(range(1, 10))
    # Los dos que la norma señala, y que coinciden con cómo trabaja FixMate.
    assert taxonomia.NIVEL_DE_REPORTE == 6
    assert taxonomia.NIVEL_DE_MANTENIMIENTO == 8


def test_cada_nivel_dice_de_dónde_sale_o_por_qué_no_se_modela():
    """Es lo que convierte la tabla en algo auditable.

    Una lista de nueve nombres no sirve de nada: la pregunta del auditor es
    «¿y esto de dónde sale?», y la respuesta tiene que estar escrita.
    """
    for n in taxonomia.NIVELES:
        assert n.origen.strip(), f"el nivel {n.numero} no dice de dónde sale"
        if not n.modelado:
            assert n.origen.startswith("no se modela:"), (
                f"el nivel {n.numero} no está modelado y no dice por qué")


def test_las_ausencias_son_tres_y_están_justificadas():
    # Planta y sección no existen en una flota que se mueve; la parte está
    # por debajo de donde RCM decide.
    assert taxonomia.NO_MODELADOS == (4, 5, 9)
    assert taxonomia.MODELADOS == (1, 2, 3, 6, 7, 8)


def test_los_niveles_del_activo_y_los_del_modo_no_se_mezclan():
    """Contarlos juntos llamaba «falta» a algo que no toca declarar ahí.

    Un informe que reclama la subunidad mirando un activo enseña a
    rellenarla con cualquier cosa, que es el problema de «Otro» otra vez.
    """
    assert taxonomia.NIVELES_DEL_ACTIVO == (1, 2, 3, 6)
    assert taxonomia.NIVELES_DEL_MODO == (7, 8)
    assert set(taxonomia.NIVELES_DEL_ACTIVO + taxonomia.NIVELES_DEL_MODO) \
        == set(taxonomia.MODELADOS)


def test_el_activo_solo_responde_por_sus_niveles():
    activo = Activo("EX-220", "Excavadora", categoria="excavadora",
                    instalacion="unidad minera")
    ctx = taxonomia.Contexto("mineria", "contratista de equipo")

    solo_activo = taxonomia.cobertura(activo, contexto=ctx)
    assert solo_activo.aplicables == (1, 2, 3, 6)
    assert solo_activo.completa is True

    con_modo = taxonomia.cobertura(
        activo, Ubicacion("termico", "refrigeracion", "panal"), ctx)
    assert con_modo.aplicables == (1, 2, 3, 6, 7, 8)
    assert con_modo.completa is True
    assert con_modo.valores[7] == "termico / refrigeracion"
    assert con_modo.valores[8] == "panal"


def test_lo_que_no_se_declara_sale_vacío_y_se_cuenta():
    # Sin instalación ni contexto: tres niveles del activo sin declarar.
    pelado = taxonomia.cobertura(Activo("EX-1", "Excavadora"))
    assert pelado.sin_declarar == (1, 2, 3)
    assert pelado.declarados == 1          # sólo el código del activo
    assert pelado.completa is False


def test_los_niveles_no_modelados_nunca_se_rellenan():
    """Ni con un parecido, ni con el contexto operacional.

    El contexto dice «interior mina, 4.200 m»; eso no es una planta ni una
    sección, y ponerlo ahí sería un dato que nadie revisó viajando como si
    fuera bueno.
    """
    activo = Activo("EX-220", "Excavadora", instalacion="unidad minera",
                    contexto="Interior mina, turno continuo, 4.200 m")
    v = taxonomia.niveles(activo, Ubicacion("termico", "refrigeracion", "panal"),
                          taxonomia.Contexto("mineria", "contratista"))
    for nivel in taxonomia.NO_MODELADOS:
        assert v[nivel] == "", f"el nivel {nivel} se rellenó solo"


def test_el_subsistema_es_un_refinamiento_del_nivel_7_y_no_un_nivel_nuevo():
    # FixMate tiene un escalón más que la norma entre el sistema y el
    # componente. No se le inventa un número: se concatena y se dice.
    v = taxonomia.niveles(Activo("EX-1", "x"),
                          Ubicacion("hidraulico", "mando final", "sello"))
    assert v[7] == "hidraulico / mando final"
    assert v[8] == "sello"
    # Y sin subsistema, el nivel 7 es el sistema a secas.
    v2 = taxonomia.niveles(Activo("EX-1", "x"), Ubicacion("hidraulico", "", "sello"))
    assert v2[7] == "hidraulico"


def test_el_análisis_entero_sale_en_filas_de_intercambio():
    analisis = cargador.analisis(EJEMPLO)
    filas = taxonomia.filas(analisis, taxonomia.Contexto("mineria", "contratista"))
    assert len(filas) == len(analisis.modos)
    # Cada registro trae su taxonomía entera, que es la forma que tiene un
    # archivo de intercambio.
    for fila in filas:
        assert fila["n6_unidad"] == "EX-220"
        assert fila["n1_industria"] == "mineria"
        assert fila["n4_planta"] == "" and fila["n9_parte"] == ""
    assert filas[0]["n8_componente"] == "panal del radiador"


def test_el_ejemplo_declara_su_instalación():
    # El que todo el mundo copia: si el modelo no declara el nivel 3, lo que
    # se enseña es a no declararlo.
    analisis = cargador.analisis(EJEMPLO)
    assert analisis.activo.instalacion
    cob = taxonomia.cobertura(analisis.activo)
    assert 3 not in cob.sin_declarar


def test_el_activo_viaja_con_su_instalación_y_la_recupera():
    activo = Activo("EX-220", "Excavadora", instalacion="unidad minera")
    assert Activo.de_dict(activo.a_dict()).instalacion == "unidad minera"
    # Y un activo viejo, sin el campo, sigue cargando.
    assert Activo.de_dict({"codigo": "EX-1", "nombre": "x"}).instalacion == ""
