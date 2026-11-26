"""Los formatos en PDF: informe técnico, ficha de trabajo, check-list y anexo."""

from __future__ import annotations

import base64
import re
import shutil
import subprocess

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402
from PIL import Image  # noqa: E402

from datos_mant import EQUIPOS  # noqa: E402
from navegador import HAY_CHROMIUM  # noqa: E402
from test_app_navegador import _contexto, _lanzar, servidor  # noqa: E402,F401

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")


@pytest.fixture(scope="module")
def pw():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="module")
def orden(pw, servidor, tmp_path_factory):
    """Una orden del C450D6 llena como en el papel de referencia."""
    d = tmp_path_factory.mktemp("doc")
    fotos = []
    for n, color in (("radiador.jpg", (40, 80, 120)), ("horometro.jpg", (120, 80, 40))):
        Image.new("RGB", (1600, 1200), color).save(d / n, "JPEG")
        fotos.append(str(d / n))
    nav = _lanzar(pw)
    pg = _contexto(nav).new_page()
    pg.goto(servidor)
    pg.wait_for_function("() => window.MANT && MANT.documentos")
    pg.evaluate("e => CAMPO.almacen.equipos.guardar(e)", EQUIPOS["C450D6"])
    pg.evaluate("() => MANT.ordenes.crear('C450D6', 'PREVENTIVO', 'PM2_500', '4017300492')")
    pg.click("#tab-mantenimiento")
    pg.click("[data-accion=confirmar]")
    pg.set_input_files("#m-o-foto-c15", fotos[0])
    pg.wait_for_selector("[data-casilla=c15] img")
    pg.set_input_files("#m-o-foto-c06", fotos[1])
    pg.wait_for_selector("[data-casilla=c06] img")
    pg.click("[data-estado-foto=c15][data-valor=OBS]")
    pg.fill("#m-o-estados-c15-nota", "Panal con polvo, se limpió")
    pg.evaluate("""() => {
      const set = (sel, v) => { const n = document.querySelector(sel); n.value = v;
        n.dispatchEvent(new Event('input', {bubbles: true})); n.dispatchEvent(new Event('change', {bubbles: true})); };
      set('#m-o-informe-cliente', 'MINERA DE PRUEBA');
      set('#m-o-informe-generalidades-voltaje', '441');
      set('#m-o-informe-generalidades-velocidad', '1800');
      set('#m-o-informe-generalidades-frecuencia', '60');
      set('#m-o-informe-repuestos-5-1', '1');
      set('#m-o-informe-pruebas-1-voltajeLL', '441');
      set('#m-o-ot-descripcion', 'INSP. RUTINARIA T9_PLATAFORMA_C450D6');
      set('#m-o-ot-defectoReco', 'Sin defecto detectado');
      set('#m-o-ot-observaciones', 'Limpieza de radiador y arranque en vacío.');
      set('#m-o-ot-firmas-tecnico-nombre', 'Técnico eléctrico');
    }""")
    for k in ["3.1", "3.2", "3.3"]:
        pg.click(f"[data-estado='informe.motor.{k}'][data-valor=OK]")
    pg.click("[data-sn='informe.operativo'][data-valor=true]")
    pg.click("[data-accion=bat-agregar]")
    pg.check("input[name=m-o-bat-tipo][value=LIBRE_MANTENIMIENTO]")
    pg.click("[data-estado='baterias.0.items.14'][data-valor=OK]")
    yield pg
    nav.close()


def _pdf(pg, cuales, tmp_path, nombre):
    b64 = pg.evaluate("""async (c) => { const b = await MANT.documentos.pdf(MANT.ordenes.actual(), c);
      const u = new Uint8Array(await b.arrayBuffer()); let s = '';
      for (let i = 0; i < u.length; i += 8192) s += String.fromCharCode.apply(null, u.subarray(i, i + 8192));
      return btoa(s); }""", cuales)
    datos = base64.b64decode(b64)
    ruta = tmp_path / nombre
    ruta.write_bytes(datos)
    return datos, ruta


def _texto(ruta):
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext no esta disponible")
    return subprocess.run(["pdftotext", "-layout", str(ruta), "-"], capture_output=True, text=True).stdout


def _paginas(datos):
    return len(re.findall(rb"/Type /Page[^s]", datos))


def test_informe_tecnico_secciones_1_a_8(orden, tmp_path):
    datos, ruta = _pdf(orden, ["informe"], tmp_path, "informe.pdf")
    assert datos.startswith(b"%PDF-") and _paginas(datos) == 2
    t = _texto(ruta)
    for esperado in ("INFORME TÉCNICO DE GRUPO ELECTRÓGENO", "MINERA DE PRUEBA", "4017300492",
                     "C450D6 / A18T042328", "HCI534E1 / X17L492615", "1. Generalidades", "441", "1800",
                     "2. Tipo de servicio", "3. Inspección del motor", "3.1. Nivel de aceite",
                     "4. Inspección de Generador", "Mantenimiento de exitatriz", "5.1. Filtro de aceite",
                     "3.1. Nivel de aceite OK", "5.1. Filtro de aceite 1",
                     "6. Parámetros de operación y prueba", "VALOR INICIAL", "Voltaje AC (Vac)",
                     "7. Observaciones", "Panal con polvo", "8. Grupo operativo", "POR LA EMPRESA", "CLIENTE"):
        assert esperado in t, esperado


def test_ficha_de_trabajo_con_desviaciones(orden, tmp_path):
    datos, ruta = _pdf(orden, ["ficha"], tmp_path, "ficha.pdf")
    assert _paginas(datos) == 2
    t = _texto(ruta)
    for esperado in ("Ficha de trabajo para Mantenimiento", "N° Orden 4017300492", "INSP. RUTINARIA",
                     "Tarea Real (Resumen Hrs Hombre)", "Descripción de Defecto RECO", "Sin defecto detectado",
                     "Crear Aviso (S/N)", "Persona Realizando Tarea", "Técnico eléctrico",
                     "Hacer notificación final y Cierre Técnico", "Desviaciones", "Demora: Traslado y sin transp."):
        assert esperado in t, esperado


def test_check_list_y_anexo(orden, tmp_path):
    datos, ruta = _pdf(orden, ["baterias"], tmp_path, "bat.pdf")
    t = _texto(ruta)
    for esperado in ("CHECK-LIST DE BATERÍAS", "C450D6", "Baterías de Libre Mantenimiento",
                     "Verificación de estados de alerta", "PM2 500", "Leyenda"):
        assert esperado in t, esperado
    datos, ruta = _pdf(orden, ["anexo"], tmp_path, "anexo.pdf")
    assert len(re.findall(rb"/Subtype /Image", datos)) == 2, "las dos fotos"
    t = _texto(ruta)
    assert "ANEXO FOTOGRÁFICO" in t and "c15 · Radiador" in t and "Observado: Panal con polvo" in t


def test_todo_en_un_pdf_desde_el_boton(orden, tmp_path):
    datos, _ = _pdf(orden, ["informe", "ficha", "baterias", "anexo"], tmp_path, "todo.pdf")
    assert _paginas(datos) == 2 + 2 + 1 + 1
    with orden.expect_download() as d:
        orden.click("[data-doc=todo]")
    assert d.value.suggested_filename == "documentos-C450D6-OT4017300492.pdf"


def test_los_items_con_punto_se_guardan(orden):
    """«3.1», «4.1.1», «5.1»: la ruta del campo no se parte en cada punto."""
    m = orden.evaluate("() => MANT.ordenes.actual().informe")
    assert m["motor"]["3.1"] == "OK" and m["motor"]["3.3"] == "OK"
    assert m["repuestos"]["5.1"] == "1"
    orden.click("[data-estado='informe.generadorTablero.4.1.6'][data-valor=NO]")
    assert orden.evaluate("() => MANT.ordenes.actual().informe.generadorTablero['4.1.6']") == "NO"
    assert "3" not in m["motor"], "no deja claves partidas"
