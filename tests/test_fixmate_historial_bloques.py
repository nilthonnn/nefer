"""El historial tal como lo exporta el sistema del taller, no como uno querría.

Todo lo demás de FixMate daba por hecho un historial de una fila por orden con
una columna de causa raíz. Un historial de verdad —trece años de un manlift
articulado— no tiene causa raíz en ninguna parte: tiene la cabecera repetida
cuarenta veces, el material despachado con la fecha delante y el nombre del
técnico detrás, y nadie que escribiera nunca por qué falló.

Así que el requisito era el equivocado, no el archivo. Aquí se prueba el lector
que lee lo que de verdad llega, y sobre todo las dos formas de perder datos en
silencio: tirar una orden porque no trae repuestos, y tragarse una cabecera
interna como si fuera una pieza.
"""

from __future__ import annotations

import pytest

from nefer.fixmate import historial_bloques as hb

# Un bloque como los que trae el export, con sus trampas:
#  - la cabecera repetida (dos bloques)
#  - una cabecera interna «SUMINISTROS | CODIGO» en medio del bloque
#  - una línea de relleno «-  -»
#  - el horómetro con separador de millares
#  - «EQUIPO OPERATIVO» y su errata, que no son hallazgos
HOJA = [
    [None, None, "HISTORIAL EQUIPO  :   MLAD041-02", None, None, None, None,
     None, None, None, None],
    [None, "ORDEN TRABAJO", "TRABAJOS REALIZADOS", "HOROMETRO", "FECHA", "MP",
     "CANTIDAD", "SUMINISTROS", "CODIGO", "SERVICIOS TERCEROS", "OBSERVACIONES"],
    [None, "031-0005135", None, "9,753.20", "24/02/2024", None, "1.00",
     " 15/07/2024 - KIT DE SELLO DE CILINDRO  -  PEREZ GOMEZ, JUAN",
     "KS-CD-MLAD", "MANTENIMIENTO DE CILINDRO PENDULAR", "EQUIPO OPERATIVO"],
    [None, None, None, None, None, None, "2.00", "SUMINISTROS", "CODIGO",
     None, None],
    [None, None, None, None, None, None, "2.00",
     " 18/06/2024 - SPRAY AFLOJATODO 10 ONZ - VISTONY  -  PEREZ GOMEZ, JUAN",
     "006715", None, None],
    [None, "ORDEN TRABAJO", "TRABAJOS REALIZADOS", "HOROMETRO", "FECHA", "MP",
     "CANTIDAD", "SUMINISTROS", "CODIGO", "SERVICIOS TERCEROS", "OBSERVACIONES"],
    [None, "030-0000830", None, "4,854.00", "23/01/2017", None, "1.00",
     "-  -", None, None, "EQUIOPO OPERATIVO"],
]


@pytest.fixture(scope="module")
def informes():
    return hb.leer_filas(HOJA, modelo="HAULOTTE HA41PX")


def test_reconoce_el_formato_por_la_cabecera_repetida():
    assert hb.es_por_bloques(HOJA)


def test_una_hoja_normal_no_pasa_por_historial_por_bloques():
    """Con una sola cabecera arriba es una tabla, y tratarla como bloques le
    perdería todas las filas menos la primera."""
    normal = [["N° OT", "Fecha", "Equipo", "Falla", "Causa raiz"],
              ["OT-1", "2026-01-01", "EX336-01", "gotea", "sello vencido"],
              ["OT-2", "2026-01-02", "EX336-01", "no arranca", "bornes"]]
    assert not hb.es_por_bloques(normal)


def test_cada_bloque_es_una_orden(informes):
    assert [i["codigo_ot"] for i in informes] == ["031-0005135", "030-0000830"]


def test_el_equipo_sale_del_titulo_de_la_hoja(informes):
    assert all(i["codigo_equipo"] == "MLAD041-02" for i in informes)
    assert all(i["modelo_equipo"] == "HAULOTTE HA41PX" for i in informes)


# ------------------------------------------- las dos formas de perder datos

def test_la_cabecera_interna_no_entra_como_repuesto(informes):
    """El export repite «SUMINISTROS | CODIGO» dentro del bloque. Colándose,
    aparecía como la pieza más comprada del taller."""
    piezas = informes[0]["repuestos"]
    assert not any(p.upper().startswith("SUMINISTROS") for p in piezas), piezas


def test_el_relleno_de_guiones_no_entra_como_repuesto(informes):
    for informe in informes:
        for pieza in informe.get("repuestos", []):
            assert set(pieza) - set(" -.·_"), f"«{pieza}» es relleno"


def test_una_orden_sin_material_no_se_tira(informes):
    """No está vacía: su fecha y su horómetro son una lectura, y de las
    lecturas sale el ritmo de uso y el próximo servicio. Tirarla perdía, en el
    archivo real, dos lecturas de un historial de trece años."""
    segunda = informes[1]
    assert segunda["fecha"] == "23/01/2017"
    assert segunda["horometro"] == "4,854.00"
    assert segunda["otros_campos"]["Alcance"] == "revision sin cambio de material"


# --------------------------------------- lo que venía pegado y no debía

@pytest.mark.parametrize("linea, pieza, fecha, quien", [
    (" 22/06/2026 - SOLDADURA SUPERCITO 7018  -  CARDENAS OCHOA, KEVIN",
     "SOLDADURA SUPERCITO 7018", "22/06/2026", "CARDENAS OCHOA, KEVIN"),
    # Dos fechas: el mismo material despachado dos veces.
    (" 15/07/2026, 25/06/2026 - KIT DE SELLO  -  TERAN REYES , GUILLERMO",
     "KIT DE SELLO", "15/07/2026, 25/06/2026", "TERAN REYES , GUILLERMO"),
    # «- VISTONY» con un solo espacio es la marca, no quien lo instaló.
    ("SPRAY AFLOJATODO 10 ONZ - VISTONY",
     "SPRAY AFLOJATODO 10 ONZ - VISTONY", "", ""),
    ("ACEITE HIDRAULICO TELLUS S2 MX 46",
     "ACEITE HIDRAULICO TELLUS S2 MX 46", "", ""),
])
def test_la_pieza_la_fecha_y_quien_se_separan(linea, pieza, fecha, quien):
    """Con el nombre pegado, «ACEITE 15W40 RIMULA R4X SHELL» eran seis
    repuestos distintos en vez de uno, uno por técnico que lo pidió."""
    assert hb.partir_linea(linea) == (pieza, fecha, quien)


def test_el_tecnico_se_guarda_aparte_y_no_se_pierde(informes):
    assert informes[0]["otros_campos"]["Tecnicos"] == "PEREZ GOMEZ, JUAN"


# ------------------------------------------- lo que no se sabe no se rellena

def test_la_causa_raiz_no_se_inventa(informes):
    """Nadie la escribió. Deducirla de lo que se cambió la convertiría en un
    dato que no es, y `cobertura()` dejaría de poder decir cuánto falta."""
    assert not any(i.get("causa_raiz") for i in informes)


def test_la_frase_hecha_del_taller_no_es_una_falla_reportada(informes):
    """«EQUIPO OPERATIVO» no es un hallazgo, ni con la errata que trae la
    plantilla de verdad («EQUIOPO»). Perseguir erratas una por una no acaba."""
    assert not any(i.get("resumen_falla") for i in informes)


def test_lo_que_hizo_un_tercero_si_es_lo_que_se_hizo(informes):
    assert informes[0]["solucion_aplicada"] == "MANTENIMIENTO DE CILINDRO PENDULAR"


def test_el_alcance_dice_el_tamano_de_la_intervencion(informes):
    """Una orden de noventa líneas no fue una reparación, fue una
    reconstrucción. Es la señal más clara que trae el archivo."""
    assert informes[0]["otros_campos"]["Alcance"] == (
        "2 lineas de material, 1 servicios de terceros")


# ------------------------------------------------ y entra por la vía normal

def test_el_excel_por_bloques_se_indexa_sin_banderas(tmp_path):
    """`nefer fixmate indexar` tiene que reconocerlo solo. Antes caía en
    «manual» y se indexaba como prosa, que es igual que no indexarlo."""
    openpyxl = pytest.importorskip("openpyxl")
    from nefer.fixmate import ingesta

    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "HISTORIAL"
    for fila in HOJA:
        hoja.append(fila)
    ruta = tmp_path / "historial-MLAD041-02.xlsx"
    libro.save(ruta)

    fragmentos = ingesta.de_archivo(ruta)
    assert len(fragmentos) == 2
    assert all(f.tipo == "informe" for f in fragmentos)
    assert {f.metadatos["codigo_ot"] for f in fragmentos} == {
        "031-0005135", "030-0000830"}
    # Y el horómetro llega entero al índice, con su separador de millares.
    uno = next(f for f in fragmentos if f.metadatos["codigo_ot"] == "031-0005135")
    assert uno.metadatos["horometro"] == "9,753.20"


# ---------------------------------------- los seis documentos del export

# El export del taller no trae un tipo de documento: trae seis, cada uno con
# su cabecera repetida. Este lector conocía dos. Medido sobre el historial de
# trece años de un manlift real: de 245 bloques leía 40 y descartaba 205 en
# silencio —el 84 %—, y entre lo descartado los 114 INFORME TECNICO CAMPO,
# que es el documento donde el técnico escribe qué encontró.
#
# No dio error en ninguna parte. El síntoma era la app diciendo «40
# fragmentos, 0 casos con causa confirmada» sobre un archivo de 1.674 filas,
# y contestando una consulta de ese manlift con el manual de otra máquina.
SEIS_DOCUMENTOS = [
    ["", "", "HISTORIAL EQUIPO  :   MLAD041-02"],
    ["", "ORDEN TRABAJO", "TRABAJOS REALIZADOS", "HOROMETRO", "FECHA", "MP",
     "CANTIDAD", "SUMINISTROS", "CODIGO", "SERVICIOS TERCEROS", "OBSERVACIONES"],
    ["", "031-0005135", "", "9,753.20", "24/02/2024", "", "1.00",
     "KIT DE SELLO DE CILINDRO", "KS-CD-MLAD",
     "MANTENIMIENTO DE CILINDRO PENDULAR", "EQUIPO OPERATIVO"],

    ["", "INFORME TECNICO CAMPO", "CLIENTE / OBRA", "HOROMETRO", "FECHA", "MP",
     "CANTIDAD", "SUMINISTROS", "CODIGO", "OBSERVACIONES"],
    ["", "031-0024384", "CONSTRUCTORA DEL SUR S.A. / U.M. EL EJEMPLO",
     "10,891.00", "02/02/2026", "", "3.00", "ACEITE HIDRAULICO TELLUS",
     "TELLUS 46", "RETENES Y SELLOS DE CILINDROS EN MAL ESTADO"],

    ["", "HOJA DE SERVICIO", "TRABAJOS REALIZADOS", "HOROMETRO", "FECHA"],
    ["", "032-0001234",
     "16/10/2024 - PINTADO GENERAL DE CANASTO TECNICO : PICHA CALCINA, ANDRE",
     "10,900.00", "16/10/2024"],

    ["", "ACTA DE RECEPCION", "CLIENTE / OBRA", "HOROMETRO", "FECHA"],
    ["", "032-0001886", "CONSTRUCTORA DEL SUR S.A. / U.M. EL EJEMPLO",
     "10,894.40", "25/02/2026"],

    ["", "GUIA DE REMISION", "CLIENTE / OBRA", "HOROMETRO", "FECHA"],
    ["", "001-0009999", "CONSTRUCTORA DEL SUR S.A. / U.M. EL EJEMPLO",
     "10,894.40", "26/02/2026"],

    ["", "CONTROL_EXTRACCIONES", "ESTADO", "HOROMETRO", "FECHA", "MP",
     "CANTIDAD", "SUMINISTROS", "CODIGO"],
    ["", "001-9000467", "CERRADO", "10,894.40", "19/05/2026", "", "1.00",
     "SENSOR INDUCTIVO DE CANASTILLA", "SIC-01"],
]


@pytest.fixture
def seis():
    return {i["codigo_ot"]: i
            for i in hb.leer_filas(SEIS_DOCUMENTOS)}


def test_los_seis_documentos_se_leen_y_se_distinguen(seis):
    """Leerlos todos no basta: hay que saber de cuál salió cada informe."""
    assert {ot: i["otros_campos"]["Documento"] for ot, i in seis.items()} == {
        "031-0005135": "orden de trabajo",
        "031-0024384": "informe tecnico de campo",
        "032-0001234": "hoja de servicio",
        "032-0001886": "acta de recepcion",
        "001-0009999": "guia de remision",
        "001-9000467": "control de extracciones",
    }


def test_el_informe_tecnico_de_campo_trae_la_falla(seis):
    """Era el documento más numeroso del archivo real, y el que se perdía."""
    assert seis["031-0024384"]["resumen_falla"] == \
        "RETENES Y SELLOS DE CILINDROS EN MAL ESTADO"


def test_el_cliente_y_la_obra_no_entran_en_el_sintoma(seis):
    """Ocupan, en los documentos de logística, la misma columna que
    «TRABAJOS REALIZADOS» en una orden. Sin nombrarla, el nombre del cliente
    se indexa como si fuera un síntoma de la máquina."""
    campo = seis["031-0024384"]
    assert "CONSTRUCTORA" not in campo.get("resumen_falla", "")
    assert campo["otros_campos"]["Cliente / obra"].startswith("CONSTRUCTORA")


def test_el_nombre_del_tecnico_sale_del_sintoma(seis):
    """«... TECNICO : PICHA CALCINA, ANDRE» venía pegado al hallazgo.

    Medido en el archivo real: 27 de 83 hallazgos lo llevaban dentro. Un
    nombre no es un síntoma —no ayuda a recuperar nada— y es dato personal
    de la gente del taller.
    """
    hoja = seis["032-0001234"]
    assert hoja["resumen_falla"] == "PINTADO GENERAL DE CANASTO"
    assert hoja["otros_campos"]["Tecnicos"] == "PICHA CALCINA, ANDRE"


def test_el_estado_del_documento_no_es_una_falla(seis):
    """«CERRADO» estaba mapeado como «trabajos realizados»: habría entrado
    como descripción de la falla, y el historial se habría llenado de averías
    llamadas «cerrado»."""
    control = seis["001-9000467"]
    assert "resumen_falla" not in control
    assert control["otros_campos"]["Estado"] == "CERRADO"


def test_la_logistica_no_finge_ser_una_averia_pero_conserva_su_lectura(seis):
    """Un acta de recepción es la máquina llegando, no una falla.

    Contarla como avería diría «245 fallas» de un equipo de alquiler que se
    despacha varias veces al año sin que se le rompa nada. Pero su fecha y su
    horómetro son una LECTURA, y de las lecturas salen el ritmo de uso y el
    próximo servicio: por eso se leen en vez de descartarse.
    """
    for ot in ("032-0001886", "001-0009999"):
        assert "resumen_falla" not in seis[ot]
        assert seis[ot]["fecha"] and seis[ot]["horometro"]


def test_el_tablero_no_cuenta_la_logistica_como_falla():
    """El efecto en el indicador, que es donde se habría notado el daño."""
    from nefer.fixmate import embeddings, ingesta, tablero
    from nefer.fixmate.indice import Indice

    informes = hb.leer_filas(SEIS_DOCUMENTOS)
    i = Indice(embeddings.EmbebedorLocal())
    i.agregar(ingesta.de_historial({"informes": informes}, "h.json"))
    t = tablero.confiabilidad(i)
    # Ninguno de estos informes trae causa raíz confirmada —nadie la
    # escribió—, así que no hay fallas que contar; lo que sí hay son
    # lecturas fechadas.
    assert t.fallas == 0, "la logística se está contando como avería"
    assert t.lecturas == len(informes)
