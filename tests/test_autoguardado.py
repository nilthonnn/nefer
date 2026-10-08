"""El acta a medias sobrevive a que el telefono descarte la app.

Es el fallo que se reporto desde el patio: el operario va colocando fotos, se
va un rato —una llamada, el almuerzo—, y al volver no queda nada. Lo tecleado
si volvia, porque va a localStorage; las fotos no, porque solo bajaban a
IndexedDB cuando alguien tocaba «Guardar», y en mitad de una toma nadie toca
«Guardar».

Aqui se reproduce el caso entero con un navegador de verdad: se cargan las
fotos, se manda la app al fondo, se CIERRA la pestaña —que es lo que hace el
sistema al descartarla, y lo que se lleva por delante todo lo que vivia en
memoria— y se vuelve a abrir en el mismo navegador. Las fotos tienen que estar.

Se sirve por http y no como archivo suelto porque IndexedDB no existe en un
origen `file://`, que es justo donde este almacen tiene que funcionar.
"""

from __future__ import annotations

import functools
import http.server
import socketserver
import threading
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "clientes" / "rd-renta" / "docs" / "app"

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402

from navegador import HAY_CHROMIUM, opciones  # noqa: E402


@pytest.fixture(scope="module")
def servida():
    """La app servida en 127.0.0.1, que es un origen seguro y con IndexedDB."""
    manejador = functools.partial(http.server.SimpleHTTPRequestHandler,
                                  directory=str(APP))
    manejador.log_message = lambda *a, **k: None

    class Servidor(socketserver.TCPServer):
        allow_reuse_address = True

    servidor = Servidor(("127.0.0.1", 0), manejador)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}/"
    servidor.shutdown()


def _acta_de_ejemplo(pg):
    pg.click("#btn-demo")
    pg.wait_for_function("document.querySelectorAll('#d-grid .slot.lleno').length === 10",
                         timeout=30000)
    # El ejemplo se carga desde la portada; el acta se llena en su propia hoja,
    # y los datos van en un panel que arranca plegado.
    pg.evaluate("RDRENTA.ir('despacho'); document.getElementById('d-datos').open = true;")
    pg.wait_for_selector("#d-cliente", state="visible", timeout=15000)


def _apunte(pg):
    return pg.evaluate("localStorage.getItem('rdrenta.sesion')")


# Las dos esperas de esta suite. Antes eran relojes —500 ms para que arrancara
# la app, 600 para que cerrara la escritura— y un reloj es una apuesta: en una
# máquina cargada se pierde, y entonces la prueba falla por lo ocupado que
# estaba el runner y no por lo que hace el programa. Una prueba así deja de
# decir nada sobre el código.
def _lista(pg):
    """Espera a que la app esté montada. Es la precondición real de todo lo
    que sigue: las pruebas llaman a `RDRENTA.proyectos` en la línea
    siguiente."""
    pg.wait_for_function(
        "() => typeof RDRENTA !== 'undefined' && !!RDRENTA.proyectos",
        timeout=30000)


def _escritura_cerrada(pg, cuantos=1):
    """Espera a que el acta esté DE VERDAD en el almacén.

    El apunte en localStorage aparece antes que la escritura en IndexedDB, y
    `volcar()` ni siquiera escribe si hay otra escritura en vuelo: anota
    `repetir` y vuelve más tarde por su cuenta. Un reloj fijo apuesta a que
    esa segunda vuelta entre a tiempo; esto espera a que las actas estén.

    Medido en esta máquina con los cuatro núcleos saturados: la app arranca
    en 60 ms y la escritura cierra 9 ms después del apunte. Los relojes que
    había —500 y 600 ms— tenían margen de sobra, así que no eran ellos; el
    que apostaba de verdad era el de 800 ms tras el segundo `volcar()`, que
    es el único que esperaba una escritura diferida."""
    pg.wait_for_function(
        "async (n) => (await RDRENTA.proyectos.listar()).length >= n",
        arg=cuantos, timeout=30000)


def test_el_acta_se_guarda_sola_sin_que_nadie_toque_guardar(servida):
    """Nadie pulsa «Guardar» en ningun momento de esta prueba."""
    if not HAY_CHROMIUM:
        pytest.skip("no hay Chromium disponible")

    fallos: list[str] = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fallos.append(str(e)))
        pg.goto(servida)
        _lista(pg)

        assert _apunte(pg) is None, "había una sesión apuntada antes de trabajar"
        _acta_de_ejemplo(pg)

        # Sin tocar nada más: el autoguardado tiene que dispararse solo.
        pg.wait_for_function("localStorage.getItem('rdrenta.sesion') !== null",
                             timeout=15000)
        guardados = pg.evaluate("RDRENTA.proyectos.listar().then(l => l.length)")
        nav.close()

    assert fallos == [], fallos
    assert guardados == 1, f"proyectos en el almacén: {guardados}"


def test_el_acta_a_medias_vuelve_despues_de_que_el_sistema_descarte_la_app(servida):
    """El caso del patio, entero.

    Cerrar la pestaña es lo que de verdad prueba algo: se lleva por delante las
    variables, los `blob:` y el estado del navegador. Lo unico que queda es lo
    que llego al disco.
    """
    if not HAY_CHROMIUM:
        pytest.skip("no hay Chromium disponible")

    fallos: list[str] = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        # El mismo contexto de las dos veces: cambiar de contexto borraria
        # IndexedDB y la prueba pasaria o fallaria por el motivo equivocado.
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True)

        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fallos.append(str(e)))
        pg.goto(servida)
        _lista(pg)
        _acta_de_ejemplo(pg)
        pg.fill("#d-cliente", "MINERA DEL SUR S.A.C.")

        # El operario se va: el sistema esconde la app antes de descartarla.
        pg.evaluate("""() => {
          Object.defineProperty(document, 'visibilityState',
                                { value: 'hidden', configurable: true });
          document.dispatchEvent(new Event('visibilitychange'));
        }""")
        pg.wait_for_function("localStorage.getItem('rdrenta.sesion') !== null",
                             timeout=15000)
        _escritura_cerrada(pg)             # ...de verdad, no por reloj
        pg.close()                         # ...y Android se lleva la app

        # Vuelve al rato y la abre otra vez.
        otra = ctx.new_page()
        otra.on("pageerror", lambda e: fallos.append(str(e)))
        otra.goto(servida)
        otra.wait_for_function(
            "document.querySelectorAll('#d-grid .slot.lleno').length === 10",
            timeout=30000)

        cliente = otra.input_value("#d-cliente")
        bandera = otra.is_visible("#proy-recuperado")
        texto = otra.inner_text("#proy-recuperado")
        nav.close()

    assert fallos == [], fallos
    assert cliente == "MINERA DEL SUR S.A.C."
    assert bandera, "el operario no se entera de que se recuperó el acta"
    assert "recuperó el acta" in texto


def test_abrir_la_app_y_no_hacer_nada_no_deja_un_proyecto_vacio(servida):
    """La fecha viene puesta de fábrica y no cuenta como trabajo.

    Sin esto, la lista de proyectos se llenaría de actas en blanco a razón de
    una por cada vez que alguien abre la app sin querer.
    """
    if not HAY_CHROMIUM:
        pytest.skip("no hay Chromium disponible")

    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True)
        pg = ctx.new_page()
        pg.goto(servida)
        _lista(pg)

        # Se fuerza el volcado en vez de esperar: si hubiera algo que guardar,
        # aquí saldría.
        # `volcar()` devuelve una promesa que se resuelve con la escritura
        # hecha, y `evaluate` la espera: no hay nada que cronometrar.
        pg.evaluate("RDRENTA.proyectos.volcar()")
        apunte = _apunte(pg)
        guardados = pg.evaluate("RDRENTA.proyectos.listar().then(l => l.length)")
        nav.close()

    assert apunte is None, "se apuntó una sesión sin que nadie trabajara"
    assert guardados == 0, f"se guardó un acta en blanco: {guardados}"


def test_empezar_una_nueva_no_arrastra_el_acta_recuperada(servida):
    """La salida del aviso tiene que dejar la pantalla limpia de verdad.

    Y el acta recuperada sigue en la lista: se descarta de la pantalla, no del
    almacén.
    """
    if not HAY_CHROMIUM:
        pytest.skip("no hay Chromium disponible")

    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True)
        pg = ctx.new_page()
        pg.goto(servida)
        _lista(pg)
        _acta_de_ejemplo(pg)
        pg.wait_for_function("localStorage.getItem('rdrenta.sesion') !== null",
                             timeout=15000)
        _escritura_cerrada(pg)
        pg.close()

        otra = ctx.new_page()
        otra.goto(servida)
        otra.wait_for_selector("#proy-recuperado", timeout=30000)
        otra.on("dialog", lambda d: d.accept())
        otra.click("#proy-recuperado button")  # «Empezar una nueva», el primero
        otra.wait_for_function(
            "document.querySelectorAll('#d-grid .slot.lleno').length === 0",
            timeout=15000)

        guardados = otra.evaluate("RDRENTA.proyectos.listar().then(l => l.length)")
        nav.close()

    assert guardados == 1, "el acta recuperada debía seguir guardada en la lista"


def test_pasarse_a_la_otra_hoja_no_escribe_encima_del_acta_anterior(servida):
    """Despacho y recepción son dos actas, no dos pestañas de la misma.

    El autoguardado escribe sobre «el proyecto abierto», y el proyecto abierto
    puede ser el de la otra hoja: sin cuidado, teclear en recepción machacaba
    el despacho que se acababa de guardar, fotos incluidas.
    """
    if not HAY_CHROMIUM:
        pytest.skip("no hay Chromium disponible")

    fallos: list[str] = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        ctx = nav.new_context(viewport={"width": 390, "height": 844},
                              has_touch=True, is_mobile=True)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: fallos.append(str(e)))
        pg.goto(servida)
        _lista(pg)

        _acta_de_ejemplo(pg)
        pg.wait_for_function("localStorage.getItem('rdrenta.sesion') !== null",
                             timeout=15000)
        _escritura_cerrada(pg)

        # Se pasa a recepción y teclea. Se manda el evento en vez de escribir a
        # mano porque el campo vive en un panel plegado; el que escucha es el
        # mismo.
        pg.evaluate("""() => {
          RDRENTA.ir('recepcion');
          const n = document.getElementById('r-cliente');
          n.value = 'OTRO CLIENTE S.A.';
          n.dispatchEvent(new Event('input', { bubbles: true }));
        }""")
        pg.evaluate("RDRENTA.proyectos.volcar()")
        _escritura_cerrada(pg, 2)          # el despacho y la recepción

        guardados = pg.evaluate("""RDRENTA.proyectos.listar().then(
          l => l.map(p => ({ vista: p.vista, fotos: (p.datos.fotos || []).length })))""")
        nav.close()

    assert fallos == [], fallos
    porVista = {p["vista"]: p["fotos"] for p in guardados}
    assert len(guardados) == 2, f"se esperaban dos actas, hay {guardados}"
    assert porVista.get("despacho") == 10, "el despacho perdió sus fotos"
    assert porVista.get("recepcion") == 0
