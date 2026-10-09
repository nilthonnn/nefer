"""Que las dos pantallas se instalen en un Android y abran sin señal.

La ronda se hace en interior mina y el turno no espera a que haya línea. Una
pantalla que necesita cobertura para abrir no sirve ahí, por buena que sea
—y el operador no va a enterarse del problema hasta que esté abajo, sin
señal y con la máquina esperando—.

Para que Android ofrezca «Instalar app» y guarde la copia hacen falta tres
cosas: un manifiesto con sus iconos, un trabajador de servicio registrado, y
que las dos cosas las sirva el mismo origen por https. Aquí se comprueban las
tres, y la de verdad: se levanta un servidor, se registra el trabajador, se
corta la red y se vuelve a abrir la pantalla.
"""

from __future__ import annotations

import functools
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "herramientas"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import piel  # noqa: E402
from navegador import HAY_CHROMIUM, opciones  # noqa: E402

PANTALLAS = {
    "la ronda CIL": RAIZ / "docs" / "fixmate" / "ronda",
    "el análisis RCM": RAIZ / "docs" / "fixmate" / "rcm",
    "armar": RAIZ / "docs" / "fixmate" / "armar",
    "la app de diagnóstico": RAIZ / "docs" / "fixmate" / "app",
}
# Las que genera el espejo con manifiesto y trabajador propios. La app de
# diagnóstico es un archivo suelto que también se descarga y se abre con
# `file://`, y por eso no registra trabajador.
GENERADAS = ("la ronda CIL", "el análisis RCM", "armar")
ICONOS = (("icono-192.png", 192), ("icono-512.png", 512),
          ("icono-512-recortable.png", 512))


def _manifiesto(carpeta: Path) -> dict:
    return json.loads((carpeta / "manifest.webmanifest").read_text(encoding="utf-8"))


@pytest.mark.parametrize("nombre", list(PANTALLAS))
def test_cada_pantalla_trae_lo_que_android_pide_para_instalarla(nombre):
    carpeta = PANTALLAS[nombre]
    m = _manifiesto(carpeta)
    # Sin `standalone` queda abierta dentro del navegador, con su barra
    # encima comiendo pantalla; sin `start_url` Android no sabe qué abrir.
    assert m["display"] == "standalone", nombre
    assert m["start_url"] == "./" and m["scope"] == "./"
    assert m["name"] and m["short_name"] and m["description"]
    assert m["lang"] == "es"
    # Un icono de 192 y uno de 512, y uno recortable: sin el recortable,
    # Android recorta el redondo y se come la marca.
    declarados = {i["src"]: i for i in m["icons"]}
    assert any(i.get("purpose") == "maskable" for i in m["icons"]), nombre
    for archivo, lado in ICONOS:
        assert archivo in declarados, f"{nombre} no declara {archivo}"
        ruta = carpeta / archivo
        assert ruta.exists(), f"{nombre}: falta {archivo}"
        assert declarados[archivo]["sizes"] == f"{lado}x{lado}"


@pytest.mark.parametrize("nombre", list(PANTALLAS))
def test_el_color_de_la_barra_del_telefono_es_el_de_la_piel(nombre):
    # Si no coincide, al abrirla el teléfono pinta una franja de otro color
    # encima de la barra del producto.
    m = _manifiesto(PANTALLAS[nombre])
    barra = piel.token("--barra")
    assert m["theme_color"].upper() == barra.upper(), nombre
    assert m["background_color"].upper() == barra.upper(), nombre
    html = (PANTALLAS[nombre] / "index.html").read_text(encoding="utf-8")
    assert f'name="theme-color" content="{barra}"' in html, nombre


@pytest.mark.parametrize("nombre", GENERADAS)
def test_la_pantalla_enlaza_su_manifiesto_y_registra_su_trabajador(nombre):
    html = (PANTALLAS[nombre] / "index.html").read_text(encoding="utf-8")
    assert '<link rel="manifest" href="manifest.webmanifest">' in html, nombre
    assert 'navigator.serviceWorker.register("sw.js")' in html, nombre
    # Y sólo servida: desde un archivo suelto el navegador no registra nada,
    # y pedirlo llena la consola de errores que no significan nada.
    assert 'location.protocol.indexOf("http") === 0' in html, nombre


@pytest.mark.parametrize("nombre", GENERADAS)
def test_el_cache_cambia_cuando_cambia_la_pantalla(nombre):
    """Si no, el teléfono que ya la guardó se queda con la versión vieja.

    Y no se entera nadie: la pantalla abre, sólo que es la de antes. Es la
    peor forma de romper una app instalada.
    """
    carpeta = PANTALLAS[nombre]
    html = (carpeta / "index.html").read_text(encoding="utf-8")
    sw = (carpeta / "sw.js").read_text(encoding="utf-8")
    corto = _manifiesto(carpeta)["short_name"]

    actual = piel.trabajador(corto, html)
    assert actual == sw, f"{nombre}: el trabajador no está al día"
    otro = piel.trabajador(corto, html + "<!-- una línea más -->")
    assert otro != sw, "el nombre del caché no cambia con la pantalla"


# ═══════════════ la prueba de verdad: sin señal ═══════════════

@pytest.fixture
def servidor():
    """La pantalla servida por http, que es como llega al teléfono."""
    raiz = RAIZ / "docs" / "fixmate"
    manejador = functools.partial(http.server.SimpleHTTPRequestHandler,
                                  directory=str(raiz))
    manejador.log_message = lambda *a, **k: None

    class Servidor(socketserver.TCPServer):
        allow_reuse_address = True

    s = Servidor(("127.0.0.1", 0), manejador)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_address[1]}"
    s.shutdown()


@pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")
# Qué se mira para saber que abrió usable y no como una cáscara: en las dos
# pantallas de campo, el botón del ejemplo; en «Armar», el de empezar una
# pauta, que es con lo que arranca el trabajo ahí.
@pytest.mark.parametrize("carpeta,marca,senal", [
    ("ronda", "Ronda CIL", "#demo"),
    ("rcm", "Análisis RCM", "#demo"),
    ("armar", "Armar", "#n-pauta"),
])
def test_la_pantalla_abre_con_la_red_cortada(servidor, carpeta, marca, senal):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        ctx = nav.new_context(viewport={"width": 390, "height": 844})
        pag = ctx.new_page()
        pag.goto(f"{servidor}/{carpeta}/")
        # El trabajador tarda en tomar el control; se espera a que esté.
        pag.wait_for_function(
            "() => navigator.serviceWorker.controller !== null", timeout=15000)

        ctx.set_offline(True)
        pag.reload()
        # La barra va en versalitas por CSS, y `inner_text` da lo que se ve.
        assert marca.upper() in pag.inner_text(".barra").upper(), (
            f"{carpeta} no abrió sin señal")
        # Y sigue siendo usable, no una cáscara.
        assert pag.locator(senal).count() == 1
        ctx.set_offline(False)
        nav.close()


@pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")
def test_la_ronda_entera_se_hace_sin_señal(servidor):
    """La prueba que importa: la ronda completa, offline, de principio a fin.

    Es la condición real —interior mina, sin cobertura— y lo que se tiene que
    poder terminar ahí es la ronda entera, no la pantalla de inicio.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              accept_downloads=True)
        pag = ctx.new_page()
        pag.goto(f"{servidor}/ronda/")
        pag.wait_for_function(
            "() => navigator.serviceWorker.controller !== null", timeout=15000)

        ctx.set_offline(True)
        pag.reload()
        pag.click("#demo")
        pag.fill("#op", "J. Quispe")
        pag.click("#ir")
        for _ in range(5):
            pag.click('button[data-r="ok"]')
        assert "Ronda completa" in pag.inner_text("body")
        with pag.expect_download() as bajada:
            pag.click("#bajar")
        assert bajada.value.suggested_filename.endswith(".json")
        ctx.set_offline(False)
        nav.close()


@pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")
@pytest.mark.parametrize("carpeta", ["ronda", "rcm", "armar"])
def test_el_boton_de_instalar_aparece_cuando_el_aparato_lo_ofrece(servidor, carpeta):
    """Sin botón, instalar es el menú de tres puntos del navegador.

    El operador no va a dar con eso, y sin instalar no hay copia local ni
    pantalla completa: queda un marcador dentro del navegador, con la barra
    del navegador encima comiéndose la pantalla.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        pag = nav.new_context(viewport={"width": 390, "height": 844}).new_page()
        pag.goto(f"{servidor}/{carpeta}/")
        # Sin el aviso del aparato no hay botón: uno que no hace nada es peor.
        assert pag.locator("#instalar").count() == 0
        pag.evaluate("window.dispatchEvent(new Event('beforeinstallprompt'))")
        assert pag.locator("#instalar").count() == 1, "no apareció el botón"
        assert pag.inner_text("#instalar").strip().lower() == "instalar"
        # Y cuando ya está instalada, se va.
        pag.evaluate("window.dispatchEvent(new Event('appinstalled'))")
        assert pag.locator("#instalar").count() == 0
        nav.close()
