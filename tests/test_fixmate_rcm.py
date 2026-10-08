"""El análisis RCM: función → falla funcional → modo de falla → consecuencia.

Lo que se prueba aquí no es que los campos se guarden. Es que el modelo **se
niegue** a aceptar las cuatro formas en que un análisis RCM se degrada en la
práctica:

1. una función sin estándar, de la que no sale ningún modo de falla útil;
2. una falla funcional huérfana, que dice cómo falla algo que nadie declaró;
3. un modo de falla «validado» que nadie puede ir a verificar;
4. «oculta» puesta como una consecuencia más, que rompe la lógica de decisión.

Y que las siete preguntas de JA1011 se cuenten con criterio binario: la norma
nació porque se vendían metodologías incompletas con ese nombre, así que
«6 de 7» no es «casi RCM», es otra cosa.
"""

from __future__ import annotations

import pytest

from nefer.fixmate.activos import Activo, Ubicacion
from nefer.fixmate.catalogo import Catalogo
from nefer.fixmate.criticidad import NO_EVALUADA, PRIORIDAD_EJEMPLO
from nefer.fixmate.rcm import (Analisis, Consecuencia, Efecto, ErrorRCM,
                               FallaFuncional, Funcion, ModoFalla, PREGUNTAS,
                               Referencia, completitud)

CODIGO_RADIADOR = "TER.SOBRECALENTAMIENTO.RADIADOR"


def _activo() -> Activo:
    return Activo("EX-220", "Excavadora hidráulica", "Komatsu", "PC220-8",
                  categoria="excavadora",
                  contexto="Interior mina, turno continuo, 4.200 m")


def _analisis() -> Analisis:
    a = Analisis(_activo())
    f = a.agregar_funcion(
        "Mantener la temperatura del refrigerante en régimen",
        "Entre 80 y 95 °C con carga continua al 100 %")
    ff = a.agregar_falla(f.id, "La temperatura supera 95 °C con carga continua")
    a.agregar_modo(ff.id, "Radiador obstruido por polvo de mina",
                   codigo_catalogo=CODIGO_RADIADOR)
    return a


# --------------------------------- las cuatro cosas que no se aceptan

def test_una_funcion_sin_estandar_no_se_puede_declarar():
    # «El motor debe funcionar» no se puede fallar de forma verificable.
    with pytest.raises(ErrorRCM, match="estandar de desempeño"):
        Funcion("F1", "El motor debe funcionar", "")


def test_una_falla_funcional_huerfana_se_rechaza():
    a = Analisis(_activo())
    with pytest.raises(ErrorRCM, match="no existe la funcion"):
        a.agregar_falla("F9", "No entrega potencia")


def test_un_modo_huerfano_se_rechaza():
    a = _analisis()
    with pytest.raises(ErrorRCM, match="no existe la falla funcional"):
        a.agregar_modo("F9.9", "Algo")


def test_no_se_puede_marcar_validado_sin_evidencia():
    with pytest.raises(ErrorRCM, match="sin evidencia"):
        ModoFalla("m1", "F1.1", "Radiador obstruido", estado="validado")


def test_con_evidencia_si_se_puede_validar():
    m = ModoFalla("m1", "F1.1", "Radiador obstruido", estado="validado",
                  evidencia=(Referencia("historial", "OT-2025-014"),))
    assert m.estado == "validado"


def test_oculta_no_es_una_consecuencia_y_el_error_dice_donde_va():
    # Es la primera bifurcación del análisis, no una categoría más. Si se
    # acepta como clase, la lógica de decisión se rompe en silencio.
    with pytest.raises(ErrorRCM, match="evidente=False"):
        Consecuencia("oculta")


def test_una_fuente_desconocida_se_rechaza():
    with pytest.raises(ErrorRCM, match="fuente"):
        Referencia("me lo dijo un amigo", "x")


# --------------------------------------- la llave hacia el catálogo

def test_el_modo_hereda_sistema_causa_y_mecanismo_del_catalogo():
    # No se reescriben: es la misma taxonomía ISO 14224 que FixMate ya usa,
    # y repetirla a mano la parte en dos.
    m = _analisis().modos[0]
    assert m.ubicacion.sistema == "termico"
    assert m.causa == "Radiador obstruido por tierra o incrustacion"
    assert m.mecanismo == "Obstruccion"


def test_lo_que_el_analista_escribio_gana_sobre_el_catalogo():
    a = Analisis(_activo())
    f = a.agregar_funcion("Refrigerar", "80-95 °C")
    ff = a.agregar_falla(f.id, "Sobrecalienta")
    m = a.agregar_modo(ff.id, "Radiador tapado", codigo_catalogo=CODIGO_RADIADOR,
                       causa="Polvo de sílice compactado en el panal")
    assert m.causa == "Polvo de sílice compactado en el panal"
    assert m.mecanismo == "Obstruccion"   # este sí se rellenó


def test_un_codigo_inventado_se_rechaza_en_vez_de_crearse():
    a = Analisis(_activo())
    f = a.agregar_funcion("Refrigerar", "80-95 °C")
    ff = a.agregar_falla(f.id, "Sobrecalienta")
    with pytest.raises(ErrorRCM, match="no esta en el catalogo"):
        a.agregar_modo(ff.id, "x", codigo_catalogo="TER.INVENTADO.XYZ")


def test_un_modo_sin_codigo_de_catalogo_es_legitimo():
    # El catálogo no cubre todo, y obligar a elegir una entrada parecida es
    # justo el problema que el catálogo evita no teniendo «Otro».
    a = Analisis(_activo())
    f = a.agregar_funcion("Refrigerar", "80-95 °C")
    ff = a.agregar_falla(f.id, "Sobrecalienta")
    m = a.agregar_modo(ff.id, "Panal deformado por un golpe de roca")
    assert m.codigo_catalogo == ""
    assert m.ubicacion.sistema == ""


def test_el_vocabulario_de_sistemas_sale_del_catalogo_y_no_de_una_lista_nueva():
    from nefer.fixmate.activos import SISTEMAS
    assert set(SISTEMAS) == {e.sistema for e in Catalogo().entradas}


# ------------------------------------------------ evidente vs. oculta

def test_el_modo_es_evidente_por_defecto_pero_se_puede_declarar_oculto():
    assert ModoFalla("m", "f", "x").evidente is True
    assert ModoFalla("m", "f", "x", evidente=False).evidente is False


def test_grave_es_seguridad_o_ambiental_y_nada_mas():
    def modo(clase):
        return ModoFalla("m", "f", "x", consecuencias=(Consecuencia(clase),))
    assert modo("seguridad").grave
    assert modo("ambiental").grave
    assert not modo("produccion").grave
    assert not modo("economica").grave
    assert not modo("no-significativa").grave


# ------------------------------------------- criticidad, sin inventar

def test_un_modo_nuevo_tiene_criticidad_no_evaluada():
    assert _analisis().modos[0].criticidad.etiqueta == NO_EVALUADA


def test_la_criticidad_se_evalua_con_el_metodo_de_la_empresa():
    m = _analisis().modos[0]
    m.evaluar_criticidad(PRIORIDAD_EJEMPLO,
                         {"severidad": 4, "frecuencia": 4, "deteccion": 2})
    assert m.criticidad.evaluada
    assert m.criticidad.etiqueta == "alta"
    assert "EJEMPLO" in m.criticidad.metodo


# ------------------------------------- las siete preguntas de JA1011

def test_son_exactamente_siete_y_en_orden():
    assert len(PREGUNTAS) == 7
    assert [p.numero for p in PREGUNTAS] == [1, 2, 3, 4, 5, 6, 7]


def test_un_analisis_vacio_no_contesta_ninguna():
    c = completitud(Analisis(_activo()))
    assert c.contestadas == 0
    assert c.completo is False
    assert c.rompe_cadena is True


def test_el_esqueleto_contesta_las_tres_primeras():
    c = completitud(_analisis())
    assert [r.pregunta.numero for r in c.respuestas if r.contestada] == [1, 2, 3]
    assert c.rompe_cadena is True   # falta Q5, que sostiene la cadena


def test_con_efecto_y_consecuencia_la_cadena_queda_entera():
    a = _analisis()
    m = a.modos[0]
    m.efecto = Efecto(local="Sube la temperatura y el ECM reduce potencia",
                      observa_operador="Aguja en rojo y pierde fuerza")
    m.consecuencias = (Consecuencia("produccion", "Se detiene el frente"),)
    c = completitud(a)
    assert c.contestadas == 5
    assert c.rompe_cadena is False
    assert "falta decidir tareas" in c.resumen()


def test_una_funcion_sin_fallas_rompe_la_q2_y_lo_dice_con_su_id():
    a = _analisis()
    f2 = a.agregar_funcion("Mover el brazo", "Ciclo completo en 12 s")
    c = completitud(a)
    q2 = c.respuestas[1]
    assert q2.contestada is False
    assert any(f2.id in t for t in q2.faltantes)


def test_seis_de_siete_no_es_completo():
    # El criterio de JA1011 es binario a propósito: la norma existe porque se
    # vendían metodologías incompletas con ese nombre.
    from nefer.fixmate.decision import Dictamen
    a = _analisis()
    m = a.modos[0]
    m.efecto = Efecto(local="Sobrecalienta")
    m.consecuencias = (Consecuencia("produccion"),)
    decisiones = {m.id: Dictamen("cbm", "se vigila la temperatura")}
    c = completitud(a, decisiones)
    assert c.contestadas == 7
    assert c.completo is True
    # Y si se quita la decisión de un modo, vuelve a no estarlo.
    a.agregar_modo(m.falla_funcional_id, "Termostato trabado")
    assert completitud(a, decisiones).completo is False


def test_la_q7_exige_justificar_la_accion_por_defecto():
    from nefer.fixmate.decision import Dictamen
    a = _analisis()
    m = a.modos[0]
    m.efecto = Efecto(local="Sobrecalienta")
    m.consecuencias = (Consecuencia("produccion"),)
    sin_motivo = {m.id: Dictamen("operar_hasta_falla", "", por_defecto=True)}
    c = completitud(a, sin_motivo)
    assert c.respuestas[6].contestada is False
    con_motivo = {m.id: Dictamen("operar_hasta_falla", "ninguna tarea se paga",
                                 por_defecto=True)}
    assert completitud(a, con_motivo).completo is True


# ---------------------------------------------- contexto operacional

def test_el_analisis_hereda_el_contexto_del_activo_si_no_se_da_otro():
    a = Analisis(_activo())
    assert "4.200 m" in a.contexto


def test_el_contexto_explicito_gana_sobre_el_del_activo():
    a = Analisis(_activo(), contexto="Superficie, turno día, clima templado")
    assert a.contexto.startswith("Superficie")


def test_el_analisis_serializa_entero_y_vuelve_legible():
    a = _analisis()
    d = a.a_dict()
    assert d["activo"]["codigo"] == "EX-220"
    assert d["modos"][0]["ubicacion"]["sistema"] == "termico"
    assert d["modos"][0]["criticidad"]["etiqueta"] == NO_EVALUADA
    assert d["funciones"][0]["estandar"]


# ═══════════ el análisis como registro auditable ═══════════

def test_una_fecha_ambigua_no_entra_en_un_registro():
    """«03/04/2026» es el 3 de abril en Lima y el 4 de marzo en Houston.

    Dos años después, nadie puede decir cuál era. Un dato faltante se ve; uno
    ambiguo parece bueno.
    """
    from nefer.fixmate.rcm import fecha_valida

    assert fecha_valida("2026-03-15", "el análisis") == "2026-03-15"
    assert fecha_valida("", "el análisis") == ""          # no declarada, legítimo
    for mala in ("03/04/2026", "15-03-2026", "2026-3-5", "marzo 2026"):
        with pytest.raises(ErrorRCM, match="ISO 8601"):
            fecha_valida(mala, "el análisis")


def test_una_fecha_que_no_existe_se_rechaza():
    from nefer.fixmate.rcm import fecha_valida

    with pytest.raises(ErrorRCM, match="no existe"):
        fecha_valida("2026-02-30", "el análisis")


def _analisis_identificado():
    a = Analisis(Activo("EX-1", "Excavadora"), contexto="mina",
                 participantes=("operador", "mantenedor"),
                 fecha="2026-03-15", revision="1",
                 aprobado_por="jefe de mantenimiento",
                 proxima_revision="2027-03-15")
    f = a.agregar_funcion("Mover tierra", "30 m³/h")
    ff = a.agregar_falla(f.id, "No mueve tierra")
    a.agregar_modo(ff.id, "Bomba gastada",
                   codigo_catalogo="HID.BAJA_PRESION.BOMBA")
    return a


def test_un_analisis_sin_aprobar_no_es_un_registro():
    from nefer.fixmate.rcm import calidad

    a = _analisis_identificado()
    a.revision = ""
    a.aprobado_por = ""
    q = calidad(a)
    assert q.conforme is False
    assert [h.clave for h in q.no_conformidades] == ["identificacion"]
    assert "numero de revision" in q.hallazgos[0].detalle


def test_un_analisis_sin_participantes_no_tiene_contexto_operacional():
    # RCM no lo hace una persona: el contexto lo tiene quien opera la máquina.
    from nefer.fixmate.rcm import calidad

    a = _analisis_identificado()
    a.participantes = ()
    assert "participantes" in [h.clave for h in calidad(a).no_conformidades]


def test_la_revisión_vencida_solo_se_mira_si_se_dice_contra_qué_día():
    """Una función que cambia de respuesta con el calendario no se puede
    probar ni comparar con el espejo de la pantalla."""
    from nefer.fixmate.rcm import calidad

    a = _analisis_identificado()
    assert calidad(a).conforme is True                    # sin «hoy», no se mira
    assert calidad(a, hoy="2026-10-08").conforme is True  # aún vigente
    vencido = calidad(a, hoy="2028-01-01")
    assert vencido.conforme is False
    assert "vencio el 2027-03-15" in vencido.hallazgos[0].detalle


def test_dos_modos_con_el_mismo_código_se_denuncian_al_revisar():
    """Es la ambigüedad que impide enganchar una anomalía de campo.

    `anomalia.enlazar()` se niega a elegir entre dos candidatos —y hace
    bien—, pero si nadie lo dice al revisar, el análisis se da por bueno y
    el enganche falla en silencio meses después.
    """
    from nefer.fixmate.rcm import calidad

    a = _analisis_identificado()
    a.agregar_modo(a.fallas[0].id, "Otra cosa",
                   codigo_catalogo="HID.BAJA_PRESION.BOMBA")
    q = calidad(a)
    hallazgo = [h for h in q.no_conformidades if h.clave == "codigo_repetido"][0]
    assert hallazgo.ids == ("F1.1.1", "F1.1.2")
    assert "HID.BAJA_PRESION.BOMBA" in hallazgo.detalle


def test_la_cobertura_de_codificación_se_mide_y_no_se_castiga():
    # Un modo sin código no es un defecto del análisis: es la medida de hasta
    # dónde alcanza el catálogo, y lo que dice si hay que agrandarlo.
    from nefer.fixmate.rcm import calidad

    a = _analisis_identificado()
    a.agregar_modo(a.fallas[0].id, "Algo que el catálogo no cubre")
    q = calidad(a)
    assert q.conforme is True
    assert q.codificados == 1 and q.modos == 2
    observación = [h for h in q.hallazgos if h.clave == "sin_codificar"][0]
    assert observación.gravedad == "observacion"
    assert observación.ids == ("F1.1.2",)


def test_estar_completo_y_ser_un_registro_válido_son_cosas_distintas():
    """La diferencia que nadie ve hasta que llega la auditoría."""
    from nefer.fixmate.rcm import calidad, completitud

    a = _analisis_identificado()
    a.revision = ""
    a.aprobado_por = ""
    # Las siete no están contestadas aquí (falta decidir), pero el punto es
    # que las dos medidas son independientes: una mira el método, la otra el
    # documento.
    assert completitud(a).contestadas >= 3
    assert calidad(a).conforme is False
