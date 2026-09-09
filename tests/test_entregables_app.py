"""La app genera el Excel y el PDF dentro del telefono.

Es una segunda implementacion del mismo formato que produce `nefer construir`.
Dos implementaciones se separan con el tiempo, asi que aqui se comprueban las
dos cosas: que la geometria copiada siga coincidiendo con la de layout.py, y
que los archivos que salen del navegador los abran los lectores de verdad.
"""

from __future__ import annotations

import io
import json
import os
import re
import zipfile
from pathlib import Path

import pytest

from nefer import build, layout

APP = Path(__file__).resolve().parents[1] / "docs" / "app" / "index.html"
FUENTE = APP.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# que las dos implementaciones no se separen
# --------------------------------------------------------------------------

def _constante_js(nombre: str) -> str:
    m = re.search(rf"\b{nombre}:\s*([^,\n]+)", FUENTE)
    assert m, f"no se encontro {nombre} en la app"
    return m.group(1).strip().strip('"')


def _var_js(nombre: str) -> str:
    """Lee `var X = 11` o `var A = 1, X = 11, B = 2`, que asi estan declaradas."""
    m = re.search(rf"\b{nombre}\s*=\s*([0-9.]+)", FUENTE)
    assert m, f"no se encontro {nombre} en la app"
    return m.group(1)


def test_geometria_compartida_con_layout():
    """Las cifras que la app copio de layout.py siguen siendo las mismas."""
    assert int(_constante_js("BLOQUES_FOTO_POR_PAGINA")) == build.BLOQUES_FOTO_POR_PAGINA
    assert int(_constante_js("BLOQUES_CONSUMIBLE_POR_PAGINA")) == \
        build.BLOQUES_CONSUMIBLE_POR_PAGINA
    assert _constante_js("CODIGO_FORMATO") == layout.CODIGO_FORMATO
    assert _constante_js("VERSION_FORMATO") == layout.VERSION_FORMATO
    assert _constante_js("TITULO_COMPARATIVO") == layout.TITULO_COMPARATIVO
    assert _constante_js("TITULO_DANOS") == layout.TITULO_DANOS

    assert int(_var_js("FILA_INICIO_FOTOS")) == layout.FILA_INICIO_FOTOS
    assert int(_var_js("ALTO_BLOQUE_FOTO")) == layout.ALTO_BLOQUE_FOTO
    assert int(_var_js("FILAS_IMAGEN")) == layout.FILAS_IMAGEN
    assert float(_var_js("ALTO_FILA_ESTANDAR")) == layout.ALTO_FILA_ESTANDAR
    assert float(_var_js("ALTO_FILA_ROTULO")) == layout.ALTO_FILA_ROTULO
    assert float(_var_js("ALTO_FILA_SEPARADOR")) == layout.ALTO_FILA_SEPARADOR


def test_anchos_de_columna_compartidos():
    bloque = re.search(r"var ANCHOS_COLUMNA = \{(.*?)\};", FUENTE, re.S)
    assert bloque, "no se encontro la tabla de anchos en la app"
    leidos = {c: float(v) for c, v in re.findall(r"([A-Z]):([\d.]+)", bloque.group(1))}
    assert leidos == layout.ANCHOS_COLUMNA


def test_paneles_compartidos():
    assert re.search(r'var PANEL_IZQ = \["A", "L"\]', FUENTE)
    assert re.search(r'PANEL_DER = \["M", "Z"\]', FUENTE)
    assert layout.PANEL_IZQ == ("A", "L")
    assert layout.PANEL_DER == ("M", "Z")


# --------------------------------------------------------------------------
# los archivos que salen del navegador
# --------------------------------------------------------------------------

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402

CHROME = next(
    (r for r in (
        os.environ.get("NEFER_CHROMIUM"),
        "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    ) if r and Path(r).exists()),
    None,
)


@pytest.fixture(scope="module")
def entregables(tmp_path_factory):
    """Arma el acta de ejemplo y descarga el PDF y el Excel, una sola vez."""
    if CHROME is None:
        pytest.skip("no hay Chromium disponible")
    destino = tmp_path_factory.mktemp("entregables")
    salida = {}
    fallos: list[str] = []

    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=CHROME)
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True,
                              accept_downloads=True, permissions=[])
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fallos.append(str(e)))
        pg.goto(APP.as_uri())
        pg.wait_for_timeout(600)
        pg.click("#btn-demo")
        pg.wait_for_timeout(2500)
        assert pg.eval_on_selector_all("#d-grid .slot.lleno", "n => n.length") == 10

        for boton, clave in (("#d-pdf", "pdf"), ("#d-xlsx", "xlsx"), ("#d-zip", "zip")):
            with pg.expect_download(timeout=60000) as espera:
                pg.click(boton)
            bajado = espera.value
            ruta = destino / bajado.suggested_filename
            bajado.save_as(ruta)
            salida[clave] = ruta
        nav.close()

    assert fallos == [], fallos
    return salida


def test_el_pdf_es_valido_y_lleva_el_acta(entregables):
    datos = entregables["pdf"].read_bytes()
    assert datos.startswith(b"%PDF-")
    assert datos.rstrip().endswith(b"%%EOF")

    # Ocho fotos por pagina: diez fotos y un accesorio caben en dos.
    assert datos.count(b"/Type /Page\n") or datos.count(b"/Type /Page ")
    paginas = len(re.findall(rb"/Type /Page[^s]", datos))
    assert paginas == 2, paginas

    # Cada foto entra como JPEG incrustado, sin recodificar en el lector.
    assert len(re.findall(rb"/Subtype /Image", datos)) == 10

    texto = _texto_de_pdf(entregables["pdf"])
    if texto is None:
        pytest.skip("pdftotext no esta disponible")
    for esperado in ("REPORTE FOTOGRÁFICO", "004-001155", "MINERA EJEMPLO S.A.C.",
                     "GE-0142", "1548.7", "VISTA LATERAL IZQUIERDA", "HORÓMETRO"):
        assert esperado in texto, esperado


def _texto_de_pdf(ruta: Path):
    import shutil
    import subprocess
    if not shutil.which("pdftotext"):
        return None
    return subprocess.run(["pdftotext", str(ruta), "-"],
                          capture_output=True, text=True).stdout


def test_el_excel_lo_abre_openpyxl_con_sus_fotos(entregables):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(entregables["xlsx"])
    ws = wb.active

    assert ws.title == "REPORTE"
    assert len(ws._images) == 10

    assert ws[layout.CELDA_ACTA].value == "004-001155"
    assert ws[layout.CELDA_CLIENTE].value == "MINERA EJEMPLO S.A.C."
    assert ws[layout.CELDA_CODIGO].value == "GE-0142"

    # Los rotulos caen en las filas que dicta layout.bloque_foto.
    esperados = ["VISTA FRONTAL", "VISTA POSTERIOR", "VISTA LATERAL IZQUIERDA",
                 "VISTA LATERAL DERECHA"]
    leidos = []
    for franja in range(2):
        fila = layout.bloque_foto(franja)["fila_rotulo"]
        leidos.append(ws[f"{layout.PANEL_IZQ[0]}{fila}"].value)
        leidos.append(ws[f"{layout.PANEL_DER[0]}{fila}"].value)
    assert leidos == esperados


def _cortes(ruta_xlsx: Path) -> list[int]:
    with zipfile.ZipFile(ruta_xlsx) as z:
        hoja = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    return sorted(int(m) for m in re.findall(r'<brk id="(\d+)"', hoja))


def test_el_excel_pagina_como_el_formato(entregables, tmp_path):
    """Sin saltos, Excel imprime la hoja entera escalada y el formato se pierde.

    Los cortes se comparan con los que pone `nefer construir` sobre el mismo
    acta: si la regla cambia alli, esta prueba lo dice.
    """
    from nefer import schema

    carpeta = tmp_path / "abierto"
    with zipfile.ZipFile(entregables["zip"]) as z:
        z.extractall(carpeta)
    manifiesto = json.loads((carpeta / "acta.json").read_text(encoding="utf-8"))
    assert schema.validar(manifiesto, carpeta) == []

    referencia = carpeta / "REFERENCIA.xlsx"
    build.construir(manifiesto, referencia, carpeta)

    assert _cortes(entregables["xlsx"]) == _cortes(referencia)


def test_el_excel_lo_abre_libreoffice(entregables, tmp_path):
    """El lector que usa la oficina: si LibreOffice no lo abre, no sirve."""
    import shutil
    import subprocess
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        pytest.skip("LibreOffice no esta instalado")

    perfil = tmp_path / "perfil"
    r = subprocess.run(
        [soffice, "-env:UserInstallation=file://" + str(perfil), "--headless",
         "--convert-to", "pdf", "--outdir", str(tmp_path), str(entregables["xlsx"])],
        capture_output=True, text=True, timeout=180)
    salida = tmp_path / (entregables["xlsx"].stem + ".pdf")
    assert salida.exists(), r.stdout + r.stderr
    assert salida.stat().st_size > 20_000

# --------------------------------------------------------------------------
# el acta de recepcion: las secciones que solo existen en un retorno
# --------------------------------------------------------------------------

RECEPCION_EN_EL_NAVEGADOR = """async () => {
  const dt = new DataTransfer();
  for (let i = 1; i <= 11; i++) {
    const c = document.createElement('canvas'); c.width = 320; c.height = 240;
    const g = c.getContext('2d');
    g.fillStyle = '#3f4c58'; g.fillRect(0, 0, 320, 240);
    g.fillStyle = '#eee'; g.font = '16px monospace';
    g.fillText('RETORNO ' + i, 20, 120);
    const b = await new Promise(r => c.toBlob(r, 'image/png'));
    dt.items.add(new File([b], 'R' + String(i).padStart(2, '0') + '.png',
                          {type: 'image/png'}));
  }
  const i = document.querySelector('#r-f3');
  i.files = dt.files;
  i.dispatchEvent(new Event('change', {bubbles: true}));
}"""


@pytest.fixture(scope="module")
def recepcion(tmp_path_factory):
    """Un acta de recepcion completa: accesorio no retornado y un daño."""
    if CHROME is None:
        pytest.skip("no hay Chromium disponible")
    destino = tmp_path_factory.mktemp("recepcion")
    salida = {}
    fallos: list[str] = []

    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=CHROME)
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True,
                              accept_downloads=True, permissions=[])
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fallos.append(str(e)))
        pg.goto(APP.as_uri())
        pg.wait_for_timeout(600)
        pg.click("#btn-demo")
        pg.wait_for_timeout(2500)

        pg.click("#tab-recepcion")
        pg.wait_for_timeout(300)
        pg.click("#r-desde-despacho")
        pg.wait_for_timeout(800)
        pg.evaluate(RECEPCION_EN_EL_NAVEGADOR)
        pg.wait_for_timeout(3000)

        for k in range(10):
            pg.click("#r-tira .tile:first-child")
            pg.click(f"#r-vistas .slot:nth-child({k + 1})")
            pg.wait_for_timeout(60)

        pg.click("#r-consumibles .par:first-child .estados button[data-e='NO_RETORNA']")
        pg.wait_for_timeout(200)
        pg.click("#r-add-comp")
        pg.wait_for_timeout(200)
        pg.fill("#r-inspeccion .par:last-child [data-item]", "JUNTA DE ESCAPE")
        pg.click("#r-inspeccion .par:last-child .estados button[data-e='D']")
        pg.wait_for_timeout(200)
        pg.fill("#r-inspeccion .par:last-child [data-obs]",
                "Junta partida en el codo de salida.")
        pg.click("#r-tira .tile:first-child")
        pg.click("#r-inspeccion .par:last-child [data-destino='insp']")
        pg.wait_for_timeout(200)

        pg.fill("#r-acta", "004-001156")
        pg.fill("#r-horometro", "1731.2")
        pg.fill("#r-resumen", "Retorna operativo; junta rota y extintor no retornado.")
        pg.wait_for_timeout(500)

        for boton, clave in (("#r-pdf", "pdf"), ("#r-xlsx", "xlsx"), ("#r-zip", "zip")):
            with pg.expect_download(timeout=90000) as espera:
                pg.click(boton)
            bajado = espera.value
            ruta = destino / bajado.suggested_filename
            bajado.save_as(ruta)
            salida[clave] = ruta
        nav.close()

    assert fallos == [], fallos
    return salida


def _titulos_por_fila(ruta_xlsx: Path) -> dict[int, str]:
    """Fila -> texto de las bandas de ancho completo (titulos y recuperacion)."""
    openpyxl = pytest.importorskip("openpyxl")
    ws = openpyxl.load_workbook(ruta_xlsx).active
    marcas = {}
    for fila in range(1, ws.max_row + 1):
        v = ws.cell(row=fila, column=1).value
        if not isinstance(v, str):
            continue
        if any(t in v for t in ("OBSERVACIONES", layout.TITULO_COMPARATIVO,
                                layout.TITULO_DANOS, "RECUPERACIÓN", "CONFORME")):
            marcas[fila] = v
    return marcas


def test_la_recepcion_lleva_las_secciones_del_formato(recepcion):
    marcas = _titulos_por_fila(recepcion["xlsx"])
    textos = list(marcas.values())
    assert any("OBSERVACIONES" == t for t in textos), textos
    assert layout.TITULO_COMPARATIVO in textos, textos
    assert layout.TITULO_DANOS in textos, textos
    assert any(t.startswith("RECUPERACIÓN 1") for t in textos), textos


def test_la_recepcion_cae_en_las_mismas_filas_que_el_escritorio(recepcion, tmp_path):
    """La prueba de fuego: mismas secciones, en las mismas filas."""
    from nefer import build as _build, schema

    carpeta = tmp_path / "abierto"
    with zipfile.ZipFile(recepcion["zip"]) as z:
        z.extractall(carpeta)
    manifiesto = json.loads((carpeta / "acta.json").read_text(encoding="utf-8"))
    assert schema.validar(manifiesto, carpeta) == []

    referencia = carpeta / "REFERENCIA.xlsx"
    _build.construir(manifiesto, referencia, carpeta)

    assert _titulos_por_fila(recepcion["xlsx"]) == _titulos_por_fila(referencia)


def test_el_pdf_de_recepcion_nombra_el_antes_y_el_despues(recepcion):
    texto = _texto_de_pdf(recepcion["pdf"])
    if texto is None:
        pytest.skip("pdftotext no esta disponible")
    for esperado in (layout.TITULO_COMPARATIVO, layout.TITULO_DANOS,
                     "ANTES · VISTA FRONTAL", "DESPUÉS · VISTA FRONTAL",
                     "EL EQUIPO RETORNÓ SIN 01 EXTINTOR DE 6 KG",
                     "RECUPERACIÓN 1", "JUNTA DE ESCAPE"):
        assert esperado in texto, esperado

    # La marca del tipo de documento tiene que decir RECEPCIÓN, no DESPACHO.
    assert "RECEPCIÓN" in texto

def test_la_recepcion_conserva_todas_las_vistas_del_despacho(tmp_path):
    """La rejilla del retorno es la misma que la de salida, foto o no foto.

    Si una vista sin foto de retorno desapareciera del acta, las dos dejarian
    de poder compararse, y una casilla vacia es justamente el dato de que esa
    vista no se fotografio al volver.
    """
    if CHROME is None:
        pytest.skip("no hay Chromium disponible")
    from nefer import schema

    fallos: list[str] = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=CHROME)
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True,
                              accept_downloads=True, permissions=[])
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fallos.append(str(e)))
        pg.goto(APP.as_uri())
        pg.wait_for_timeout(600)
        pg.click("#btn-demo")
        pg.wait_for_timeout(2500)
        despacho = json.loads(pg.input_value("#d-salida"))

        pg.click("#tab-recepcion")
        pg.wait_for_timeout(300)
        pg.click("#r-desde-despacho")
        pg.wait_for_timeout(800)
        # Sólo seis vistas fotografiadas de las diez que salieron.
        pg.evaluate("""async () => {
          const dt = new DataTransfer();
          for (let i = 1; i <= 6; i++) {
            const c = document.createElement('canvas'); c.width = 320; c.height = 240;
            const g = c.getContext('2d');
            g.fillStyle = '#3f4c58'; g.fillRect(0, 0, 320, 240);
            const b = await new Promise(r => c.toBlob(r, 'image/png'));
            dt.items.add(new File([b], 'R' + i + '.png', {type: 'image/png'}));
          }
          const i = document.querySelector('#r-f3');
          i.files = dt.files;
          i.dispatchEvent(new Event('change', {bubbles: true}));
        }""")
        pg.wait_for_timeout(2500)
        for k in range(6):
            pg.click("#r-tira .tile:first-child")
            pg.click(f"#r-vistas .slot:nth-child({k + 1})")
            pg.wait_for_timeout(60)

        pg.fill("#r-acta", "004-001157")
        pg.fill("#r-horometro", "1731.2")
        pg.fill("#r-resumen", "Retorna operativo; faltan cuatro vistas.")
        pg.wait_for_timeout(400)
        acta = json.loads(pg.input_value("#r-salida"))

        with pg.expect_download(timeout=90000) as espera:
            pg.click("#r-zip")
        paquete = tmp_path / espera.value.suggested_filename
        espera.value.save_as(paquete)
        nav.close()

    assert fallos == [], fallos

    salieron = [f["descripcion"] for f in despacho["registro_fotografico"]]
    volvieron = [f["descripcion"] for f in acta["registro_fotografico"]]
    assert volvieron == salieron, volvieron
    assert sum(1 for f in acta["registro_fotografico"] if f.get("archivo")) == 6

    # El acta incompleta sigue siendo valida: la casilla vacia es legitima.
    carpeta = tmp_path / "abierto"
    with zipfile.ZipFile(paquete) as z:
        z.extractall(carpeta)
    manifiesto = json.loads((carpeta / "acta.json").read_text(encoding="utf-8"))
    assert schema.validar(manifiesto, carpeta) == []

    # Y la herramienta de escritorio imprime las diez casillas con su rotulo.
    openpyxl = pytest.importorskip("openpyxl")
    referencia = carpeta / "REFERENCIA.xlsx"
    build.construir(manifiesto, referencia, carpeta)
    ws = openpyxl.load_workbook(referencia).active
    impresos = []
    for franja in range(5):
        fila = layout.bloque_foto(franja)["fila_rotulo"]
        impresos.append(ws[f"{layout.PANEL_IZQ[0]}{fila}"].value)
        impresos.append(ws[f"{layout.PANEL_DER[0]}{fila}"].value)
    assert impresos == salieron, impresos

def test_las_vistas_de_la_app_son_las_de_layout():
    """La app y la herramienta de escritorio tienen que ofrecer las mismas.

    Si divergen, un acta levantada en el telefono deja de encajar en el
    formato que imprime la computadora.
    """
    # Hay otra `var VISTAS` en el nucleo, con los nombres de las pestañas: se
    # ancla en la que declara las familias de equipo.
    bloque = re.search(r"var VISTAS = \{\s*\n\s*grupo_electrogeno:(.*?)\n  \};",
                       FUENTE, re.S)
    assert bloque, "no se encontro la tabla de vistas de la app"

    leidas: dict[str, list[str]] = {}
    cuerpo_completo = "grupo_electrogeno:" + bloque.group(1)
    for familia, cuerpo in re.findall(r"(\w+):\s*\[(.*?)\]", cuerpo_completo, re.S):
        leidas[familia] = re.findall(r'"([^"]+)"', cuerpo)

    assert leidas == layout.VISTAS_POR_CATEGORIA


def test_el_selector_de_familias_ofrece_todas():
    opciones = set(re.findall(r'<option value="(\w+)">', FUENTE))
    assert layout.VISTAS_POR_CATEGORIA.keys() <= opciones, \
        sorted(layout.VISTAS_POR_CATEGORIA.keys() - opciones)


def test_el_catalogo_de_accesorios_esta_publicado():
    """El operador elige de una lista; sin ella hay que teclearlo todo."""
    bloque = re.search(r"var ACCESORIOS = \[(.*?)\];", FUENTE, re.S)
    assert bloque, "no se encontro el catalogo de accesorios"
    items = re.findall(r'"((?:[^"\\]|\\.)*)"', bloque.group(1))
    assert len(items) >= 15, items
    # Los que aparecen en las actas reales que sirvieron de plantilla.
    for esperado in ("BARRA PUESTA A TIERRA", "GATA DE TIRO", "CHAPA DE PUERTA",
                     "ESTROBO DE SEGURIDAD", "GOMA DE ACOPLE TIPO CHICAGO"):
        assert esperado in items, esperado


def test_la_recepcion_arranca_sin_acta_de_despacho(tmp_path):
    """En el patio nadie lleva el acta.json del despacho en el telefono."""
    if CHROME is None:
        pytest.skip("no hay Chromium disponible")
    from nefer import schema

    fallos: list[str] = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=CHROME)
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True,
                              accept_downloads=True, permissions=[])
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fallos.append(str(e)))
        pg.goto(APP.as_uri())
        pg.wait_for_timeout(600)
        pg.click("#tab-recepcion")
        pg.wait_for_timeout(300)

        pg.select_option("#r-cat", "compresor")
        pg.click("#r-empezar")
        pg.wait_for_timeout(600)

        rotulos = pg.eval_on_selector_all("#r-vistas .slot .cap span:first-child",
                                          "n => n.map(x => x.textContent)")
        assert rotulos == layout.VISTAS_POR_CATEGORIA["compresor"], rotulos

        pg.evaluate("""async () => {
          const dt = new DataTransfer();
          for (let i = 1; i <= 9; i++) {
            const c = document.createElement('canvas'); c.width = 320; c.height = 240;
            const g = c.getContext('2d');
            g.fillStyle = '#3f4c58'; g.fillRect(0, 0, 320, 240);
            const b = await new Promise(r => c.toBlob(r, 'image/png'));
            dt.items.add(new File([b], 'R' + i + '.png', {type: 'image/png'}));
          }
          const i = document.querySelector('#r-f3');
          i.files = dt.files;
          i.dispatchEvent(new Event('change', {bubbles: true}));
        }""")
        pg.wait_for_timeout(3000)
        for k in range(9):
            pg.click("#r-tira .tile:first-child")
            pg.click(f"#r-vistas .slot:nth-child({k + 1})")
            pg.wait_for_timeout(60)

        # Un accesorio del catalogo, no retornado: genera recuperacion.
        pg.click("#r-add-cons")
        pg.wait_for_timeout(300)
        pg.fill("#r-consumibles .par:last-child [data-cons-nombre]",
                'CONOS DE SEGURIDAD DE 28"')
        pg.click("#r-consumibles .par:last-child .estados button[data-e='NO_RETORNA']")
        pg.wait_for_timeout(300)

        for campo, valor in (("#r-acta", "000-000001"), ("#r-horometro", "1700.87"),
                             ("#r-cliente", "CLIENTE DE PRUEBA S.A.C."),
                             ("#r-codigo_equipo", "C000-00"),
                             ("#r-modelo_equipo", "COMPRESOR TRANSPORTABLE DE 375 CFM"),
                             ("#r-resumen", "Retorna operativo; faltan los conos.")):
            pg.fill(campo, valor)
        pg.wait_for_timeout(400)

        with pg.expect_download(timeout=90000) as espera:
            pg.click("#r-zip")
        paquete = tmp_path / espera.value.suggested_filename
        espera.value.save_as(paquete)
        nav.close()

    assert fallos == [], fallos

    carpeta = tmp_path / "abierto"
    with zipfile.ZipFile(paquete) as z:
        z.extractall(carpeta)
    manifiesto = json.loads((carpeta / "acta.json").read_text(encoding="utf-8"))
    assert schema.validar(manifiesto, carpeta) == []
    assert manifiesto["encabezado"]["categoria"] == "compresor"
    assert manifiesto["encabezado"]["tipo_documento"] == "RECEPCION"
    assert len(manifiesto["registro_fotografico"]) == 9

    # Y el acta imprime la recuperacion del accesorio que no volvio.
    openpyxl = pytest.importorskip("openpyxl")
    referencia = carpeta / "REFERENCIA.xlsx"
    build.construir(manifiesto, referencia, carpeta)
    ws = openpyxl.load_workbook(referencia).active
    bandas = [ws.cell(row=f, column=1).value for f in range(1, ws.max_row + 1)]
    assert any(isinstance(v, str) and v.startswith("RECUPERACIÓN 1") for v in bandas)
