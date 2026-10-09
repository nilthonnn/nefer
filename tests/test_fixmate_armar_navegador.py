"""La pantalla de «Armar» en un navegador de verdad, y lo que sale de ella.

Esta pantalla es la que faltaba: hasta que existió, las dos pantallas de
campo abrían un `.json` que solo podía producir alguien que conociera el
esquema y lo escribiera a mano. Un usuario real solo podía ver el ejemplo.

Lo que se prueba aquí no es cosmético. Son las cuatro cosas que, si fallan,
la vuelven inservible otra vez:

1. **Escribir no pierde el cursor.** Un formulario que se vuelve a pintar en
   cada tecla deja el criterio de aceptación en tres palabras, porque nadie
   escribe dos líneas peleando con el cursor.
2. **Lo último de la hoja se puede tocar.** El panel va fijo abajo, y la caja
   de pegar desde el Excel le quedaba debajo: existía y no se podía abrir.
3. **Lo que sale de aquí, entra allá.** La pauta se abre en la Ronda CIL y el
   análisis en la mesa de trabajo, en el navegador, de verdad. Es lo único
   que prueba que las tres pantallas son un producto y no tres demos.
4. **Abrir para corregir una coma no borra la reunión.** El análisis de
   ejemplo trae la criticidad y la `decision` de cada modo —las respuestas
   del equipo al árbol de JA1011—. Reescribirlo sin ellas sería una pérdida
   silenciosa: el archivo nuevo se vería perfecto.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from navegador import HAY_CHROMIUM, opciones  # noqa: E402

ARMAR = RAIZ / "docs" / "fixmate" / "armar" / "index.html"
RONDA = RAIZ / "docs" / "fixmate" / "ronda" / "index.html"
MESA = RAIZ / "docs" / "fixmate" / "rcm" / "index.html"
EJEMPLOS = RAIZ / "ejemplos" / "rcm-tpm"

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")


@pytest.fixture(scope="module")
def navegador():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        nav = pw.chromium.launch(**opciones())
        yield nav
        nav.close()


@pytest.fixture
def pagina(navegador):
    ctx = navegador.new_context(viewport={"width": 1280, "height": 900},
                               accept_downloads=True)
    pag = ctx.new_page()
    errores = []
    pag.on("pageerror", lambda e: errores.append(str(e)))
    pag.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
    pag.goto(ARMAR.as_uri())
    yield pag, errores
    ctx.close()


def _llenar_pauta(pag):
    """Lo mínimo que hace una pauta válida, con el formulario ya abierto."""
    pag.fill('[data-ruta="activo_codigo"]', "EX-220-03")
    pag.fill('[data-ruta="nombre"]', "Ronda de arranque de turno")
    pag.fill('[data-ruta="puntos.0.punto"]', "visor de nivel del reductor de giro")
    pag.fill('[data-ruta="puntos.0.criterio"]',
             "el nivel queda entre las dos marcas del visor")


def _pauta_minima(pag):
    pag.click("#n-pauta")
    _llenar_pauta(pag)


def _analisis_minimo(pag):
    pag.click("#n-analisis")
    pag.fill('[data-ruta="activo.codigo"]', "EX-220-03")
    pag.fill('[data-ruta="activo.nombre"]', "Excavadora hidráulica")
    pag.fill('[data-ruta="funciones.0.descripcion"]', "Girar la superestructura 360°")
    pag.fill('[data-ruta="funciones.0.estandar"]', "a 9 rpm con carga de 2,1 m³")
    pag.click('details[data-llave="funciones.0.fallas.0"] > summary')
    pag.fill('[data-ruta="funciones.0.fallas.0.descripcion"]', "No gira")
    pag.click('details[data-llave="funciones.0.fallas.0.modos.0"] > summary')
    pag.fill('[data-ruta="funciones.0.fallas.0.modos.0.descripcion"]',
             "Corona de giro con desgaste en los dientes")


def _bajar(pag) -> dict:
    with pag.expect_download() as bajada:
        pag.click("#bajar")
    return json.loads(Path(bajada.value.path()).read_text(encoding="utf-8"))


def _abrir_en(pag, ruta_pantalla: Path, archivo: Path, boton: str = "#archivo"):
    pag.goto(ruta_pantalla.as_uri())
    with pag.expect_file_chooser() as elector:
        pag.click(boton)
    elector.value.set_files(str(archivo))


def _guardar(tmp_path: Path, nombre: str, datos: dict) -> Path:
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


# ------------------------------------------------------------ cómo se escribe

def test_escribir_no_pierde_el_cursor(pagina):
    """Tecla por tecla, en el campo más largo que hay que escribir."""
    pag, errores = pagina
    pag.click("#n-pauta")
    campo = '[data-ruta="puntos.0.criterio"]'
    pag.click(campo)
    texto = "el nivel queda entre las dos marcas del visor, con la máquina en plano"
    pag.keyboard.type(texto, delay=1)
    assert pag.input_value(campo) == texto
    # Y el cursor sigue ahí: si la hoja se hubiera vuelto a armar, el campo
    # con el foco sería otro —o ninguno— y el texto estaría cortado.
    enfocado = pag.evaluate(
        "document.activeElement && document.activeElement.getAttribute('data-ruta')")
    assert enfocado == "puntos.0.criterio"
    assert not errores, errores


def test_el_panel_no_tapa_lo_ultimo_de_la_hoja(pagina):
    """El panel va fijo abajo. Lo último de la hoja le quedaba debajo."""
    pag, errores = pagina
    _pauta_minima(pag)
    # La caja de pegar es lo último que hay, y es la que no se podía abrir.
    pag.click('details[data-llave="pegar"] > summary', timeout=5000)
    assert pag.is_visible("#pegado")
    # Medido, no supuesto: con la página al final del todo, lo último que hay
    # escrito queda por encima del borde de arriba del panel.
    pag.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    hoja, panel_arriba = pag.evaluate(
        "[document.getElementById('pegado').getBoundingClientRect().bottom,"
        " document.getElementById('panel').getBoundingClientRect().top]")
    assert hoja <= panel_arriba, \
        f"lo último termina en {hoja} y el panel empieza en {panel_arriba}"
    assert not errores, errores


def test_pegar_desde_el_excel(pagina):
    """Las filas buenas entran; las malas vuelven con su número de línea."""
    pag, errores = pagina
    _pauta_minima(pag)
    pag.click('details[data-llave="pegar"] > summary')
    pag.fill("#pegado",
             "limpiar\tradiador, cara de entrada\tsin tierra entre aletas\t40\n"
             "lubricar\tengrasador del pin de pluma\tsale grasa limpia\t25\n"
             "vigilar\tcualquier cosa\tque esté bien\t10\n"
             "inspeccionar\t\tfalta el punto\t15")
    pag.click('[data-accion="pegar"]')

    nota = pag.inner_text(".aviso.nota")
    assert "2 punto(s) agregados" in nota, nota
    # Lo que no entró se dice, con la línea: un importador que se come filas
    # calladas es peor que no tener importador.
    assert "linea 3" in nota and "linea 4" in nota, nota
    assert pag.locator('details[data-llave^="puntos."]').count() == 3
    assert not errores, errores


def test_lo_que_falta_se_marca_y_el_boton_queda_trabado(pagina):
    pag, errores = pagina
    pag.click("#n-pauta")
    assert not pag.is_enabled("#bajar")
    # El campo que falta se marca donde está, no sólo en la lista de abajo.
    assert pag.locator('.campo.falta [data-ruta="activo_codigo"]').count() == 1
    _llenar_pauta(pag)
    assert pag.is_enabled("#bajar")
    assert pag.locator('.campo.falta [data-ruta="activo_codigo"]').count() == 0
    assert not errores, errores


def test_el_catalogo_rellena_sin_pisar(pagina):
    """Espejo de `ModoFalla.desde_catalogo()`: rellena huecos, no corrige."""
    pag, errores = pagina
    _analisis_minimo(pag)
    base = '[data-ruta="funciones.0.fallas.0.modos.0'
    pag.fill(base + '.mecanismo"]', "Abrasión por polvo de sílice")
    pag.select_option(base + '.codigo_catalogo"]', "ADM.RESTRICCION.FILTRO")
    assert pag.input_value(base + '.causa"]') == "Filtro de aire colmatado"
    # Lo que el analista ya escribió gana.
    assert pag.input_value(base + '.mecanismo"]') == "Abrasión por polvo de sílice"
    assert not errores, errores


def test_el_modo_oculto_se_ve_y_sale_como_booleano(pagina):
    pag, errores = pagina
    _analisis_minimo(pag)
    pag.select_option('[data-ruta="funciones.0.fallas.0.modos.0.evidente"]', "no")
    chips = pag.inner_text('details[data-llave="funciones.0.fallas.0.modos.0"] > summary')
    assert "oculta" in chips.lower(), chips
    datos = _bajar(pag)
    assert datos["funciones"][0]["fallas"][0]["modos"][0]["evidente"] is False
    assert not errores, errores


# ------------------------------------- lo que sale de aquí, entra allá

def test_la_pauta_que_sale_la_abre_la_ronda(pagina, tmp_path):
    """La prueba de que las pantallas son un producto y no tres demos."""
    pag, errores = pagina
    _pauta_minima(pag)
    pag.click('details[data-llave="pegar"] > summary')
    pag.fill("#pegado", "limpiar\tradiador\tsin tierra entre aletas\t40")
    pag.click('[data-accion="pegar"]')
    datos = _bajar(pag)

    # Primero la oficina: es la misma que va a recibir la ronda de vuelta.
    from nefer.fixmate import cargador
    pauta = cargador.checklist_de_dict(datos)
    assert len(pauta.puntos) == 2
    assert pauta.presupuesto_seg == 70

    # Y ahora el teléfono del operador, de verdad.
    archivo = _guardar(tmp_path, "pauta.json", datos)
    _abrir_en(pag, RONDA, archivo)
    pag.wait_for_selector("#op")
    pag.fill("#op", "operador de prueba")
    pag.click("#ir")
    pag.wait_for_selector(".punto")
    assert "visor de nivel" in pag.inner_text(".punto").lower()
    assert "entre las dos marcas" in pag.inner_text(".criterio").lower()
    assert not errores, errores


def test_el_analisis_que_sale_lo_abre_la_mesa(pagina, tmp_path):
    pag, errores = pagina
    _analisis_minimo(pag)
    pag.fill('[data-ruta="funciones.0.fallas.0.modos.0.efecto.local"]',
             "la superestructura se traba")
    datos = _bajar(pag)

    from nefer.fixmate import cargador
    a = cargador.analisis_de_dict(datos)
    assert [m.id for m in a.modos] == ["F1.1.1"]

    archivo = _guardar(tmp_path, "analisis.json", datos)
    _abrir_en(pag, MESA, archivo)
    pag.wait_for_selector(".arbol, #arbol, .modo", timeout=10000)
    cuerpo = pag.inner_text("body").lower()
    assert "corona de giro" in cuerpo, cuerpo[:600]
    assert "ex-220-03" in cuerpo
    assert not errores, errores


# ------------------------------------- abrir lo que ya existe, sin perder nada

def test_abrir_el_analisis_de_ejemplo_no_borra_la_reunion(pagina, tmp_path):
    """Corregir una coma no puede costar las respuestas del árbol."""
    pag, errores = pagina
    original = json.loads((EJEMPLOS / "analisis-ex220.json").read_text(encoding="utf-8"))

    with pag.expect_file_chooser() as elector:
        pag.click("#abrir")
    elector.value.set_files(str(EJEMPLOS / "analisis-ex220.json"))
    pag.wait_for_selector('[data-ruta="activo.codigo"]')
    assert pag.input_value('[data-ruta="activo.codigo"]') == original["activo"]["codigo"]

    vuelto = _bajar(pag)

    from nefer.fixmate import cargador
    antes = cargador.analisis_de_dict(original)
    despues = cargador.analisis_de_dict(vuelto)
    assert len(despues.funciones) == len(antes.funciones)
    assert len(despues.fallas) == len(antes.fallas)
    assert len(despues.modos) == len(antes.modos)
    assert [m.descripcion for m in despues.modos] == [m.descripcion for m in antes.modos]
    assert [m.evidente for m in despues.modos] == [m.evidente for m in antes.modos]
    assert [m.clases for m in despues.modos] == [m.clases for m in antes.modos]

    # Lo que esta pantalla NO edita y por eso podría haber borrado:
    assert vuelto["metodo_criticidad"] == original["metodo_criticidad"]
    assert [m.criticidad.valores for m in despues.modos] == \
           [m.criticidad.valores for m in antes.modos]
    decisiones_antes = cargador.decisiones_de_dict(original, antes)
    decisiones_despues = cargador.decisiones_de_dict(vuelto, despues)
    assert decisiones_antes, "el ejemplo tiene que traer decisiones, o esto no mide nada"
    assert set(decisiones_despues) == set(decisiones_antes)
    assert not errores, errores


def test_abrir_la_pauta_de_ejemplo_y_devolverla_igual(pagina, tmp_path):
    pag, errores = pagina
    with pag.expect_file_chooser() as elector:
        pag.click("#abrir")
    elector.value.set_files(str(EJEMPLOS / "pauta-ex220.json"))
    pag.wait_for_selector('[data-ruta="activo_codigo"]')

    vuelto = _bajar(pag)

    from nefer.fixmate import cargador
    antes = cargador.checklist(EJEMPLOS / "pauta-ex220.json")
    despues = cargador.checklist_de_dict(vuelto)
    assert despues.id == antes.id
    assert despues.frecuencia == antes.frecuencia
    assert despues.presupuesto_seg == antes.presupuesto_seg
    assert [(p.id, p.clase, p.punto, p.criterio, p.segundos, p.alcance_operador,
             p.codigo_catalogo, p.modo_falla_id) for p in despues.puntos] == \
           [(p.id, p.clase, p.punto, p.criterio, p.segundos, p.alcance_operador,
             p.codigo_catalogo, p.modo_falla_id) for p in antes.puntos]
    assert not errores, errores
