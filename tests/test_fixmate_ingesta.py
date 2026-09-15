"""De los papeles del taller a fragmentos indexables.

Lo que se comprueba aqui es que no se pierda por el camino lo unico que un
manual OEM no trae: la observacion que el tecnico escribio a mano y la causa
raiz que se confirmo al cerrar la orden.
"""

import json

import pytest

from nefer.fixmate import ingesta

INFORME = {
    "codigo_ot": "OT-2026-0455",
    "codigo_equipo": "GE074-02",
    "codigos_dtc": ["p0300"],
    "resumen_falla": "Humo negro y marcha inestable en frio.",
    "causa_raiz": "Inyector del cilindro 3 con retorno excesivo.",
    "solucion_aplicada": "Se reemplazo el inyector y se purgo el sistema.",
    "pasos": ["Medir el retorno de inyectores.",
              "Apretar el prisionero a 30 N·m."],
    "herramientas": ["Juego de probetas"],
    "repuestos": ["Inyector 0445110xxx"],
}


def test_un_informe_conserva_causa_solucion_y_procedimiento():
    fragmento = ingesta.de_informe(INFORME, fuente="historial.json")
    assert fragmento.id == "ot:OT-2026-0455"
    assert fragmento.tipo == "informe"
    assert fragmento.metadatos["causa_raiz"].startswith("Inyector")
    assert fragmento.metadatos["pasos"][0].startswith("Medir")
    assert fragmento.metadatos["repuestos"] == ["Inyector 0445110xxx"]
    # El texto indexable lleva todo: es lo que la busqueda lee.
    for pedazo in ("OT-2026-0455", "Humo negro", "Inyector del cilindro 3",
                   "Juego de probetas"):
        assert pedazo in fragmento.texto


def test_el_codigo_de_falla_se_guarda_normalizado_y_tambien_el_que_estaba_suelto():
    informe = dict(INFORME, resumen_falla="Falla intermitente, el bus marca SPN 157")
    codigos = ingesta.de_informe(informe).metadatos["codigos_dtc"]
    assert codigos[0] == "P0300"        # declarado en minusculas, guardado canonico
    assert "SPN157" in codigos          # detectado dentro del relato


def test_el_torque_del_procedimiento_queda_a_mano():
    assert ingesta.de_informe(INFORME).metadatos["torques"] == ["30 N·m"]


def test_un_informe_sin_ot_igual_entra_con_un_identificador_propio():
    fragmento = ingesta.de_informe({"resumen_falla": "algo"}, n=4)
    assert fragmento.id == "ot:SIN-OT-5"


def test_historial_acepta_lista_pelada_y_objeto_con_informes():
    assert len(ingesta.de_historial([INFORME, INFORME])) == 2
    assert len(ingesta.de_historial({"informes": [INFORME]})) == 1


MANIFIESTO = {
    "encabezado": {"tipo_documento": "RECEPCION", "n_acta": "001-000123",
                   "codigo_equipo": "GE074-01", "modelo_equipo": "GRUPO ELECTROGENO",
                   "categoria": "grupo_electrogeno", "fecha": "2026-08-26",
                   "cliente": "CONSTRUCTORA ANDINA", "horometro": 1548.7},
    "inspeccion_componentes": [
        {"item": "Breaker principal", "estado": "OK", "observacion": ""},
        {"item": "Barra de puesta a tierra", "estado": "D",
         "observacion": "No retorno con el equipo."},
        {"item": "Nivel de combustible", "estado": "OBS",
         "observacion": "Tanque al 35%."},
    ],
    "resumen_ejecutivo": "Equipo operativo con dos observaciones.",
}


def test_un_acta_da_un_fragmento_del_acta_y_uno_por_hallazgo():
    fragmentos = ingesta.de_manifiesto(MANIFIESTO, fuente="acta.json")
    assert len(fragmentos) == 3      # el acta + los dos componentes OBS/D
    assert fragmentos[0].id == "acta:001-000123"
    assert [f.metadatos.get("estado") for f in fragmentos[1:]] == ["D", "OBS"]
    # Un componente OK no es un antecedente de falla y no ocupa lugar.
    assert all("Breaker" not in f.texto for f in fragmentos[1:])


def test_la_observacion_escrita_a_mano_es_lo_que_se_indexa():
    fragmentos = ingesta.de_manifiesto(MANIFIESTO)
    assert "No retorno con el equipo." in fragmentos[1].texto
    assert fragmentos[1].metadatos["codigo_equipo"] == "GE074-01"


def test_un_consumible_que_no_retorno_es_un_antecedente():
    # Es lo unico que sobrevive al viaje por el Excel —la hoja de inspeccion
    # no se relee— y es un hecho registrado del equipo como cualquier otro.
    acta = dict(MANIFIESTO, consumibles=[
        {"descripcion": "EXTINTOR DE 6 KG", "estado_recepcion": "OK"},
        {"descripcion": "BARRA PUESTA A TIERRA", "estado_recepcion": "NO_RETORNA",
         "texto_recepcion": "EL EQUIPO RETORNO SIN BARRA PUESTA A TIERRA",
         "recuperacion": "RECUPERACION N° 3: BARRA PUESTA A TIERRA"},
    ])
    fragmentos = ingesta.de_manifiesto(acta)
    consumibles = [f for f in fragmentos if f.id.startswith("acta:001-000123:c")]

    assert len(consumibles) == 1, "el que retorno OK no es un antecedente de nada"
    assert consumibles[0].metadatos["item"] == "BARRA PUESTA A TIERRA"
    assert "RETORNO SIN BARRA" in consumibles[0].texto


MANUAL = """# Manual de taller

## Sistema de admision

El indicador de restriccion se lee a regimen maximo sin carga.

Herramientas: llave de 13 mm, linterna.

## Sistema de inyeccion

Par de apriete del prisionero de inyector: 30 N·m. El codigo P0300 aparece
cuando falla la combustion en mas de un cilindro.
"""


def test_un_manual_se_corta_por_seccion_y_no_por_numero_de_caracteres():
    fragmentos = ingesta.de_manual(MANUAL, fuente="manual.md")
    secciones = [f.metadatos["seccion"] for f in fragmentos]
    assert "Sistema de admision" in secciones and "Sistema de inyeccion" in secciones
    assert all(f.tipo == "manual" for f in fragmentos)


def test_del_manual_salen_los_torques_las_herramientas_y_los_codigos():
    porseccion = {f.metadatos["seccion"]: f for f in ingesta.de_manual(MANUAL)}
    inyeccion = porseccion["Sistema de inyeccion"]
    assert inyeccion.metadatos["torques"] == ["30 N·m"]
    assert inyeccion.metadatos["codigos_dtc"] == ["P0300"]
    assert porseccion["Sistema de admision"].metadatos["herramientas"] == [
        "llave de 13 mm", "linterna"]


def test_un_documento_sin_titulos_es_una_sola_seccion():
    fragmentos = ingesta.de_manual("Texto suelto sin encabezados.", fuente="notas.txt")
    assert len(fragmentos) == 1 and fragmentos[0].metadatos["seccion"] == ""


def test_de_archivo_distingue_acta_de_historial(tmp_path):
    acta = tmp_path / "acta.json"
    acta.write_text(json.dumps(MANIFIESTO), encoding="utf-8")
    historial = tmp_path / "historial.json"
    historial.write_text(json.dumps({"informes": [INFORME]}), encoding="utf-8")

    assert ingesta.de_archivo(acta)[0].tipo == "acta"
    assert ingesta.de_archivo(historial)[0].tipo == "informe"


def test_un_json_que_no_es_ninguno_de_los_dos_lo_dice(tmp_path):
    suelto = tmp_path / "cualquiera.json"
    suelto.write_text('{"cosa": 1}', encoding="utf-8")
    with pytest.raises(ingesta.ErrorIngesta, match="encabezado"):
        ingesta.de_archivo(suelto)


def test_recorrer_entra_en_las_carpetas_y_deja_fuera_lo_que_no_se_indexa(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "manual.md").write_text("# a\n\ntexto", encoding="utf-8")
    (tmp_path / "foto.jpg").write_bytes(b"no soy texto")
    (tmp_path / ".oculto.md").write_text("# b\n\ntexto", encoding="utf-8")

    encontrados = [r.name for r in ingesta.recorrer([tmp_path])]
    assert encontrados == ["manual.md"]


def test_una_ruta_que_no_existe_es_un_error_y_no_un_silencio(tmp_path):
    with pytest.raises(ingesta.ErrorIngesta, match="no existe"):
        ingesta.recorrer([tmp_path / "fantasma"])


def test_el_corpus_de_ejemplo_se_indexa_entero():
    from pathlib import Path

    from nefer.fixmate import indexar

    ejemplos = Path(__file__).resolve().parents[1] / "ejemplos" / "fixmate"
    indice = indexar([ejemplos])
    assert len(indice) >= 8
    tipos = {f.tipo for f in indice.fragmentos}
    assert tipos == {"informe", "manual"}


# ------------------------------- el historial como esta de verdad: en Excel

def _libro(tmp_path, filas, nombre="historial.xlsx", hoja="HISTORIAL"):
    from openpyxl import Workbook

    libro = Workbook()
    hoja_activa = libro.active
    hoja_activa.title = hoja
    for fila in filas:
        hoja_activa.append(fila)
    ruta = tmp_path / nombre
    libro.save(ruta)
    return ruta


FILAS_TALLER = [
    ["MAQUINARIAS DEL SUR S.A.C."],
    ["Historial de fallas 2026"],
    [],
    ["N° OT", "Fecha", "Equipo", "Código de falla", "Falla reportada",
     "Causa raíz", "Trabajo realizado", "Repuestos", "Técnico", "HH"],
    ["OT-2026-0412", "2026-03-14", "GE074-01", "P0300",
     "Humo negro y pérdida de potencia a 4100 msnm", "Filtro de aire colmatado",
     "Cambio de elemento primario y secundario", "Filtro P533781; Filtro P533782",
     "J. Quispe", 1.5],
    ["OT-2026-0455", "2026-04-02", "GE074-02", "P0300; SPN 157",
     "Marcha inestable en frío", "Inyector con retorno excesivo",
     "Reemplazo de inyector y purga", "Inyector 0445110xxx", "M. Ríos", 3],
]


def test_el_historial_en_excel_se_lee_fila_por_fila(tmp_path):
    fragmentos = ingesta.de_archivo(_libro(tmp_path, FILAS_TALLER))
    assert len(fragmentos) == 2
    assert all(f.tipo == "informe" for f in fragmentos)

    primero = fragmentos[0].metadatos
    assert primero["codigo_ot"] == "OT-2026-0412"
    assert primero["codigo_equipo"] == "GE074-01"
    assert primero["causa_raiz"] == "Filtro de aire colmatado"
    assert primero["solucion_aplicada"].startswith("Cambio de elemento")
    assert primero["repuestos"] == ["Filtro P533781", "Filtro P533782"]


def test_las_columnas_se_reconocen_como_las_escribe_el_taller(tmp_path):
    # "N° OT", "Falla reportada" y "Trabajo realizado" no son los nombres del
    # esquema; son los que estan en el libro de la oficina.
    assert ingesta.clave_columna("N° OT") == "n ot"
    assert ingesta.clave_columna("Nº de Orden") == "no de orden"
    assert ingesta.clave_columna("CAUSA RAÍZ:") == "causa raiz"


def test_los_codigos_de_falla_de_una_celda_se_separan(tmp_path):
    fragmentos = ingesta.de_archivo(_libro(tmp_path, FILAS_TALLER))
    assert fragmentos[1].metadatos["codigos_dtc"] == ["P0300", "SPN157"]


def test_las_columnas_que_no_son_del_esquema_no_se_tiran(tmp_path):
    # Por el tecnico que la atendio tambien se busca.
    fragmento = ingesta.de_archivo(_libro(tmp_path, FILAS_TALLER))[0]
    assert "J. Quispe" in fragmento.texto
    assert fragmento.metadatos["col_tecnico"] == "J. Quispe"


def test_un_excel_sin_columna_de_falla_ni_de_causa_lo_dice(tmp_path):
    ruta = _libro(tmp_path, [["Cliente", "Monto"], ["ANDINA", 1200]],
                  nombre="facturas.xlsx")
    with pytest.raises(ingesta.ErrorIngesta, match="Falla"):
        ingesta.de_historial_xlsx(ruta)


def test_un_excel_que_no_es_historial_se_indexa_como_manual(tmp_path):
    ruta = _libro(tmp_path, [["Par de apriete", "30 N·m"], ["Código", "P0300"]],
                  nombre="tabla-de-torques.xlsx", hoja="Inyección")
    fragmentos = ingesta.de_archivo(ruta)
    assert fragmentos[0].tipo == "manual"
    assert fragmentos[0].metadatos["torques"] == ["30 N·m"]


def test_un_acta_de_nefer_en_excel_se_reconoce_como_acta(tmp_path):
    from nefer import build

    manifiesto = dict(MANIFIESTO, consumibles=[
        {"descripcion": "BARRA PUESTA A TIERRA", "estado_recepcion": "NO_RETORNA",
         "texto_recepcion": "EL EQUIPO RETORNO SIN BARRA PUESTA A TIERRA"}])
    xlsx, _ = build.construir(manifiesto, tmp_path / "acta.xlsx", raiz=tmp_path)

    assert ingesta.es_acta_de_nefer(xlsx)
    fragmentos = ingesta.de_archivo(xlsx)
    assert fragmentos[0].tipo == "acta"
    assert any("BARRA PUESTA A TIERRA" in f.texto for f in fragmentos)


def test_cada_fragmento_sabe_de_que_archivo_salio(tmp_path):
    ruta = _libro(tmp_path, FILAS_TALLER)
    assert all(f.metadatos["_origen"] == str(ruta) for f in ingesta.de_archivo(ruta))


def test_un_manual_en_word_entra_como_manual(tmp_path):
    import zipfile

    W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    ruta = tmp_path / "manual.docx"
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml",
                   f'<?xml version="1.0"?><w:document {W}><w:body>'
                   '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
                   '<w:r><w:t>Sistema de inyeccion</w:t></w:r></w:p>'
                   '<w:p><w:r><w:t>Par de apriete del prisionero: 30 N.m. '
                   'El codigo P0300 indica fallo de combustion.</w:t></w:r></w:p>'
                   '</w:body></w:document>')
    fragmentos = ingesta.de_archivo(ruta)
    assert fragmentos[0].tipo == "manual"
    assert fragmentos[0].metadatos["seccion"] == "Sistema de inyeccion"
    assert fragmentos[0].metadatos["torques"] == ["30 N.m"]
    assert fragmentos[0].metadatos["codigos_dtc"] == ["P0300"]
