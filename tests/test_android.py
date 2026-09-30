"""La cadena que lleva la app al telefono Android, comprobada sin un telefono.

Compilar el .apk hace falta el SDK entero y eso pasa en la integracion; aqui se
comprueba lo que se puede romper editando, que es casi todo: que el contenedor
empaqueta la app que de verdad se publica, que la pagina y el puente de Java
hablan el mismo idioma, que la direccion de descarga es la misma en los tres
sitios donde esta escrita, y que la llave de firma no acaba en el repositorio.
"""

from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CLON = RAIZ / "clientes" / "rd-renta"
ANDROID = CLON / "android"
APP = CLON / "docs" / "app" / "index.html"
FLUJO = RAIZ / ".github" / "workflows" / "apk.yml"

ANDROID_XML = "{http://schemas.android.com/apk/res/android}"


@pytest.fixture(scope="module")
def manifiesto() -> ET.Element:
    return ET.parse(ANDROID / "app" / "src" / "main" / "AndroidManifest.xml").getroot()


def _texto(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


# ---------- lo que va dentro del .apk ----------

def test_el_apk_toma_la_app_que_de_verdad_se_publica():
    """No hay una copia de la app dentro del proyecto de Android.

    Si la hubiera, se quedaria atras el dia que nadie se acordara de
    sincronizarla, y el operario instalaria una version vieja sin enterarse.
    La compilacion la toma de `docs/app/`, que es la misma carpeta que se
    publica en Pages.
    """
    gradle = _texto(ANDROID / "app" / "build.gradle")
    assert 'rootProject.file("../docs/app")' in gradle
    assert (CLON / "docs" / "app" / "index.html").is_file()

    copiadas = list((ANDROID / "app" / "src" / "main" / "assets").rglob("*")) \
        if (ANDROID / "app" / "src" / "main" / "assets").is_dir() else []
    assert not copiadas, (
        "hay una copia de la app dentro del proyecto de Android: "
        f"{[str(a) for a in copiadas[:5]]}. La compilacion ya la trae sola.")


def test_la_direccion_que_carga_el_contenedor_es_la_que_sirve_el_cargador():
    """El dominio y el prefijo tienen que cuadrar o la app abre en negro.

    `WebViewAssetLoader` sirve `/app/` desde la raiz de los assets; la Activity
    carga `https://<dominio>/app/index.html`. Si alguien mueve uno sin el otro,
    el .apk compila igual y lo que se instala es una pantalla vacia.
    """
    java = _texto(ANDROID / "app" / "src" / "main" / "java" / "pe" / "rdrental"
                  / "actas" / "MainActivity.java")
    dominio = re.search(r'String DOMINIO = "([^"]+)"', java).group(1)
    inicio = re.search(r'String INICIO = "https://" \+ DOMINIO \+ "([^"]+)"', java).group(1)
    prefijo = re.search(r'addPathHandler\("([^"]+)"', java).group(1)

    assert dominio.endswith(".local"), "el dominio no puede existir en internet"
    assert inicio.startswith(prefijo), (
        f"la Activity carga {inicio} pero el cargador sirve {prefijo}")
    # Y lo que hay detras del prefijo tiene que existir en docs/app/.
    assert (CLON / "docs" / "app" / inicio[len(prefijo):]).is_file()


def test_el_trabajador_de_servicio_se_queda_fuera_del_apk():
    """Dentro del .apk los archivos ya son locales.

    Un trabajador de servicio ahi solo pone una cache por encima de otra, y con
    ella la posibilidad de seguir sirviendo la version anterior despues de
    actualizar la aplicacion.
    """
    assert 'exclude("sw.js")' in _texto(ANDROID / "app" / "build.gradle")
    assert "!CONTEXTO.enAndroid" in _texto(APP), \
        "la pagina registraria el trabajador de servicio tambien dentro del .apk"


# ---------- el puente ----------

def test_la_pagina_solo_llama_a_metodos_que_el_puente_declara():
    """Un nombre mal escrito en el puente no da error: da `undefined`.

    La pagina llamaria a un metodo que no existe, la exportacion fallaria en el
    telefono y aqui no se habria enterado nadie. Se comparan los dos lados.
    """
    java = _texto(ANDROID / "app" / "src" / "main" / "java" / "pe" / "rdrental"
                  / "actas" / "Anfitrion.java")
    declarados = set(re.findall(
        r"@JavascriptInterface\s+public\s+\S+\s+(\w+)\s*\(", java))
    assert declarados, "el puente no declara ningun metodo"

    llamados = set(re.findall(r"window\.Anfitrion\.(\w+)\s*\(", _texto(APP)))
    assert llamados, "la pagina no usa el puente"
    assert llamados <= declarados, (
        f"la pagina llama a {sorted(llamados - declarados)}, que el puente no tiene")

    # Y el protocolo entero tiene que estar en uso: abrir, trozo y cerrar.
    assert {"abrir", "trozo", "cerrar"} <= llamados


def test_el_acta_viaja_a_trozos_y_no_de_una_vez():
    """Un acta de veinte fotos pasa de los diez megas.

    Esa cadena cruzando el puente de JavaScript de una sola vez es lo que tumba
    un telefono de gama baja, asi que va troceada. El tope tambien esta puesto
    en Java: si uno de los dos cambia y el otro no, no pasa nada grave, pero el
    trozo no puede desaparecer.
    """
    pagina = _texto(APP)
    trozo = int(re.search(r"var TROZO_ANFITRION = (\d+) \* 1024", pagina).group(1))
    assert 64 <= trozo <= 1024, f"trozo de {trozo} KB: o es inutil o revienta el puente"
    assert "blob.slice(desde, desde + TROZO_ANFITRION)" in pagina


def test_la_pagina_reconoce_el_contenedor_por_el_puente():
    """No por el agente de usuario, que cualquiera puede escribir."""
    pagina = _texto(APP)
    trozo = pagina[pagina.index("var CONTEXTO ="):pagina.index("var ICONO_192")]
    assert "window.Anfitrion" in trozo
    assert "userAgent" not in trozo


# ---------- permisos ----------

def test_la_aplicacion_no_puede_salir_a_la_red(manifiesto):
    """Es la promesa que la pagina le hace al cliente, y aqui se hace cumplir.

    Sin permiso de INTERNET no es una cuestion de confianza: el sistema no la
    deja, haga lo que haga el codigo de dentro.
    """
    permisos = {p.get(ANDROID_XML + "name")
                for p in manifiesto.iter("uses-permission")}
    assert "android.permission.INTERNET" not in permisos
    assert "android.permission.ACCESS_NETWORK_STATE" not in permisos
    assert "android.permission.CAMERA" in permisos, "sin esto no hay fotos"


def test_el_permiso_de_almacenamiento_solo_alcanza_a_los_telefonos_viejos(manifiesto):
    """De Android 10 en adelante se escribe por MediaStore, sin pedir nada."""
    for permiso in manifiesto.iter("uses-permission"):
        if permiso.get(ANDROID_XML + "name").endswith("WRITE_EXTERNAL_STORAGE"):
            assert permiso.get(ANDROID_XML + "maxSdkVersion") == "28"
            return
    pytest.fail("falta el permiso de escritura para Android 9 y anteriores")


def test_la_camara_no_se_exige_para_instalar(manifiesto):
    """Una tableta sin camara sigue sirviendo para revisar y exportar actas."""
    for rasgo in manifiesto.iter("uses-feature"):
        if "camera" in rasgo.get(ANDROID_XML + "name"):
            assert rasgo.get(ANDROID_XML + "required") == "false"


# ---------- la direccion de descarga ----------

def test_la_direccion_de_descarga_es_la_misma_en_los_tres_sitios():
    """El boton, el codigo QR impreso y lo que publica la compilacion.

    Si se separan, el QR del taller lleva a un archivo que no existe y nadie se
    entera hasta que un operario lo escanea.
    """
    flujo = _texto(FLUJO)
    archivo = re.search(r"^  ARCHIVO: (\S+)$", flujo, re.M).group(1)
    esperada = ("https://github.com/nilthonnn/nefer/releases/latest/download/"
                f"{archivo}")

    portada = _texto(CLON / "docs" / "index.html")
    assert f'href="{esperada}"' in portada, f"la portada no ofrece {esperada}"

    qr = _texto(CLON / "docs" / "qr-apk.svg")
    assert esperada in qr, \
        "el QR apunta a otra direccion; rehagalo con herramientas/generar-qr.py"

    manual = _texto(CLON / "docs" / "MANUAL-ANDROID.md")
    assert esperada in manual


def test_cada_compilacion_publica_su_propia_version_con_el_apk_dentro():
    """Aqui las publicaciones nacen inmutables.

    Una vez publicada no admite que se le cuelgue nada despues, asi que
    reescribir una etiqueta fija deja una publicacion vacia y una direccion de
    descarga que da 404. El .apk tiene que ir en la propia creacion, y la
    direccion estable la da `latest/download`, no la etiqueta.
    """
    flujo = _texto(FLUJO)
    publicar = flujo[flujo.index("- name: Publicar para descargar"):]

    assert "gh release upload" not in publicar, (
        "subir el .apk despues de crear la publicacion no funciona: "
        "las publicaciones son inmutables")
    assert 'etiqueta="android-v${{ github.run_number }}"' in publicar, \
        "la etiqueta tiene que ser distinta en cada compilacion"
    assert 'gh release create "$etiqueta" "$APK"' in publicar, \
        "el .apk tiene que ir dentro de la creacion"
    assert "--latest" in publicar, \
        "sin esto `latest/download` apuntaria a otra publicacion"

    # Y que se compruebe que de verdad quedo dentro.
    assert "salió sin el .apk" in publicar


def test_el_apk_se_publica_solo_desde_main():
    """La direccion de descarga es una sola.

    No puede quedarse apuntando a lo que se estaba probando en una rama.
    """
    flujo = _texto(FLUJO)
    publicar = flujo[flujo.index("- name: Publicar para descargar"):]
    assert "github.ref == 'refs/heads/main'" in publicar.split("run:")[0]


def test_la_compilacion_comprueba_el_apk_antes_de_publicarlo():
    """Un .apk que compila puede seguir siendo una pantalla en negro."""
    flujo = _texto(FLUJO)
    for senal in ("apksigner", "verify --verbose", "aapt2\" dump badging",
                  "window.Anfitrion",
                  "el .apk no lleva la misma app que se publica"):
        assert senal in flujo, f"la compilacion no comprueba: {senal}"


# ---------- la llave ----------

def test_la_llave_de_firma_no_entra_en_el_repositorio():
    """Con la llave cualquiera puede publicar una actualizacion de esta app."""
    ignorados = _texto(RAIZ / ".gitignore")
    assert "*.jks" in ignorados and "*.keystore" in ignorados

    seguidos = subprocess.run(
        ["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True)
    llaves = [linea for linea in seguidos.stdout.splitlines()
              if linea.endswith((".jks", ".keystore"))]
    assert not llaves, f"hay una llave versionada: {llaves}"

    herramienta = RAIZ / "herramientas" / "crear-llave-android.sh"
    assert herramienta.is_file(), "no hay forma de crear la llave propia"


def test_sin_llave_propia_la_compilacion_avisa():
    """Firmar con una llave distinta cada vez obliga a desinstalar para actualizar.

    Es un compromiso aceptable mientras no haya llave propia, pero tiene que
    decirse: callarlo deja al operario delante de un «App no instalada».
    """
    flujo = _texto(FLUJO)
    assert "::warning::sin llave propia" in flujo
    assert "desinstalar" in flujo


# ---------- iconos ----------

def test_el_icono_esta_en_todas_las_densidades():
    """Sin la densidad que toca, Android escala el icono y se ve sucio."""
    recursos = ANDROID / "app" / "src" / "main" / "res"
    for densidad in ("mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"):
        carpeta = recursos / f"mipmap-{densidad}"
        assert (carpeta / "ic_launcher.png").is_file(), f"falta el icono {densidad}"
        assert (carpeta / "ic_launcher_foreground.png").is_file(), \
            f"falta el dibujo adaptable {densidad}"
    adaptable = recursos / "mipmap-anydpi-v26" / "ic_launcher.xml"
    assert adaptable.is_file(), "sin icono adaptable, Android 8 lo mete en un cuadro blanco"
    assert "@mipmap/ic_launcher_foreground" in _texto(adaptable)
