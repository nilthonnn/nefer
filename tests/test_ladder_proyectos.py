"""Los proyectos integradores de LadderLab: la línea de transferencia.

Dos fajas, un cilindro neumático y cuatro sensores, con un modelo de planta que
mueve las cajas. Se prueba lo que un alumno o un cambio en el modelo pueden
romper sin que nadie lo note:

- que cada reto pase con su solución, también con ciclos de scan irregulares
  (en vivo el navegador no entrega ciclos de 10 ms exactos: así apareció una
  carrera entre el fin de carrera y la transferencia de la caja);
- que el programa inicial no pase;
- que el corrector rechace los errores típicos, cada uno por su motivo;
- que en el simulador en vivo, con el programa del ejemplo, la línea
  despache cajas sin fallas de planta.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from navegador import HAY_CHROMIUM, opciones  # noqa: E402

APP = RAIZ / "docs" / "ladder"
RETOS = ("linea", "diagnostico", "lote", "falla_cilindro")

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")


@pytest.fixture(scope="module")
def pag():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        p = nav.new_page()
        errores = []
        p.on("pageerror", lambda e: errores.append(str(e)))
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


def test_nivel_y_orden(pag):
    niveles = pag.evaluate("NIVELES.map(n => n.id)")
    assert niveles.index("proyectos") == niveles.index("avanzado") + 1 < niveles.index("energia")
    ids = pag.evaluate("LECCIONES.map(l => l.id)")
    assert [i for i in ids if i in RETOS] == list(RETOS)
    assert ids.index("falla_cilindro") < ids.index("grupo"), "los proyectos van antes de la ruta minera"


@pytest.mark.parametrize("id_", RETOS)
@pytest.mark.parametrize("irregular", [False, True])
def test_la_solucion_pasa(pag, id_, irregular):
    r = _corregir(pag, id_, "clone(R.solucion)", irregular)
    assert r["ok"], r


@pytest.mark.parametrize("id_", RETOS)
def test_el_inicio_no_pasa(pag, id_):
    assert not _corregir(pag, id_, "clone(R.inicio)")["ok"]


ERRORES = {
    "faja 1 sin el permiso del cilindro": ("linea", "(()=>{const s=clone(R.solucion); s[2].net.items.splice(3,1); return s;})()", "Faja_1"),
    "faja 1 sin esperar al sensor 2": ("linea", "(()=>{const s=clone(R.solucion); s[2].net.items.splice(2,1); return s;})()", "Choque en la transferencia"),
    "cilindro sin autorretención": ("linea", "(()=>{const s=clone(R.solucion); s[3].net.items[1]=NO('%I0.2'); return s;})()", "Cilindro"),
    "sin retorno": ("linea", "(()=>{const s=clone(R.solucion); s.splice(4,1); return s;})()", "Cilindro"),
    "lote sin detener la faja 1": ("lote", "(()=>{const s=clone(R.solucion); s[2].net.items.splice(4,1); return s;})()", "Faja_1"),
    "falla sin retirar la orden": ("falla_cilindro", "(()=>{const s=clone(R.solucion); s[3].net.items.splice(3,1); return s;})()", "Cilindro"),
}


@pytest.mark.parametrize("nombre", list(ERRORES))
def test_el_corrector_rechaza_errores_tipicos(pag, nombre):
    id_, prog, motivo = ERRORES[nombre]
    r = _corregir(pag, id_, prog)
    assert not r["ok"], f"{nombre}: el corrector lo dejó pasar"
    assert motivo in r["motivo"], r


def test_el_diagnostico_trae_dos_errores_distintos_de_la_solucion(pag):
    dif = pag.evaluate("""(() => { const R = LECCIONES.find(l => l.id === 'diagnostico').reto;
        return R.inicio.map((s, i) => JSON.stringify(s) !== JSON.stringify(R.solucion[i])).filter(Boolean).length; })()""")
    assert dif == 2


def test_en_vivo_despacha_sin_fallas(pag):
    """El simulador real, con su reloj irregular: Partida y 12 s de producción."""
    pag.goto((APP / "index.html").as_uri() + "#/l/linea")
    pag.wait_for_selector(".hmi svg")
    b = pag.locator('.in[data-a="%I0.1"] .pb')
    b.dispatch_event("pointerdown", {"pointerId": 3})
    pag.wait_for_timeout(200)
    b.dispatch_event("pointerup", {"pointerId": 3})
    pag.wait_for_timeout(12000)
    estado = pag.evaluate("({ f: SIM.eng.fault, e: SIM.eng.ps.empujes, d: SIM.eng.ps.despachadas })")
    assert estado["f"] is None, estado
    assert estado["e"] >= 2, estado
    assert "Cajas despachadas" in pag.inner_html(".hmi")
