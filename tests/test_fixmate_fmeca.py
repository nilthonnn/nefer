"""La matriz FMECA y el contraste contra el historial real.

Exportar la matriz es mecánico. Lo que vale es `contrastar()`: un FMECA se
escribe en una sala con gente que opina, y después la máquina falla como le
parece. La frecuencia histórica de cada modo no se declara, se cuenta.

Y lo que NO hace es igual de importante: contar no corrige. Un modo que
nunca ocurrió no se borra ni se marca inválido — automatizar eso sería
borrar tareas de seguridad por falta de evidencia, que es justo lo que la
guarda de `decision.py` impide.
"""

from __future__ import annotations

from nefer.fixmate import embeddings, fmeca, ingesta
from nefer.fixmate.activos import Activo, Ubicacion
from nefer.fixmate.criticidad import PRIORIDAD_EJEMPLO
from nefer.fixmate.decision import Decisiones, Respuestas
from nefer.fixmate.indice import Indice
from nefer.fixmate.plan import generar
from nefer.fixmate.rcm import (Analisis, Consecuencia, Efecto, Referencia)

RADIADOR = "TER.SOBRECALENTAMIENTO.RADIADOR"
TERMOSTATO = "TER.SOBRECALENTAMIENTO.TERMOSTATO"
FILTRO = "ADM.RESTRICCION.FILTRO"


def _analisis() -> Analisis:
    a = Analisis(Activo("EX-220", "Excavadora"))
    f = a.agregar_funcion("Mantener la temperatura del refrigerante",
                          "80-95 °C con carga continua")
    ff = a.agregar_falla(f.id, "La temperatura supera 95 °C")
    m = a.agregar_modo(ff.id, "Radiador obstruido", codigo_catalogo=RADIADOR,
                       ubicacion=Ubicacion("termico", "refrigeracion", "radiador"),
                       evidencia=(Referencia("historial", "OT-2025-014",
                                             "Ya ocurrió dos veces"),))
    m.efecto = Efecto(local="Sube la temperatura y el ECM reduce potencia",
                      observa_operador="Aguja en rojo")
    m.consecuencias = (Consecuencia("produccion"),)
    m.evaluar_criticidad(PRIORIDAD_EJEMPLO,
                         {"severidad": 4, "frecuencia": 4, "deteccion": 2})
    oculto = a.agregar_modo(ff.id, "Termostato trabado",
                            codigo_catalogo=TERMOSTATO, evidente=False)
    oculto.consecuencias = (Consecuencia("seguridad"),)
    return a


def _decisiones(a) -> Decisiones:
    d = Decisiones()
    d.registrar(a.modos[0], Respuestas(detectable=True, viable=True))
    d.registrar(a.modos[1], Respuestas(probable=True))
    return d


def _historial() -> Indice:
    informes = [
        # Dos escrituras distintas de la misma causa: el cruce es por código.
        {"codigo_ot": "OT-1", "codigo_equipo": "EX-220", "resumen_falla": "x",
         "causa_raiz": "Radiador obstruido por tierra", "solucion_aplicada": "Lavado"},
        {"codigo_ot": "OT-2", "codigo_equipo": "EX-220", "resumen_falla": "y",
         "causa_raiz": "radiador tapado con tierra", "solucion_aplicada": "Lavado"},
        # Una causa que el análisis no cubre.
        {"codigo_ot": "OT-3", "codigo_equipo": "EX-220", "resumen_falla": "z",
         "causa_raiz": "Filtro de aire colmatado", "solucion_aplicada": "Cambio"},
        # Una que el catálogo no puede codificar.
        {"codigo_ot": "OT-4", "codigo_equipo": "EX-220", "resumen_falla": "w",
         "causa_raiz": "se rompió una cosa rara", "solucion_aplicada": "Arreglo"},
        # De otra máquina: no debe contarse.
        {"codigo_ot": "OT-5", "codigo_equipo": "CA-310", "resumen_falla": "v",
         "causa_raiz": "Radiador obstruido por tierra", "solucion_aplicada": "Lavado"},
    ]
    i = Indice(embeddings.EmbebedorLocal())
    i.agregar(ingesta.de_historial({"informes": informes}, "h.json"))
    return i


# ------------------------------------------------------ exportar la matriz

def test_una_fila_por_modo_de_falla():
    a = _analisis()
    assert len(fmeca.filas(a)) == len(a.modos) == 2


def test_la_fila_recorre_la_cadena_completa_de_izquierda_a_derecha():
    f = fmeca.filas(_analisis())[0]
    assert f["activo"] == "EX-220"
    assert f["sistema"] == "termico" and f["componente"] == "radiador"
    assert f["funcion"].startswith("Mantener") and f["estandar"]
    assert f["falla_funcional"] and f["modo_falla"] and f["causa"]
    assert f["efecto_local"] and f["consecuencias"] == "produccion"
    assert f["criticidad"] == "alta" and "EJEMPLO" in f["metodo_criticidad"]


def test_la_evidencia_y_su_fuente_van_en_columnas_distintas():
    f = fmeca.filas(_analisis())[0]
    assert f["evidencia"] == "Ya ocurrió dos veces"
    assert f["fuente"] == "historial:OT-2025-014"


def test_oculta_se_imprime_como_texto_porque_es_donde_el_lector_la_busca():
    filas = fmeca.filas(_analisis())
    assert filas[0]["evidente"] == "si"
    assert filas[1]["evidente"] == "no (oculta)"


def test_la_frecuencia_historica_sale_vacia_mientras_nadie_haya_contado():
    # Cero diría «se contó y no ocurrió». Lo que pasa es que nadie contó.
    assert fmeca.filas(_analisis())[0]["frecuencia_historica"] == ""


def test_con_decision_y_plan_la_fila_llega_hasta_la_tarea():
    a = _analisis()
    d = _decisiones(a)
    p = generar(a, d)
    p.tareas[0].descripcion = "Inspeccionar el panal a contraluz"
    f = fmeca.filas(a, d, p)[0]
    assert f["estrategia"] == "Mantenimiento segun condicion"
    assert f["motivo_estrategia"]
    assert f["tarea"] == "Inspeccionar el panal a contraluz"
    assert f["disparador"] == "condicion"
    assert f["responsable"] == "predictivo"


def test_el_csv_usa_punto_y_coma_para_que_excel_lo_abra_en_columnas():
    csv = fmeca.a_csv(_analisis())
    cabecera = csv.splitlines()[0]
    assert cabecera.startswith("activo;sistema;")
    assert cabecera.split(";") == list(fmeca.COLUMNAS)
    assert len(csv.splitlines()) == 3        # cabecera + dos modos


def test_el_csv_tambien_acepta_coma_si_hace_falta():
    assert fmeca.a_csv(_analisis(), delimitador=",").splitlines()[0].startswith("activo,")


# ═══════════ contrastar: la frecuencia se cuenta, no se declara ═══════════

def test_dos_escrituras_de_la_misma_causa_cuentan_como_una_sola():
    # El cruce es por código del catálogo, que es la única llave estable:
    # cruzar por texto libre juntaría «colmatado» con «tapado» a veces sí y a
    # veces no.
    c = fmeca.contrastar(_analisis(), _historial())
    assert c.frecuencias["F1.1.1"] == 2


def test_el_historial_de_otra_maquina_no_cuenta():
    c = fmeca.contrastar(_analisis(), _historial())
    assert c.frecuencias["F1.1.1"] == 2      # la quinta OT es de CA-310


def test_los_modos_que_nunca_ocurrieron_salen_a_la_luz_sin_borrarse():
    # Puede ser prevención que funciona, o una fila copiada de otra máquina.
    # El dato no distingue; lo pone a la vista para que alguien mire.
    a = _analisis()
    c = fmeca.contrastar(a, _historial())
    assert c.nunca_ocurrieron == ("F1.1.2",)
    assert len(a.modos) == 2                 # nada se borró
    assert a.modos[1].estado == "propuesto"  # nada se marcó inválido


def test_las_causas_del_historial_sin_modo_que_las_cubra_son_la_lista_de_trabajo():
    c = fmeca.contrastar(_analisis(), _historial())
    assert c.sin_cubrir == ((FILTRO, 1),)


def test_lo_que_el_catalogo_no_pudo_codificar_se_cuenta_aparte():
    # Es la medida honesta de cuánto alcanza el catálogo.
    assert fmeca.contrastar(_analisis(), _historial()).sin_codificar == 1


def test_la_cobertura_es_la_fraccion_codificada_que_el_analisis_cubre():
    # 2 del radiador cubiertos, 1 del filtro no: 2/3.
    c = fmeca.contrastar(_analisis(), _historial())
    assert abs(c.cobertura - 2 / 3) < 1e-9


def test_sin_historial_la_cobertura_es_none_y_no_cero():
    vacio = Indice(embeddings.EmbebedorLocal())
    assert fmeca.contrastar(_analisis(), vacio).cobertura is None


def test_contrastar_no_toca_el_analisis_salvo_que_se_lo_pidan():
    # Medir y modificar son dos permisos distintos.
    a = _analisis()
    fmeca.contrastar(a, _historial())
    assert all(m.frecuencia_historica is None for m in a.modos)
    fmeca.contrastar(a, _historial(), aplicar=True)
    assert a.modos[0].frecuencia_historica == 2
    assert a.modos[1].frecuencia_historica == 0


def test_tras_contrastar_la_matriz_muestra_la_frecuencia_contada():
    a = _analisis()
    fmeca.contrastar(a, _historial(), aplicar=True)
    filas = fmeca.filas(a)
    assert filas[0]["frecuencia_historica"] == 2
    assert filas[1]["frecuencia_historica"] == 0   # ahora sí es un cero medido


def test_un_informe_que_ya_trae_codigo_no_se_reclasifica():
    # Alguien lo decidió; el clasificador no lo pisa.
    informe = {"codigo_ot": "OT-9", "codigo_equipo": "EX-220",
               "resumen_falla": "x", "causa_raiz": "una cosa rara sin pistas",
               "solucion_aplicada": "y", "codigo_catalogo": RADIADOR}
    i = Indice(embeddings.EmbebedorLocal())
    i.agregar(ingesta.de_historial({"informes": [informe]}, "h.json"))
    c = fmeca.contrastar(_analisis(), i)
    assert c.frecuencias["F1.1.1"] == 1
    assert c.sin_codificar == 0
