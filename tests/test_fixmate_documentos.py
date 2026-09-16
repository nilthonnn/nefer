"""Leer lo que el taller tiene de verdad: PDF, Word y Excel.

Los PDF de estas pruebas se arman byte a byte, con sus flujos comprimidos y
su tabla de fuentes, porque es la unica forma de saber que texto tiene que
salir. Ademas se lee uno de verdad, generado por otra herramienta, para que
el lector no funcione solo con los PDF que escribe esta suite.
"""

import zipfile
import zlib
from pathlib import Path

import pytest

from nefer.fixmate import documentos, pdf_texto

RAIZ = Path(__file__).resolve().parents[1]

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


# ------------------------------------------------------------------- PDF

def _pdf(objetos: list[bytes]) -> bytes:
    salida = bytearray(b"%PDF-1.4\n")
    for n, objeto in enumerate(objetos, 1):
        salida += b"%d 0 obj\n" % n + objeto + b"\nendobj\n"
    salida += b"trailer << /Root 1 0 R >>\n%%EOF\n"
    return bytes(salida)


def _flujo(contenido: bytes, comprimido: bool = True, extra: bytes = b"") -> bytes:
    if comprimido:
        contenido = zlib.compress(contenido)
        extra += b" /Filter /FlateDecode"
    return (b"<< /Length %d%s >>\nstream\n" % (len(contenido), extra)
            + contenido + b"\nendstream")


def pdf_simple(texto: bytes = b"Par de apriete del prisionero de inyector: 30 N.m") -> bytes:
    contenido = b"BT /F1 12 Tf 72 720 Td (" + texto + b") Tj ET"
    return _pdf([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>",
        _flujo(contenido),
    ])


def test_lee_un_pdf_con_el_lector_propio(tmp_path):
    ruta = tmp_path / "manual.pdf"
    ruta.write_bytes(pdf_simple())
    assert "Par de apriete del prisionero de inyector: 30 N.m" in pdf_texto.extraer(
        ruta, preferir="propio")


def test_cada_linea_del_pdf_sale_en_su_linea(tmp_path):
    contenido = (b"BT /F1 12 Tf 72 720 Td (Sistema de admision) Tj "
                 b"0 -14 Td (El indicador se lee sin carga.) Tj ET")
    ruta = tmp_path / "dos-lineas.pdf"
    ruta.write_bytes(_pdf([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>",
        _flujo(contenido)]))
    lineas = pdf_texto.extraer(ruta, preferir="propio").splitlines()
    assert "Sistema de admision" in lineas
    assert "El indicador se lee sin carga." in lineas


def test_lee_una_fuente_con_tabla_de_caracteres(tmp_path):
    # Una fuente incrustada no escribe letras, escribe codigos: sin su tabla
    # ToUnicode el texto sale como simbolos. Es el caso de casi todo PDF
    # generado por Word.
    cmap = (b"begincmap\n2 beginbfchar\n<0001> <0050>\n<0002> <0033>\nendbfchar\n"
            b"1 beginbfrange\n<000A> <000C> <0078>\nendbfrange\nendcmap")
    contenido = (b"BT /F1 12 Tf (\x00\x01\x00\x02) Tj T* "
                 b"[(\x00\x0a) -300 (\x00\x0b\x00\x0c)] TJ ET")
    ruta = tmp_path / "incrustada.pdf"
    ruta.write_bytes(_pdf([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type0 /BaseFont /AAAA+Barlow /ToUnicode 5 0 R >>",
        _flujo(cmap),
        _flujo(contenido)]))
    texto = pdf_texto.texto_de(ruta.read_bytes())
    assert "P3" in texto           # los dos bfchar
    assert "x yz" in texto         # el rango, con el espacio del salto grande


def test_un_pdf_escaneado_no_se_devuelve_como_texto_vacio(tmp_path):
    # Sin capa de texto no hay nada que recuperar. Devolver "" haria que se
    # indexara un manual vacio y nadie lo notaria.
    ruta = tmp_path / "escaneado.pdf"
    ruta.write_bytes(_pdf([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>",
        _flujo(b"q 612 0 0 792 0 0 cm /Im0 Do Q")]))
    with pytest.raises(pdf_texto.ErrorPDFTexto, match="OCR"):
        pdf_texto.extraer(ruta)


def test_tambien_lee_un_pdf_que_no_escribio_esta_suite():
    # Uno generado por otra herramienta, con ASCII85 sobre Flate y seis
    # fuentes incrustadas: el caso que rompe a los lectores de juguete.
    ajeno = Path("/mnt/skills/examples/theme-factory/theme-showcase.pdf")
    if not ajeno.is_file():
        pytest.skip("no hay un PDF ajeno a mano en esta maquina")
    texto = pdf_texto.extraer(ajeno, preferir="propio")
    assert len(texto.split()) > 100
    assert "Typography" in texto


def test_el_lector_se_puede_elegir_y_uno_inexistente_es_un_error(tmp_path):
    ruta = tmp_path / "m.pdf"
    ruta.write_bytes(pdf_simple())
    with pytest.raises(ValueError, match="lector desconocido"):
        pdf_texto.extraer(ruta, preferir="magia")


# ------------------------------------------------------------------ Word

def escribir_docx(ruta: Path, cuerpo: str) -> Path:
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml",
                   f'<?xml version="1.0"?><w:document {W}><w:body>{cuerpo}'
                   f'</w:body></w:document>')
    return ruta


def test_los_titulos_de_word_salen_como_secciones(tmp_path):
    # De esto depende que el troceado por secciones funcione igual venga de
    # Markdown o de un Word de la oficina.
    ruta = escribir_docx(tmp_path / "manual.docx", """
      <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Inyección</w:t></w:r></w:p>
      <w:p><w:r><w:t xml:space="preserve">Prisionero: </w:t></w:r><w:r><w:t>30 N·m.</w:t></w:r></w:p>
      <w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>Códigos</w:t></w:r></w:p>
      <w:tbl><w:tr><w:tc><w:p><w:r><w:t>P0300</w:t></w:r></w:p></w:tc>
             <w:tc><w:p><w:r><w:t>Fallo de combustión</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
    """)
    texto = documentos.leer(ruta)
    assert "# Inyección" in texto
    assert "## Códigos" in texto
    assert "Prisionero: 30 N·m." in texto          # dos trozos, una frase
    assert "P0300 | Fallo de combustión" in texto  # la tabla, fila por fila


def test_un_docx_que_no_es_un_docx_lo_dice(tmp_path):
    ruta = tmp_path / "falso.docx"
    ruta.write_bytes(b"no soy un zip")
    with pytest.raises(documentos.ErrorDocumento, match="docx"):
        documentos.leer(ruta)


# ----------------------------------------------------------------- Excel

def escribir_xlsx(ruta: Path, filas, hoja: str = "Hoja1") -> Path:
    from openpyxl import Workbook

    libro = Workbook()
    hoja_activa = libro.active
    hoja_activa.title = hoja
    for fila in filas:
        hoja_activa.append(fila)
    libro.save(ruta)
    return ruta


def test_cada_hoja_de_excel_es_una_seccion(tmp_path):
    ruta = escribir_xlsx(tmp_path / "manual.xlsx",
                         [["Par de apriete", "30 N·m"], ["Código", "P0300"]],
                         hoja="Inyección")
    texto = documentos.leer(ruta)
    assert "## Inyección" in texto
    assert "Par de apriete | 30 N·m" in texto


def test_el_encabezado_no_tiene_que_estar_en_la_primera_fila(tmp_path):
    # Arriba de la tabla siempre hay un membrete y dos filas en blanco.
    ruta = escribir_xlsx(tmp_path / "historial.xlsx", [
        ["MAQUINARIAS DEL SUR S.A.C."],
        [],
        ["N° OT", "Equipo", "Falla", "Causa raíz"],
        ["OT-1", "GE074-01", "Humo negro", "Filtro colmatado"],
        ["OT-2", "GE074-02", "No arranca", "Batería sulfatada"],
    ])
    filas = documentos.tabla(ruta)
    assert len(filas) == 2
    assert filas[0]["N° OT"] == "OT-1"
    assert filas[1]["Causa raíz"] == "Batería sulfatada"


def test_las_fechas_de_excel_salen_en_formato_de_fecha(tmp_path):
    import datetime as dt

    ruta = escribir_xlsx(tmp_path / "f.xlsx", [
        ["Fecha", "Falla"], [dt.datetime(2026, 3, 14), "Humo negro"]])
    assert documentos.tabla(ruta)[0]["Fecha"] == "2026-03-14"


def test_una_hoja_que_no_existe_dice_cuales_hay(tmp_path):
    ruta = escribir_xlsx(tmp_path / "x.xlsx", [["a"], ["b"]], hoja="ÚNICA")
    with pytest.raises(documentos.ErrorDocumento, match="ÚNICA"):
        documentos.tabla(ruta, hoja="OTRA")


# ----------------------------------------------------------------- varios

def test_un_formato_que_no_se_lee_lo_dice_por_su_nombre(tmp_path):
    ruta = tmp_path / "plano.dwg"
    ruta.write_bytes(b"0")
    with pytest.raises(documentos.ErrorDocumento, match="no soportado"):
        documentos.leer(ruta)


def test_un_doc_antiguo_sin_libreoffice_explica_como_salir(tmp_path, monkeypatch):
    monkeypatch.setattr(documentos.shutil, "which", lambda _: None)
    ruta = tmp_path / "manual-1998.doc"
    ruta.write_bytes(b"\xd0\xcf\x11\xe0")
    with pytest.raises(documentos.ErrorDocumento, match="LibreOffice"):
        documentos.leer(ruta)


def test_el_texto_plano_se_lee_tal_cual(tmp_path):
    ruta = tmp_path / "notas.txt"
    ruta.write_text("Par de apriete: 30 N·m\n", encoding="utf-8")
    assert documentos.leer(ruta).strip() == "Par de apriete: 30 N·m"


def test_un_pdf_con_una_barra_de_mas_no_tumba_la_indexacion(tmp_path):
    """`\\8` no es un escape octal, y tratarlo como si lo fuera reventaba.

    Un solo PDF raro en la carpeta abortaba `nefer fixmate indexar` entero
    con un ValueError sin dueño.
    """
    contenido = rb"BT /F1 12 Tf 72 720 Td (Par de apriete \8 del prisionero: 30 N.m) Tj ET"
    ruta = tmp_path / "raro.pdf"
    ruta.write_bytes(_pdf([
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>",
        _flujo(contenido)]))

    texto = pdf_texto.extraer(ruta, preferir="propio")
    assert "Par de apriete" in texto and "30 N.m" in texto


def test_un_escape_octal_corta_en_el_primer_digito_que_no_lo_es():
    """`\\1a2` es el carácter 1 seguido de «a2», no el carácter 12.

    El filtro colaba los dígitos octales sueltos de la ventana de tres en vez
    de cortar en el primero que no lo era: leía otro carácter y se comía la
    letra de en medio. En un manual eso es una palabra rota por página.
    """
    from nefer.fixmate.pdf_texto import _cadena_literal

    assert _cadena_literal(rb"\1a2") == b"\x01a2"
    assert _cadena_literal(rb"\101") == b"A"          # tres dígitos, completo
    assert _cadena_literal(rb"\0053") == b"\x053"     # tres y sobra un dígito
    assert _cadena_literal(rb"\12") == b"\n"
    assert _cadena_literal(rb"\8x") == b"8x"          # no es octal: literal
