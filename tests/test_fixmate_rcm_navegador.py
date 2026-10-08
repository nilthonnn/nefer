"""La pantalla de análisis RCM en un navegador de verdad, en una mesa.

Esto no es trabajo de campo: es cuatro personas, un proyector y un modo de
falla en discusión. Lo que se prueba aquí son las decisiones de diseño que
salen de esa mesa, y una propiedad que no es cosmética:

1. **«Sin evaluar» es un botón del mismo tamaño que «Sí» y «No».** Si la
   única forma de dejar una pregunta sin contestar fuera no tocarla, no se
   podría distinguir «decidimos que no» de «no lo miramos», y esa diferencia
   es la que dice cuánto trabajo falta.
2. **El camino se ve mientras se contesta.** El valor de RCM no es la
   estrategia que sale: es poder discutir por qué salió ésa.
3. **La guarda se ve en pantalla.** Con consecuencia de seguridad y sin
   tarea proactiva, la pantalla dice rediseño obligatorio y no ofrece
   «operar hasta la falla» por ninguna vía.
4. **Lo que se exporta vuelve a entrar.** El archivo que baja esta pantalla
   lo tiene que leer `cargador.analisis()` y dar las mismas decisiones.
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

APP = RAIZ / "docs" / "fixmate" / "rcm" / "index.html"

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")

# El modo de falla de la manguera de freno: consecuencia de seguridad, nada
# detectable y sin intervalo de edad. Es el que tiene que terminar en
# rediseño obligatorio.
FRENO = "F2.1.1"
# La válvula de alivio pegada: falla oculta.
OCULTA = "F1.1.3"


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
    pag.goto(APP.as_uri())
    yield pag, errores
    ctx.close()


def _abrir(pag):
    pag.click("#demo")


def _responder(pag, campo, valor):
    pag.click(f'button[data-campo="{campo}"][data-valor="{valor}"]')


def test_el_analisis_de_ejemplo_va_detras_de_un_boton_que_dice_que_es_inventado(pagina):
    # Un análisis RCM que se ve completo sobre una máquina que no existe es
    # exactamente la clase de documento que alguien firma.
    pag, _ = pagina
    texto = pag.inner_text("#demo")
    assert "inventado" in texto.lower()
    assert "EX-220" in texto


def test_la_pantalla_dice_desde_el_inicio_lo_que_no_hace(pagina):
    pag, _ = pagina
    texto = pag.inner_text("#app")
    assert "No evalúa criticidad" in texto
    assert "No arma la matriz FMECA" in texto
    assert "No inventa respuestas" in texto


def test_al_abrir_el_ejemplo_las_siete_preguntas_quedan_contestadas(pagina):
    pag, errores = pagina
    _abrir(pag)
    texto = pag.inner_text("#app")
    assert "Las siete están contestadas" in texto
    # Las cuatro que sostienen la cadena están marcadas como tales. Los chips
    # salen en mayúsculas por CSS, y `inner_text` devuelve lo que se ve.
    assert texto.lower().count("sostiene la cadena") == 4
    assert not errores, errores


def test_el_contexto_operacional_se_ve_antes_que_nada(pagina):
    pag, _ = pagina
    _abrir(pag)
    texto = pag.inner_text("#app")
    assert "4.200 m" in texto
    assert "otro análisis" in texto  # el aviso de no copiar entre contextos


def test_la_falla_oculta_se_explica_como_falla_multiple(pagina):
    pag, _ = pagina
    _abrir(pag)
    pag.click(f'button[data-modo="{OCULTA}"]')
    ficha = pag.inner_text("#ficha").lower()
    assert "falla oculta" in ficha
    assert "falla múltiple" in ficha
    # Y la pregunta de la rama evidente queda marcada como no aplicable.
    assert "no aplica a este modo" in ficha


def test_lo_que_el_catalogo_hereda_no_se_ve_como_un_hueco(pagina):
    """Causa en blanco no significa lo mismo con código que sin él.

    Si el modo declara un código de catálogo, la oficina hereda causa y
    mecanismo de ahí. Decir «sin declarar» en pantalla haría ver como un
    hueco algo que el archivo sí tiene, y mandaría a alguien a rellenarlo.
    """
    pag, _ = pagina
    _abrir(pag)
    # F1.1.1 trae código de catálogo y no escribe causa; F2.1.1 no trae
    # código y escribe la suya.
    pag.click('button[data-modo="F1.1.1"]')
    con_codigo = pag.inner_text("#ficha")
    assert "TER.SOBRECALENTAMIENTO.RADIADOR" in con_codigo
    assert "lo hereda del catálogo de fallas" in con_codigo

    pag.click(f'button[data-modo="{FRENO}"]')
    sin_codigo = pag.inner_text("#ficha")
    assert "sin codificar" in sin_codigo
    assert "lo hereda del catálogo" not in sin_codigo
    assert "abrazadera suelta" in sin_codigo  # la causa que sí está escrita


def test_una_decision_incompleta_dice_por_que_lo_esta(pagina):
    pag, _ = pagina
    _abrir(pag)
    pag.click(f'button[data-modo="{FRENO}"]')
    dictamen = pag.inner_text(".dictamen").lower()
    assert "decisión incompleta" in dictamen
    assert "incluso una que este modo no use" in dictamen


def test_sin_evaluar_es_un_boton_del_mismo_tamano_que_si_y_no(pagina):
    pag, _ = pagina
    _abrir(pag)
    cajas = [pag.query_selector(
        f'button[data-campo="detectable"][data-valor="{v}"]').bounding_box()
        for v in ("si", "no", "nd")]
    anchos = [c["width"] for c in cajas]
    altos = [c["height"] for c in cajas]
    assert max(anchos) - min(anchos) < 1, anchos
    assert max(altos) - min(altos) < 1, altos
    # Y los tres están a la misma altura: ninguno más abajo que otro.
    assert len({round(c["y"]) for c in cajas}) == 1


def test_la_guarda_de_seguridad_se_ve_en_pantalla(pagina):
    """Sin tarea proactiva y con consecuencia de seguridad: rediseño."""
    pag, _ = pagina
    _abrir(pag)
    pag.click(f'button[data-modo="{FRENO}"]')
    for campo, valor in (("detectable", "no"), ("intervalo_edad", "no"),
                         ("restaurable", "no"), ("viable", "si"),
                         ("costo_efectiva", "no")):
        _responder(pag, campo, valor)
    dictamen = pag.inner_text(".dictamen").lower()
    assert "rediseño obligatorio" in dictamen
    assert "no es una salida legal" in dictamen
    # La estrategia elegida es el titular, y es rediseño. El rótulo viene de
    # Python, en español sin tildes como el resto del código.
    titulo = pag.inner_text(".dictamen > div:first-child").strip().lower()
    assert titulo == "rediseño o cambio de ingenieria"
    # Y el último paso del camino es la guarda cerrándose, no una elección.
    ultimo = pag.inner_text(".camino li:last-child").lower()
    assert "¿operar hasta la falla?" in ultimo
    assert "la guarda lo impide" in ultimo


def test_el_camino_se_reescribe_con_cada_respuesta(pagina):
    pag, _ = pagina
    _abrir(pag)
    pag.click(f'button[data-modo="{FRENO}"]')
    _responder(pag, "detectable", "si")
    _responder(pag, "viable", "si")
    assert "Mantenimiento segun condicion" in pag.inner_text(".dictamen")
    pasos_cbm = pag.eval_on_selector_all(".camino li", "n => n.length")

    _responder(pag, "detectable", "no")
    dictamen = pag.inner_text(".dictamen")
    assert "Mantenimiento segun condicion" not in dictamen
    pasos = pag.eval_on_selector_all(".camino li", "n => n.length")
    assert pasos > pasos_cbm, "el camino tiene que crecer al descartar CBM"
    # Y la pregunta que el árbol usó queda marcada como usada.
    assert "la usó el árbol" in pag.inner_text("#app").lower()


def test_el_89_por_ciento_aparece_cuando_no_hay_intervalo_de_edad(pagina):
    pag, _ = pagina
    _abrir(pag)
    pag.click(f'button[data-modo="{FRENO}"]')
    _responder(pag, "detectable", "no")
    _responder(pag, "intervalo_edad", "no")
    texto = pag.inner_text("#app")
    assert "Nowlan y Heap" in texto
    assert "89 %" in texto


def test_sin_datos_economicos_no_se_declara_ahorro(pagina):
    pag, _ = pagina
    _abrir(pag)
    # El radiador: detectable y viable, consecuencia de producción. Sin dato
    # económico, la tarea se conserva y el aviso lo dice.
    pag.click('button[data-modo="F1.1.1"]')
    _responder(pag, "costo_efectiva", "nd")
    dictamen = pag.inner_text(".dictamen")
    assert "Mantenimiento segun condicion" in dictamen
    assert "Informacion economica insuficiente" in dictamen
    assert "no se declara ahorro" in dictamen


def test_quitar_la_decision_devuelve_la_Q6_a_pendiente(pagina):
    pag, _ = pagina
    _abrir(pag)
    assert "Las siete están contestadas" in pag.inner_text("#app")
    pag.click(f'button[data-modo="{FRENO}"]')
    pag.click("#quitar")
    texto = pag.inner_text("#app")
    assert "Las siete están contestadas" not in texto
    # Baja a 5/7: la Q6 queda abierta, y con ella la Q7, que depende de que
    # todos los modos estén decididos.
    assert "5 de 7 contestadas" in texto
    assert f"el modo {FRENO} no tiene decision de estrategia" in texto
    # Y el modo queda «sin decidir» en el árbol, no con la decisión anterior.
    assert "sin decidir" in pag.inner_text(".arbol").lower()


def test_el_tablero_cuenta_los_redisenos_obligatorios(pagina):
    pag, _ = pagina
    _abrir(pag)
    # Las etiquetas del tablero van en versalitas por CSS, y `inner_text`
    # devuelve lo que se ve.
    texto = pag.inner_text("#app").lower()
    assert "rediseños obligatorios" in texto
    assert "no es una salida legal" in texto


def test_lo_que_baja_la_pantalla_vuelve_a_entrar_por_el_cargador(pagina, tmp_path):
    """El archivo exportado es el mismo formato que lee la oficina.

    Si la pantalla exportara una forma propia, el análisis haría un viaje de
    ida sin vuelta: se decidiría en pantalla y se volvería a decidir a mano
    en el comando, que es justo lo que este proyecto no quiere.
    """
    from nefer.fixmate import cargador

    pag, _ = pagina
    _abrir(pag)
    pag.click(f'button[data-modo="{FRENO}"]')
    for campo, valor in (("detectable", "no"), ("intervalo_edad", "no"),
                         ("restaurable", "no"), ("viable", "si"),
                         ("costo_efectiva", "no")):
        _responder(pag, campo, valor)

    with pag.expect_download() as esperando:
        pag.click("#bajar")
    destino = tmp_path / "exportado.json"
    esperando.value.save_as(destino)

    datos = json.loads(destino.read_text(encoding="utf-8"))
    analisis = cargador.analisis_de_dict(datos)
    decisiones = cargador.decisiones_de_dict(datos, analisis)
    assert len(decisiones) == len(analisis.modos)
    dictamen = decisiones.get(FRENO)
    assert dictamen is not None
    assert dictamen.estrategia == "rediseno"
    assert dictamen.bloqueado_por_seguridad is True


def test_un_archivo_que_no_es_un_analisis_lo_dice_sin_romperse(pagina, tmp_path):
    pag, errores = pagina
    malo = tmp_path / "no-es-analisis.json"
    malo.write_text(json.dumps({"activo": {"codigo": "X-1", "nombre": "x"},
                                "funciones": [{"descripcion": "hacer algo"}]}),
                    encoding="utf-8")
    pag.set_input_files("input[type=file]", str(malo))
    # Leer el archivo es asíncrono: se espera el aviso, no un reloj.
    pag.wait_for_selector(".aviso.peligro")
    texto = pag.inner_text("#app")
    assert "estándar de desempeño" in texto
    assert "no se puede fallar de forma verificable" in texto
    assert not errores, errores


# ═══════════ la ronda del operador, encima del análisis ═══════════

RONDA = RAIZ / "ejemplos" / "rcm-tpm" / "ronda-ex220-telefono.json"


def _abrir_ronda(pag, ruta):
    pag.click("#abrir-ronda")
    pag.set_input_files("#entrada-ronda", str(ruta))
    pag.wait_for_selector("#quitar-ronda, .aviso.peligro")


def test_la_ronda_del_operador_cae_sobre_su_modo_de_falla(pagina):
    """El circuito que justifica todo lo demás.

    El operador ve algo en el turno; la oficina abre el análisis y ve **en
    qué modo de falla** cayó eso que vio. Sin esto, la ronda es una lista de
    hallazgos y el análisis es un documento, y nadie los cruza nunca.
    """
    pag, errores = pagina
    _abrir(pag)
    _abrir_ronda(pag, RONDA)
    texto = pag.inner_text("#app").lower()
    assert "evidencia de campo" in texto
    assert "(operador del turno a)" in texto
    assert "todos los hallazgos" in texto     # ninguno quedó suelto
    # El modo queda marcado en el árbol, y el hallazgo se ve en su ficha.
    assert "1 en campo" in pag.inner_text(".arbol").lower()
    pag.click('button[data-modo="F1.1.1"]')
    ficha = pag.inner_text("#ficha").lower()
    assert "visto en campo" in ficha
    assert "panal esta tapado con tierra" in ficha
    assert "la pauta declara el modo" in ficha
    assert not errores, errores


def test_la_ronda_incompleta_se_dice_antes_de_usarla_como_evidencia(pagina):
    pag, _ = pagina
    _abrir(pag)
    _abrir_ronda(pag, RONDA)
    texto = pag.inner_text("#app")
    assert "incompleta" in texto
    assert "no dice nada del modo de falla" in texto


def test_un_hallazgo_sin_codigo_no_se_engancha_al_mas_parecido(pagina, tmp_path):
    pag, _ = pagina
    _abrir(pag)
    suelto = tmp_path / "ronda-suelta.json"
    suelto.write_text(json.dumps({
        "ejecucion": {"id": "r", "activo_codigo": "EX-220", "operador": "X",
                      "fecha": "2026-03-20"},
        "anomalias": [
            {"id": "r.1", "activo_codigo": "EX-220", "componente": "Manguera",
             "descripcion": "Gotea por la union", "codigo_catalogo": "",
             "modo_falla_id": ""},
            {"id": "r.2", "activo_codigo": "EX-220", "componente": "Panal",
             "descripcion": "Tapado", "modo_falla_id": "",
             "codigo_catalogo": "TER.SOBRECALENTAMIENTO.RADIADOR"},
        ]}), encoding="utf-8")
    _abrir_ronda(pag, suelto)
    texto = pag.inner_text("#app")
    assert "No engancharon, y por qué" in texto
    assert "el telefono no clasifica texto libre" in texto
    assert "fixmate tpm anomalias" in texto
    # El que sí trae código engancha por código, y lo dice.
    pag.click('button[data-modo="F1.1.1"]')
    assert "por codigo de catalogo" in pag.inner_text("#ficha")


def test_una_ronda_de_otra_maquina_no_se_mezcla(pagina, tmp_path):
    pag, _ = pagina
    _abrir(pag)
    ajena = tmp_path / "ronda-ajena.json"
    ajena.write_text(json.dumps({
        "ejecucion": {"id": "r", "activo_codigo": "CA-740", "operador": "X",
                      "fecha": "2026-03-20"},
        "anomalias": [{"id": "r.1", "activo_codigo": "CA-740", "descripcion": "x",
                       "codigo_catalogo": "TER.SOBRECALENTAMIENTO.RADIADOR",
                       "modo_falla_id": ""}]}), encoding="utf-8")
    _abrir_ronda(pag, ajena)
    texto = pag.inner_text("#app")
    assert "La ronda es de" in texto and "CA-740" in texto
    assert "ensucia las dos" in texto
    assert "1 en campo" not in pag.inner_text(".arbol")


def test_la_ronda_no_se_guarda_dentro_del_analisis(pagina, tmp_path):
    """La ronda sigue siendo la ronda.

    Meterla dentro del archivo del análisis obligaría a inventar un campo que
    el cargador no lee, y el primer cliente que lo abriera con el comando
    perdería la evidencia sin enterarse.
    """
    from nefer.fixmate import cargador

    pag, _ = pagina
    _abrir(pag)
    _abrir_ronda(pag, RONDA)
    with pag.expect_download() as esperando:
        pag.click("#bajar")
    destino = tmp_path / "exportado.json"
    esperando.value.save_as(destino)
    datos = json.loads(destino.read_text(encoding="utf-8"))
    assert "anomalias" not in datos and "ronda" not in datos
    cargador.analisis_de_dict(datos)     # sigue entrando por el cargador


# ═══════════ el análisis como registro, en pantalla ═══════════

def test_el_ejemplo_se_ve_como_un_registro_identificado(pagina):
    pag, _ = pagina
    _abrir(pag)
    texto = pag.inner_text("#app")
    # El encabezado va en versalitas por CSS.
    assert "el análisis como registro" in texto.lower()
    assert "Identificado y auditable" in texto
    assert "Revisión 1" in texto
    assert "(jefe de mantenimiento)" in texto
    assert "se revisa el 2027-03-15" in texto


def test_un_analisis_completo_puede_no_ser_un_registro_valido(pagina, tmp_path):
    """Las siete contestadas y aun así sin dueño.

    Es la diferencia que nadie ve hasta que llega la auditoría: la
    completitud dice si el análisis está terminado; el registro, si se puede
    saber dentro de dos años quién responde por él.
    """
    import json as _json

    pag, _ = pagina
    doc = _json.loads((RAIZ / "ejemplos" / "rcm-tpm" / "analisis-ex220.json")
                      .read_text(encoding="utf-8"))
    for campo in ("revision", "aprobado_por", "proxima_revision"):
        doc.pop(campo, None)
    sin_firma = tmp_path / "sin-firma.json"
    sin_firma.write_text(_json.dumps(doc), encoding="utf-8")

    pag.set_input_files("input[type=file]", str(sin_firma))
    pag.wait_for_selector(".arbol")
    texto = pag.inner_text("#app")
    assert "Las siete están contestadas" in texto
    assert "1 no conformidad(es) de registro" in texto
    assert "no declara numero de revision, quien lo aprobo" in texto
    assert "Sin revisión · sin aprobar" in texto


def test_dos_modos_con_el_mismo_codigo_se_denuncian_al_revisar(pagina, tmp_path):
    """La ambigüedad que impide enganchar una anomalía de campo.

    `anomalia.enlazar` se niega a elegir entre dos modos con el mismo código
    —y hace bien—, pero si nadie lo dice al revisar, el análisis se da por
    bueno y el enganche falla en silencio meses después.
    """
    import json as _json

    pag, _ = pagina
    doc = _json.loads((RAIZ / "ejemplos" / "rcm-tpm" / "analisis-ex220.json")
                      .read_text(encoding="utf-8"))
    doc["funciones"][0]["fallas"][0]["modos"][1]["codigo_catalogo"] = \
        "TER.SOBRECALENTAMIENTO.RADIADOR"
    repetido = tmp_path / "repetido.json"
    repetido.write_text(_json.dumps(doc), encoding="utf-8")

    pag.set_input_files("input[type=file]", str(repetido))
    pag.wait_for_selector(".arbol")
    texto = pag.inner_text("#app")
    assert "declaran el mismo codigo" in texto
    assert "F1.1.1, F1.1.2" in texto
    assert "la ambiguedad se resuelve aqui" in texto
