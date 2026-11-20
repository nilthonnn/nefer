"""Tablero de transferencia de tres interruptores, bloque de motor de mina y
la guía «¿Cómo se resuelve?».

- Cada reto nuevo pasa con su solución (con ciclos exactos e irregulares) y
  no pasa con el programa inicial.
- El corrector rechaza los errores típicos: sin enclavamiento, sin separar
  local/remoto, sin congelar en manual, sin transición con retardo…
- La guía explica cada segmento de cada solución con los nombres de las
  variables, y el panel se abre y avanza paso a paso en la app.
- La ruta de mina avisa que sus escenarios son de ejemplo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from navegador import HAY_CHROMIUM, opciones  # noqa: E402

APP = RAIZ / "docs" / "ladder"
NUEVOS = ("tta3_leds", "tta3_manual", "tta3_auto", "motor")

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


def _corregir(pag, id_, prog_js, irregular=False):
    return pag.evaluate(
        """([id, prog, irr]) => { const R = LECCIONES.find(l => l.id === id).reto;
           const g = grade(R, eval(prog), irr ? { irregular: true } : undefined), u = g.res[g.res.length - 1];
           return { ok: g.ok, paso: g.res.length, motivo: u.bad || u.wrong.map(w => w.n).join(", ") }; }""",
        [id_, prog_js, irregular])


def test_orden_de_niveles(pag):
    niveles = pag.evaluate("NIVELES.map(n => n.id)")
    assert niveles[-3:] == ["proyectos", "tablero", "energia"]
    ids = pag.evaluate("LECCIONES.map(l => l.id)")
    assert ids.index("tta3_leds") < ids.index("tta3_manual") < ids.index("tta3_auto") < ids.index("motor") < ids.index("grupo")


@pytest.mark.parametrize("id_", NUEVOS)
@pytest.mark.parametrize("irregular", [False, True])
def test_la_solucion_pasa(pag, id_, irregular):
    r = _corregir(pag, id_, "clone(R.solucion)", irregular)
    assert r["ok"], r


@pytest.mark.parametrize("id_", NUEVOS)
def test_el_inicio_no_pasa(pag, id_):
    assert not _corregir(pag, id_, "clone(R.inicio)")["ok"]


ERRORES = {
    "LED abierto con contacto NA": ("tta3_leds", "(()=>{const s=clone(R.solucion); s[0].net.items[0]=NO('%I0.2'); return s;})()", "LED_CB001_Abierto"),
    "mando manual sin enclavamiento": ("tta3_manual", "(()=>{const s=clone(R.solucion); s[1].net.items.splice(2,1); return s;})()", "a la vez"),
    "mando manual sin Mando_Local": ("tta3_manual", "(()=>{const s=clone(R.solucion); s[1].net.items[0].br[0].items.splice(0,1); return s;})()", "tensión residual"),
    "automático sin congelar en manual": ("tta3_auto", "(()=>{const s=clone(R.solucion); s[7].net=S(NO('%I0.5'),NO('%M0.2'),NO('%I0.1'),NC('%I0.2'),COIL('%Q0.1')); return s;})()", "Cmd_CB002"),
    "libera el grupo en manual": ("tta3_auto", "(()=>{const s=clone(R.solucion); s[5].net.items.splice(0,1); return s;})()", "Arranque_Gen"),
    "automático sin transición con retardo": ("tta3_auto", "(()=>{const s=clone(R.solucion); s[8].net.items[0].br[0].items.splice(4,1); return s;})()", "tensión residual"),
    "motor sin separar local y remoto": ("motor", "(()=>{const s=clone(R.solucion); s[0].net.items[0]=P([NO('%I0.7')],[P([NO('%I0.1')],[NO('%Q0.0')]),NO('%I0.2')]); return s;})()", "Contactor"),
    "motor sin permisivo": ("motor", "(()=>{const s=clone(R.solucion); s[0].net.items.splice(1,1); return s;})()", "Contactor"),
    "motor sin falla de confirmación": ("motor", "(()=>{const s=clone(R.solucion); s.splice(1,1); return s;})()", "Falla_Arranque"),
}


@pytest.mark.parametrize("nombre", list(ERRORES))
def test_el_corrector_rechaza_errores_tipicos(pag, nombre):
    id_, prog, motivo = ERRORES[nombre]
    r = _corregir(pag, id_, prog)
    assert not r["ok"], f"{nombre}: el corrector lo dejó pasar"
    assert motivo in r["motivo"], r


def test_la_guia_explica_cada_segmento_de_cada_solucion(pag):
    malos = pag.evaluate("""LECCIONES.filter(l => l.reto).flatMap(l => l.reto.solucion.map((s, i) => {
        const x = explicarSegmento(s, l.reto.tags);
        return (/→ ./.test(x.texto) && !/undefined|«\\?»/.test(x.texto)) ? null : l.id + ' #' + (i + 1) + ': ' + x.texto; })).filter(Boolean)""")
    assert not malos, malos


def test_las_notas_de_la_guia_apuntan_a_segmentos_que_existen(pag):
    malas = pag.evaluate("""LECCIONES.filter(l => l.reto && l.reto.guia && l.reto.guia.notas).flatMap(l =>
        Object.keys(l.reto.guia.notas).filter(k => !(+k < l.reto.solucion.length)).map(k => l.id + ' nota ' + k))""")
    assert not malas, malas


def test_el_panel_de_la_guia_avanza_paso_a_paso(pag):
    pag.goto((APP / "index.html").as_uri() + "#/l/tta3_manual")
    pag.click('.tabs button[data-t="reto"]')
    pag.click(".b-guia")
    assert pag.is_visible(".guia") and "Estrategia" in pag.inner_text(".guia")
    total = pag.evaluate("LECCIONES.find(l => l.id === 'tta3_manual').reto.solucion.length")
    for i in range(total):
        pag.click(".b-gsig")
    assert pag.locator(".guia .paso").count() == total
    assert pag.locator(".guia .paso svg").count() == total
    assert "Mando_Local" in pag.inner_html(".guia") or "Mando Local" in pag.inner_text(".guia")


def test_la_ruta_de_mina_avisa_que_es_un_escenario_de_ejemplo(pag):
    sin_aviso = pag.evaluate("LECCIONES.filter(l => l.nivel === 'energia' && !/de ejemplo/.test((l.mina || '') + l.teoria)).map(l => l.id)")
    assert not sin_aviso, sin_aviso
    assert pag.evaluate("LECCIONES.filter(l => l.nivel === 'tablero').every(l => /foto/i.test(l.teoria))")


@pytest.mark.parametrize("ruta", ["#/", "#/l/enclavamiento", "#/l/tta3_auto", "#/lab", "#/ref"])
def test_lo_oculto_no_se_ve(pag, ruta):
    """`.btn` fijaba display y pisaba el atributo hidden: el botón «Instalar» y
    «+ Segmento» se veían donde no servían. La auditoría de completitud lo
    encontró en una captura del manual."""
    pag.goto((APP / "index.html").as_uri() + ruta)
    pag.wait_for_timeout(300)
    assert pag.evaluate("Array.from(document.querySelectorAll('[hidden]')).filter(e => getComputedStyle(e).display !== 'none').length") == 0
