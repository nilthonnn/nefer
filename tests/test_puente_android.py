"""El acta sale del telefono por el puente del contenedor de Android.

Dentro de la aplicacion de Android la pagina no puede descargar lo que ella
misma acaba de armar: el PDF, el Excel y el .zip existen solo en memoria y el
contenedor nunca llega a verlos. Se los pasa a trozos por un puente.

Ese trayecto —trocear, cruzar el puente en base64 y volver a juntarlo— es donde
se pierde un byte sin que nadie lo note: el archivo llega, pesa casi lo mismo y
no abre. Aqui se conduce el navegador de verdad con un puente falso al otro
lado, y se comprueba que lo que llega es exactamente lo que salio.

Se prueba contra la app del clon de RD RENTAL, que es la que va dentro del
.apk.
"""

from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "clientes" / "rd-renta" / "docs" / "app" / "index.html"

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402

from navegador import HAY_CHROMIUM, opciones  # noqa: E402


# El contenedor, tal como lo ve la pagina: los mismos cuatro metodos que
# declara Anfitrion.java, y una lista de lo que ha recibido para mirarla luego.
PUENTE_FALSO = """
window.__recibido = [];
window.Anfitrion = {
  _abiertos: {}, _n: 0,
  abrir: function (nombre, mime) {
    var vale = "e" + (++this._n);
    this._abiertos[vale] = { nombre: nombre, mime: mime, trozos: [] };
    return vale;
  },
  trozo: function (vale, base64) {
    var envio = this._abiertos[vale];
    if (!envio) { return "ERROR:el envío ya no está abierto"; }
    envio.trozos.push(base64);
    return "";
  },
  cerrar: function (vale) {
    var envio = this._abiertos[vale];
    if (!envio) { return "ERROR:el envío ya no está abierto"; }
    delete this._abiertos[vale];
    window.__recibido.push(envio);
    return "OK:Descargas/RD RENTAL/" + envio.nombre;
  },
  cancelar: function (vale) { delete this._abiertos[vale]; },
  version: function () { return "1.0 (1)"; }
};
"""


@pytest.fixture(scope="module")
def entregado():
    """Levanta un acta de ejemplo y exporta el Excel y el paquete por el puente."""
    if not HAY_CHROMIUM:
        pytest.skip("no hay Chromium disponible")

    fallos: list[str] = []
    descargas: list[str] = []

    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True,
                              accept_downloads=True, permissions=[])
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fallos.append(str(e)))
        # El puente tiene que existir ANTES de que corra la pagina: es de donde
        # saca `CONTEXTO.enAndroid`, y eso se decide al arrancar.
        pg.add_init_script(PUENTE_FALSO)
        # Si algo se descargara por el camino de siempre, el puente no se
        # estaria usando y la prueba no probaria nada.
        pg.on("download", lambda d: descargas.append(d.suggested_filename))

        pg.goto(APP.as_uri())
        pg.wait_for_timeout(600)
        assert pg.evaluate("RDRENTA.CONTEXTO.enAndroid") is True, \
            "la app no reconocio el contenedor"

        pg.click("#btn-demo")
        pg.wait_for_timeout(2500)
        assert pg.eval_on_selector_all("#d-grid .slot.lleno", "n => n.length") == 10

        pg.click("#d-xlsx")
        pg.wait_for_function("window.__recibido.length >= 1", timeout=60000)
        pg.click("#d-zip")
        pg.wait_for_function("window.__recibido.length >= 2", timeout=60000)
        aviso = pg.inner_text("#d-copiado")

        # Un archivo mayor que el trozo, por el mismo embudo: 0..255 repetido,
        # que delata cualquier byte perdido, repetido o fuera de sitio.
        pg.evaluate("""() => new Promise(function (listo) {
          var patron = new Uint8Array(256 * 5120);
          for (var i = 0; i < patron.length; i++) { patron[i] = i % 256; }
          RDRENTA.entregar(new Blob([patron]), "grande.bin", function () { });
          var espera = setInterval(function () {
            if (window.__recibido.length >= 3) { clearInterval(espera); listo(); }
          }, 50);
        })""")
        pg.wait_for_function("window.__recibido.length >= 3", timeout=60000)

        recibido = pg.evaluate("window.__recibido")
        nav.close()

    assert fallos == [], fallos
    assert descargas == [], f"salio por el camino de siempre: {descargas}"
    return {"envios": recibido[:2], "grande": recibido[2], "aviso": aviso}


def _juntar(envio) -> bytes:
    """Lo mismo que hace Anfitrion.java: descodificar trozo a trozo y pegar."""
    return b"".join(base64.b64decode(t) for t in envio["trozos"])


def test_el_excel_llega_entero_por_el_puente(entregado):
    envio = entregado["envios"][0]
    assert envio["nombre"].endswith(".xlsx")

    datos = _juntar(envio)
    # Si se perdiera o se repitiera un byte, esto es lo primero que se rompe.
    libro = zipfile.ZipFile(io.BytesIO(datos))
    assert libro.testzip() is None
    assert "xl/workbook.xml" in libro.namelist()
    imagenes = [n for n in libro.namelist() if n.startswith("xl/media/")]
    # Las diez fotos del acta y el logo de la cabecera.
    assert len(imagenes) == 11, imagenes


def test_el_paquete_llega_entero_por_el_puente(entregado):
    envio = entregado["envios"][1]
    assert envio["nombre"].endswith(".zip")

    paquete = zipfile.ZipFile(io.BytesIO(_juntar(envio)))
    assert paquete.testzip() is None
    nombres = paquete.namelist()
    assert any(n.endswith(".json") for n in nombres), nombres
    assert sum(1 for n in nombres if n.startswith("fotos/")) == 10


def test_un_acta_grande_cruza_el_puente_a_trozos_y_sin_perder_un_byte(entregado):
    """El acta de ejemplo cabe en un viaje; una de verdad, con veinte fotos, no.

    Ese es justo el caso que no se puede probar con la demo y el que tumba un
    telefono de gama baja, asi que se fuerza: un archivo de mas de un mega por
    el mismo embudo por el que salen el PDF, el Excel y el paquete.
    """
    grande = entregado["grande"]
    assert len(grande["trozos"]) == 3, \
        f"1,25 MB tendrian que ir en tres viajes, no en {len(grande['trozos'])}"
    # Ningun trozo puede pasarse del tamano acordado (base64 crece 4/3).
    for trozo in grande["trozos"]:
        assert len(base64.b64decode(trozo)) <= 512 * 1024
    # Y lo que llega al otro lado tiene que ser, byte a byte, lo que salio.
    assert _juntar(grande) == bytes(range(256)) * 5120


def test_el_aviso_dice_donde_quedo_el_archivo(entregado):
    """En un telefono, «guardado» a secas no le sirve a nadie."""
    # La hoja lo pinta en mayusculas; lo que importa es lo que dice.
    assert "descargas/rd rental/" in entregado["aviso"].lower(), entregado["aviso"]
