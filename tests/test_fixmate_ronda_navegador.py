"""La ronda CIL en un navegador de verdad, a tamaño de teléfono.

Lo que se prueba aquí no es que los botones pinten: es que las tres
decisiones de diseño que vienen del guante y del socavón sobrevivan a un
navegador real.

1. «No pude ver» tiene que ser **igual de fácil de tocar** que «OK». Si es
   más chico o está más abajo, el operador marca OK, y un OK falso contamina
   la ronda entera.
2. Un punto a la vez, a pantalla completa, sin scroll para contestar.
3. El reloj mide, pero el tiempo que el operador tarda en **escribir la
   nota** no es tiempo de inspección.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from navegador import HAY_CHROMIUM, opciones  # noqa: E402

APP = RAIZ / "docs" / "fixmate" / "ronda" / "index.html"

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")


@pytest.fixture(scope="module")
def pagina():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        navegador = pw.chromium.launch(**opciones())
        ctx = navegador.new_context(viewport={"width": 390, "height": 844})
        pag = ctx.new_page()
        errores = []
        pag.on("pageerror", lambda e: errores.append(str(e)))
        pag.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
        pag.goto(APP.as_uri())
        yield pag, errores
        navegador.close()


def _arrancar(pag, operador="J. Quispe"):
    """Carga la pauta de ejemplo y entra al primer punto."""
    pag.goto(APP.as_uri())
    pag.click("#demo")
    pag.fill("#op", operador)
    pag.click("#ir")


def test_la_pauta_de_ejemplo_va_detras_de_un_boton_que_dice_que_es_inventada(pagina):
    # Mezclada con una pauta de verdad, el operador registraría una ronda
    # sobre una máquina que no existe.
    pag, _ = pagina
    pag.goto(APP.as_uri())
    texto = pag.inner_text("#demo")
    assert "inventado" in texto.lower()
    assert "EX-220" in texto


def test_una_ronda_no_empieza_sin_responsable(pagina):
    pag, _ = pagina
    pag.goto(APP.as_uri())
    pag.click("#demo")
    pag.click("#ir")
    # Sigue en la pantalla del operador: no avanzó.
    assert pag.locator("#op").count() == 1


def test_los_tres_botones_miden_lo_mismo_y_caben_en_pantalla(pagina):
    # La prueba que más importa de este archivo.
    pag, _ = pagina
    _arrancar(pag)
    cajas = [pag.locator(f'button[data-r="{r}"]').bounding_box()
             for r in ("ok", "nok", "sin_acceso")]
    anchos = [round(c["width"]) for c in cajas]
    altos = [round(c["height"]) for c in cajas]
    assert min(altos) >= 56, f"algún botón baja de 56 px: {altos}"
    assert max(anchos) - min(anchos) <= 1, f"no miden lo mismo: {anchos}"
    assert max(altos) - min(altos) <= 1, f"no miden lo mismo de alto: {altos}"
    # Y el tercero entra sin desplazar la pantalla.
    fondo = cajas[2]["y"] + cajas[2]["height"]
    assert fondo <= pag.viewport_size["height"] + 1, f"«no pude ver» queda fuera: {fondo}"


def test_un_punto_a_la_vez_y_avanza_al_contestar(pagina):
    pag, _ = pagina
    _arrancar(pag)
    assert pag.inner_text("#paso") == "1 / 5"
    primero = pag.inner_text(".punto")
    pag.click('button[data-r="ok"]')
    assert pag.inner_text("#paso") == "2 / 5"
    assert pag.inner_text(".punto") != primero


def test_el_criterio_esta_a_la_vista_sin_desplazar(pagina):
    pag, _ = pagina
    _arrancar(pag)
    caja = pag.locator(".criterio").bounding_box()
    assert caja["y"] + caja["height"] <= pag.viewport_size["height"]
    assert pag.inner_text(".criterio").strip()


def test_un_punto_sin_ver_deja_la_ronda_incompleta(pagina):
    pag, _ = pagina
    _arrancar(pag)
    pag.click('button[data-r="ok"]')
    pag.click('button[data-r="ok"]')
    pag.click('button[data-r="sin_acceso"]')
    pag.click("text=Guarda cerrada")
    pag.click("#listo")
    pag.click('button[data-r="ok"]')
    pag.click('button[data-r="ok"]')
    cuerpo = pag.inner_text("body")
    assert "Ronda incompleta" in cuerpo
    assert "no cuenta como visto" in cuerpo


def test_una_anomalia_fuera_del_alcance_sale_marcada_para_el_tecnico(pagina):
    pag, _ = pagina
    _arrancar(pag)
    pag.click('button[data-r="ok"]')      # 1 panel
    pag.click('button[data-r="ok"]')      # 2 visor
    pag.click('button[data-r="nok"]')     # 3 freno: alcance_operador false
    assert "vaya el tecnico" in pag.inner_text(".velo")
    pag.fill("#nota", "El pedal se va al fondo")
    pag.click("#listo")
    pag.click('button[data-r="ok"]')
    pag.click('button[data-r="ok"]')
    cuerpo = pag.inner_text("body")
    assert "El pedal se va al fondo" in cuerpo
    assert "detiene" in cuerpo.lower() or "Se detiene" in cuerpo


def test_escribir_la_nota_no_cuenta_como_tiempo_de_inspeccion(pagina):
    # Los segundos se toman al TOCAR el botón, antes de abrir el diálogo.
    pag, _ = pagina
    _arrancar(pag)
    pag.click('button[data-r="nok"]')
    pag.wait_for_timeout(2500)            # el operador tarda en escribir
    pag.fill("#nota", "Panal tapado")
    pag.click("#listo")
    for _ in range(4):
        pag.click('button[data-r="ok"]')
    # Con 2,5 s de escritura, si contaran, la ronda no saldría sospechosa.
    assert "Demasiado rapida" in pag.inner_text("body")


def test_una_ronda_entera_a_toques_se_marca_sospechosa(pagina):
    pag, _ = pagina
    _arrancar(pag)
    for _ in range(5):
        pag.click('button[data-r="ok"]')
    cuerpo = pag.inner_text("body")
    assert "Ronda completa" in cuerpo
    assert "Demasiado rapida" in cuerpo
    assert "no una norma" in cuerpo       # el criterio es de planta


def test_la_ronda_se_puede_guardar_como_archivo_para_la_oficina(pagina):
    pag, _ = pagina
    _arrancar(pag)
    for _ in range(5):
        pag.click('button[data-r="ok"]')
    with pag.expect_download() as bajada:
        pag.click("#bajar")
    descarga = bajada.value
    assert descarga.suggested_filename.endswith(".json")

    import json
    destino = Path(descarga.path())
    datos = json.loads(destino.read_text(encoding="utf-8"))
    assert datos["ejecucion"]["operador"] == "J. Quispe"
    assert len(datos["ejecucion"]["items"]) == 5
    assert datos["estado"]["completa"] is True


def test_el_archivo_que_sale_del_telefono_lo_lee_la_oficina(pagina, tmp_path):
    # El circuito completo: lo que el teléfono exporta tiene que entrar por
    # el cargador de Python sin tocarlo a mano.
    import json

    from nefer.fixmate import cargador
    from nefer.fixmate.tpm import estado

    pag, _ = pagina
    _arrancar(pag, "R. Mamani")
    pag.click('button[data-r="nok"]')
    pag.fill("#nota", "Panal tapado con tierra")
    pag.click("#listo")
    for _ in range(4):
        pag.click('button[data-r="ok"]')
    with pag.expect_download() as bajada:
        pag.click("#bajar")
    datos = json.loads(Path(bajada.value.path()).read_text(encoding="utf-8"))

    ejecucion = cargador.ejecucion_de_dict(datos["ejecucion"])
    pauta = cargador.checklist(RAIZ / "ejemplos" / "rcm-tpm" / "pauta-ex220.json")
    e = estado(ejecucion, pauta)
    assert e.respondidos == 5 and e.nok == 1
    assert ejecucion.operador == "R. Mamani"


def test_una_pauta_sin_criterio_se_rechaza_y_lo_explica(pagina):
    pag, _ = pagina
    pag.goto(APP.as_uri())
    pag.evaluate("""() => {
      empezar({id: "x", activo_codigo: "EX-1", nombre: "mala",
               puntos: [{clase: "limpiar", punto: "Un sitio", criterio: ""}]});
    }""")
    assert "no tiene criterio" in pag.inner_text("body")


def test_sin_errores_de_consola(pagina):
    pag, errores = pagina
    assert errores == []
