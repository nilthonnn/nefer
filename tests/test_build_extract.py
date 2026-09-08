"""Ida y vuelta: manifiesto -> Excel -> manifiesto."""

import json

import openpyxl
import pytest

from nefer import build, extract, layout, schema


def foto_falsa(ruta, color=(200, 120, 40)):
    Image = pytest.importorskip("PIL.Image", reason="Pillow es necesario para las imagenes")
    Image.new("RGB", (640, 480), color).save(ruta)


@pytest.fixture
def manifiesto(tmp_path):
    fotos = tmp_path / "fotos"
    fotos.mkdir()
    vistas = ["VISTA FRONTAL", "VISTA POSTERIOR", "VISTA LATERAL IZQUIERDA",
              "VISTA LATERAL DERECHA", "HORÓMETRO", "PANEL DE CONTROL"]
    registro = []
    for i, vista in enumerate(vistas, start=1):
        nombre = f"foto{i}.png"
        foto_falsa(fotos / nombre)
        registro.append({"foto_id": i, "descripcion": vista, "archivo": f"fotos/{nombre}"})

    foto_falsa(fotos / "extintor.png", (200, 30, 30))
    return {
        "encabezado": {
            "empresa": "Maquinarias del Sur S.A.C.",
            "tipo_documento": "RECEPCION",
            "n_acta": "031-004000",
            "n_guia": "EG07-00009999",
            "cliente": "CONSTRUCTORA DEMO S.A.C.",
            "obra": "OBRA DEMO",
            "fecha": "2026-03-15",
            "horometro": 2450.5,
            "codigo_equipo": "GE074-99",
            "modelo_equipo": "GRUPO ELECTRÓGENO INSONORIZADO DE 74 KW",
            "categoria": "grupo_electrogeno",
        },
        "inspeccion_componentes": [
            {"item": "Módulo de control", "estado": "OK", "observacion": ""},
            {"item": "Nivel de combustible", "estado": "OBS",
             "observacion": "Tanque al 45%."},
        ],
        "registro_fotografico": registro,
        "consumibles": [{
            "descripcion": "EXTINTOR DE 6 KG",
            "cantidad": 1,
            "estado_recepcion": "NO_RETORNA",
            "foto_despacho": "fotos/extintor.png",
        }],
        "control_consumibles": [
            {"consumible": "Combustible diésel", "unidad": "%",
             "despacho": 100, "recepcion": 45},
        ],
        "resumen_ejecutivo": "Equipo operativo; retorna sin extintor, se genera recuperacion.",
    }


def test_manifiesto_de_prueba_es_valido(manifiesto, tmp_path):
    assert schema.validar(manifiesto, tmp_path) == []


def test_construye_las_hojas_esperadas(manifiesto, tmp_path):
    salida, avisos = build.construir(manifiesto, tmp_path / "acta.xlsx", raiz=tmp_path)
    assert avisos == []
    wb = openpyxl.load_workbook(salida)
    assert wb.sheetnames == ["REPORTE", "INSPECCIÓN", "CONSUMIBLES",
                             "GUÍA OPERADOR", "GUÍA CLIENTE"]


def test_cabecera_en_las_celdas_del_formato(manifiesto, tmp_path):
    salida, _ = build.construir(manifiesto, tmp_path / "acta.xlsx", raiz=tmp_path)
    ws = openpyxl.load_workbook(salida)["REPORTE"]
    assert ws[layout.CELDA_ACTA].value == "031-004000"
    assert ws[layout.CELDA_CODIGO].value == "GE074-99"
    assert ws[layout.CELDA_HOROMETRO].value == 2450.5
    # Es una recepcion: la "X" va en la casilla derecha, no en la de despacho.
    assert ws[layout.CELDA_MARCA_RECEPCION].value == "X"
    assert ws[layout.CELDA_MARCA_DESPACHO].value is None


def test_las_fotos_quedan_ancladas_en_su_bloque(manifiesto, tmp_path):
    salida, _ = build.construir(manifiesto, tmp_path / "acta.xlsx", raiz=tmp_path)
    ws = openpyxl.load_workbook(salida)["REPORTE"]
    # 6 fotos + 1 consumible. Sin logo: el manifiesto no declara ninguno.
    assert len(ws._images) == 7
    filas = {img.anchor._from.row + 1 for img in ws._images}
    assert layout.bloque_foto(0)["fila_imagen_inicio"] in filas
    assert layout.bloque_foto(2)["fila_imagen_inicio"] in filas


def test_el_logo_es_opcional_y_configurable(manifiesto, tmp_path):
    """El paquete no trae logo: lo aporta quien usa la herramienta."""
    salida, _ = build.construir(manifiesto, tmp_path / "sin-logo.xlsx", raiz=tmp_path)
    assert len(openpyxl.load_workbook(salida)["REPORTE"]._images) == 7

    foto_falsa(tmp_path / "fotos" / "logo.png", (10, 60, 140))
    manifiesto["encabezado"]["logo"] = "fotos/logo.png"
    salida, _ = build.construir(manifiesto, tmp_path / "con-logo.xlsx", raiz=tmp_path)
    imagenes = openpyxl.load_workbook(salida)["REPORTE"]._images
    assert len(imagenes) == 8
    assert any(img.anchor._from.row == 0 for img in imagenes), "el logo va en la fila 1"


def test_control_documental_configurable(manifiesto, tmp_path):
    """Cada organizacion pone su propio codigo, version y fecha de formato."""
    manifiesto["encabezado"].update(
        {"codigo_formato": "PROC-045", "version_formato": "03",
         "fecha_formato": "01/02/2026"})
    salida, _ = build.construir(manifiesto, tmp_path / "acta.xlsx", raiz=tmp_path)
    ws = openpyxl.load_workbook(salida)["REPORTE"]
    assert ws["S1"].value == "CÓDIGO: PROC-045"
    assert ws["S2"].value == "VERSIÓN: 03"
    assert ws["S3"].value == "FECHA: 01/02/2026"


def test_consumo_calculado_en_la_hoja_de_consumibles(manifiesto, tmp_path):
    salida, _ = build.construir(manifiesto, tmp_path / "acta.xlsx", raiz=tmp_path)
    ws = openpyxl.load_workbook(salida)["CONSUMIBLES"]
    fila = [c.value for c in ws[5]]          # fila 4 = encabezados, 5 = primer dato
    assert fila[3] == 100 and fila[4] == 45 and fila[5] == 55


def test_ida_y_vuelta_conserva_los_datos(manifiesto, tmp_path):
    salida, _ = build.construir(manifiesto, tmp_path / "acta.xlsx", raiz=tmp_path)
    recuperado = extract.extraer(salida)

    original = manifiesto["encabezado"]
    vuelta = recuperado["encabezado"]
    for campo in ("tipo_documento", "n_acta", "n_guia", "fecha",
                  "horometro", "codigo_equipo", "categoria"):
        assert vuelta[campo] == original[campo], campo
    assert vuelta["cliente"].strip() == original["cliente"]

    assert [f["descripcion"] for f in recuperado["registro_fotografico"]] == \
           [f["descripcion"] for f in manifiesto["registro_fotografico"]]
    assert len(recuperado["consumibles"]) == 1
    assert recuperado["consumibles"][0]["estado_recepcion"] == "NO_RETORNA"


def test_horometro_ilegible_se_imprime_como_leyenda(manifiesto, tmp_path):
    manifiesto["encabezado"]["horometro"] = schema.REVISION_MANUAL
    salida, _ = build.construir(manifiesto, tmp_path / "acta.xlsx", raiz=tmp_path)
    ws = openpyxl.load_workbook(salida)["REPORTE"]
    assert ws[layout.CELDA_HOROMETRO].value == schema.REVISION_MANUAL
    assert extract.extraer(salida)["encabezado"]["horometro"] == schema.REVISION_MANUAL


def test_imagen_no_soportada_avisa_sin_romper(manifiesto, tmp_path):
    (tmp_path / "fotos" / "roto.tiff").write_bytes(b"no soy una imagen")
    manifiesto["registro_fotografico"][0]["archivo"] = "fotos/roto.tiff"
    _, avisos = build.construir(manifiesto, tmp_path / "acta.xlsx", raiz=tmp_path)
    assert len(avisos) == 1 and "roto.tiff" in avisos[0]


def test_cli_construir_y_validar(manifiesto, tmp_path):
    from nefer.cli import main

    ruta = tmp_path / "acta.json"
    ruta.write_text(json.dumps(manifiesto, ensure_ascii=False), encoding="utf-8")
    assert main(["validar", str(ruta), "--verificar-fotos"]) == 0
    assert main(["construir", str(ruta), "-o", str(tmp_path / "salida.xlsx")]) == 0
    assert (tmp_path / "salida.xlsx").exists()
