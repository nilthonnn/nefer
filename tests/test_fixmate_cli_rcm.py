"""Los subcomandos `nefer fixmate rcm` y `nefer fixmate tpm`.

Lo que se prueba sobre todo son los **errores**. Un «KeyError: 'estandar'»
obliga a abrir el código; «la función 1 no declara estándar de desempeño» se
arregla sin preguntarle a nadie. El valor del cargador no es el parseo.
"""

from __future__ import annotations

import json

import pytest

from nefer.fixmate import cargador, cli

ANALISIS = {
    "activo": {"codigo": "EX-220", "nombre": "Excavadora", "modelo": "PC220-8"},
    "contexto": "Interior mina, 4.200 m",
    "funciones": [{
        "descripcion": "Mantener la temperatura del refrigerante",
        "estandar": "80-95 °C con carga continua",
        "fallas": [{
            "descripcion": "La temperatura supera 95 °C",
            "modos": [
                {"descripcion": "Radiador obstruido por polvo",
                 "codigo_catalogo": "TER.SOBRECALENTAMIENTO.RADIADOR",
                 "efecto": {"local": "Sube la temperatura"},
                 "consecuencias": [{"clase": "produccion"}],
                 "decision": {"detectable": True, "viable": True}},
                {"descripcion": "Válvula de alivio pegada", "evidente": False,
                 "efecto": {"local": "No alivia; nada lo indica"},
                 "consecuencias": [{"clase": "seguridad"}],
                 "decision": {"probable": False}},
            ]}]}],
}

PAUTA = {
    "id": "cl-ex220", "activo_codigo": "EX-220", "nombre": "Ronda de arranque",
    "frecuencia": "diaria",
    "puntos": [
        {"clase": "limpiar", "punto": "Rejilla del radiador",
         "criterio": "Sin costra de tierra", "segundos": 8,
         "codigo_catalogo": "TER.SOBRECALENTAMIENTO.RADIADOR",
         "modo_falla_id": "F1.1.1"},
        {"clase": "inspeccionar", "punto": "Guarda del acople",
         "criterio": "Puesta y con sus pernos", "segundos": 5,
         "alcance_operador": False},
    ],
}


def _escribir(tmp_path, nombre, datos):
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return str(ruta)


def _correr(argv, capsys) -> tuple[int, str]:
    codigo = cli.main(argv) if hasattr(cli, "main") else _via_nefer(argv)
    return codigo, capsys.readouterr().out


def _via_nefer(argv):
    from nefer.cli import main as nefer_main
    return nefer_main(["fixmate", *argv])


# ------------------------------------------- el cargador y sus errores

def test_el_analisis_se_carga_entero_desde_json(tmp_path):
    a = cargador.analisis(_escribir(tmp_path, "a.json", ANALISIS))
    assert a.activo.codigo == "EX-220"
    assert len(a.funciones) == 1 and len(a.modos) == 2
    # Y hereda del catálogo sin que el JSON lo repita.
    assert a.modos[0].ubicacion.sistema == "termico"
    assert a.modos[0].mecanismo == "Obstruccion"


def test_las_llaves_se_reconstruyen_por_anidamiento(tmp_path):
    # En un JSON escrito a mano, anidar es más fácil de no equivocar que
    # repetir ids.
    a = cargador.analisis(_escribir(tmp_path, "a.json", ANALISIS))
    assert a.modos[0].id == "F1.1.1" and a.modos[1].id == "F1.1.2"
    assert a.fallas[0].funcion_id == a.funciones[0].id


def test_el_error_dice_que_funcion_y_que_le_falta(tmp_path):
    malo = json.loads(json.dumps(ANALISIS))
    malo["funciones"][0]["estandar"] = ""
    ruta = _escribir(tmp_path, "malo.json", malo)
    with pytest.raises(cargador.ErrorCargador) as exc:
        cargador.analisis(ruta)
    assert "funcion 1" in str(exc.value)
    assert "estandar de desempeño" in str(exc.value)


def test_el_error_llega_hasta_el_modo_concreto(tmp_path):
    malo = json.loads(json.dumps(ANALISIS))
    malo["funciones"][0]["fallas"][0]["modos"][0]["consecuencias"] = ["oculta"]
    with pytest.raises(cargador.ErrorCargador) as exc:
        cargador.analisis(_escribir(tmp_path, "malo.json", malo))
    assert "modo 1" in str(exc.value)
    assert "evidente=False" in str(exc.value)


def test_un_json_que_no_es_json_lo_dice_sin_traza(tmp_path):
    ruta = tmp_path / "roto.json"
    ruta.write_text("{esto no es json", encoding="utf-8")
    with pytest.raises(cargador.ErrorCargador, match="no es JSON legible"):
        cargador.analisis(str(ruta))


def test_un_archivo_que_no_existe_lo_dice(tmp_path):
    with pytest.raises(cargador.ErrorCargador, match="no existe"):
        cargador.analisis(str(tmp_path / "fantasma.json"))


def test_una_pregunta_inventada_en_la_decision_se_rechaza(tmp_path):
    malo = json.loads(json.dumps(ANALISIS))
    malo["funciones"][0]["fallas"][0]["modos"][0]["decision"] = {"barato": True}
    with pytest.raises(cargador.ErrorCargador) as exc:
        cargador.analisis_y_decisiones(_escribir(tmp_path, "m.json", malo))
    assert "no es una pregunta del arbol" in str(exc.value)


def test_un_modo_sin_decision_simplemente_no_se_decide(tmp_path):
    # No se le inventa una respuesta conservadora para que el análisis
    # parezca completo: la Q6 existe para denunciar eso.
    sin = json.loads(json.dumps(ANALISIS))
    del sin["funciones"][0]["fallas"][0]["modos"][1]["decision"]
    a, d = cargador.analisis_y_decisiones(_escribir(tmp_path, "s.json", sin))
    assert len(d) == 1
    from nefer.fixmate.rcm import completitud
    assert completitud(a, d.por_modo).completo is False


def test_un_metodo_de_criticidad_desconocido_se_rechaza_con_los_que_hay(tmp_path):
    malo = json.loads(json.dumps(ANALISIS))
    malo["metodo_criticidad"] = "la matriz del jefe"
    with pytest.raises(cargador.ErrorCargador) as exc:
        cargador.analisis(_escribir(tmp_path, "m.json", malo))
    assert "EJEMPLO" in str(exc.value)


# ---------------------------------------------------- `rcm analizar`

def test_rcm_analizar_sale_0_cuando_las_siete_estan_contestadas(tmp_path, capsys):
    codigo, salida = _correr(["rcm", "analizar",
                              _escribir(tmp_path, "a.json", ANALISIS)], capsys)
    assert codigo == 0
    assert "Las siete preguntas de JA1011 estan contestadas" in salida


def test_rcm_analizar_sale_2_cuando_falta_algo_y_dice_que(tmp_path, capsys):
    incompleto = json.loads(json.dumps(ANALISIS))
    for m in incompleto["funciones"][0]["fallas"][0]["modos"]:
        m.pop("decision", None)
    codigo, salida = _correr(["rcm", "analizar",
                              _escribir(tmp_path, "i.json", incompleto)], capsys)
    assert codigo == 2
    assert "Q6" in salida and "no tiene decision de estrategia" in salida


def test_rcm_analizar_denuncia_el_rediseno_obligatorio(tmp_path, capsys):
    _, salida = _correr(["rcm", "analizar",
                         _escribir(tmp_path, "a.json", ANALISIS)], capsys)
    assert "rediseño OBLIGATORIO" in salida
    assert "1 ocultos" in salida


def test_rcm_analizar_con_indexar_mete_los_modos_al_indice(tmp_path, capsys):
    from nefer.fixmate import embeddings
    from nefer.fixmate.indice import Indice

    indice = str(tmp_path / "i.json")
    Indice(embeddings.EmbebedorLocal()).guardar(indice)
    codigo, salida = _correr(["-i", indice, "rcm", "analizar",
                              _escribir(tmp_path, "a.json", ANALISIS),
                              "--indexar"], capsys)
    assert codigo == 0 and "2 modos de falla indexados" in salida
    assert len(Indice.cargar(indice)) == 2


# ------------------------------------------------------ `rcm matriz`

def test_rcm_matriz_escribe_un_csv_con_una_fila_por_modo(tmp_path, capsys):
    salida_csv = tmp_path / "fmeca.csv"
    codigo, _ = _correr(["rcm", "matriz", _escribir(tmp_path, "a.json", ANALISIS),
                         "-o", str(salida_csv)], capsys)
    assert codigo == 0
    lineas = salida_csv.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 3
    assert lineas[0].startswith("activo;sistema;")
    assert "no (oculta)" in lineas[2]


# ------------------------------------------------------ `rcm tareas`

def test_rcm_tareas_muestra_lo_que_le_falta_a_cada_tarea(tmp_path, capsys):
    codigo, salida = _correr(["rcm", "tareas",
                              _escribir(tmp_path, "a.json", ANALISIS)], capsys)
    assert codigo == 0
    assert "2 tareas · 0 listas · 2 en borrador" in salida
    assert "falta: que parametro se mide" in salida


# ------------------------------------------------- `tpm checklist`

def test_tpm_checklist_lista_los_puntos_y_marca_los_del_tecnico(tmp_path, capsys):
    codigo, salida = _correr(["tpm", "checklist",
                              _escribir(tmp_path, "p.json", PAUTA)], capsys)
    assert codigo == 0
    assert "presupuesto 13 s" in salida
    assert "[TECNICO]" in salida      # el punto fuera del alcance del operador


# -------------------------------------------------- `tpm ejecutar`

def test_tpm_ejecutar_levanta_la_anomalia_y_la_enlaza_con_rcm(tmp_path, capsys):
    pauta = _escribir(tmp_path, "p.json", PAUTA)
    analisis = _escribir(tmp_path, "a.json", ANALISIS)
    ejecucion = _escribir(tmp_path, "e.json", {
        "id": "ej-1", "checklist_id": "cl-ex220", "activo_codigo": "EX-220",
        "operador": "J. Quispe", "fecha": "2026-03-02",
        "items": [
            {"punto_id": "cl-ex220.1", "resultado": "nok",
             "observacion": "Radiador obstruido por tierra", "segundos": 9},
            {"punto_id": "cl-ex220.2", "resultado": "ok", "segundos": 6},
        ]})
    codigo, salida = _correr(["tpm", "ejecutar", ejecucion, "-p", pauta,
                              "--rcm", analisis], capsys)
    assert codigo == 0
    assert "Ronda COMPLETA" in salida
    assert "modo F1.1.1" in salida


def test_tpm_ejecutar_avisa_cuando_la_ronda_quedo_incompleta(tmp_path, capsys):
    pauta = _escribir(tmp_path, "p.json", PAUTA)
    ejecucion = _escribir(tmp_path, "e.json", {
        "id": "ej-2", "checklist_id": "cl-ex220", "activo_codigo": "EX-220",
        "operador": "J. Quispe",
        "items": [
            {"punto_id": "cl-ex220.1", "resultado": "ok", "segundos": 8},
            {"punto_id": "cl-ex220.2", "resultado": "sin_acceso",
             "observacion": "Guarda soldada", "segundos": 3},
        ]})
    codigo, salida = _correr(["tpm", "ejecutar", ejecucion, "-p", pauta], capsys)
    assert codigo == 0
    assert "Ronda INCOMPLETA" in salida
    assert "no cuenta como visto" in salida
    assert "Sin anomalias" in salida     # sin_acceso no genera anomalía
