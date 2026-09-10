"""Pruebas de la aplicacion de campo contra un navegador real.

Validan las dos vias por las que entra una foto —galeria y camara— tal como
las usa el operador: abriendo el selector de archivos de verdad y disparando
una camara de verdad, no inyectando ficheros por detras.

Se saltan enteras si no hay Playwright o Chromium: `python -m pytest` tiene
que seguir pasando en una maquina sin navegador.
"""

from __future__ import annotations

import io
import json
import os
import struct
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402
from PIL import Image  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "docs" / "app" / "index.html"

from navegador import HAY_CHROMIUM, opciones  # noqa: E402

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")

UA_ANDROID = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120 Mobile Safari/537.36")


# --------------------------------------------------------------------------
# fotos de prueba, fabricadas como las entrega un telefono
# --------------------------------------------------------------------------

def _bloque_exif(fecha: str) -> bytes:
    """TIFF minimo con DateTimeOriginal. 20 bytes de texto, contando el nulo."""
    texto = fecha.encode("ascii") + b"\x00"
    assert len(texto) == 20
    t = bytearray()
    t += b"II\x2a\x00" + struct.pack("<I", 8)
    t += struct.pack("<H", 1)
    t += struct.pack("<HHII", 0x8769, 4, 1, 26)     # puntero al ExifIFD
    t += struct.pack("<I", 0)
    t += struct.pack("<H", 1)
    t += struct.pack("<HHII", 0x9003, 2, 20, 44)    # DateTimeOriginal
    t += struct.pack("<I", 0)
    t += texto
    return b"Exif\x00\x00" + bytes(t)


def _jpeg(ruta: Path, color, fecha: str | None = None, tam=(1024, 768)) -> Path:
    img = Image.new("RGB", tam, color)
    if fecha:
        img.save(ruta, "JPEG", quality=90, exif=_bloque_exif(fecha))
    else:
        img.save(ruta, "JPEG", quality=90)
    return ruta


@pytest.fixture(scope="module")
def fotos(tmp_path_factory) -> dict[str, Path]:
    """Un juego de archivos como los que llegan de un telefono de verdad."""
    d = tmp_path_factory.mktemp("fotos")
    salida = {
        # nombradas y con hora de captura, en desorden alfabetico a proposito
        "frontal": _jpeg(d / "03-frontal.jpg", (92, 104, 118), "2026:09:09 07:41:12"),
        "posterior": _jpeg(d / "01-posterior.jpg", (104, 92, 84), "2026:09:09 07:42:30"),
        "horometro": _jpeg(d / "02-horometro.jpg", (34, 36, 40), "2026:09:09 07:43:05"),
        # como la entrega un selector de Android: sin extension
        "sin_nombre": _jpeg(d / "content-1000012345", (70, 90, 70)),
        # grande, como sale de la camara del telefono
        "grande": _jpeg(d / "IMG_4088.jpg", (120, 110, 100),
                        "2026:09:09 07:44:00", tam=(3024, 4032)),
    }
    # un HEIC que ningun navegador decodifica
    heic = d / "IMG_4021.HEIC"
    heic.write_bytes(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 64)
    salida["heic"] = heic
    # algo que no es una imagen
    texto = d / "notas.txt"
    texto.write_text("esto no es una foto")
    salida["texto"] = texto
    # nombre repetido, en otra carpeta
    otra = d / "otra"
    otra.mkdir()
    salida["repetida"] = _jpeg(otra / "03-frontal.jpg", (60, 70, 80))
    # sin ninguna pista en el nombre, y en orden alfabetico inverso a su hora:
    # solo el EXIF puede ordenarlas bien
    salida["tarde"] = _jpeg(d / "aaa.jpg", (30, 60, 90), "2026:09:09 08:30:00")
    salida["media"] = _jpeg(d / "mmm.jpg", (60, 90, 30), "2026:09:09 08:20:00")
    salida["pronto"] = _jpeg(d / "zzz.jpg", (90, 30, 60), "2026:09:09 08:10:00")
    return salida


# --------------------------------------------------------------------------
# utilidades de navegador
# --------------------------------------------------------------------------

class App:
    """La aplicacion abierta en una pagina, con lo justo para conducirla."""

    def __init__(self, pagina):
        self.pg = pagina
        self.errores: list[str] = []
        pagina.on("pageerror", lambda e: self.errores.append(str(e)))

    def despacho(self):
        self.pg.click("#tab-despacho")
        self.pg.wait_for_timeout(200)
        return self

    def cargar_por_galeria(self, rutas, selector="label[for='d-file']"):
        """Pasa por el selector de archivos de verdad, como el operador."""
        with self.pg.expect_file_chooser(timeout=10000) as fc:
            self.pg.click(selector)
        fc.value.set_files([str(r) for r in rutas])
        self._esperar_carga(len(rutas))
        return self

    def _esperar_carga(self, cuantas):
        self.pg.wait_for_function(
            "() => document.querySelector('#d-progreso').hidden",
            timeout=30000)
        self.pg.wait_for_timeout(400)

    @property
    def llenas(self) -> int:
        return self.pg.eval_on_selector_all("#d-grid .slot.lleno", "n => n.length")

    @property
    def bandeja(self) -> int:
        return int(self.pg.inner_text("#d-t-bandeja"))

    @property
    def mensaje(self) -> str:
        return " ".join(self.pg.inner_text("#d-estado").split())

    @property
    def acta(self) -> dict:
        return json.loads(self.pg.input_value("#d-salida"))

    def rotulos(self) -> list[tuple[str, str]]:
        return [(f["descripcion"], f["archivo"]) for f in self.acta["registro_fotografico"]]


def _lanzar(pw, *, camara=False):
    args = (["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"]
            if camara else [])
    return pw.chromium.launch(**opciones(args=args))


def _contexto(nav, *, movil=False, camara=False, descargas=False):
    opciones = {"viewport": {"width": 390, "height": 844}, "locale": "es-PE"}
    if movil:
        opciones.update(has_touch=True, is_mobile=True, user_agent=UA_ANDROID)
    opciones["permissions"] = ["camera"] if camara else []
    if descargas:
        opciones["accept_downloads"] = True
    return nav.new_context(**opciones)


def _sin_camara(pagina):
    """Un navegador que no ofrece camara: fuerza la via del selector."""
    pagina.add_init_script(
        "Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:undefined});")


# ==========================================================================
# GALERIA
# ==========================================================================

@pytest.mark.parametrize("movil", [False, True], ids=["computadora", "celular"])
def test_galeria_carga_y_ordena_por_hora_de_captura(fotos, movil):
    """Las fotos entran por el selector real y se ordenan por su EXIF."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=movil).new_page()
        _sin_camara(pg)
        pg.goto(APP.as_uri())
        app = App(pg).despacho()

        app.cargar_por_galeria([fotos["frontal"], fotos["posterior"], fotos["horometro"]])

        assert app.llenas == 3, app.mensaje
        assert app.bandeja == 0
        rotulos = app.rotulos()
        # El nombre manda sobre la hora: cada archivo cae en su vista.
        assert rotulos[0] == ("VISTA FRONTAL", "fotos/03-frontal.jpg")
        assert ("VISTA POSTERIOR", "fotos/01-posterior.jpg") in rotulos
        assert ("HORÓMETRO", "fotos/02-horometro.jpg") in rotulos
        assert app.errores == []
        nav.close()


def test_galeria_ordena_por_hora_de_captura_cuando_el_nombre_no_dice_nada(fotos):
    """Sin pista en el nombre, manda el EXIF: zzz.jpg es la primera del carrete."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav).new_page()
        _sin_camara(pg)
        pg.goto(APP.as_uri())
        app = App(pg).despacho()

        # Se entregan en orden alfabetico; la hora de captura es la inversa.
        app.cargar_por_galeria([fotos["tarde"], fotos["media"], fotos["pronto"]])

        assert app.llenas == 3, app.mensaje
        assert app.rotulos() == [
            ("VISTA FRONTAL", "fotos/zzz.jpg"),      # 08:10
            ("VISTA POSTERIOR", "fotos/mmm.jpg"),    # 08:20
            ("VISTA LATERAL IZQUIERDA", "fotos/aaa.jpg"),  # 08:30
        ]
        assert app.errores == []
        nav.close()


def test_cargar_mas_fotos_no_deshace_lo_ya_colocado(fotos):
    """Lo que el operador ordena a mano manda sobre cualquier propuesta."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav).new_page()
        _sin_camara(pg)
        pg.goto(APP.as_uri())
        app = App(pg).despacho()

        app.cargar_por_galeria([fotos["frontal"], fotos["posterior"]])
        assert app.llenas == 2, app.mensaje

        # Se saca la frontal de su casilla y se lleva a mano a PANEL DE CONTROL.
        pg.click("#d-grid .slot:nth-child(1)")           # vaciar: vuelve a la bandeja
        pg.wait_for_timeout(250)
        pg.click("#d-tray .tile")                        # elegirla
        pg.wait_for_timeout(200)
        casillas = pg.query_selector_all("#d-grid .slot")
        assert casillas[5].query_selector(".cap span").inner_text() == "PANEL DE CONTROL"
        casillas[5].click()
        pg.wait_for_timeout(300)
        assert ("PANEL DE CONTROL", "fotos/03-frontal.jpg") in app.rotulos()

        # Llega una foto mas: no puede mover nada de lo anterior.
        app.cargar_por_galeria([fotos["horometro"]])

        rotulos = app.rotulos()
        assert ("PANEL DE CONTROL", "fotos/03-frontal.jpg") in rotulos, rotulos
        assert ("VISTA POSTERIOR", "fotos/01-posterior.jpg") in rotulos, rotulos
        assert ("HORÓMETRO", "fotos/02-horometro.jpg") in rotulos, rotulos
        assert app.errores == []
        nav.close()


def test_galeria_admite_archivo_sin_extension_ni_tipo(fotos):
    """Lo que entrega un selector de Android: sin extension y sin tipo MIME."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        _sin_camara(pg)
        pg.goto(APP.as_uri())
        app = App(pg).despacho()

        app.cargar_por_galeria([fotos["sin_nombre"]])

        assert app.llenas == 1, app.mensaje
        assert "no entraron" not in app.mensaje.lower()
        assert app.errores == []
        nav.close()


def test_galeria_nombra_lo_que_no_puede_abrir(fotos):
    """Nada desaparece en silencio: cada descarte se explica por su nombre."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav).new_page()
        _sin_camara(pg)
        pg.goto(APP.as_uri())
        app = App(pg).despacho()

        app.cargar_por_galeria([fotos["frontal"], fotos["heic"], fotos["texto"],
                                fotos["sin_nombre"]])

        assert app.llenas == 2, app.mensaje
        assert "2 de 4 fotos cargadas" in app.mensaje
        assert "IMG_4021.HEIC" in app.mensaje
        assert "HEIC" in app.mensaje
        assert "notas.txt" in app.mensaje
        assert app.errores == []
        nav.close()


def test_galeria_reduce_la_foto_grande(fotos, tmp_path):
    """Una foto de 3024x4032 no puede viajar entera en el paquete."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        ctx = _contexto(nav, descargas=True)
        pg = ctx.new_page()
        _sin_camara(pg)
        pg.goto(APP.as_uri())
        app = App(pg).despacho()

        app.cargar_por_galeria([fotos["grande"]])
        assert app.llenas == 1, app.mensaje

        mostrada = pg.evaluate(
            "() => { const i = document.querySelector('#d-grid .slot.lleno img');"
            "        return {w: i.naturalWidth, h: i.naturalHeight}; }")
        assert max(mostrada["w"], mostrada["h"]) == 1600

        paquete = _guardar_paquete(pg, tmp_path)
        with zipfile.ZipFile(paquete) as z:
            nombre = [n for n in z.namelist() if n.startswith("fotos/")][0]
            im = Image.open(io.BytesIO(z.read(nombre)))
        assert max(im.size) == 1600
        assert paquete.stat().st_size < fotos["grande"].stat().st_size / 2
        assert app.errores == []
        nav.close()


def test_galeria_separa_nombres_repetidos(fotos, tmp_path):
    """Dos fotos con el mismo nombre no pueden apuntar al mismo archivo."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, descargas=True).new_page()
        _sin_camara(pg)
        pg.goto(APP.as_uri())
        app = App(pg).despacho()

        app.cargar_por_galeria([fotos["frontal"], fotos["repetida"]])
        assert app.llenas == 2, app.mensaje

        citados = [f["archivo"] for f in app.acta["registro_fotografico"]]
        assert len(set(citados)) == 2, citados

        with zipfile.ZipFile(_guardar_paquete(pg, tmp_path)) as z:
            empaquetados = sorted(n for n in z.namelist() if n.startswith("fotos/"))
        assert empaquetados == sorted(citados)
        nav.close()


def test_galeria_dice_algo_cuando_el_selector_no_devuelve_nada():
    """Cancelar el selector no puede dejar la pantalla muda."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav).new_page()
        _sin_camara(pg)
        pg.goto(APP.as_uri())
        app = App(pg).despacho()

        pg.evaluate("""() => {
          const i = document.querySelector('#d-file');
          i.dispatchEvent(new Event('change', {bubbles: true}));
        }""")
        pg.wait_for_timeout(400)

        assert "no devolvió ningún archivo" in app.mensaje
        assert app.errores == []
        nav.close()


def test_galeria_funciona_dentro_de_un_marco_con_sandbox(fotos, tmp_path):
    """Publicada como pagina, la app va incrustada: el selector debe abrirse."""
    marco = tmp_path / "marco.html"
    marco.write_text(
        '<!doctype html><meta charset="utf-8"><body style="margin:0">'
        '<iframe style="width:390px;height:800px;border:0" '
        'sandbox="allow-scripts allow-forms allow-popups allow-modals" '
        f'src="{APP.as_uri()}"></iframe>', encoding="utf-8")

    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav).new_page()
        errores: list[str] = []
        pg.on("pageerror", lambda e: errores.append(str(e)))
        pg.goto(marco.as_uri())
        pg.wait_for_timeout(800)
        dentro = pg.frame_locator("iframe")

        dentro.locator("#tab-despacho").click()
        with pg.expect_file_chooser(timeout=10000) as fc:
            dentro.locator("label[for='d-file']").click()
        fc.value.set_files([str(fotos["frontal"]), str(fotos["posterior"])])
        pg.wait_for_timeout(3000)

        assert dentro.locator("#d-grid .slot.lleno").count() == 2
        assert errores == []
        nav.close()


# ==========================================================================
# CAMARA
# ==========================================================================

def test_camara_recorre_las_casillas_y_cada_foto_cae_en_la_suya(servidor):
    """El disparo entra en la casilla que el panel anuncia, y avanza sola."""
    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True).new_page()
        pg.goto(servidor)
        app = App(pg).despacho()

        pg.click("#d-camara-app")
        pg.wait_for_function(
            "() => { const v = document.querySelector('#cam-video');"
            "        return v && v.videoWidth > 0; }", timeout=15000)

        assert pg.is_visible("#camara")
        assert pg.is_hidden("#cam-aviso")
        assert pg.inner_text("#cam-rotulo") == "VISTA FRONTAL"

        esperados = []
        for _ in range(4):
            esperados.append(pg.inner_text("#cam-rotulo"))
            pg.click("#cam-disparar")
            pg.wait_for_timeout(1200)

        assert esperados == ["VISTA FRONTAL", "VISTA POSTERIOR",
                             "VISTA LATERAL IZQUIERDA", "VISTA LATERAL DERECHA"]
        assert pg.inner_text("#cam-rotulo") == "HORÓMETRO"
        assert "quedan 6" in pg.inner_text("#cam-cuenta")

        pg.click("#cam-cerrar")
        pg.wait_for_timeout(300)
        assert pg.is_hidden("#camara")

        assert app.llenas == 4
        # Cada foto queda nombrada por la vista que ocupa.
        assert app.rotulos() == [
            ("VISTA FRONTAL", "fotos/01-vista-frontal.jpg"),
            ("VISTA POSTERIOR", "fotos/02-vista-posterior.jpg"),
            ("VISTA LATERAL IZQUIERDA", "fotos/03-vista-lateral-izquierda.jpg"),
            ("VISTA LATERAL DERECHA", "fotos/04-vista-lateral-derecha.jpg"),
        ]
        assert app.errores == []
        nav.close()


def test_el_despacho_admite_vistas_ademas_de_las_del_formato(servidor):
    """En el patio aparece lo que aparece, y hay que fotografiarlo en la rejilla.

    La vista se anade, se le escribe el rotulo, se fotografia como cualquier
    otra y viaja en el acta como una vista mas. Se puede quitar sin descolocar
    las demas.
    """
    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True).new_page()
        errores: list[str] = []
        pg.on("pageerror", lambda e: errores.append(str(e)))
        pg.goto(servidor)
        app = App(pg).despacho()

        del_formato = pg.eval_on_selector_all("#d-grid .slot", "n => n.length")
        assert del_formato == 10

        pg.click("#d-add-vista")
        pg.wait_for_timeout(300)
        assert pg.eval_on_selector_all("#d-grid .slot", "n => n.length") == del_formato + 1
        assert pg.input_value("[data-vista-rotulo='0']") == "VISTA ADICIONAL 1"

        # El rótulo se escribe encima, letra a letra, sin perder el foco.
        pg.fill("[data-vista-rotulo='0']", "")
        pg.click("[data-vista-rotulo='0']")
        pg.keyboard.type("Enganche trasero", delay=25)
        pg.wait_for_timeout(200)
        assert pg.input_value("[data-vista-rotulo='0']") == "Enganche trasero"
        assert pg.evaluate("() => document.activeElement.dataset.vistaRotulo") == "0"

        # La cámara apunta a esa casilla, con su rótulo.
        pg.query_selector_all("#d-grid .slot")[-1].click()
        pg.wait_for_function("() => document.querySelector('#cam-video').videoWidth > 0",
                             timeout=15000)
        assert pg.inner_text("#cam-rotulo") == "ENGANCHE TRASERO"
        pg.click("#cam-disparar")
        pg.wait_for_timeout(1500)
        pg.click("#cam-cerrar")
        pg.wait_for_timeout(500)

        # Y llega al acta como una vista más, en mayúsculas como las del formato.
        assert app.rotulos() == [("ENGANCHE TRASERO", "fotos/11-enganche-trasero.jpg")]

        # Una segunda que se quita: la primera se queda donde estaba.
        pg.click("#d-add-vista")
        pg.wait_for_timeout(300)
        pg.click("[data-vista-quitar='1']")
        pg.wait_for_timeout(300)
        assert pg.eval_on_selector_all("[data-vista-rotulo]",
                                       "n => n.map(x => x.value)") == ["Enganche trasero"]
        assert app.rotulos() == [("ENGANCHE TRASERO", "fotos/11-enganche-trasero.jpg")]
        assert errores == [], errores
        nav.close()


def test_la_camara_de_la_recepcion_pinta_la_foto_que_toma(servidor):
    """La foto tiene que verse en la casilla, no solo guardarse.

    Medido antes del arreglo: `$("#r-c3")` no existia, la linea lanzaba
    TypeError y `pintar()` no llegaba a correr. La foto entraba en la bandeja y
    la pantalla seguia igual —en el patio, «la camara no guarda la foto»—.
    """
    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True).new_page()
        errores: list[str] = []
        pg.on("pageerror", lambda e: errores.append(str(e)))
        pg.goto(servidor)
        pg.wait_for_timeout(300)

        pg.click("#tab-recepcion")
        pg.wait_for_timeout(200)
        pg.select_option("#r-cat", "grupo_electrogeno")
        pg.click("#r-empezar")
        pg.wait_for_timeout(600)

        pg.click("#r-camara-app")
        pg.wait_for_function("() => document.querySelector('#cam-video').videoWidth > 0",
                             timeout=15000)
        rotulo = pg.inner_text("#cam-rotulo")
        pg.click("#cam-disparar")
        pg.wait_for_timeout(1500)
        pg.click("#cam-cerrar")
        pg.wait_for_timeout(500)

        assert errores == [], errores
        # La casilla de esa vista quedó ocupada, a la vista del operador.
        llenas = pg.eval_on_selector_all("#r-vistas .slot.lleno", "n => n.length")
        assert llenas == 1, f"{rotulo}: la foto no se pintó en su casilla"
        assert "1 foto(s)" in pg.inner_text("#r-e3").lower()
        nav.close()


def test_camara_saltar_deja_la_casilla_vacia(servidor):
    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True).new_page()
        pg.goto(servidor)
        app = App(pg).despacho()

        pg.click("#d-camara-app")
        pg.wait_for_function("() => document.querySelector('#cam-video').videoWidth > 0",
                             timeout=15000)
        pg.click("#cam-saltar")
        pg.wait_for_timeout(200)
        assert pg.inner_text("#cam-rotulo") == "VISTA POSTERIOR"

        pg.click("#cam-disparar")
        pg.wait_for_timeout(1200)
        pg.click("#cam-cerrar")
        pg.wait_for_timeout(300)

        assert app.rotulos() == [("VISTA POSTERIOR", "fotos/02-vista-posterior.jpg")]
        assert app.errores == []
        nav.close()


def test_camara_desde_una_casilla_concreta(servidor):
    """Tocar una casilla vacia fotografia solo para esa casilla."""
    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True).new_page()
        pg.goto(servidor)
        app = App(pg).despacho()

        casillas = pg.query_selector_all("#d-grid .slot")
        objetivo = casillas[4]                      # HORÓMETRO
        rotulo = objetivo.query_selector(".cap span").inner_text()
        objetivo.click()
        pg.wait_for_function("() => document.querySelector('#cam-video').videoWidth > 0",
                             timeout=15000)

        assert pg.inner_text("#cam-rotulo") == rotulo == "HORÓMETRO"
        assert "quedan 1" in pg.inner_text("#cam-cuenta")

        pg.click("#cam-disparar")
        pg.wait_for_timeout(1200)
        pg.click("#cam-cerrar")
        pg.wait_for_timeout(400)

        assert app.rotulos() == [("HORÓMETRO", "fotos/05-horometro.jpg")]
        assert app.errores == []
        nav.close()


def test_camara_denegada_ofrece_la_galeria_sin_perder_la_casilla(fotos, servidor):
    """Si la camara no se concede, el operador sale por la galeria."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        pg.add_init_script("""
          Object.defineProperty(navigator, 'mediaDevices', {configurable: true, value: {
            getUserMedia: () => Promise.reject(
              Object.assign(new Error('x'), {name: 'NotAllowedError'}))}});
        """)
        pg.goto(servidor)
        app = App(pg).despacho()

        casillas = pg.query_selector_all("#d-grid .slot")
        casillas[4].click()                          # HORÓMETRO
        pg.wait_for_timeout(900)

        assert pg.is_visible("#cam-aviso")
        aviso = " ".join(pg.inner_text("#cam-aviso").split())
        assert "bloqueada" in aviso
        # Servida y de primer nivel, el motivo es el permiso del navegador.
        assert "permiso" in aviso and "Cámara" in aviso

        with pg.expect_file_chooser(timeout=10000) as fc:
            pg.click("#cam-galeria")
        fc.value.set_files([str(fotos["frontal"])])
        pg.wait_for_function("() => document.querySelector('#d-progreso').hidden",
                             timeout=30000)
        pg.wait_for_timeout(500)

        assert pg.is_hidden("#camara")
        # La foto va a la casilla que se habia tocado, no a la primera libre.
        assert app.rotulos() == [("HORÓMETRO", "fotos/03-frontal.jpg")]

        # Comprobado el fallo, la camara deja de interponerse.
        assert pg.is_hidden("#d-camara-app")
        vacias = pg.query_selector_all("#d-grid .slot:not(.lleno)")
        with pg.expect_file_chooser(timeout=10000) as fc2:
            vacias[0].click()
        fc2.value.set_files([str(fotos["posterior"])])
        pg.wait_for_function("() => document.querySelector('#d-progreso').hidden",
                             timeout=30000)
        assert pg.is_hidden("#camara")
        assert app.errores == []
        nav.close()


def test_escribir_en_una_observacion_no_pierde_el_foco(servidor):
    """Repintar recreaba el campo y el operador escribia de letra en letra.

    Medido antes del arreglo: al teclear «CONOS» en el nombre quedaba «C», y
    lo mismo en la recepcion. Un formulario asi no se puede llenar en el patio.
    """
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        errores: list[str] = []
        pg.on("pageerror", lambda e: errores.append(str(e)))
        pg.goto(servidor)

        # --- despacho ---
        pg.click("#tab-despacho")
        pg.wait_for_timeout(200)
        pg.click("#d-add-cons")
        pg.click("[data-acc-nombre='0']")
        pg.keyboard.type("CONOS", delay=40)
        pg.wait_for_timeout(200)
        assert pg.input_value("[data-acc-nombre='0']") == "CONOS"
        assert pg.evaluate("() => document.activeElement.dataset.accNombre") == "0"
        # Y la descripción se redacta sola con lo escrito.
        assert pg.input_value("[data-acc-texto='0']") == "01 CONOS DESPACHADO"

        # Escribir en medio de la descripción respeta el cursor.
        pg.evaluate("""() => { const n = document.querySelector("[data-acc-texto='0']");
                               n.focus(); n.setSelectionRange(3, 3); }""")
        pg.keyboard.type("XY", delay=40)
        pg.wait_for_timeout(200)
        assert pg.input_value("[data-acc-texto='0']") == "01 XYCONOS DESPACHADO"
        assert pg.eval_on_selector("[data-acc-texto='0']", "n => n.selectionStart") == 5

        # --- recepción ---
        pg.click("#tab-recepcion")
        pg.wait_for_timeout(200)
        pg.select_option("#r-cat", "grupo_electrogeno")
        pg.click("#r-empezar")
        pg.wait_for_timeout(400)
        pg.click("#r-add-cons")
        pg.click("[data-cons-nombre='0']")
        pg.keyboard.type("EXTINTOR", delay=40)
        pg.wait_for_timeout(200)
        assert pg.input_value("[data-cons-nombre='0']") == "EXTINTOR"
        assert pg.evaluate("() => document.activeElement.dataset.consNombre") == "0"

        assert errores == []
        nav.close()


def test_la_camara_ofrece_la_galeria_sin_que_haga_falta_que_falle(fotos, servidor):
    """Las dos vias de la foto viven en el mismo mando.

    Antes, con camara concedida, elegir una foto ya tomada obligaba a cerrar
    la camara y buscar el boton en otra parte de la pantalla; el destino se
    perdia por el camino. El boton de galeria esta siempre, y respeta la
    casilla a la que se apunto.
    """
    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True).new_page()
        pg.goto(servidor)
        app = App(pg).despacho()

        casillas = pg.query_selector_all("#d-grid .slot")
        casillas[4].click()                          # HORÓMETRO
        pg.wait_for_function("() => document.querySelector('#cam-video').videoWidth > 0",
                             timeout=15000)
        assert pg.is_hidden("#cam-aviso")            # la camara funciona
        assert pg.is_visible("#cam-galeria")

        with pg.expect_file_chooser(timeout=10000) as fc:
            pg.click("#cam-galeria")
        fc.value.set_files([str(fotos["frontal"])])
        pg.wait_for_function("() => document.querySelector('#d-progreso').hidden",
                             timeout=30000)
        pg.wait_for_timeout(500)

        assert pg.is_hidden("#camara")
        assert app.rotulos() == [("HORÓMETRO", "fotos/03-frontal.jpg")]
        assert app.errores == []
        nav.close()


def test_la_observacion_se_fotografia_por_camara_o_por_galeria(fotos, servidor):
    """El mismo mando en la seccion OBSERVACIONES, que es lo que se anade abajo."""
    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True).new_page()
        pg.goto(servidor)
        app = App(pg).despacho()

        pg.click("#d-add-cons")
        pg.fill("[data-acc-nombre='0']", 'CONOS DE SEGURIDAD DE 28"')
        pg.wait_for_timeout(200)

        pg.click("#d-cons label[data-acc='0']")
        pg.wait_for_function("() => document.querySelector('#cam-video').videoWidth > 0",
                             timeout=15000)
        assert pg.inner_text("#cam-rotulo") == 'CONOS DE SEGURIDAD DE 28"'
        assert pg.is_visible("#cam-galeria")

        with pg.expect_file_chooser(timeout=10000) as fc:
            pg.click("#cam-galeria")
        fc.value.set_files([str(fotos["frontal"])])
        pg.wait_for_function("() => document.querySelector('#d-progreso').hidden",
                             timeout=30000)
        pg.wait_for_timeout(500)

        assert pg.is_hidden("#camara")
        consumibles = app.acta["consumibles"]
        assert len(consumibles) == 1
        assert consumibles[0]["descripcion"] == 'CONOS DE SEGURIDAD DE 28"'
        assert consumibles[0]["foto_despacho"] == "fotos/03-frontal.jpg"
        assert app.errores == []
        nav.close()


def test_sin_camara_la_casilla_vacia_abre_el_selector(fotos):
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        _sin_camara(pg)
        pg.goto(APP.as_uri())
        app = App(pg).despacho()

        assert pg.is_hidden("#d-camara-app")
        vacias = pg.query_selector_all("#d-grid .slot:not(.lleno)")
        objetivo = vacias[2]
        rotulo = objetivo.query_selector(".cap span").inner_text()
        with pg.expect_file_chooser(timeout=10000) as fc:
            objetivo.click()
        fc.value.set_files([str(fotos["frontal"])])
        pg.wait_for_function("() => document.querySelector('#d-progreso').hidden",
                             timeout=30000)
        pg.wait_for_timeout(400)

        assert app.rotulos() == [(rotulo, "fotos/03-frontal.jpg")]
        assert app.errores == []
        nav.close()


def test_camara_en_marco_con_sandbox_no_deja_al_operador_sin_salida(fotos, tmp_path):
    """Incrustada y sin permiso de camara, la galeria tiene que seguir ahi."""
    marco = tmp_path / "marco2.html"
    marco.write_text(
        '<!doctype html><meta charset="utf-8"><body style="margin:0">'
        '<iframe style="width:390px;height:800px;border:0" '
        'sandbox="allow-scripts allow-forms allow-popups allow-modals" '
        f'src="{APP.as_uri()}"></iframe>', encoding="utf-8")

    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        errores: list[str] = []
        pg.on("pageerror", lambda e: errores.append(str(e)))
        pg.goto(marco.as_uri())
        pg.wait_for_timeout(800)
        dentro = pg.frame_locator("iframe")
        dentro.locator("#tab-despacho").click()
        pg.wait_for_timeout(300)

        # La galeria funciona aunque la camara no se conceda.
        with pg.expect_file_chooser(timeout=10000) as fc:
            dentro.locator("label[for='d-file']").click()
        fc.value.set_files([str(fotos["frontal"])])
        pg.wait_for_timeout(3000)
        assert dentro.locator("#d-grid .slot.lleno").count() == 1
        assert errores == []
        nav.close()


# ==========================================================================
# SERVIDA POR HTTP: es la unica forma de que el telefono conceda la camara
# ==========================================================================

@pytest.fixture(scope="session")
def servidor():
    """Sirve docs/app por http, como lo hara GitHub Pages."""
    import functools
    import http.server
    import socketserver
    import threading

    raiz = APP.parent
    manejador = functools.partial(http.server.SimpleHTTPRequestHandler,
                                  directory=str(raiz))
    manejador.log_message = lambda *a, **k: None

    class Silencioso(socketserver.TCPServer):
        allow_reuse_address = True

    srv = Silencioso(("127.0.0.1", 0), manejador)
    puerto = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{puerto}/"
    srv.shutdown()


SONDA_ORIGEN = """async () => {
  const r = {seguro: window.isSecureContext, protocolo: location.protocol};
  try {
    const p = await navigator.permissions.query({name: 'camera'});
    r.permiso = p.state;
  } catch (e) { r.permiso = 'no consultable'; }
  try {
    const s = await navigator.mediaDevices.getUserMedia({video: true});
    s.getTracks().forEach(t => t.stop());
    r.camara = 'concedida';
  } catch (e) { r.camara = 'rechazada:' + e.name; }
  return r;
}"""


def test_desde_un_archivo_local_la_camara_no_puede_concederse():
    """El motivo de fondo: a `file://` el navegador le niega la camara.

    Sin --use-fake-ui, el permiso hay que concederlo, y a un origen local no
    se le puede conceder. Esta prueba fija el porque de todo lo demas.
    """
    with sync_playwright() as pw:
        nav = pw.chromium.launch(
            **opciones(args=["--use-fake-device-for-media-stream"]))
        # permissions=[] deniega sin preguntar: sin esto el dialogo se queda
        # abierto y la promesa nunca se resuelve.
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True,
                              user_agent=UA_ANDROID, permissions=[])
        pg = ctx.new_page()
        pg.goto(APP.as_uri())
        pg.wait_for_timeout(400)

        r = pg.evaluate(SONDA_ORIGEN)
        assert r["protocolo"] == "file:"
        assert r["camara"].startswith("rechazada"), r
        nav.close()


def test_servida_por_http_la_camara_se_concede(servidor):
    with sync_playwright() as pw:
        nav = pw.chromium.launch(
            **opciones(args=["--use-fake-device-for-media-stream"]))
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True,
                              user_agent=UA_ANDROID, permissions=["camera"])
        pg = ctx.new_page()
        pg.goto(servidor)
        pg.wait_for_timeout(400)

        r = pg.evaluate(SONDA_ORIGEN)
        assert r["camara"] == "concedida", r
        assert r["permiso"] == "granted", r
        nav.close()


def test_servida_declara_manifiesto_externo_y_registra_el_trabajador(servidor):
    """Servida es una aplicacion instalable de verdad, y guarda para sin senal."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        pg.goto(servidor)
        pg.wait_for_timeout(600)

        manifiesto = pg.get_attribute('head link[rel="manifest"]', "href")
        assert manifiesto == "manifest.webmanifest", manifiesto

        cdp = pg.context.new_cdp_session(pg)
        datos = cdp.send("Page.getAppManifest")
        assert datos.get("errors") == [], datos.get("errors")
        leido = json.loads(datos["data"])
        assert leido["display"] == "standalone"
        assert len(leido["icons"]) == 3

        registrado = pg.evaluate("""async () => {
          const r = await navigator.serviceWorker.getRegistration();
          return !!r;
        }""")
        assert registrado, "el trabajador de servicio no se registro"
        nav.close()


def test_servida_abre_sin_conexion(servidor):
    """Cortada la red, la app tiene que seguir abriendo: es el caso del patio."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        ctx = _contexto(nav, movil=True)
        pg = ctx.new_page()
        pg.goto(servidor)
        pg.wait_for_function("""async () => {
          const r = await navigator.serviceWorker.getRegistration();
          return !!(r && r.active);
        }""", timeout=15000)
        pg.wait_for_timeout(600)

        ctx.set_offline(True)
        pg.goto(servidor)
        pg.wait_for_timeout(800)

        assert pg.is_visible("#tab-despacho")
        assert pg.inner_text("h1") != ""
        pg.click("#tab-despacho")
        assert pg.eval_on_selector_all("#d-grid .slot", "n => n.length") == 10
        nav.close()


def test_desde_archivo_local_avisa_de_que_la_camara_no_puede_abrirse():
    """El operador tiene que saberlo antes de estar en el patio."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        pg.goto(APP.as_uri())
        pg.wait_for_timeout(500)

        assert pg.is_visible("#aviso-contexto")
        aviso = " ".join(pg.inner_text("#aviso-contexto").split())
        assert "desactivada" in aviso
        assert "github.io" in aviso
        # Y dice cuales son las vias que si funcionan aqui.
        assert "Galería" in aviso and "Cámara del sistema" in aviso
        # Y el boton de camara no se ofrece donde no puede funcionar.
        pg.click("#tab-despacho")
        assert pg.is_hidden("#d-camara-app")
        assert pg.is_visible("#aviso-contexto-d")
        nav.close()


def test_desde_archivo_local_la_camara_del_sistema_sigue_disponible(fotos):
    """La camara del sistema pasa por el selector, no por getUserMedia.

    Es la via que le queda a un archivo descargado, y por eso se ofrece como
    principal justo donde la camara integrada no puede abrirse.
    """
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        pg.goto(APP.as_uri())
        app = App(pg).despacho()

        boton = pg.query_selector("#d-camara-lb")
        assert boton.is_visible(), "no se ofrece la camara del sistema"
        assert "primary" in (boton.get_attribute("class") or "")
        entrada = pg.query_selector("#d-camara")
        assert entrada.get_attribute("capture") == "environment"

        # Abre el selector del sistema, que en el telefono ofrece la camara.
        with pg.expect_file_chooser(timeout=10000) as fc:
            boton.click()
        fc.value.set_files([str(fotos["frontal"])])
        pg.wait_for_function("() => document.querySelector('#d-progreso').hidden",
                             timeout=30000)
        pg.wait_for_timeout(400)

        assert app.llenas == 1, app.mensaje
        assert app.errores == []
        nav.close()


def test_desde_archivo_local_la_casilla_vacia_lleva_a_la_camara_del_telefono(fotos):
    """Tocar una casilla vacia abre el selector del sistema —camara o galeria—
    y la foto entra en esa casilla."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        pg.goto(APP.as_uri())
        app = App(pg).despacho()

        # No se estorba con la camara integrada, que aqui no puede abrirse.
        assert pg.is_hidden("#d-camara-app")

        vacias = pg.query_selector_all("#d-grid .slot:not(.lleno)")
        objetivo = vacias[4]
        rotulo = objetivo.query_selector(".cap span").inner_text()
        assert objetivo.evaluate("n => n.tagName") == "LABEL"

        with pg.expect_file_chooser(timeout=10000) as fc:
            objetivo.click()
        fc.value.set_files([str(fotos["frontal"])])
        pg.wait_for_function("() => document.querySelector('#d-progreso').hidden",
                             timeout=30000)
        pg.wait_for_timeout(400)

        assert app.rotulos() == [(rotulo, "fotos/03-frontal.jpg")]
        assert app.errores == []
        nav.close()


def test_el_ejemplo_arma_un_acta_entera_sin_camara_ni_galeria(tmp_path):
    """El demo tiene que poder recorrerse sin cargar ni una sola foto."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        ctx = _contexto(nav, movil=True, descargas=True)
        pg = ctx.new_page()
        pg.goto(APP.as_uri())
        pg.wait_for_timeout(500)

        pg.click("#btn-demo")                      # un solo toque desde el inicio
        pg.wait_for_timeout(2500)
        app = App(pg)

        assert pg.eval_on_selector(".vista.activa", "n => n.id") == "v-despacho"
        assert app.llenas == 10
        assert "Acta completa" in app.mensaje

        with pg.expect_download() as espera:
            pg.click("#d-zip")
        ruta = tmp_path / espera.value.suggested_filename
        espera.value.save_as(ruta)
        with zipfile.ZipFile(ruta) as z:
            assert z.testzip() is None
            assert len([n for n in z.namelist() if n.startswith("fotos/")]) == 10
            manifiesto = json.loads(z.read("acta.json"))

        from nefer import schema
        carpeta = tmp_path / "abierto"
        with zipfile.ZipFile(ruta) as z:
            z.extractall(carpeta)
        assert schema.validar(manifiesto, carpeta) == []
        assert app.errores == []
        nav.close()


def test_servida_muestra_los_acentos_bien(servidor):
    """Sin <meta charset> el servidor no dice la codificacion y el navegador
    adivina mal: la app entera sale con HORÃ“METRO y DAÃ‘OS."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        pg.goto(servidor)
        pg.wait_for_timeout(400)
        pg.click("#tab-despacho")

        rotulos = pg.eval_on_selector_all("#d-grid .cap span:first-child",
                                          "n => n.map(x => x.textContent)")
        assert "HORÓMETRO" in rotulos, rotulos
        assert "VISTA LATERAL IZQUIERDA" in rotulos, rotulos
        assert not any("Ã" in r for r in rotulos), rotulos
        nav.close()


def test_servida_no_muestra_el_aviso_y_ofrece_la_camara(servidor):
    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True).new_page()
        pg.goto(servidor)
        pg.wait_for_timeout(600)

        assert pg.is_hidden("#aviso-contexto")
        pg.click("#tab-despacho")
        assert pg.is_visible("#d-camara-app")
        nav.close()


# ==========================================================================
# DE LA CAMARA AL ACTA IMPRESA
# ==========================================================================

def _guardar_paquete(pg, destino: Path) -> Path:
    pg.eval_on_selector("#d-datos", "e => e.open = true")
    for campo, valor in (("#d-cliente", "MINERA EJEMPLO S.A.C."),
                         ("#d-equipo", "GE-0142"), ("#d-modelo", "C90D5 / 90 kVA"),
                         ("#d-horometro", "1548.7"),
                         ("#d-resumen", "Equipo sale operativo; sin observaciones.")):
        pg.fill(campo, valor)
    pg.wait_for_timeout(300)
    with pg.expect_download() as espera:
        pg.click("#d-zip")
    bajado = espera.value
    ruta = destino / bajado.suggested_filename
    bajado.save_as(ruta)
    return ruta


def test_de_la_camara_al_acta_valida(tmp_path, servidor):
    """El paquete que sale de la camara pasa `nefer validar` y genera el acta."""
    from nefer import build, schema

    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True, descargas=True).new_page()
        pg.goto(servidor)
        app = App(pg).despacho()

        pg.click("#d-camara-app")
        pg.wait_for_function("() => document.querySelector('#cam-video').videoWidth > 0",
                             timeout=15000)
        for _ in range(3):
            pg.click("#cam-disparar")
            pg.wait_for_timeout(1200)
        pg.click("#cam-cerrar")
        pg.wait_for_timeout(400)
        assert app.llenas == 3

        paquete = _guardar_paquete(pg, tmp_path)
        assert app.errores == []
        nav.close()

    carpeta = tmp_path / "abierto"
    with zipfile.ZipFile(paquete) as z:
        assert z.testzip() is None
        z.extractall(carpeta)

    manifiesto = json.loads((carpeta / "acta.json").read_text(encoding="utf-8"))
    assert schema.validar(manifiesto, carpeta) == []

    xlsx = carpeta / "ACTA.xlsx"
    build.construir(manifiesto, xlsx, carpeta)
    assert xlsx.exists() and xlsx.stat().st_size > 10_000

    # Las tres fotos llegan incrustadas al Excel, cada una bajo su rotulo.
    with zipfile.ZipFile(xlsx) as z:
        medios = [n for n in z.namelist() if n.startswith("xl/media/")]
    assert len(medios) == 3, medios

# ==========================================================================
# RECEPCION: las mismas rutas que despacho
# ==========================================================================

def _empezar_recepcion(pg, familia="compresor"):
    pg.click("#tab-recepcion")
    pg.wait_for_timeout(300)
    pg.select_option("#r-cat", familia)
    pg.click("#r-empezar")
    pg.wait_for_timeout(600)


def test_recepcion_ofrece_las_mismas_rutas_que_despacho(servidor):
    """Un operador no puede tener que aprenderse dos menus distintos."""
    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True).new_page()
        pg.goto(servidor)
        pg.wait_for_timeout(600)

        pg.click("#tab-despacho")
        pg.wait_for_timeout(200)
        en_despacho = {
            "camara_app": pg.is_visible("#d-camara-app"),
            "camara_sistema": pg.is_visible("#d-camara-lb"),
            "galeria": pg.is_visible("#d-file-lb"),
            "carpeta": pg.is_visible("#d-carpeta-lb"),
        }

        _empezar_recepcion(pg)
        en_recepcion = {
            "camara_app": pg.is_visible("#r-camara-app"),
            "camara_sistema": pg.is_visible("#r-camara-lb"),
            "galeria": pg.is_visible("#r-f3-lb"),
            "carpeta": pg.is_visible("#r-carpeta3-lb"),
        }

        assert en_recepcion == en_despacho, (en_recepcion, en_despacho)
        assert pg.inner_text("#r-f3-lb") == pg.inner_text("#d-file-lb")
        nav.close()


def test_en_recepcion_el_recuadro_vacio_abre_la_camara_de_esa_vista(servidor):
    """Igual que la casilla vacia del despacho: se toca y se fotografia ahi."""
    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True).new_page()
        pg.goto(servidor)
        pg.wait_for_timeout(600)
        _empezar_recepcion(pg, "torre_iluminacion")

        casilla = pg.query_selector("#r-vistas .slot")
        assert pg.evaluate("n => n.tagName", casilla) == "LABEL"
        rotulo = pg.eval_on_selector("#r-vistas .slot .cap span", "n => n.textContent")

        casilla.click()
        pg.wait_for_function(
            "() => document.querySelector('#cam-video').videoWidth > 0", timeout=15000)
        assert pg.inner_text("#cam-rotulo") == rotulo

        pg.click("#cam-disparar")
        pg.wait_for_timeout(1500)
        pg.click("#cam-cerrar")
        pg.wait_for_timeout(500)

        acta = json.loads(pg.input_value("#r-salida"))
        conFoto = [f for f in acta["registro_fotografico"] if f.get("archivo")]
        assert len(conFoto) == 1
        assert conFoto[0]["descripcion"] == rotulo
        nav.close()


def test_en_recepcion_sin_camara_el_recuadro_abre_el_selector(fotos):
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        _sin_camara(pg)
        pg.goto(APP.as_uri())
        pg.wait_for_timeout(600)
        _empezar_recepcion(pg)

        assert pg.is_hidden("#r-camara-app")
        casillas = pg.query_selector_all("#r-vistas .slot")
        casilla = casillas[2]
        rotulo = casilla.query_selector(".cap span").inner_text()

        with pg.expect_file_chooser(timeout=10000) as fc:
            casilla.click()
        fc.value.set_files([str(fotos["frontal"])])
        pg.wait_for_timeout(4000)

        acta = json.loads(pg.input_value("#r-salida"))
        conFoto = [f for f in acta["registro_fotografico"] if f.get("archivo")]
        assert len(conFoto) == 1, acta["registro_fotografico"]
        assert conFoto[0]["descripcion"] == rotulo
        nav.close()

def test_recepcion_muestra_una_casilla_por_cada_vista_del_formato(servidor):
    """La plantilla tiene tantas ventanas como vistas: la app tambien."""
    from nefer import layout

    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True).new_page()
        pg.goto(servidor)
        pg.wait_for_timeout(600)

        for familia, vistas in layout.VISTAS_POR_CATEGORIA.items():
            pg.click("#tab-recepcion")
            pg.wait_for_timeout(150)
            pg.select_option("#r-cat", familia)
            pg.click("#r-empezar")
            pg.wait_for_timeout(500)

            rotulos = pg.eval_on_selector_all(
                "#r-vistas .slot .cap span:first-child",
                "n => n.map(x => x.textContent)")
            assert rotulos == vistas, (familia, rotulos)
            # Y un campo de observacion por vista, fuera de la rejilla.
            assert pg.eval_on_selector_all("#r-obs-lista input", "n => n.length") == \
                len(vistas), familia
        nav.close()


def test_la_casilla_llena_de_recepcion_se_vacia_al_tocarla(servidor):
    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True).new_page()
        pg.goto(servidor)
        pg.wait_for_timeout(600)
        _empezar_recepcion(pg, "generico")

        pg.query_selector("#r-vistas .slot").click()
        pg.wait_for_function(
            "() => document.querySelector('#cam-video').videoWidth > 0", timeout=15000)
        pg.click("#cam-disparar")
        pg.wait_for_timeout(1300)
        pg.click("#cam-cerrar")
        pg.wait_for_timeout(500)
        assert pg.eval_on_selector_all("#r-vistas .slot.lleno", "n => n.length") == 1

        # Llena vuelve a ser un boton, y tocarlo la vacia.
        llena = pg.query_selector("#r-vistas .slot.lleno")
        assert pg.evaluate("n => n.tagName", llena) == "BUTTON"
        llena.click()
        pg.wait_for_timeout(400)
        assert pg.eval_on_selector_all("#r-vistas .slot.lleno", "n => n.length") == 0
        # Y la foto vuelve a la bandeja, no se pierde.
        assert int(pg.inner_text("#r-t-tira")) == 1
        nav.close()

def test_observaciones_tiene_la_forma_de_la_tabla_del_formato(servidor):
    """Cabecera DESPACHO|RECEPCION, dos fotos, rotulos y franja de recuperacion."""
    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        pg = _contexto(nav, movil=True, camara=True).new_page()
        pg.goto(servidor)
        pg.wait_for_timeout(600)
        _empezar_recepcion(pg)

        pg.click("#r-add-cons")
        pg.wait_for_timeout(400)
        pg.fill("#r-consumibles [data-cons-nombre]", 'CONOS DE SEGURIDAD DE 28"')
        pg.wait_for_timeout(300)
        pg.fill("#r-consumibles [data-cons-cant]", "2")
        pg.wait_for_timeout(300)

        cabecera = pg.eval_on_selector_all("#r-consumibles .obs-cab span",
                                           "n => n.map(x => x.textContent)")
        assert cabecera == ["DESPACHO", "RECEPCIÓN"], cabecera

        celdas = pg.eval_on_selector_all("#r-consumibles .obs-fotos > *",
                                         "n => n.map(x => x.tagName)")
        assert celdas == ["LABEL", "LABEL"], celdas

        # Conforme: la franja va en blanco, que una banda amarilla sin nada
        # que recuperar se lee como un dato que falta.
        franja = pg.eval_on_selector("#r-consumibles .obs-recuperacion",
                                     "n => getComputedStyle(n).backgroundColor")
        assert franja != "rgb(255, 255, 0)", franja

        pg.click("#r-consumibles .estados button[data-e='NO_RETORNA']")
        pg.wait_for_timeout(400)

        # Los rotulos son campos: se redactan solos y se pueden reescribir.
        rotulos = pg.eval_on_selector_all("#r-consumibles .obs-rotulos input",
                                          "n => n.map(x => x.value)")
        assert rotulos[0] == '02 CONOS DE SEGURIDAD DE 28" DESPACHADO', rotulos
        assert rotulos[1] == 'EL EQUIPO RETORNÓ SIN 02 CONOS DE SEGURIDAD DE 28"', rotulos

        franja = pg.eval_on_selector("#r-consumibles .obs-recuperacion",
                                     "n => getComputedStyle(n).backgroundColor")
        assert franja == "rgb(255, 255, 0)", franja
        valor = pg.input_value("#r-consumibles [data-cons-recup]")
        assert valor == 'RECUPERACIÓN N° 1 : 02 CONOS DE SEGURIDAD DE 28"', valor
        nav.close()


def test_las_dos_celdas_de_observaciones_cargan_foto(servidor, tmp_path):
    """La de despacho tambien: sin ella la tabla queda coja."""
    from nefer import schema

    with sync_playwright() as pw:
        nav = _lanzar(pw, camara=True)
        ctx = _contexto(nav, movil=True, camara=True, descargas=True)
        pg = ctx.new_page()
        pg.goto(servidor)
        pg.wait_for_timeout(600)
        _empezar_recepcion(pg)

        pg.click("#r-add-cons")
        pg.wait_for_timeout(400)
        pg.fill("#r-consumibles [data-cons-nombre]", "BARRA PUESTA A TIERRA")
        pg.wait_for_timeout(300)
        pg.click("#r-consumibles .estados button[data-e='D']")
        pg.wait_for_timeout(300)

        for selector in ("[data-destino='consAntes']", "[data-destino='cons']"):
            pg.click("#r-consumibles " + selector)
            pg.wait_for_function(
                "() => document.querySelector('#cam-video').videoWidth > 0", timeout=15000)
            pg.click("#cam-disparar")
            pg.wait_for_timeout(1300)
            pg.click("#cam-cerrar")
            pg.wait_for_timeout(600)

        assert pg.eval_on_selector_all("#r-consumibles .obs-fotos img", "n => n.length") == 2

        acta = json.loads(pg.input_value("#r-salida"))
        cons = acta["consumibles"][0]
        assert cons["foto_despacho"].startswith("fotos/despacho/"), cons
        assert cons["foto_recepcion"].startswith("fotos/"), cons

        for campo, valor in (("#r-acta", "000-000003"), ("#r-horometro", "10"),
                             ("#r-cliente", "CLIENTE DE PRUEBA S.A.C."),
                             ("#r-codigo_equipo", "C000-00"),
                             ("#r-modelo_equipo", "COMPRESOR DE PRUEBA"),
                             ("#r-resumen", "Barra de tierra dañada.")):
            pg.fill(campo, valor)
        pg.wait_for_timeout(400)
        with pg.expect_download(timeout=90000) as espera:
            pg.click("#r-zip")
        paquete = tmp_path / espera.value.suggested_filename
        espera.value.save_as(paquete)
        nav.close()

    # Las dos fotos viajan en el paquete y el acta las encuentra.
    carpeta = tmp_path / "abierto"
    with zipfile.ZipFile(paquete) as z:
        z.extractall(carpeta)
        nombres = z.namelist()
    assert any(n.startswith("fotos/despacho/") for n in nombres), nombres
    manifiesto = json.loads((carpeta / "acta.json").read_text(encoding="utf-8"))
    assert schema.validar(manifiesto, carpeta) == []


def test_la_recuperacion_escrita_a_mano_manda(servidor):
    """La redaccion automatica es un punto de partida, no la ultima palabra."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        _sin_camara(pg)
        pg.goto(servidor)
        pg.wait_for_timeout(600)
        _empezar_recepcion(pg)

        pg.click("#r-add-cons")
        pg.wait_for_timeout(400)
        pg.fill("#r-consumibles [data-cons-nombre]", "GATA DE TIRO")
        pg.wait_for_timeout(300)
        pg.click("#r-consumibles .estados button[data-e='D']")
        pg.wait_for_timeout(300)

        pg.fill("#r-consumibles [data-cons-recup]",
                "RECUPERACIÓN 1 : 01 GATA — POR EVALUAR POR PLANTA")
        pg.wait_for_timeout(400)

        acta = json.loads(pg.input_value("#r-salida"))
        assert acta["consumibles"][0]["recuperacion"] == \
            "RECUPERACIÓN 1 : 01 GATA — POR EVALUAR POR PLANTA"
        nav.close()

def _accesorio(pg, indice, nombre, estado):
    pg.click("#r-add-cons")
    pg.wait_for_timeout(350)
    pg.fill(f"#r-consumibles .par:nth-child({indice + 1}) [data-cons-nombre]", nombre)
    pg.wait_for_timeout(250)
    pg.click(f"#r-consumibles .par:nth-child({indice + 1}) "
             f".estados button[data-e='{estado}']")
    pg.wait_for_timeout(350)


def test_la_recuperacion_se_numera_progresivamente(servidor):
    """El primero que falte es la N° 1, el siguiente la N° 2.

    El numero es el ordinal dentro de su serie, no el del bloque: un accesorio
    que vuelve conforme no consume un numero de recuperacion.
    """
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        _sin_camara(pg)
        pg.goto(servidor)
        pg.wait_for_timeout(600)
        _empezar_recepcion(pg)

        for i, (nombre, estado) in enumerate([
                ("BARRA PUESTA A TIERRA", "OK"),
                ('CONOS DE SEGURIDAD DE 28"', "NO_RETORNA"),
                ("GATA DE TIRO", "OK"),
                ("CHAPA DE PUERTA", "D")]):
            _accesorio(pg, i, nombre, estado)

        franjas = pg.eval_on_selector_all("#r-consumibles [data-cons-recup]",
                                          "n => n.map(x => x.value)")
        assert franjas[0].startswith("CONFORME N° 1"), franjas
        assert franjas[1].startswith("RECUPERACIÓN N° 1"), franjas
        assert franjas[2].startswith("CONFORME N° 2"), franjas
        assert franjas[3].startswith("RECUPERACIÓN N° 2"), franjas
        nav.close()


def test_los_rotulos_de_observaciones_se_pueden_escribir(servidor):
    """Lo que falta o el daño se describe con las palabras del que firma."""
    with sync_playwright() as pw:
        nav = _lanzar(pw)
        pg = _contexto(nav, movil=True).new_page()
        _sin_camara(pg)
        pg.goto(servidor)
        pg.wait_for_timeout(600)
        _empezar_recepcion(pg)
        _accesorio(pg, 0, 'CONOS DE SEGURIDAD DE 28"', "NO_RETORNA")

        # Hay un campo por lado, no un texto fijo.
        assert pg.eval_on_selector_all("#r-consumibles [data-cons-tizq]",
                                       "n => n.length") == 1
        assert pg.eval_on_selector_all("#r-consumibles [data-cons-tder]",
                                       "n => n.length") == 1

        propio = 'EL EQUIPO RETORNÓ SIN 02 CONOS DE 28" (SE FACTURAN)'
        pg.fill("#r-consumibles [data-cons-tder]", propio)
        pg.wait_for_timeout(400)

        acta = json.loads(pg.input_value("#r-salida"))
        assert acta["consumibles"][0]["texto_recepcion"] == propio, acta["consumibles"][0]
        # Lo que no se toca no viaja: lo redacta el acta.
        assert "texto_despacho" not in acta["consumibles"][0]
        nav.close()
