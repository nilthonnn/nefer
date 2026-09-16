"""El diagnostico: de donde sale cada frase de la respuesta.

Dos reglas se prueban aqui una y otra vez porque de ellas depende que un
tecnico pueda fiarse de lo que lee: no se responde sin antecedente, y no se
devuelve un torque que no este escrito en la fuente.
"""

import pytest

from nefer.fixmate import motor as m
from nefer.fixmate.indice import Fragmento, Indice

INFORME_INYECTOR = Fragmento(
    id="ot:OT-455", tipo="informe", fuente="historial.json",
    texto="ORDEN DE TRABAJO OT-455\nFalla: humo negro y marcha inestable.\n"
          "Causa: inyector con retorno excesivo.\nApretar el prisionero a 30 N·m.",
    metadatos={"codigo_ot": "OT-455", "codigos_dtc": ["P0300"],
               "codigo_equipo": "GE074-02",
               "resumen_falla": "Humo negro y marcha inestable en frio.",
               "causa_raiz": "Inyector del cilindro 3 con retorno excesivo.",
               "solucion_aplicada": "Se reemplazo el inyector.",
               "pasos": ["Medir el retorno de inyectores.",
                         "Reemplazar el inyector fuera de tolerancia."],
               "herramientas": ["Juego de probetas"],
               "repuestos": ["Inyector 0445110xxx"],
               "torques": ["30 N·m"]})

INFORME_FILTRO = Fragmento(
    id="ot:OT-412", tipo="informe", fuente="historial.json",
    texto="ORDEN DE TRABAJO OT-412\nFalla: humo negro al tomar carga en altura.\n"
          "Causa: filtro de aire colmatado.",
    metadatos={"codigo_ot": "OT-412", "codigos_dtc": ["P0300"],
               "codigo_equipo": "GE074-01",
               "resumen_falla": "Humo negro y perdida de potencia en altura.",
               "causa_raiz": "Filtro de aire colmatado por polvo de mina.",
               "solucion_aplicada": "Se reemplazo el elemento primario.",
               "pasos": ["Abrir la caja del filtro de aire.",
                         "Reemplazar elemento primario y secundario."],
               "herramientas": ["Llave de 13 mm"],
               "repuestos": ["Filtro P533781"]})

SECCION_MANUAL = Fragmento(
    id="man:1", tipo="manual", fuente="manual.md",
    texto="Sistema de inyeccion\nPar de apriete del prisionero: 30 N·m.",
    metadatos={"seccion": "Sistema de inyeccion", "torques": ["30 N·m"],
               "herramientas": ["Torquimetro"]})


def _motor(fragmentos=None, redactor=None) -> m.Motor:
    indice = Indice()
    indice.agregar(list(fragmentos or [INFORME_INYECTOR, INFORME_FILTRO, SECCION_MANUAL]))
    return m.Motor(indice, redactor=redactor)


# ------------------------------------------------------------- la consulta

def test_una_consulta_vacia_no_llega_al_indice():
    with pytest.raises(ValueError, match="vacia"):
        m.Consulta("   ")


def test_el_limite_se_queda_dentro_de_lo_razonable():
    assert m.Consulta("humo", limite=99).limite == 10
    assert m.Consulta("humo", limite=0).limite == 1


def test_el_codigo_dictado_se_normaliza_antes_de_filtrar():
    assert m.Consulta("humo", codigo_dtc="spn 157").codigo_dtc == "SPN157"


# ------------------------------------------------------------ la evidencia

def test_sin_antecedentes_no_hay_diagnostico():
    motor = m.Motor(Indice())
    with pytest.raises(m.SinEvidencia):
        motor.consultar(m.Consulta("cualquier falla"))


def test_lo_que_no_se_parece_a_nada_tampoco_da_diagnostico():
    motor = _motor()
    with pytest.raises(m.SinEvidencia):
        motor.consultar(m.Consulta("tramites de aduana del contenedor"))


def test_un_codigo_que_nadie_registro_no_deja_al_tecnico_sin_respuesta():
    # El filtro afina, no esconde: si no hay nada con ese codigo se responde
    # por la descripcion, diciendo que el filtro no se pudo aplicar.
    diagnostico = _motor().consultar(m.Consulta("humo negro", codigo_dtc="U9999"))
    assert m.AVISO_SIN_FILTRO in diagnostico.avisos
    assert diagnostico.evidencia_historica


def test_la_evidencia_cita_de_donde_salio_cada_cosa():
    diagnostico = _motor().consultar(m.Consulta("humo negro y marcha inestable"))
    primera = diagnostico.evidencia_historica[0]
    assert primera.codigo_ot == "OT-455"
    assert primera.fuente == "historial.json"
    assert primera.similitud > 0 and primera.extracto


# --------------------------------------------------- el redactor sin modelo

def test_la_causa_raiz_es_la_del_antecedente_mas_parecido():
    diagnostico = _motor().consultar(m.Consulta("humo negro y marcha inestable en frio"))
    assert "Inyector" in diagnostico.causa_raiz_mas_probable
    assert diagnostico.redactor == "extractivo"


def test_los_pasos_salen_de_un_solo_antecedente_y_no_de_dos_mezclados():
    diagnostico = _motor().consultar(m.Consulta("humo negro y marcha inestable en frio"))
    assert diagnostico.pasos_recomendados == [
        "Medir el retorno de inyectores",
        "Reemplazar el inyector fuera de tolerancia"]
    assert "Abrir la caja del filtro de aire" not in diagnostico.pasos_recomendados


def test_la_otra_causa_no_se_calla_aunque_no_aporte_los_pasos():
    diagnostico = _motor().consultar(m.Consulta("humo negro", limite=3))
    assert "OT-412" in diagnostico.diagnostico_probabilistico
    assert "OT-412" in [e.codigo_ot for e in diagnostico.evidencia_historica]


def test_ningun_torque_se_inventa():
    diagnostico = _motor().consultar(m.Consulta("humo negro y marcha inestable"))
    escrito = " ".join(e.extracto for e in diagnostico.evidencia_historica)
    for torque in diagnostico.torques:
        assert torque in escrito, f"{torque} no esta en ninguna fuente citada"
    assert m.AVISO_TORQUE in diagnostico.avisos


def test_sin_procedimiento_escrito_no_se_inventan_pasos():
    # Partir en frases la prosa de un manual da una lista numerada que se lee
    # como un procedimiento y no lo es. En campo, eso se ejecuta.
    motor = m.Motor(_indice_de([SECCION_MANUAL]))
    diagnostico = motor.consultar(m.Consulta("par de apriete del prisionero"))

    assert diagnostico.pasos_recomendados == []
    assert m.AVISO_SIN_PROCEDIMIENTO in diagnostico.avisos
    assert "Sistema de inyeccion" in diagnostico.causa_raiz_mas_probable
    # Lo que si hay —el torque escrito en el manual— se entrega igual.
    assert diagnostico.torques == ["30 N·m"]


def test_un_manual_no_confirma_una_causa_raiz():
    diagnostico = m.Motor(_indice_de([SECCION_MANUAL])).consultar(
        m.Consulta("par de apriete del prisionero"))
    assert diagnostico.causa_raiz_mas_probable.startswith("No consta")


def test_las_herramientas_del_manual_valen_para_cualquier_antecedente():
    diagnostico = _motor().consultar(m.Consulta("apriete del prisionero de inyeccion"))
    assert "Torquimetro" in diagnostico.herramientas_y_repuestos


def test_una_evidencia_floja_se_declara_floja():
    # Lo recuperado apenas roza la consulta. Se responde —es lo unico que hay—
    # pero rotulado como pista, no como diagnostico.
    flojo = Fragmento(id="x", tipo="informe", fuente="h.json",
                      texto="Cambio de aceite programado de rutina en el taller "
                            "central, con relleno de refrigerante.",
                      metadatos={"codigo_ot": "OT-1"})
    diagnostico = m.Motor(_indice_de([flojo]), umbral=0.0).consultar(
        m.Consulta("se escucha un ruido raro en la caja"))

    assert diagnostico.confianza == "baja"
    assert m.AVISO_POCA_EVIDENCIA in diagnostico.avisos


def _indice_de(fragmentos) -> Indice:
    indice = Indice()
    indice.agregar(fragmentos)
    return indice


# ------------------------------------------------- la costura del redactor
#
# Hubo un redactor que llamaba a OpenAI y se quito: en faena no hay red, y el
# historial de fallas de una flota no se manda a un tercero. La costura queda,
# para el dia que se enchufe un modelo que corra en la propia maquina, y se
# prueba con uno falso -- que es lo unico que se podia probar de verdad.

def test_un_redactor_enchufado_ve_la_evidencia_recuperada():
    vistos = {}

    def redactor(consulta, coincidencias, causas_probables=None, medicion=None):
        vistos["contexto"] = m.contexto(coincidencias)
        return {"diagnostico_probabilistico": "Lo redacto el modelo.",
                "causa_raiz_mas_probable": "Inyector.",
                "pasos_recomendados": ["Paso del modelo"],
                "herramientas_y_repuestos": [], "torques": []}

    redactor.nombre = "enchufado"
    diagnostico = _motor(redactor=redactor).consultar(m.Consulta("humo negro"))

    assert diagnostico.redactor == "enchufado"
    assert diagnostico.pasos_recomendados == ["Paso del modelo"]
    assert "OT-" in vistos["contexto"], "el redactor tiene que ver los antecedentes"
    # La evidencia la pone el indice, no el redactor: se cita igual.
    assert diagnostico.evidencia_historica


def test_si_el_redactor_enchufado_falla_la_respuesta_sale_igual():
    def redactor(consulta, coincidencias, causas_probables=None, medicion=None):
        raise m.ErrorRedactor("el modelo no respondio: timeout")

    diagnostico = _motor(redactor=redactor).consultar(m.Consulta("humo negro"))

    assert diagnostico.redactor == "extractivo"
    assert diagnostico.causa_raiz_mas_probable
    assert any("no respondio" in aviso for aviso in diagnostico.avisos)


def test_el_diagnostico_se_serializa_entero_a_json():
    diagnostico = _motor().consultar(m.Consulta("humo negro"))
    d = diagnostico.a_dict()
    assert set(d) >= {"diagnostico_probabilistico", "causa_raiz_mas_probable",
                      "pasos_recomendados", "herramientas_y_repuestos", "torques",
                      "evidencia_historica", "confianza", "redactor", "avisos"}
    assert isinstance(d["evidencia_historica"][0], dict)


# ------------------------- cuando la busqueda y el historial no coinciden

CAUSAS_REPETIDAS = [
    ("humo negro al tomar carga", "Filtro de aire colmatado"),
    ("perdida de potencia y humo negro en altura", "Filtro de aire colmatado por polvo"),
    ("humo negro en pendiente con carga", "Filtro de aire colmatado; admision restringida"),
    ("el motor no levanta carga y humea", "Filtro de aire colmatado por polvo de mina"),
    ("marcha inestable en frio", "Inyector con retorno excesivo"),
    ("cascabeleo y humo en ralenti", "Inyector con retorno excesivo por aguja"),
    ("falla de combustion en un cilindro", "Inyector con retorno excesivo"),
    ("ralenti irregular y olor a diesel", "Inyector con retorno excesivo por asiento"),
    ("fuga de aceite hidraulico y perdida de fuerza al cargar",
     "Sello del vastago cortado"),
    ("charco de aceite bajo la maquina", "Sello del vastago cortado por rebaba"),
    ("goteo en el cilindro del brazo", "Sello del vastago cortado en el brazo"),
    ("perdida de aceite por el vastago", "Sello del vastago cortado"),
    ("no arranca en la mañana", "Baterias sulfatadas"),
    ("el arranque gira lento", "Baterias sulfatadas por descargas profundas"),
]


def _indice_con_historial() -> Indice:
    indice = Indice()
    indice.agregar([
        Fragmento(id=f"ot:OT-{n}", tipo="informe", fuente="historial.json",
                  texto=f"ORDEN DE TRABAJO OT-{n}\nFalla: {falla}\nCausa: {causa}",
                  metadatos={"codigo_ot": f"OT-{n}", "resumen_falla": falla,
                             "causa_raiz": causa,
                             "solucion_aplicada": f"Se corrigio: {causa}",
                             "pasos": [f"Paso propio de OT-{n}"]})
        for n, (falla, causa) in enumerate(CAUSAS_REPETIDAS)])
    return indice


def test_el_historial_completo_corrige_lo_que_trajo_la_busqueda():
    # «pierde fuerza» aparece literal en el informe de un sello de vastago, y
    # por parecido de palabras ese se cuela arriba. El historial entero dice
    # otra cosa, y esa es la que manda: la respuesta sale del antecedente de
    # la causa que el historial respalda, no del primero de la lista.
    motor = m.Motor(_indice_con_historial())
    diagnostico = motor.consultar(m.Consulta("sale humo negro y pierde fuerza", limite=3))

    assert "Filtro de aire colmatado" in diagnostico.causa_raiz_mas_probable
    assert diagnostico.causas_probables[0]["causa"].startswith("Filtro de aire")
    assert diagnostico.pasos_recomendados, "tiene que traer el procedimiento de esa causa"


def test_si_la_busqueda_no_trajo_esa_causa_se_va_a_buscar_al_indice():
    # Se simula el caso malo: la busqueda devolvio solo antecedentes de otra
    # averia. El motor va al indice por el de la causa que el historial
    # respalda, en vez de contestar con el primero que le llego.
    motor = m.Motor(_indice_con_historial())
    consulta = m.Consulta("sale humo negro y pierde fuerza")
    otros = [c for c in motor.indice.buscar(consulta.texto, limite=5, umbral=0.0)
             if "Filtro" not in str(c.fragmento.metadatos.get("causa_raiz"))][:2]
    causas = motor.causas_probables(consulta)

    apoyo = motor.apoyo_estadistico(consulta, otros, causas)
    assert apoyo is not None
    assert "Filtro de aire" in apoyo.fragmento.metadatos["causa_raiz"]
    assert apoyo.fragmento.id in {f.id for f in motor.indice.fragmentos}


def test_si_la_busqueda_ya_trajo_esa_causa_no_se_añade_nada():
    motor = m.Motor(_indice_con_historial())
    consulta = m.Consulta("humo negro al tomar carga")
    coincidencias = motor.indice.buscar(consulta.texto, limite=3, umbral=0.0)
    assert motor.apoyo_estadistico(
        consulta, coincidencias, motor.causas_probables(consulta)) is None


def test_una_estadistica_floja_no_mueve_la_evidencia():
    motor = m.Motor(_indice_con_historial())
    consulta = m.Consulta("humo negro")
    flojas = [{"causa": "Filtro de aire colmatado", "probabilidad": 0.2, "casos": 4}]
    assert motor.apoyo_estadistico(consulta, [], flojas) is None


def test_cuando_se_añade_evidencia_se_avisa():
    motor = m.Motor(_indice_con_historial())
    consulta = m.Consulta("sale humo negro y pierde fuerza")
    # El aviso sale cuando el apoyo entra; se comprueba sobre el mismo camino
    # que usa `consultar`.
    coincidencias, avisos = motor.recuperar(consulta)
    causas = motor.causas_probables(consulta)
    if motor.apoyo_estadistico(consulta, coincidencias, causas) is not None:
        assert m.AVISO_APOYO in motor.consultar(consulta).avisos
    else:
        assert m.AVISO_APOYO not in motor.consultar(consulta).avisos


def test_lo_que_se_añade_sale_del_indice_y_no_de_la_nada():
    motor = m.Motor(_indice_con_historial())
    diagnostico = motor.consultar(m.Consulta("sale humo negro y pierde fuerza"))
    en_indice = {f.id for f in motor.indice.fragmentos}
    assert all(e.id in en_indice for e in diagnostico.evidencia_historica)


def test_sin_clasificador_entrenado_no_se_toca_el_orden_de_la_busqueda():
    motor = _motor()      # tres fragmentos: no hay con que entrenar
    diagnostico = motor.consultar(m.Consulta("humo negro y marcha inestable"))
    assert diagnostico.causas_probables == []
    assert diagnostico.precision_medida is None
    assert m.AVISO_APOYO not in diagnostico.avisos


def test_la_estadistica_se_publica_con_su_respaldo():
    diagnostico = m.Motor(_indice_con_historial()).consultar(
        m.Consulta("no arranca y el arranque gira lento"))
    medida = diagnostico.precision_medida

    assert medida["casos"] == len(CAUSAS_REPETIDAS)
    assert 0.0 <= medida["precision"] <= 1.0
    assert "linea_base" in medida, "un acierto sin linea base no significa nada"
    # Y el texto del diagnostico lo dice, no solo el JSON.
    assert "%" in diagnostico.diagnostico_probabilistico
    assert str(medida["casos"]) in diagnostico.diagnostico_probabilistico


def test_el_diagnostico_dice_que_consulta_entendio():
    diagnostico = _motor().consultar(m.Consulta("humo negro y marcha inestable"))
    assert diagnostico.consulta_interpretada == "humo negro y marcha inestable"


def test_el_modelo_tambien_ve_lo_que_dice_el_historial_completo():
    visto = {}

    def redactor(consulta, coincidencias, causas_probables=None, medicion=None):
        visto["causas"] = causas_probables
        visto["medicion"] = medicion
        return {"diagnostico_probabilistico": "x", "causa_raiz_mas_probable": "y",
                "pasos_recomendados": [], "herramientas_y_repuestos": [], "torques": []}

    m.Motor(_indice_con_historial(), redactor=redactor).consultar(
        m.Consulta("humo negro al tomar carga"))
    assert visto["causas"][0]["causa"].startswith("Filtro de aire")
    assert visto["medicion"]["casos"] == len(CAUSAS_REPETIDAS)


def test_una_falla_nueva_le_gana_a_la_estadistica():
    # El informe que se registro ayer describe exactamente esto y sale
    # primero, con mucho parecido. El clasificador aprendio de las averias
    # viejas y no puede saberlo todavia: aqui manda la evidencia, no la
    # estadistica. Si no, el asistente nunca aprenderia nada nuevo.
    indice = _indice_con_historial()
    indice.agregar([Fragmento(
        id="ot:OT-NUEVA", tipo="informe", fuente="historial.json",
        texto="ORDEN DE TRABAJO OT-NUEVA\nFalla: el ventilador no gira y el "
              "motor se calienta\nCausa: correa del ventilador partida",
        metadatos={"codigo_ot": "OT-NUEVA",
                   "resumen_falla": "El ventilador no gira y el motor se calienta",
                   "causa_raiz": "Correa del ventilador partida",
                   "solucion_aplicada": "Se cambio la correa",
                   "pasos": ["Cambiar la correa y alinear la polea"]})])

    diagnostico = m.Motor(indice).consultar(
        m.Consulta("el ventilador no gira y el motor se calienta"))

    assert diagnostico.causa_raiz_mas_probable == "Correa del ventilador partida"
    assert diagnostico.pasos_recomendados == ["Cambiar la correa y alinear la polea"]
    # La estadistica no desaparece: queda como segunda opinion, en el texto.
    assert diagnostico.causas_probables
    assert m.AVISO_APOYO not in diagnostico.avisos


def test_con_evidencia_fuerte_no_se_va_a_buscar_mas():
    motor = m.Motor(_indice_con_historial())
    consulta = m.Consulta("marcha inestable en frio")
    coincidencias = motor.indice.buscar(consulta.texto, limite=3, umbral=0.0)
    assert coincidencias[0].puntaje >= m.UMBRAL_EVIDENCIA_FUERTE
    assert motor.apoyo_estadistico(
        consulta, coincidencias, motor.causas_probables(consulta)) is None


def _coincidencia(ot, causa, pasos=None, torques=None, puntaje=0.4, tipo="informe"):
    from nefer.fixmate.indice import Coincidencia, Fragmento

    meta = {"codigo_ot": ot, "causa_raiz": causa}
    if pasos:
        meta["pasos"] = pasos
    if torques:
        meta["torques"] = torques
    return Coincidencia(Fragmento(id="ot:" + ot, texto="humo negro al subir",
                                  fuente="historial.json", tipo=tipo, metadatos=meta),
                        puntaje, puntaje, puntaje)


PROBABLES = [{"causa": "Filtro de aire colmatado", "probabilidad": 0.9, "casos": 12}]


def test_el_procedimiento_no_se_toma_de_una_averia_distinta():
    """Se respondía una causa y se entregaba el procedimiento de otra.

    «humo negro» recupera igual el informe del filtro de aire y el del
    inyector. Tomando los pasos del primero que tuviera, salía «filtro de
    aire colmatado, según OT-1» con el procedimiento de cambiar un inyector
    debajo —y su par de apriete— atribuido a OT-1. El técnico aprieta a ese
    valor un perno que no es ese, que es justo lo que este paquete promete
    que no pasa.
    """
    from nefer.fixmate.motor import Consulta, redactar_extractivo

    filtro = _coincidencia("OT-1", "Filtro de aire colmatado", puntaje=0.30)
    inyector = _coincidencia("OT-2", "Inyector con retorno excesivo",
                             pasos=["Desmontar el inyector 3",
                                    "Apretar el prisionero a 30 N·m"],
                             torques=["30 N·m"], puntaje=0.40)

    salida = redactar_extractivo(Consulta(texto="humo negro al subir"),
                                 [inyector, filtro], causas_probables=PROBABLES)

    assert salida["causa_raiz_mas_probable"] == "Filtro de aire colmatado"
    assert salida["pasos_recomendados"] == [], "el procedimiento era de otra avería"
    assert salida["torques"] == [], "el par de apriete era de otra avería"
    # Y no se promete un procedimiento que no se entrega.
    assert "el procedimiento salen" not in salida["diagnostico_probabilistico"]


def test_el_procedimiento_de_la_misma_causa_si_se_usa_y_se_cita():
    from nefer.fixmate.motor import Consulta, redactar_extractivo

    filtro = _coincidencia("OT-1", "Filtro de aire colmatado", puntaje=0.30)
    inyector = _coincidencia("OT-2", "Inyector con retorno excesivo",
                             pasos=["Desmontar el inyector 3"], puntaje=0.40)
    otro_filtro = _coincidencia("OT-3", "Filtro de aire colmatado",
                                pasos=["Cambiar el filtro primario"],
                                torques=["12 N·m"], puntaje=0.25)

    salida = redactar_extractivo(Consulta(texto="humo negro al subir"),
                                 [inyector, filtro, otro_filtro],
                                 causas_probables=PROBABLES)

    assert salida["pasos_recomendados"] == ["Cambiar el filtro primario"]
    assert salida["torques"] == ["12 N·m"]
    # De dónde salió se dice: si no, no se sabe a qué se refiere el apriete.
    assert "OT-3" in salida["diagnostico_probabilistico"]
