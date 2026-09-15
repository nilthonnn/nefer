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


# --------------------------------------------------- el redactor con modelo

def test_el_json_del_modelo_se_lee_aunque_venga_con_cercas_de_codigo():
    leido = m.json_del_modelo(
        '```json\n{"diagnostico_probabilistico": "x", "causa_raiz_mas_probable": "y", '
        '"pasos_recomendados": ["p"], "herramientas_y_repuestos": [], "torques": []}\n```')
    assert leido["diagnostico_probabilistico"] == "x"
    assert leido["pasos_recomendados"] == ["p"]


def test_el_json_del_modelo_se_rescata_de_una_frase_amable():
    leido = m.json_del_modelo(
        'Claro, aqui tienes: {"diagnostico_probabilistico": "x", '
        '"causa_raiz_mas_probable": "y"} Espero que sirva.')
    assert leido["causa_raiz_mas_probable"] == "y"
    assert leido["pasos_recomendados"] == []


def test_una_lista_que_llega_como_cadena_se_vuelve_lista():
    leido = m.json_del_modelo('{"diagnostico_probabilistico": "x", '
                              '"pasos_recomendados": "un solo paso"}')
    assert leido["pasos_recomendados"] == ["un solo paso"]


def test_lo_que_no_es_json_no_se_cuela_como_diagnostico():
    with pytest.raises(m.ErrorRedactor):
        m.json_del_modelo("No tengo suficiente informacion para responder.")


def test_un_json_sin_diagnostico_no_vale():
    with pytest.raises(m.ErrorRedactor):
        m.json_del_modelo('{"causa_raiz_mas_probable": "y"}')


def test_el_modelo_redacta_sobre_la_evidencia_recuperada():
    vistos = {}

    def redactor(consulta, coincidencias):
        vistos["contexto"] = m.contexto(coincidencias)
        return {"diagnostico_probabilistico": "Lo redacto el modelo.",
                "causa_raiz_mas_probable": "Inyector.",
                "pasos_recomendados": ["Paso del modelo"],
                "herramientas_y_repuestos": [], "torques": []}

    redactor.nombre = "llm:falso"
    diagnostico = _motor(redactor=redactor).consultar(m.Consulta("humo negro"))

    assert diagnostico.redactor == "llm:falso"
    assert diagnostico.pasos_recomendados == ["Paso del modelo"]
    assert "OT-" in vistos["contexto"], "el modelo tiene que ver los antecedentes"
    # La evidencia la pone el indice, no el modelo: se cita igual.
    assert diagnostico.evidencia_historica


def test_si_el_modelo_no_contesta_la_respuesta_sale_igual():
    def redactor(consulta, coincidencias):
        raise m.ErrorRedactor("el modelo no respondio: timeout")

    diagnostico = _motor(redactor=redactor).consultar(m.Consulta("humo negro"))

    assert diagnostico.redactor == "extractivo"
    assert diagnostico.causa_raiz_mas_probable
    assert any("no respondio" in aviso for aviso in diagnostico.avisos)


def test_el_redactor_con_modelo_no_arranca_sin_clave(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(m.ErrorRedactor, match="OPENAI_API_KEY"):
        m.RedactorLLM()(m.Consulta("humo"), [])


def test_el_diagnostico_se_serializa_entero_a_json():
    diagnostico = _motor().consultar(m.Consulta("humo negro"))
    d = diagnostico.a_dict()
    assert set(d) >= {"diagnostico_probabilistico", "causa_raiz_mas_probable",
                      "pasos_recomendados", "herramientas_y_repuestos", "torques",
                      "evidencia_historica", "confianza", "redactor", "avisos"}
    assert isinstance(d["evidencia_historica"][0], dict)
