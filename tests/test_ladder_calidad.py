"""La revisión de calidad de LadderLab: las reglas de la skill plc-code-analysis
(Czarnak/totally-integrated-claude) que se pueden comprobar sobre un programa LAD.

- Ninguna solución de referencia tiene observaciones ALTA, MEDIA ni BAJA: lo
  que la app enseña tiene que pasar su propio revisor.
- Cada regla detecta el error que dice detectar, con un programa que lo tiene.
- La revisión aparece en la app al comprobar un reto y en el laboratorio.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from navegador import HAY_CHROMIUM, opciones  # noqa: E402

APP = RAIZ / "docs" / "ladder"
pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")


@pytest.fixture(scope="module")
def pag():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        p = nav.new_page(viewport={"width": 1360, "height": 900})
        errores = []
        p.on("pageerror", lambda e: errores.append(str(e)))
        p.on("dialog", lambda d: d.accept())
        p.goto((APP / "index.html").as_uri())
        p.wait_for_selector(".hero")
        yield p
        assert not errores, errores
        nav.close()


def test_las_soluciones_pasan_su_propio_revisor(pag):
    malas = pag.evaluate("""LECCIONES.filter(l => l.reto).flatMap(l => revisarCalidad(l.reto.solucion, l.reto.tags)
        .filter(h => h.sev !== 'INFO').map(h => l.id + ': ' + h.sev + ' ' + h.titulo + ' (' + h.donde + ')'))""")
    assert not malas, malas


CASOS = {
    "Doble asignación de una bobina": "[SEG('', S(NO('%I0.0'), COIL('%Q0.0'))), SEG('', S(NO('%I0.1'), COIL('%Q0.0')))]",
    "Se escribe en una entrada": "[SEG('', S(NO('%I0.1'), COIL('%I0.0')))]",
    "Set sin Reset": "[SEG('', S(NO('%I0.0'), SET('%Q0.0')))]",
    "Bobina y Set/Reset sobre la misma señal": "[SEG('', S(NO('%I0.0'), COIL('%Q0.0'))), SEG('', S(NO('%I0.1'), RST('%Q0.0')))]",
    "Instancia de temporizador o contador reutilizada": "[SEG('', S(NO('%I0.0'), TON('T1','T#1s'), COIL('%Q0.0'))), SEG('', S(NO('%I0.1'), TON('T1','T#2s'), COIL('%Q0.1')))]",
    "Bit de flanco compartido": "[SEG('', S(PC('%I0.0','%M10.0'), COIL('%Q0.0'))), SEG('', S(PC('%I0.1','%M10.0'), COIL('%Q0.1')))]",
    "Bit de flanco escrito por el programa": "[SEG('', S(PC('%I0.0','%M10.0'), COIL('%Q0.0'))), SEG('', S(NO('%I0.1'), COIL('%M10.0')))]",
    "Se lee una señal que nada escribe": "[SEG('', S(NO('%M5.0'), COIL('%Q0.0')))]",
    "Se lee una instancia que no existe": "[SEG('', S(NO('T9.Q'), COIL('%Q0.0')))]",
}


@pytest.mark.parametrize("titulo", list(CASOS))
def test_cada_regla_detecta_su_error(pag, titulo):
    titulos = pag.evaluate(f"revisarCalidad({CASOS[titulo]}, []).map(h => h.titulo)")
    assert titulo in titulos, titulos


def test_analogica_en_bruto_sin_vigilar_y_vigilada(pag):
    sin = pag.evaluate("revisarCalidad([SEG('', S(CMP('>', '%IW64', '100'), COIL('%Q0.0')))], [TAG('%IW64','Nivel','analog'), TAG('%Q0.0','B')]).map(h => h.titulo)")
    assert "Entrada analógica sin vigilancia de rango" in sin
    con = pag.evaluate("revisarCalidad([SEG('', S(CMP('>', '%IW64', '100'), COIL('%Q0.0'))), SEG('', S(CMP('>', '%IW64', '27648'), COIL('%Q0.1')))], [TAG('%IW64','Nivel','analog'), TAG('%Q0.0','B'), TAG('%Q0.1','A')]).map(h => h.titulo)")
    assert "Entrada analógica sin vigilancia de rango" not in con
    kw = pag.evaluate("revisarCalidad([SEG('', S(CMP('>', '%IW64', '100'), COIL('%Q0.0')))], [TAG('%IW64','Carga','analog','',{unit:'kW'}), TAG('%Q0.0','B')]).length")
    assert kw == 0, "una medida ya en unidades de ingeniería no es una señal en bruto"


def test_el_error_a_proposito_de_la_leccion_de_oficio_se_detecta(pag):
    t = pag.evaluate("(() => { const L = LECCIONES.find(l => l.id === 'oficio'); return revisarCalidad(L.ejemplo.prog, L.ejemplo.tags).map(h => h.sev + ' ' + h.titulo); })()")
    assert "ALTA Doble asignación de una bobina" in t


def test_la_revision_aparece_en_el_reto_y_en_el_laboratorio(pag):
    pag.goto((APP / "index.html").as_uri() + "#/l/enclavamiento")
    pag.click('.tabs button[data-t="reto"]')
    pag.click(".b-sol")
    pag.click(".b-chk")
    assert "Revisión de calidad" in pag.inner_text(".reto .out")
    assert "Sin observaciones" in pag.inner_text(".reto .out")
    pag.goto((APP / "index.html").as_uri() + "#/lab")
    pag.click(".b-cal")
    assert "Revisión de calidad" in pag.inner_text(".calbox")
