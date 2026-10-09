"""La cadena que lleva la ronda CIL a un teléfono Android, sin un teléfono.

Compilar el .apk hace falta el SDK entero y eso pasa en la integración. Aquí
se comprueba lo que se puede romper editando, que es casi todo: que el
contenedor empaqueta la pantalla que de verdad se publica, que la pantalla y
el puente de Java hablan el mismo idioma, que la app no puede salir a la red,
y que la llave de firma no acaba en el repositorio.

Y lo que de verdad aporta el APK sobre la página: **el puente**. En un
WebView una descarga `blob:` no llega a ningún lado —ni siquiera dispara el
escuchador de descargas de Android—, así que sin puente el botón de guardar
parecería funcionar y la ronda del turno no quedaría en ninguna parte. Eso se
prueba con un puente falso en un navegador de verdad.
"""

from __future__ import annotations

import base64
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from navegador import HAY_CHROMIUM, opciones  # noqa: E402

PROYECTO = RAIZ / "movil" / "fixmate-ronda" / "android"
JAVA = PROYECTO / "app" / "src" / "main" / "java" / "pe" / "fixmate" / "ronda"
PANTALLA = RAIZ / "docs" / "fixmate" / "ronda" / "index.html"
FLUJO = RAIZ / ".github" / "workflows" / "apk-fixmate.yml"

ANDROID_XML = "{http://schemas.android.com/apk/res/android}"
# El nombre con el que la pantalla busca el puente. Si los dos lados dejan de
# llamarlo igual, el botón de guardar deja de guardar y no hay error en
# ninguna parte: por eso está escrito una vez aquí y se comprueba en los dos.
PUENTE = "PuenteFixMate"


def _texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifiesto() -> ET.Element:
    return ET.parse(PROYECTO / "app" / "src" / "main" / "AndroidManifest.xml").getroot()


# ---------- lo que va dentro del .apk ----------

def test_el_apk_toma_la_pantalla_que_de_verdad_se_publica():
    """No hay una copia de la ronda dentro del proyecto de Android.

    Si la hubiera, se quedaría atrás el día que nadie se acordara de
    sincronizarla, y el operador haría la ronda con una pauta vieja sin
    enterarse. La compilación la toma de `docs/fixmate/ronda/`, que es la
    misma carpeta que se publica.
    """
    gradle = _texto(PROYECTO / "app" / "build.gradle")
    assert 'rootProject.file("../../../docs/fixmate/ronda")' in gradle
    assert PANTALLA.is_file()

    assets = PROYECTO / "app" / "src" / "main" / "assets"
    copiadas = list(assets.rglob("*")) if assets.is_dir() else []
    assert not copiadas, (
        "hay una copia de la pantalla dentro del proyecto de Android: "
        f"{[str(a) for a in copiadas[:5]]}. La compilación ya la trae sola.")


def test_la_direccion_que_carga_el_contenedor_es_la_que_sirve_el_cargador():
    """El dominio y el prefijo tienen que cuadrar o la app abre en negro."""
    java = _texto(JAVA / "PantallaPrincipal.java")
    dominio = re.search(r'DOMINIO = "([^"]+)"', java)
    inicio = re.search(r'INICIO = "https://" \+ DOMINIO \+ "([^"]+)"', java)
    assert dominio and inicio, "no se encuentra el dominio o la dirección de inicio"
    assert inicio.group(1) == "/www/index.html"

    gradle = _texto(PROYECTO / "app" / "build.gradle")
    assert "src/main/assets/www" in gradle, (
        "la pantalla se copia a otro sitio del que el contenedor la busca")
    # El dominio tiene que ser `.localhost`: es el único que no resuelve fuera.
    assert dominio.group(1).endswith(".localhost")


def test_el_trabajador_de_servicio_se_queda_fuera_del_apk():
    """Dentro del APK no pinta nada, y además intentaría salir a la red.

    Los archivos ya son locales, así que no hay nada que guardar; y como sus
    peticiones no pasan por el cargador de assets, registrarlo fallaría en
    cada arranque contra una red que la app no tiene permiso de usar.

    Son dos candados, a propósito: el `exclude` del copiado y la pantalla,
    que no lo registra cuando detecta el puente. Uno solo se deshace de un
    descuido.
    """
    gradle = _texto(PROYECTO / "app" / "build.gradle")
    assert "exclude 'sw.js'" in gradle
    assert "EN_APK" in _texto(PANTALLA)
    assert '!EN_APK && "serviceWorker" in navigator' in _texto(PANTALLA)


def test_la_pantalla_solo_llama_a_metodos_que_el_puente_declara():
    """Un método que JavaScript llama y Java no tiene no da error: devuelve
    `undefined`, el botón no hace nada y nadie se entera hasta el socavón."""
    java = _texto(JAVA / "PuenteArchivos.java")
    declarados = set(re.findall(
        r"@JavascriptInterface\s+public\s+\w+\s+(\w+)\(", java))
    assert declarados, "el puente no declara ningún método para JavaScript"

    llamados = set(re.findall(r"puente\.(\w+)\(", _texto(PANTALLA)))
    assert llamados, "la pantalla no usa el puente"
    assert llamados <= declarados, (
        f"la pantalla llama a {sorted(llamados - declarados)}, que el puente "
        "no declara")


def test_los_dos_lados_llaman_igual_al_puente():
    assert f'"{PUENTE}"' in _texto(JAVA / "PantallaPrincipal.java")
    assert f"window.{PUENTE}" in _texto(PANTALLA)


def test_la_pantalla_reconoce_el_contenedor_por_el_puente():
    # Es lo único que distingue «servida por el sitio» de «dentro del APK»:
    # el protocolo dice https en los dos casos.
    pantalla = _texto(PANTALLA)
    assert f'typeof window.{PUENTE} !== "undefined"' in pantalla
    assert 'location.protocol === "file:" || EN_APK' in pantalla


# ---------- lo que la app puede y no puede hacer ----------

def test_la_aplicacion_no_puede_salir_a_la_red(manifiesto):
    """Sin permiso de INTERNET no es una promesa: es que no puede.

    Una ronda que no puede salir a la red es una cosa menos que explicarle a
    un auditor, y una menos que falle a 300 m bajo tierra.
    """
    permisos = {p.get(ANDROID_XML + "name")
                for p in manifiesto.iter("uses-permission")}
    assert "android.permission.INTERNET" not in permisos, permisos


def test_el_permiso_de_almacenamiento_solo_alcanza_a_los_telefonos_viejos(manifiesto):
    # Desde Android 10 se escribe por MediaStore, que no pide permiso.
    for permiso in manifiesto.iter("uses-permission"):
        if permiso.get(ANDROID_XML + "name").endswith("WRITE_EXTERNAL_STORAGE"):
            assert permiso.get(ANDROID_XML + "maxSdkVersion") == "28"
            return
    pytest.fail("no está el permiso de escritura para Android 9 y anteriores")


def test_la_camara_y_la_ubicacion_no_se_piden(manifiesto):
    # La ronda no fotografía ni geolocaliza. Pedir un permiso que no se usa es
    # la forma más barata de que una mina no apruebe la instalación.
    permisos = {p.get(ANDROID_XML + "name")
                for p in manifiesto.iter("uses-permission")}
    assert not [p for p in permisos if "CAMERA" in p or "LOCATION" in p], permisos


def test_el_icono_esta_en_todas_las_densidades():
    res = PROYECTO / "app" / "src" / "main" / "res"
    for densidad in ("mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"):
        carpeta = res / f"mipmap-{densidad}"
        for nombre in ("ic_launcher.png", "ic_launcher_round.png",
                       "ic_launcher_foreground.png"):
            assert (carpeta / nombre).is_file(), f"falta {densidad}/{nombre}"
    for nombre in ("ic_launcher.xml", "ic_launcher_round.xml"):
        assert (res / "mipmap-anydpi-v26" / nombre).is_file()


def test_el_icono_del_apk_es_el_mismo_de_la_ronda_publicada():
    """El del teléfono y el del sitio salen del mismo dibujo.

    Dos iconos distintos para la misma cosa hacen dudar de si son la misma
    cosa, que es justo lo que no conviene con una app instalada a mano.
    """
    sys.path.insert(0, str(RAIZ / "herramientas"))
    import importlib.util

    ruta = RAIZ / "herramientas" / "iconos-fixmate.py"
    spec = importlib.util.spec_from_file_location("iconos_fixmate", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    from PIL import Image

    generado = modulo.dibujar(192, marca="ronda").convert("RGB")
    publicado = Image.open(
        RAIZ / "docs" / "fixmate" / "ronda" / "icono-192.png").convert("RGB")
    assert generado.tobytes() == publicado.tobytes(), (
        "el icono publicado no sale del mismo dibujo que el del APK: corra "
        "`python3 herramientas/iconos-fixmate.py`")


def test_todos_los_recursos_xml_se_pueden_leer():
    """Un XML que no parsea tumba la compilación entera, y tarde.

    Esto ya pasó: un comentario con `--` dentro —el nombre de un token de la
    piel— hizo fallar `mergeReleaseResources` después de bajar el SDK, cinco
    minutos adentro. La comprobación cuesta milisegundos y lo dice antes de
    empujar.
    """
    xmls = sorted(PROYECTO.rglob("*.xml"))
    assert xmls, "no hay recursos XML en el proyecto"
    for ruta in xmls:
        try:
            ET.parse(ruta)
        except ET.ParseError as exc:
            pytest.fail(f"{ruta.relative_to(RAIZ)} no se puede leer: {exc}")


# ---------- la cadena de publicación ----------

def test_la_direccion_de_descarga_es_la_misma_en_todos_los_sitios():
    flujo = _texto(FLUJO)
    archivo = re.search(r"ARCHIVO:\s*(\S+)", flujo)
    assert archivo and archivo.group(1).endswith(".apk")
    nombre = archivo.group(1)
    # El nombre del archivo compilado por Gradle y el que se publica tienen
    # que ser reconocibles entre sí, o alguien publica otra cosa.
    gradle = _texto(PROYECTO / "app" / "build.gradle")
    assert nombre.removesuffix(".apk") in gradle


def test_el_apk_se_publica_solo_desde_main():
    flujo = _texto(FLUJO)
    publicar = flujo.index("Publicar para descargar")
    tramo = flujo[publicar:publicar + 400]
    assert "github.ref == 'refs/heads/main'" in tramo
    assert "github.event_name == 'push'" in tramo


def test_la_compilacion_comprueba_el_apk_antes_de_publicarlo():
    flujo = _texto(FLUJO)
    # Lo de dentro: que la pantalla viaje entera y que sea la publicada.
    assert "no lleva la misma pantalla que se publica" in flujo
    assert "apksigner" in flujo and "aapt2" in flujo
    # Y que el .apk quede de verdad dentro de la publicación.
    assert "la publicación $etiqueta salió sin el .apk" in flujo


def test_la_llave_de_firma_no_entra_en_el_repositorio():
    sospechosos = [p for p in PROYECTO.rglob("*")
                   if p.suffix in (".jks", ".keystore", ".p12")]
    assert not sospechosos, sospechosos
    flujo = _texto(FLUJO)
    assert "secrets.ANDROID_ALMACEN_BASE64" in flujo


def test_sin_llave_propia_la_compilacion_avisa():
    # Firmada con una llave provisional, la versión siguiente no se puede
    # instalar encima: hay que desinstalar antes, y eso borra lo que haya.
    flujo = _texto(FLUJO)
    assert "firma" in flujo and "provisional" in flujo
    assert "exigirá desinstalar antes" in flujo


# ---------- el puente, en un navegador de verdad ----------

PUENTE_FALSO = """
window.PuenteFixMate = {
  recibido: null,
  respuesta: "",
  guardar: function (nombre, base64, mime) {
    this.recibido = { nombre: nombre, base64: base64, mime: mime };
    return this.respuesta;
  },
  version: function () { return "1.0-prueba"; }
};
"""


@pytest.fixture
def ronda_en_apk():
    """La pantalla con un puente falso puesto antes de que arranque."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        ctx = nav.new_context(viewport={"width": 390, "height": 844})
        ctx.add_init_script(PUENTE_FALSO)
        pag = ctx.new_page()
        errores = []
        pag.on("pageerror", lambda e: errores.append(str(e)))
        pag.goto(PANTALLA.as_uri())
        yield pag, errores
        nav.close()


def _hacer_la_ronda(pag, operador="J. Quispe"):
    pag.click("#demo")
    pag.fill("#op", operador)
    pag.click("#ir")
    for _ in range(5):
        pag.click('button[data-r="ok"]')


@pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")
def test_dentro_del_apk_la_ronda_sale_por_el_puente(ronda_en_apk):
    """Lo único que el APK aporta sobre la página, y lo único que puede
    romperse en silencio: sin esto el botón no guarda nada."""
    pag, errores = ronda_en_apk
    _hacer_la_ronda(pag, "R. Mamani")
    pag.click("#bajar")

    recibido = pag.evaluate("window.PuenteFixMate.recibido")
    assert recibido, "el botón de guardar no usó el puente"
    assert recibido["nombre"].endswith(".json")
    assert recibido["mime"] == "application/json"

    datos = json.loads(base64.b64decode(recibido["base64"]).decode("utf-8"))
    assert datos["ejecucion"]["operador"] == "R. Mamani"
    assert len(datos["ejecucion"]["items"]) == 5
    assert datos["estado"]["completa"] is True
    # Y se le dice al operador dónde quedó.
    assert "Descargas" in pag.inner_text("#aviso-guardado")
    assert not errores, errores


@pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")
def test_si_el_puente_no_pudo_guardar_la_pantalla_lo_dice(ronda_en_apk):
    # Un operador mirando un botón que no hizo nada vuelve a tocarlo, y
    # termina con tres archivos o con ninguno.
    pag, _ = ronda_en_apk
    pag.evaluate("window.PuenteFixMate.respuesta = 'No hay carpeta de Descargas.'")
    _hacer_la_ronda(pag)
    pag.click("#bajar")
    aviso = pag.inner_text("#aviso-guardado")
    assert "No hay carpeta de Descargas." in aviso
    assert "peligro" in pag.get_attribute("#aviso-guardado", "class")


@pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")
def test_dentro_del_apk_no_hay_enlaces_a_carpetas_que_no_viajan(ronda_en_apk):
    pag, _ = ronda_en_apk
    assert pag.locator(".barra .vinculos").count() == 0


@pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")
def test_el_boton_de_atras_cierra_el_dialogo_y_no_la_ronda(ronda_en_apk):
    """`atras()` es lo que Java consulta antes de cerrar.

    Cerrar de un toque a mitad de una ronda es perder el turno entero: los
    puntos contestados viven en la pantalla, no en un archivo.
    """
    pag, _ = ronda_en_apk
    pag.click("#demo")
    pag.fill("#op", "J. Quispe")
    pag.click("#ir")

    assert pag.evaluate("atras()") is False, "sin diálogo abierto no hay nada que cerrar"
    pag.click('button[data-r="nok"]')
    assert pag.locator(".velo").count() == 1
    assert pag.evaluate("atras()") is True, "con el diálogo abierto tenía que cerrarlo"
    assert pag.locator(".velo").count() == 0
    # Y la ronda sigue en pie, en el mismo punto.
    assert pag.inner_text("#paso") == "1 / 5"


# --------------------------------- por donde ENTRA la pauta en el APK

def test_el_webview_abre_el_selector_de_archivos():
    """Sin esto, «Abrir pauta del equipo» no hace NADA en el APK.

    En un WebView, un `<input type="file">` no abre selector, no da error y
    no avisa si la aplicación no implementa `onShowFileChooser`. El operador
    toca el botón y no pasa nada.

    Y pesa más de lo que parece: el APK existe para las minas que no dejan
    instalar desde el navegador, y ese botón es la **única** forma de meterle
    una pauta. Sin él, ahí la ronda no arranca — sólo funcionaba el botón del
    ejemplo, que es un taller inventado.
    """
    java = _texto(JAVA / "PantallaPrincipal.java")
    assert "setWebChromeClient" in java, "el WebView no tiene WebChromeClient"
    assert "onShowFileChooser" in java, (
        "sin `onShowFileChooser` el input de archivo del APK no hace nada")
    assert "startActivityForResult" in java
    assert "FileChooserParams.parseResult" in java, (
        "lo que elige el operador tiene que volver al WebView por parseResult")


def test_el_selector_contesta_siempre_aunque_el_operador_cancele():
    """Un callback sin contestar deja el botón muerto hasta cerrar la app.

    Mientras no se le contesta, el WebView cree que hay un selector abierto y
    no abre otro. Hay tres caminos que abandonan el callback y los tres
    tienen que contestarlo: una petición nueva encima de otra, que no haya
    con qué abrir archivos, y que la app se cierre con el selector abierto.
    """
    java = _texto(JAVA / "PantallaPrincipal.java")
    assert java.count("onReceiveValue(null)") >= 3, (
        "faltan caminos que contesten el callback: " +
        str(java.count("onReceiveValue(null)")) + " de 3")
    # Y el que sí eligió archivo se contesta con lo que eligió.
    assert "onReceiveValue(\n                WebChromeClient.FileChooserParams" in java \
        or "onReceiveValue(WebChromeClient.FileChooserParams" in java


def test_el_webview_puede_leer_lo_que_devuelve_el_selector():
    """El selector del sistema devuelve `content://`.

    Con `setAllowContentAccess(false)` el botón abría el selector y después
    no cargaba nada: dos bloqueos encadenados, y el segundo sin mensaje.
    `file://` sigue cerrado, que es el endurecimiento que sí hace falta: el
    contenido de la app va por el cargador de assets.
    """
    java = _texto(JAVA / "PantallaPrincipal.java")
    assert "setAllowContentAccess(true)" in java, (
        "sin acceso a content:// el archivo elegido no se puede leer")
    assert "setAllowFileAccess(false)" in java, (
        "file:// no hace falta y abrirlo es perder el endurecimiento")


def test_si_no_hay_con_que_abrir_archivos_se_dice_y_no_se_queda_esperando():
    java = _texto(JAVA / "PantallaPrincipal.java")
    assert "R.string.sin_selector" in java
    cadenas = _texto(PROYECTO / "app" / "src" / "main" / "res" / "values" / "strings.xml")
    assert 'name="sin_selector"' in cadenas
    # Un mensaje que sólo dice que falló no sirve: tiene que decir qué hacer.
    assert "WhatsApp" in cadenas or "Descargas" in cadenas
