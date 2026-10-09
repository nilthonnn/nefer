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


# UNA SOLA PÁGINA PARA TODO EL ARCHIVO, y por eso cada prueba tiene que
# dejarla como la encontró — o, más simple, empezar navegando de nuevo.
#
# Es `module` a propósito: levantar Chromium diecisiete veces cuesta más que
# todas las pruebas juntas. El precio es este contrato, y se paga olvidándolo:
# una prueba que mira `.aviso.peligro` sin navegar primero lee el aviso que
# dejó la anterior, y `wait_for_selector` se lo devuelve AL INSTANTE porque ya
# estaba ahí. Pasa en local y falla en CI, o al revés: es una carrera.
#
# Use `_arrancar()` o `_elegir()`, que navegan. No mire el DOM sin hacerlo.
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


def _elegir(pag, ruta):
    """Abre la pantalla limpia, elige un archivo y devuelve el aviso.

    El `goto` no es ceremonia: borra el aviso de la prueba anterior, que es lo
    único que hace que esperar el aviso nuevo signifique algo. Se comprueba
    además que no haya quedado ninguno, para que la espera no pueda volver a
    quedarse con uno viejo sin que nadie lo note.
    """
    pag.goto(APP.as_uri())
    pag.wait_for_selector("#archivo")
    assert pag.locator(".aviso.peligro").count() == 0, (
        "la pantalla no arrancó limpia: queda un aviso de otra prueba")
    with pag.expect_file_chooser() as elector:
        pag.click("#archivo")
    elector.value.set_files(str(ruta))
    return pag.wait_for_selector(".aviso.peligro").inner_text()


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
    """El circuito completo: el archivo ENTERO, tal como sale del teléfono.

    Esta prueba decía esto mismo y no lo probaba: desenvolvía el archivo a
    mano —`datos["ejecucion"]`— antes de dárselo al cargador, y así el único
    formato que el producto genera era el único que el cargador no aceptaba.
    `fixmate tpm ejecutar` sobre el archivo del operador fallaba con «la
    ejecucion necesita responsable», que además es la causa equivocada: el
    responsable estaba, un nivel más adentro. Se encontró probando con el
    historial de una máquina real.

    La oficina recibe un `.json` por WhatsApp y lo pasa por el comando. No
    abre un editor para quitarle una capa: si la prueba lo hace, no está
    probando lo que hace la oficina.
    """
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
    archivo = Path(bajada.value.path())
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    assert "ejecucion" in datos, "el teléfono dejó de envolver la ejecución"

    # Sin tocarlo: el archivo completo, por el cargador y por la ruta de disco.
    ejecucion = cargador.ejecucion_de_dict(datos)
    pauta = cargador.checklist(RAIZ / "ejemplos" / "rcm-tpm" / "pauta-ex220.json")
    e = estado(ejecucion, pauta)
    assert e.respondidos == 5 and e.nok == 1
    assert ejecucion.operador == "R. Mamani"

    copia = tmp_path / "ronda-del-telefono.json"
    copia.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    assert cargador.ejecucion(copia).operador == "R. Mamani"

    # Y una ejecución suelta —la que escribe la oficina a mano— sigue
    # entrando: el envoltorio se admite, no se exige.
    assert cargador.ejecucion_de_dict(datos["ejecucion"]).operador == "R. Mamani"


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


# ------------------------- «Abrir pauta del equipo»: lo que puede elegir
#
# Las cuatro navegan primero, con `_elegir()`. La primera versión de estas
# pruebas no lo hacía y leía el aviso que dejaba la prueba anterior: pasaban
# aquí y fallaban en CI, cada una con el mensaje de otra. Ver el contrato del
# fixture, arriba.

def test_elegir_el_excel_por_error_dice_que_hacer(pagina, tmp_path):
    """Es el error más probable: el Excel es lo que el taller tiene a mano.

    Lo que decía antes era el error del parser de JavaScript —«Unexpected
    token 'P', "PK"... is not valid JSON»—, que a un operador en un socavón
    no le dice nada y, sobre todo, no le dice qué hacer.
    """
    pag, _ = pagina
    # Un .xlsx de verdad empieza por «PK»: es un zip.
    falso = tmp_path / "historial.xlsx"
    falso.write_bytes(b"PK\x03\x04" + b"\x00" * 64)
    aviso = _elegir(pag, falso)
    assert "planilla" in aviso.lower() or "office" in aviso.lower(), aviso
    # Y dice de dónde sale la pauta, que es lo que resuelve el problema.
    assert "armar" in aviso.lower() and ".json" in aviso.lower(), aviso


def test_un_json_que_no_es_pauta_no_se_confunde_con_una_pauta_vacia(pagina, tmp_path):
    """Decirle «no trae puntos» manda a agregarle puntos a un archivo que
    nunca fue una pauta."""
    import json

    pag, _ = pagina
    otro = tmp_path / "cualquiera.json"
    otro.write_text(json.dumps({"hola": "mundo"}), encoding="utf-8")
    aviso = _elegir(pag, otro)
    assert "no es una pauta" in aviso.lower(), aviso


def test_una_pauta_sin_puntos_nombra_el_equipo_y_a_quien_le_toca(pagina, tmp_path):
    import json

    pag, _ = pagina
    vacia = tmp_path / "pauta.json"
    vacia.write_text(json.dumps(
        {"id": "p1", "activo_codigo": "MLAD041-02", "puntos": []}), encoding="utf-8")
    aviso = _elegir(pag, vacia)
    assert "MLAD041-02" in aviso, aviso
    assert "armar" in aviso.lower(), aviso


def test_la_pauta_buena_arranca_sin_avisos(pagina):
    """El control de que los avisos nuevos no se disparen de más.

    No se mira la lista de errores de consola: es del módulo entero y
    acumularía los de las dieciséis pruebas anteriores. De eso responde
    `test_sin_errores_de_consola`.
    """
    pag, _ = pagina
    pag.goto(APP.as_uri())
    pag.wait_for_selector("#archivo")
    with pag.expect_file_chooser() as elector:
        pag.click("#archivo")
    elector.value.set_files(str(RAIZ / "ejemplos" / "rcm-tpm" / "pauta-ex220.json"))
    pag.wait_for_selector("#op")
    assert pag.locator(".aviso.peligro").count() == 0


# --------------------------------------- el contrato del fixture, vigilado

# Las pruebas que no navegan antes de mirar el DOM. `test_sin_errores_de_consola`
# es la única legítima: no mira la pantalla, mira la lista de errores que el
# fixture viene acumulando desde la primera prueba.
SIN_NAVEGAR = {"test_sin_errores_de_consola"}

# Lo que deja la página en un estado conocido.
NAVEGAN = ("_arrancar", "_elegir", "goto")


def test_toda_prueba_navega_antes_de_mirar_la_pantalla():
    """El fixture es de módulo: una sola página para las diecisiete.

    Una prueba que mira el DOM sin navegar primero lee lo que dejó la
    anterior — y `wait_for_selector` se lo devuelve AL INSTANTE, porque ya
    estaba ahí. Pasó: tres pruebas nuevas leyeron cada una el mensaje de
    otra, pasaron aquí y fallaron en CI. Es una carrera, así que «me pasó a
    mí en local» no prueba nada.

    Esto lo hace mecánico en vez de recordado, que es la única forma de que
    aguante al próximo que agregue una prueba al final del archivo.
    """
    import ast

    arbol = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    culpables = []
    for nodo in arbol.body:
        if not (isinstance(nodo, ast.FunctionDef)
                and nodo.name.startswith("test_")
                and "pagina" in [a.arg for a in nodo.args.args]):
            continue
        if nodo.name in SIN_NAVEGAR:
            continue
        # Las llamadas de la función, en el orden en que están escritas.
        llamadas = sorted(
            (n for n in ast.walk(nodo) if isinstance(n, ast.Call)),
            key=lambda n: (n.lineno, n.col_offset))
        primera = None
        for llamada in llamadas:
            texto = ast.unparse(llamada.func)
            if any(x in texto for x in NAVEGAN):
                primera = "navega"
                break
            if texto.startswith("pag.") or ".locator" in texto:
                primera = texto
                break
        if primera != "navega":
            culpables.append(f"{nodo.name} (primero hace: {primera})")
    assert not culpables, (
        "estas pruebas miran la página sin navegar primero, así que leen lo "
        "que dejó la anterior:\n  " + "\n  ".join(culpables) +
        "\nUse _arrancar() o _elegir(), o añádala a SIN_NAVEGAR con su motivo.")
