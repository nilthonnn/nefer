"""INT-001: el recorrido completo, de punta a punta.

    TPM (ronda del operador)
      → anomalía
        → FixMate (diagnóstico sobre el historial)
          → modo de falla RCM
            → estrategia
              → tarea
                → cierre
                  → historial
                    → aprendizaje

Es la prueba que justifica la arquitectura entera. Si esta cadena se corta en
algún eslabón, los módulos funcionan por separado y el producto no existe.

Y la segunda mitad del archivo prueba lo contrario: que la cadena **se niega
a cerrarse sola** donde no hay evidencia. Un enlace que falta se ve; uno
inventado se suma con los demás y contamina el MTBF por modo.
"""

from __future__ import annotations

import datetime as dt

from nefer.fixmate import (anomalia as _anomalia, aprendizaje, cierre,
                           embeddings, fmeca, indexado, ingesta, tablero)
from nefer.fixmate.activos import Activo
from nefer.fixmate.decision import Decisiones, Respuestas
from nefer.fixmate.indice import Indice
from nefer.fixmate.motor import Consulta, Motor
from nefer.fixmate.plan import falta_por_completar, generar
from nefer.fixmate.rcm import (Analisis, Consecuencia, Efecto, Referencia,
                               completitud)
from nefer.fixmate.tpm import Checklist, Ejecucion, estado

RADIADOR = "TER.SOBRECALENTAMIENTO.RADIADOR"
HOY = dt.date(2026, 3, 2)


def _historial() -> list[dict]:
    """Un historial real: la misma causa escrita de tres formas distintas."""
    return [
        {"codigo_ot": "OT-2025-014", "codigo_equipo": "EX-220",
         "fecha": "2025-11-10", "resumen_falla": "Se recalienta en pendiente",
         "causa_raiz": "Radiador obstruido por tierra",
         "solucion_aplicada": "Lavado del panal a contraflujo",
         "pasos": ["Detener y dejar enfriar", "Lavar el panal a contraflujo"]},
        {"codigo_ot": "OT-2026-003", "codigo_equipo": "EX-220",
         "fecha": "2026-01-15", "resumen_falla": "Temperatura alta con carga",
         "causa_raiz": "radiador tapado con tierra y polvo",
         "solucion_aplicada": "Lavado del panal"},
        {"codigo_ot": "OT-2026-009", "codigo_equipo": "EX-220",
         "fecha": "2026-02-20", "resumen_falla": "Pierde fuerza y humea",
         "causa_raiz": "Filtro de aire colmatado",
         "solucion_aplicada": "Cambio de filtro primario"},
    ]


def _montar(tmp_path):
    """Toda la cadena montada: historial, análisis, decisiones, pauta, índice."""
    ruta_historial = tmp_path / "historial.json"
    import json
    ruta_historial.write_text(
        json.dumps({"informes": _historial()}, ensure_ascii=False),
        encoding="utf-8")

    indice = Indice(embeddings.EmbebedorLocal())
    indice.agregar(ingesta.de_historial({"informes": _historial()},
                                        str(ruta_historial)))

    a = Analisis(Activo("EX-220", "Excavadora hidráulica", "Komatsu", "PC220-8",
                        categoria="excavadora"),
                 contexto="Interior mina, turno continuo, 4.200 m")
    f = a.agregar_funcion("Mantener la temperatura del refrigerante en régimen",
                          "Entre 80 y 95 °C con carga continua al 100 %")
    ff = a.agregar_falla(f.id, "La temperatura supera 95 °C con carga continua")
    m = a.agregar_modo(ff.id, "Radiador obstruido por polvo de mina",
                       codigo_catalogo=RADIADOR,
                       evidencia=(Referencia("historial", "OT-2025-014"),),
                       estado="validado")
    m.efecto = Efecto(local="Sube la temperatura y el ECM reduce potencia",
                      observa_operador="Aguja en rojo, pierde fuerza")
    m.consecuencias = (Consecuencia("produccion", "Se detiene el frente"),)

    d = Decisiones()
    d.registrar(m, Respuestas(detectable=True, viable=True))

    pauta = Checklist("cl-ex220", "EX-220", "Ronda de arranque")
    pauta.agregar("limpiar", "Rejilla del radiador", "Sin costra de tierra",
                  segundos=8, codigo_catalogo=RADIADOR, modo_falla_id=m.id)
    pauta.agregar("inspeccionar", "Visor de nivel", "Entre mín y máx",
                  segundos=5)

    indexado.indexar(indice, indexado.de_analisis(a, d))
    indexado.indexar(indice, [indexado.de_checklist(pauta)])
    return indice, a, d, pauta, ruta_historial


# ═══════════════════════ INT-001: la cadena entera ═══════════════════════

def test_int_001_de_la_ronda_del_operador_al_aprendizaje(tmp_path):
    indice, analisis, decisiones, pauta, ruta_historial = _montar(tmp_path)
    modo = analisis.modos[0]

    # ── 1. El operador hace la ronda y encuentra algo.
    ronda = Ejecucion("ej-1", pauta.id, "EX-220", "J. Quispe",
                      fecha=HOY.isoformat())
    ronda.registrar(pauta.puntos[0].id, "nok",
                    "El panal está tapado con tierra", 9)
    ronda.registrar(pauta.puntos[1].id, "ok", "", 6)
    assert estado(ronda, pauta).completa is True

    # ── 2. La ronda levanta una anomalía, ya enlazada al modo de falla RCM.
    anomalias = _anomalia.desde_ejecucion(ronda, pauta, analisis, hoy=HOY)
    assert len(anomalias) == 1
    an = anomalias[0]
    assert an.codigo_catalogo == RADIADOR
    assert an.modo_falla_id == modo.id

    # ── 3. FixMate diagnostica sobre el historial, y trae el contexto RCM.
    diag = Motor(indice).consultar(
        Consulta(an.descripcion, codigo_equipo="EX-220", limite=5))
    assert diag.causa_raiz_mas_probable
    assert any(x["origen"] == "analisis RCM" for x in diag.contexto_rcm)
    rcm_ctx = next(x for x in diag.contexto_rcm if x["origen"] == "analisis RCM")
    assert rcm_ctx["modo_falla_id"] == modo.id

    # ── 4. El modo de falla trae su estrategia, y la estrategia su tarea.
    assert rcm_ctx["estrategia"] == "cbm"
    plan = generar(analisis, decisiones)
    assert len(plan.tareas) == 1
    tarea = plan.tareas[0]
    assert tarea.modo_falla_id == modo.id
    assert tarea.disparador == "condicion"
    # Y nace incompleta, que es lo correcto: el límite lo pone el OEM.
    assert falta_por_completar(tarea)

    # ── 5. El técnico cierra el caso, con la trazabilidad puesta.
    informe = cierre.desde_diagnostico(
        Consulta(an.descripcion, codigo_equipo="EX-220"), diag,
        "Lavado del panal a contraflujo",
        causa="Radiador obstruido por tierra",
        codigo_equipo="EX-220", anomalia_id=an.id)
    assert informe["modo_falla_id"] == modo.id   # un solo modo en la evidencia

    guardado = cierre.registrar(informe, ruta_historial, indice, hoy=HOY)
    an.cerrar("Lavado del panal", "R. Mamani", hoy=HOY)
    an.codigo_ot = guardado["codigo_ot"]

    # ── 6. El cierre entró al índice: el próximo técnico ya lo encuentra.
    nuevo = next(f for f in indice.fragmentos
                 if f.metadatos.get("codigo_ot") == guardado["codigo_ot"])
    assert nuevo.metadatos["modo_falla_id"] == modo.id
    assert nuevo.metadatos["anomalia_id"] == an.id

    # ── 7. El aprendizaje: lo que se cerró hoy ya es el antecedente de
    #      mañana. Con cuatro casos el clasificador bayesiano NO se entrena
    #      —hacen falta doce— y eso es correcto: declara por qué en vez de
    #      inventar un porcentaje sobre cuatro informes.
    clasificador = aprendizaje.desde_indice(indice)
    assert clasificador.entrenado is False
    assert "casos" in clasificador.motivo
    assert clasificador.predecir("radiador tapado tierra", 2) == []
    # Lo que sí ocurrió, que es el aprendizaje de verdad: el cierre ya se
    # recupera como evidencia para el próximo que pregunte.
    otra = Motor(indice).consultar(Consulta("panal tapado con tierra", limite=5))
    assert guardado["codigo_ot"] in {e.codigo_ot for e in otra.evidencia_historica}

    # ── 8. Y el contraste cuenta que este modo ya ocurrió tres veces.
    contraste = fmeca.contrastar(analisis, indice, aplicar=True)
    assert contraste.frecuencias[modo.id] == 3
    assert modo.frecuencia_historica == 3
    # El filtro de aire sigue sin modo que lo cubra: es la lista de trabajo.
    assert contraste.sin_cubrir == (("ADM.RESTRICCION.FILTRO", 1),)

    # ── 9. El tablero refleja la vuelta completa.
    t = tablero.completo([analisis], {"EX-220": decisiones}, [pauta], [ronda],
                         [an], indice, HOY)
    assert t["rcm"]["modos"] == 1 and t["rcm"]["modos_recurrentes"] == 1
    assert t["rcm"]["analisis_completos"] == 1
    assert t["tpm"]["cumplimiento"] == 1.0
    assert t["tpm"]["anomalias_cerradas"] == 1
    assert t["tpm"]["anomalias_sin_enlazar"] == 0
    assert t["confiabilidad"]["fallas"] == 4


# ═══════════ la cadena se niega a cerrarse donde no hay evidencia ═══════════

def test_la_anomalia_que_el_catalogo_no_codifica_no_llega_a_rcm(tmp_path):
    indice, analisis, _, pauta, _ = _montar(tmp_path)
    sin_codigo = Checklist("cl-x", "EX-220", "Otra ronda")
    sin_codigo.agregar("inspeccionar", "Un sitio cualquiera", "Que esté bien")
    ronda = Ejecucion("ej-9", sin_codigo.id, "EX-220", "J. Q.",
                      fecha=HOY.isoformat())
    ronda.registrar(sin_codigo.puntos[0].id, "nok", "Algo raro", 5)

    an = _anomalia.desde_ejecucion(ronda, sin_codigo, analisis, hoy=HOY)[0]
    assert an.codigo_catalogo == ""
    assert an.enlazada is False
    # Y eso se cuenta, en vez de desaparecer.
    assert tablero.tpm([], [], [an], HOY).anomalias_sin_enlazar == 1


def test_un_diagnostico_con_dos_modos_en_la_evidencia_no_elige_uno(tmp_path):
    # Eso lo sabe el técnico que desarmó. Adivinarlo contaminaría la
    # frecuencia histórica, que es el número que decide la estrategia.
    indice, analisis, decisiones, _, _ = _montar(tmp_path)
    ff = analisis.fallas[0]
    otro = analisis.agregar_modo(ff.id, "Termostato trabado",
                                 codigo_catalogo="TER.SOBRECALENTAMIENTO.TERMOSTATO")
    otro.efecto = Efecto(local="No abre el paso al radiador")
    otro.consecuencias = (Consecuencia("produccion"),)
    decisiones.registrar(otro, Respuestas(detectable=False, intervalo_edad=True,
                                          restaurable=False, viable=True))
    indexado.indexar(indice, [indexado.de_modo_falla(analisis, otro,
                                                     decisiones.get(otro.id))])

    diag = Motor(indice).consultar(Consulta("radiador tierra termostato", limite=5))
    modos = {x["modo_falla_id"] for x in diag.contexto_rcm
             if x["origen"] == "analisis RCM"}
    assert len(modos) == 2
    informe = cierre.desde_diagnostico(Consulta("x"), diag, "Lavado",
                                       causa="Radiador obstruido")
    assert "modo_falla_id" not in informe


def test_un_informe_viejo_sin_trazabilidad_sigue_siendo_valido(tmp_path):
    # Un historial de cinco años no tiene modo_falla_id, y exigirlo
    # convertiría cada informe viejo en inválido.
    indice, analisis, _, _, ruta = _montar(tmp_path)
    viejo = {"resumen_falla": "Pierde potencia", "causa_raiz": "Inyector sucio",
             "solucion_aplicada": "Limpieza de inyectores"}
    guardado = cierre.registrar(viejo, ruta, indice, hoy=HOY)
    fragmento = next(f for f in indice.fragmentos
                     if f.metadatos.get("codigo_ot") == guardado["codigo_ot"])
    assert "modo_falla_id" not in fragmento.metadatos
    # Y el análisis lo lee como «no evaluado», no como un modo inventado.
    contraste = fmeca.contrastar(analisis, indice)
    assert guardado["codigo_ot"] not in str(contraste.frecuencias)


def test_un_analisis_sin_decisiones_no_produce_plan_ni_se_declara_completo(tmp_path):
    _, analisis, _, _, _ = _montar(tmp_path)
    vacias = Decisiones()
    assert generar(analisis, vacias).tareas == []
    assert completitud(analisis, vacias.por_modo).completo is False
