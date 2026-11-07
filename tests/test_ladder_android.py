"""LadderLab en Android: las cuatro formas de llevarla al teléfono.

1. **El APK** (`movil/ladderlab/android`): un WebView que sirve `docs/ladder`
   desde dentro, con un puente nativo para guardar en Descargas. Compilarlo
   pide el SDK y eso pasa en la integración; aquí se prueba lo que se rompe
   editando: que empaqueta la app que se publica, que la app y el puente se
   llaman igual, que no puede salir a la red y que, con un puente falso, la
   app se comporta como dentro del APK.
2. **Instalada desde Chrome** (PWA): que el trabajador de servicio la deje
   abrir sin señal.
3. **Un solo archivo** (`descargas/LadderLab.html`): lo que se abre desde
   Descargas. Android lo entrega como `content://` y desde ahí Chrome no carga
   los archivos de al lado; por eso tiene que funcionar sin ninguno.
4. **El .zip**: que trae el archivo único arriba y dice en el LEEME cuál abrir.

Una vez una persona pudo abrir la carpeta del .zip en Android y se quedó en
blanco: estas pruebas existen para que no vuelva a pasar.
"""

from __future__ import annotations

import base64
import functools
import http.server
import importlib.util
import json
import re
import shutil
import sys
import threading
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from navegador import HAY_CHROMIUM, opciones  # noqa: E402

APP = RAIZ / "docs" / "ladder"
DESCARGAS = APP / "descargas"
PROYECTO = RAIZ / "movil" / "ladderlab" / "android"
JAVA = PROYECTO / "app" / "src" / "main" / "java" / "pe" / "ladderlab" / "app"
FLUJO = RAIZ / ".github" / "workflows" / "apk-ladderlab.yml"
ANDROID_XML = "{http://schemas.android.com/apk/res/android}"
PUENTE = "PuenteLadder"

con_navegador = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")


def _texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def _empaquetador():
    spec = importlib.util.spec_from_file_location("empaquetar_ladder", RAIZ / "herramientas" / "empaquetar-ladder.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- el APK

def test_el_apk_toma_la_app_que_de_verdad_se_publica():
    gradle = _texto(PROYECTO / "app" / "build.gradle")
    assert 'rootProject.file("../../../docs/ladder")' in gradle
    assert "exclude 'sw.js'" in gradle, "el trabajador de servicio no debe viajar en el APK"
    assert "exclude 'descargas/**'" in gradle, "las descargas no tienen nada que hacer dentro del APK"
    assert not (PROYECTO / "app" / "src" / "main" / "assets").exists(), "no debe haber una copia versionada de la app"
    assert "app/src/main/assets/" in _texto(PROYECTO / ".gitignore")


def test_identidad_propia():
    gradle = _texto(PROYECTO / "app" / "build.gradle")
    assert "applicationId 'pe.ladderlab.app'" in gradle
    assert "namespace 'pe.ladderlab.app'" in gradle
    for f in JAVA.glob("*.java"):
        assert _texto(f).startswith("package pe.ladderlab.app;"), f.name
    assert '"ladderlab.localhost"' in _texto(JAVA / "PantallaPrincipal.java")


def test_la_aplicacion_no_puede_salir_a_la_red():
    raiz = ET.parse(PROYECTO / "app" / "src" / "main" / "AndroidManifest.xml").getroot()
    permisos = {p.get(ANDROID_XML + "name") for p in raiz.iter("uses-permission")}
    assert "android.permission.INTERNET" not in permisos


def test_los_dos_lados_llaman_igual_al_puente():
    java = _texto(JAVA / "PantallaPrincipal.java")
    assert f'"{PUENTE}"' in java
    app = _texto(APP / "index.html")
    assert f"window.{PUENTE}" in app
    declarados = set(re.findall(r"@JavascriptInterface\s+public\s+\w+\s+(\w+)\(", _texto(JAVA / "PuenteArchivos.java")))
    llamados = set(re.findall(rf"{PUENTE}\.(\w+)\(", app))
    assert llamados and llamados <= declarados, sorted(llamados - declarados)


def test_atras_existe_para_el_boton_del_telefono():
    assert "(typeof atras === 'function') ? atras() : false" in _texto(JAVA / "PantallaPrincipal.java")
    assert "function atras()" in _texto(APP / "index.html")


def test_los_enlaces_internos_apuntan_a_archivos():
    """El cargador de assets del APK no sirve carpetas: `manual/` daría 404."""
    for f in (APP / "index.html", APP / "manual" / "index.html"):
        html = _texto(f)
        assert not re.search(r'href="(manual/|\.\./)"', html), f


def test_iconos_en_todas_las_densidades():
    res = PROYECTO / "app" / "src" / "main" / "res"
    for d in ("mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"):
        for n in ("ic_launcher", "ic_launcher_round", "ic_launcher_foreground"):
            assert (res / f"mipmap-{d}" / f"{n}.png").exists(), (d, n)


def test_el_flujo_compila_publica_y_comprueba():
    flujo = _texto(FLUJO)
    for senal in ("herramientas/empaquetar-ladder.py", "tests/test_ladder_android.py",
                  "assembleRelease", "ladderlab.apk", "gh release create", "PuenteLadder"):
        assert senal in flujo, senal
    assert "ANDROID_ALMACEN_BASE64" in flujo, "la llave de firma llega por secretos"
    assert not list(RAIZ.glob("**/*.jks")), "una llave de firma no puede estar en el repositorio"


# ---------------------------------------------------------- las descargas

def test_el_archivo_unico_esta_al_dia():
    esperado = _empaquetador().archivo_unico()
    assert (DESCARGAS / "LadderLab.html").read_text(encoding="utf-8") == esperado, \
        "corre python3 herramientas/empaquetar-ladder.py"


def test_el_archivo_unico_no_depende_de_nada_al_lado():
    html = _texto(DESCARGAS / "LadderLab.html")
    assert not re.search(r'<script[^>]+src=', html)
    assert 'rel="manifest"' not in html
    assert not re.search(r'(src|href)="(lecciones|energia|icono|manual/)', html)
    assert "const UN_ARCHIVO = true;" in html


def test_el_zip_trae_el_archivo_unico_y_lo_explica():
    z = zipfile.ZipFile(DESCARGAS / "LadderLab-demo.zip")
    nombres = set(z.namelist())
    for n in ("LadderLab-demo/LadderLab.html", "LadderLab-demo/LEEME.txt",
              "LadderLab-demo/Manual-de-uso-LadderLab.pdf", "LadderLab-demo/LadderLab/index.html",
              "LadderLab-demo/LadderLab/lecciones.js", "LadderLab-demo/LadderLab/energia.js",
              "LadderLab-demo/LadderLab/manual/index.html"):
        assert n in nombres, n
    assert z.read("LadderLab-demo/LadderLab.html") == (DESCARGAS / "LadderLab.html").read_bytes()
    leeme = z.read("LadderLab-demo/LEEME.txt").decode("utf-8")
    assert "ANDROID" in leeme and "LadderLab.html" in leeme and "NO abras" in leeme
    assert z.read("LadderLab-demo/Manual-de-uso-LadderLab.pdf")[:5] == b"%PDF-"


# ------------------------------------------------------- en un navegador

PUENTE_FALSO = """
window.PuenteLadder = {
  recibido: null,
  guardar(nombre, b64, mime) { this.recibido = { nombre, b64, mime }; return ""; },
  version() { return "prueba"; }
};
"""

ANDROID = {"viewport": {"width": 412, "height": 915}, "device_scale_factor": 2.6, "is_mobile": True, "has_touch": True,
           "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36"}


@pytest.fixture(scope="module")
def servidor():
    """`docs/ladder` servida por http en 127.0.0.1, como la sirve el APK o el sitio."""
    manejador = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(APP))
    manejador.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), manejador)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/"
    srv.shutdown()


@pytest.fixture(scope="module")
def nav():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(**opciones())
        yield b
        b.close()


def _tocar_y_mantener(pag, selector, ms=200):
    """Un dedo, no un ratón: eventos de puntero de tipo touch."""
    caja = pag.locator(selector).first
    caja.dispatch_event("pointerdown", {"pointerId": 7, "pointerType": "touch", "isPrimary": True})
    pag.wait_for_timeout(ms)
    caja.dispatch_event("pointerup", {"pointerId": 7, "pointerType": "touch", "isPrimary": True})


@con_navegador
def test_archivo_unico_en_android_sin_nada_al_lado(nav, tmp_path):
    """Lo que pasa al abrirlo desde Descargas: ningún archivo vecino disponible."""
    solo = tmp_path / "LadderLab.html"
    shutil.copy(DESCARGAS / "LadderLab.html", solo)
    ctx = nav.new_context(**ANDROID)
    pag = ctx.new_page()
    errores, vecinos = [], []
    pag.on("pageerror", lambda e: errores.append(str(e)))
    pag.on("request", lambda r: vecinos.append(r.url) if r.url.startswith("file:") and r.url != solo.as_uri() else None)
    pag.goto(solo.as_uri() + "#/l/enclavamiento")
    pag.wait_for_selector(".sim .in .pb")
    _tocar_y_mantener(pag, '.in[data-a="%I0.0"] .pb')
    pag.wait_for_timeout(200)
    assert pag.evaluate("SIM.eng.v['%Q0.0']") == 1, "el dedo no arrancó el motor"
    retos = pag.evaluate("LECCIONES.filter(l => l.reto).map(l => [l.id, grade(l.reto, l.reto.solucion).ok])")
    assert len(retos) == 20 and all(ok for _, ok in retos), retos
    assert pag.evaluate("document.documentElement.scrollWidth") <= 412
    assert not errores, errores
    assert not vecinos, vecinos
    ctx.close()


@con_navegador
def test_la_carpeta_abierta_como_en_android_no_sirve(nav):
    """Documenta la causa: sin los archivos de al lado, la versión en carpeta
    no arranca. Por eso en Android se ofrece el archivo único o el APK."""
    ctx = nav.new_context(**ANDROID)
    pag = ctx.new_page()
    errores = []
    pag.on("pageerror", lambda e: errores.append(str(e)))
    pag.route(re.compile(r".*/(lecciones|energia)\.js$"), lambda r: r.abort())
    pag.goto((APP / "index.html").as_uri())
    pag.wait_for_timeout(300)
    assert errores, "si la carpeta funcionara sin sus vecinos, esta prueba sobraría"
    ctx.close()


@con_navegador
def test_dentro_del_apk(nav, servidor):
    ctx = nav.new_context(**ANDROID)
    ctx.add_init_script(PUENTE_FALSO)
    pag = ctx.new_page()
    errores, pedidos = [], []
    pag.on("pageerror", lambda e: errores.append(str(e)))
    pag.on("request", lambda r: pedidos.append(r.url))
    pag.goto(servidor + "index.html")
    pag.wait_for_selector(".hero")
    # sin descargas ni trabajador de servicio
    assert "descargas/" not in pag.inner_html("#nav")
    assert pag.evaluate("navigator.serviceWorker.getRegistration().then(r => !!r)") is False
    # exportar sale por el puente
    pag.goto(servidor + "index.html#/lab")
    pag.click(".b-exp")
    rec = pag.evaluate("window.PuenteLadder.recibido")
    assert rec and rec["nombre"].endswith(".json") and rec["mime"] == "application/json"
    assert isinstance(json.loads(base64.b64decode(rec["b64"]).decode("utf-8"))["prog"], list)
    assert "Descargas" in pag.inner_text("#toast")
    # botón atrás: editor → lección → inicio → salir
    pag.goto(servidor + "index.html#/l/logica")
    pag.click('.tabs button[data-t="reto"]')
    pag.locator(".segs .el").first.click()
    assert pag.is_visible("#sheet")
    assert pag.evaluate("atras()") is True and not pag.is_visible("#sheet")
    assert pag.evaluate("atras()") is True
    pag.wait_for_selector(".hero")
    assert pag.evaluate("atras()") is False
    # el manual se sirve como archivo
    pag.goto(servidor + "manual/index.html")
    assert "Manual de uso" in pag.title()
    assert not any("sw.js" in u or "/descargas/" in u for u in pedidos), pedidos
    assert not errores, errores
    ctx.close()


@con_navegador
def test_instalada_desde_chrome_abre_sin_senal(nav, servidor):
    ctx = nav.new_context(**ANDROID)
    pag = ctx.new_page()
    pag.goto(servidor + "index.html")
    pag.evaluate("navigator.serviceWorker.ready.then(() => true)")
    pag.reload()
    pag.wait_for_function("navigator.serviceWorker.controller !== null", timeout=10000)
    man = pag.evaluate("fetch('manifest.webmanifest').then(r => r.json())")
    assert man["display"] == "standalone" and man["start_url"] == "./"
    assert {"192x192", "512x512"} <= {i["sizes"] for i in man["icons"]}
    ctx.set_offline(True)
    pag.reload()
    pag.wait_for_selector(".hero")
    pag.goto(servidor + "index.html#/l/sincronismo")
    pag.wait_for_selector(".hmi svg")
    ctx.close()
