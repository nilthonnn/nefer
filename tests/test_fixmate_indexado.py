"""RCM y TPM como fragmentos: la integración del §6, sin escribir integración.

La prueba que justifica todo el diseño es `test_una_consulta_de_campo_recupera_el_analisis_rcm`:
el motor de diagnóstico encuentra un modo de falla RCM **sin que se le haya
tocado una línea**, porque el análisis ya es evidencia como cualquier otra.

Y la que protege el diseño es `test_un_fragmento_rcm_no_aporta_pasos`: un
análisis RCM tiene estrategia, no procedimiento. Si llevara pasos, el motor
podría responder «cambie el radiador» citando un análisis que nunca dijo
cómo hacerlo.
"""

from __future__ import annotations

from nefer.fixmate import embeddings, indexado, ingesta
from nefer.fixmate.activos import Activo
from nefer.fixmate.anomalia import Anomalia
from nefer.fixmate.decision import Decisiones, Respuestas
from nefer.fixmate.indice import Indice
from nefer.fixmate.motor import Consulta, Motor, contexto_rcm
from nefer.fixmate.rcm import Analisis, Consecuencia, Efecto
from nefer.fixmate.tpm import Checklist

CODIGO_RADIADOR = "TER.SOBRECALENTAMIENTO.RADIADOR"


def _analisis() -> tuple[Analisis, Decisiones]:
    a = Analisis(Activo("EX-220", "Excavadora", categoria="excavadora"),
                 contexto="Interior mina, 4.200 m")
    f = a.agregar_funcion("Mantener la temperatura del refrigerante",
                          "80-95 °C con carga continua")
    ff = a.agregar_falla(f.id, "La temperatura supera 95 °C")
    m = a.agregar_modo(ff.id, "Radiador obstruido por polvo",
                       codigo_catalogo=CODIGO_RADIADOR)
    m.efecto = Efecto(local="Sube la temperatura y el ECM reduce potencia",
                      observa_operador="Aguja en rojo, pierde fuerza")
    m.consecuencias = (Consecuencia("produccion", "Se detiene el frente"),)
    d = Decisiones()
    d.registrar(m, Respuestas(detectable=True, viable=True))
    return a, d


def _pauta() -> Checklist:
    c = Checklist("cl-ex220", "EX-220", "Ronda de arranque")
    c.agregar("limpiar", "Rejilla del radiador", "Sin costra de tierra",
              codigo_catalogo=CODIGO_RADIADOR, modo_falla_id="F1.1.1")
    return c


def _indice(*grupos) -> Indice:
    i = Indice(embeddings.EmbebedorLocal())
    for g in grupos:
        i.agregar(list(g))
    return i


# ------------------------------- el fragmento RCM y lo que lleva dentro

def test_un_modo_de_falla_se_convierte_en_un_fragmento():
    a, d = _analisis()
    frs = indexado.de_analisis(a, d)
    assert len(frs) == 1                     # uno por modo, no uno por análisis
    f = frs[0]
    assert f.tipo == "rcm"
    assert f.id == "rcm:EX-220:F1.1.1"


def test_la_unidad_es_el_modo_y_no_el_analisis_entero():
    # Un análisis completo en un solo fragmento recuperaría la bomba entera
    # cuando se pregunta por el radiador.
    a, d = _analisis()
    a.agregar_modo("F1.1", "Termostato trabado")
    assert len(indexado.de_analisis(a, d)) == 2


def test_el_fragmento_usa_las_mismas_claves_que_los_informes():
    # Así los filtros y las preferencias del motor funcionan sin tocarlo.
    f = indexado.de_analisis(*_analisis())[0]
    assert f.metadatos["codigo_equipo"] == "EX-220"
    assert f.metadatos["categoria"] == "excavadora"
    assert f.metadatos["causa_raiz"]
    assert f.metadatos["resumen_falla"]


def test_un_fragmento_rcm_no_aporta_pasos():
    # Un análisis RCM tiene estrategia, no procedimiento. Si llevara pasos,
    # el motor podría responder «cambie el radiador» citando un análisis que
    # nunca dijo cómo.
    f = indexado.de_analisis(*_analisis())[0]
    assert "pasos" not in f.metadatos


def test_el_fragmento_lleva_la_estrategia_cuando_hay_decision():
    f = indexado.de_analisis(*_analisis())[0]
    assert f.metadatos["estrategia"] == "cbm"
    assert "Motivo de la estrategia" in f.texto


def test_sin_decision_el_fragmento_sigue_siendo_valido():
    a, _ = _analisis()
    f = indexado.de_analisis(a)[0]
    assert "estrategia" not in f.metadatos
    assert f.metadatos["modo_falla_id"] == "F1.1.1"


def test_el_texto_lleva_el_vocabulario_de_campo_del_catalogo():
    # Sin las pistas, un análisis redactado en lenguaje de norma puntuaba
    # 0,000 contra una consulta real.
    f = indexado.de_analisis(*_analisis())[0]
    assert "panal" in f.texto and "tierra" in f.texto


def test_un_modo_sin_codigo_de_catalogo_se_indexa_igual_sin_pistas():
    a = Analisis(Activo("EX-220", "Excavadora"))
    fn = a.agregar_funcion("Refrigerar", "80-95 °C")
    ff = a.agregar_falla(fn.id, "Sobrecalienta")
    a.agregar_modo(ff.id, "Panal deformado por un golpe de roca")
    f = indexado.de_analisis(a)[0]
    assert "Como se describe en campo" not in f.texto
    assert "Panal deformado" in f.texto


# ═══════════ la integración del §6: el motor no se tocó ═══════════

def test_una_consulta_de_campo_recupera_el_analisis_rcm():
    idx = _indice(indexado.de_analisis(*_analisis()))
    r = Motor(idx).consultar(Consulta("radiador tapado con tierra"))
    assert r.evidencia_historica[0].tipo == "rcm"
    assert r.contexto_rcm
    assert r.contexto_rcm[0]["origen"] == "analisis RCM"
    assert r.contexto_rcm[0]["estrategia_rotulo"] == "Mantenimiento segun condicion"


def test_el_procedimiento_sigue_saliendo_de_los_informes_y_no_del_rcm():
    informe = {"codigo_ot": "OT-1", "codigo_equipo": "EX-220",
               "resumen_falla": "Radiador tapado con tierra",
               "causa_raiz": "Radiador obstruido por tierra",
               "solucion_aplicada": "Lavado del panal",
               "pasos": ["Detener y enfriar", "Lavar el panal a contraflujo"]}
    idx = _indice(ingesta.de_historial({"informes": [informe]}, "h.json"),
                  indexado.de_analisis(*_analisis()))
    r = Motor(idx).consultar(Consulta("radiador tapado con tierra", limite=5))
    assert r.pasos_recomendados == ["Detener y enfriar",
                                    "Lavar el panal a contraflujo"]


def test_sin_analisis_cargado_el_contexto_esta_vacio_y_no_falta():
    # El campo está y dice que no hay, en vez de faltar y hacer creer que la
    # pregunta no se hizo.
    informe = {"codigo_ot": "OT-1", "resumen_falla": "Radiador tapado",
               "causa_raiz": "Radiador obstruido", "solucion_aplicada": "Lavado"}
    idx = _indice(ingesta.de_historial({"informes": [informe]}, "h.json"))
    r = Motor(idx).consultar(Consulta("radiador tapado"))
    assert r.contexto_rcm == []
    assert "contexto_rcm" in r.a_dict()


def test_cada_entrada_del_contexto_declara_su_origen():
    # Mezclar un modo de falla con un procedimiento de manual sin decir cuál
    # es cuál es lo que la regla de evidencia prohíbe.
    a, d = _analisis()
    anomalia = Anomalia("an-1", "EX-220", "Panal tapado con tierra",
                        codigo_catalogo=CODIGO_RADIADOR, modo_falla_id="F1.1.1")
    idx = _indice(indexado.de_analisis(a, d), [indexado.de_checklist(_pauta())],
                  [indexado.de_anomalia(anomalia)])
    cs = idx.buscar("radiador tierra panal", limite=5, umbral=0.0)
    origenes = {x["origen"] for x in contexto_rcm(cs)}
    assert origenes == {"analisis RCM", "pauta de mantenimiento autonomo",
                        "anomalia TPM"}


# ------------------------------------------ pauta y anomalía indexadas

def test_la_pauta_se_indexa_con_sus_puntos_y_sus_llaves():
    f = indexado.de_checklist(_pauta())
    assert f.tipo == "tpm"
    assert "Rejilla del radiador" in f.texto
    assert f.metadatos["codigos_catalogo"] == [CODIGO_RADIADOR]
    assert f.metadatos["modos_falla"] == ["F1.1.1"]


def test_una_anomalia_abierta_tambien_se_indexa():
    # Es justamente la que conviene que aparezca: puede ser la misma que ya
    # está reportada.
    a = Anomalia("an-1", "EX-220", "Panal tapado con tierra")
    f = indexado.de_anomalia(a)
    assert f.tipo == "anomalia"
    assert f.metadatos["abierta"] is True


def test_la_anomalia_no_declara_causa_raiz():
    # Una anomalía es lo que se observó, no una causa confirmada. Si la
    # declarara, entraría al clasificador bayesiano como si lo fuera.
    f = indexado.de_anomalia(Anomalia("an-1", "EX-220", "Panal tapado"))
    assert f.metadatos["causa_raiz"] == ""
