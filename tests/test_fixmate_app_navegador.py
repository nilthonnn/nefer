"""La pestaña de diagnóstico, conducida en un navegador de verdad.

El motor ya se compara contra el de Python en `test_fixmate_cruce.py`. Lo que
se prueba aquí es lo otro: que en el teléfono se pueda cargar el índice, que
quede guardado para la próxima vez —que es lo que hace que sirva sin señal— y
que la respuesta aparezca en pantalla con su evidencia.

Se salta entera sin Playwright o sin Chromium.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="Playwright no esta instalado")
from playwright.sync_api import sync_playwright  # noqa: E402

from navegador import HAY_CHROMIUM, opciones  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "docs" / "app" / "index.html"
EJEMPLOS = RAIZ / "ejemplos" / "fixmate"

pytestmark = pytest.mark.skipif(not HAY_CHROMIUM, reason="no hay Chromium disponible")

UA_ANDROID = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120 Mobile Safari/537.36")


@pytest.fixture(scope="module")
def indice(tmp_path_factory) -> Path:
    from nefer.fixmate import Indice, Motor, actualizar

    indice = Indice()
    actualizar(indice, [EJEMPLOS])
    indice.medicion = Motor(indice).medicion()
    return indice.guardar(tmp_path_factory.mktemp("indice") / "indice.json")


class Telefono:
    """La app abierta como la abre un operario, en un teléfono."""

    def __init__(self, pw, contexto_extra=None):
        self.navegador = pw.chromium.launch(**opciones())
        self.contexto = self.navegador.new_context(
            user_agent=UA_ANDROID, viewport={"width": 412, "height": 915},
            **(contexto_extra or {}))
        self.pg = self.contexto.new_page()
        self.pg.goto(APP.as_uri())
        self.pg.click("#tab-diagnostico")

    def cargar(self, ruta: Path):
        with self.pg.expect_file_chooser() as elegido:
            self.pg.click("label[for='dx-archivo']")
        elegido.value.set_files(str(ruta))
        self.pg.wait_for_selector("#dx-listo:not([hidden])", timeout=15000)

    def consultar(self, texto: str, dtc: str = ""):
        self.pg.fill("#dx-consulta", texto)
        if dtc:
            self.pg.fill("#dx-dtc", dtc)
        self.pg.click("#dx-buscar")
        self.pg.wait_for_timeout(300)

    def cerrar(self):
        self.contexto.close()
        self.navegador.close()


def test_la_pestana_esta_y_pide_los_papeles_antes_de_nada():
    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            assert t.pg.is_visible("#v-diagnostico")
            assert t.pg.is_visible("#dx-sin-indice"), "sin índice tiene que pedirlo"
            assert not t.pg.is_visible("#dx-listo")
            texto = t.pg.text_content("#dx-sin-indice")
            assert "Todavía no hay nada cargado" in texto
            # Y dice qué hay que traer, no sólo que falta algo.
            assert "historial" in texto.lower() and "manuales" in texto.lower()
        finally:
            t.cerrar()


def test_con_el_indice_cargado_contesta_con_su_evidencia(indice):
    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            t.cargar(indice)
            estado = t.pg.text_content("#dx-estado")
            assert "fragmentos" in estado

            t.consultar("gotea aceite por el cilindro del brazo toda la noche")
            salida = t.pg.text_content("#dx-salida")
            assert "Sello del vástago cortado" in salida
            assert "EVIDENCIA" in salida.upper()
            assert "OT-2026-0501" in salida
            # Y lo que dice el historial entero, con su medición al lado.
            assert "LO QUE DICE EL HISTORIAL COMPLETO" in salida.upper()
            assert "acierta el" in salida
        finally:
            t.cerrar()


def test_el_torque_que_ensena_sale_de_la_fuente(indice):
    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            t.cargar(indice)
            t.consultar("que apriete lleva el perno de la tapa del cilindro")
            salida = t.pg.text_content("#dx-salida")
            assert "210 N·m" in salida
            assert "manual OEM" in salida, "tiene que avisar de contrastarlo"
        finally:
            t.cerrar()


def test_sin_antecedentes_lo_dice_y_no_inventa(indice):
    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            t.cargar(indice)
            t.consultar("tramites de aduana del contenedor en el puerto")
            assert "No hay antecedentes" in t.pg.text_content("#dx-estado")
            assert t.pg.text_content("#dx-salida").strip() == ""
        finally:
            t.cerrar()


def test_el_indice_queda_guardado_para_la_proxima_vez(indice):
    """Lo que hace que sirva en el socavón: se carga una vez y ya está."""
    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            t.cargar(indice)
            # Se vuelve a abrir la app en el mismo teléfono, sin tocar nada.
            otra = t.contexto.new_page()
            otra.goto(APP.as_uri())
            otra.click("#tab-diagnostico")
            otra.wait_for_selector("#dx-listo:not([hidden])", timeout=15000)
            assert "guardado en este teléfono" in otra.text_content("#dx-estado")

            otra.fill("#dx-consulta", "no arranca en la mañana")
            otra.click("#dx-buscar")
            otra.wait_for_timeout(300)
            assert "Baterías" in otra.text_content("#dx-salida")
        finally:
            t.cerrar()


def test_un_indice_de_otro_embebedor_se_rechaza_con_su_motivo(indice, tmp_path):
    # Mezclar embebedores no da error: da respuestas sin sentido. El teléfono
    # tiene que negarse igual que la herramienta de escritorio.
    datos = json.loads(indice.read_text(encoding="utf-8"))
    datos["embebedor"] = "openai-text-embedding-3-small"
    ajeno = tmp_path / "ajeno.json"
    ajeno.write_text(json.dumps(datos), encoding="utf-8")

    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            with t.pg.expect_file_chooser() as elegido:
                t.pg.click("label[for='dx-archivo']")
            elegido.value.set_files(str(ajeno))
            t.pg.wait_for_timeout(500)
            estado = t.pg.text_content("#dx-estado")
            assert "Vuelva a indexarlo" in estado or "vuelva a indexarlo" in estado
            assert t.pg.is_visible("#dx-sin-indice"), "sigue sin índice utilizable"
        finally:
            t.cerrar()


def test_el_archivo_suelto_trae_su_indice_de_ejemplo():
    """El que se manda por WhatsApp demuestra el diagnóstico sin preparar nada."""
    descargable = RAIZ / "docs" / "nefer-app.html"
    with sync_playwright() as pw:
        navegador = pw.chromium.launch(**opciones())
        pg = navegador.new_context(user_agent=UA_ANDROID).new_page()
        try:
            pg.goto(descargable.as_uri())
            pg.click("#tab-diagnostico")
            pg.wait_for_selector("#dx-listo:not([hidden])", timeout=15000)
            assert "ejemplo incrustado" in pg.text_content("#dx-estado")

            pg.fill("#dx-consulta", "humo negro y pierde fuerza")
            pg.click("#dx-buscar")
            pg.wait_for_timeout(300)
            assert "Filtro de aire" in pg.text_content("#dx-salida")
        finally:
            navegador.close()


# ------------------------------- cerrar el círculo desde el propio teléfono

def test_lo_que_se_cierra_en_faena_responde_en_el_acto(indice):
    """Sin señal y sin reindexar: lo que el técnico registra, ya se encuentra."""
    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            t.cargar(indice)
            # Una falla que el índice no tiene: nadie la registró todavía.
            t.consultar("el ventilador no gira y el motor se calienta")
            assert not t.pg.is_hidden("#dx-cierre"), (
                "aunque no haya antecedentes —sobre todo entonces— tiene que "
                "poder registrarse lo que resulte")

            t.pg.fill("#dx-c-causa", "Correa del ventilador partida por polea desalineada")
            t.pg.fill("#dx-c-solucion", "Se cambió la correa y se alineó la polea")
            t.pg.fill("#dx-c-equipo", "GE074-03")
            t.pg.fill("#dx-c-repuestos", "Correa 8PK1230")
            t.pg.click("#dx-registrar")
            t.pg.wait_for_timeout(400)
            assert "registrado OT-CAMPO" in t.pg.text_content("#dx-c-aviso")

            # Y la siguiente consulta ya lo encuentra, en el mismo teléfono.
            t.consultar("el ventilador no gira y sube la temperatura")
            salida = t.pg.text_content("#dx-salida")
            assert "Correa del ventilador partida" in salida
            assert "Correa 8PK1230" in salida
        finally:
            t.cerrar()


def test_un_informe_sin_causa_ni_solucion_no_se_registra(indice):
    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            t.cargar(indice)
            t.consultar("ruido raro en la caja de transmisión")
            t.pg.fill("#dx-c-causa", "")
            t.pg.fill("#dx-c-solucion", "")
            t.pg.click("#dx-registrar")
            t.pg.wait_for_timeout(200)
            assert "falta la causa" in t.pg.text_content("#dx-c-aviso")
            assert t.pg.is_hidden("#dx-envio"), "no hay nada pendiente que enviar"
        finally:
            t.cerrar()


def test_lo_registrado_sobrevive_a_cerrar_la_app(indice):
    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            t.cargar(indice)
            t.consultar("el ventilador no gira")
            t.pg.fill("#dx-c-causa", "Correa partida")
            t.pg.fill("#dx-c-solucion", "Se cambió la correa")
            t.pg.click("#dx-registrar")
            t.pg.wait_for_timeout(400)

            otra = t.contexto.new_page()
            otra.goto(APP.as_uri())
            otra.click("#tab-diagnostico")
            otra.wait_for_selector("#dx-listo:not([hidden])", timeout=15000)
            otra.wait_for_timeout(300)
            assert "por enviar" in otra.text_content("#dx-pend")

            otra.fill("#dx-consulta", "el ventilador no gira")
            otra.click("#dx-buscar")
            otra.wait_for_timeout(300)
            assert "Correa partida" in otra.text_content("#dx-salida")
        finally:
            t.cerrar()


def test_los_informes_se_envian_como_un_archivo_para_la_oficina(indice, tmp_path):
    """Un archivo por WhatsApp es toda la sincronización que un taller necesita."""
    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            t.cargar(indice)
            t.consultar("el ventilador no gira")
            t.pg.fill("#dx-c-causa", "Correa partida")
            t.pg.fill("#dx-c-solucion", "Se cambió la correa")
            t.pg.fill("#dx-c-equipo", "GE074-03")
            t.pg.click("#dx-registrar")
            t.pg.wait_for_timeout(400)

            with t.pg.expect_download() as bajada:
                t.pg.click("#dx-enviar")
            archivo = tmp_path / "envio.json"
            bajada.value.save_as(str(archivo))

            envio = json.loads(archivo.read_text(encoding="utf-8"))
            assert len(envio["pendientes"]) == 1
            informe = envio["pendientes"][0]
            assert informe["causa_raiz"] == "Correa partida"
            assert informe["codigo_equipo"] == "GE074-03"
            assert informe["codigo_ot"].startswith("OT-CAMPO-")

            # Y la oficina lo mete en su historial con lo que ya tiene.
            from nefer.fixmate import cierre

            historial = tmp_path / "historial.json"
            parte = cierre.recibir(archivo, historial)
            assert len(parte.nuevos) == 1 and not parte.rechazados
            # Reenviarlo —que es lo que va a pasar— no duplica nada.
            assert not cierre.recibir(archivo, historial).nuevos
        finally:
            t.cerrar()


# ------------------------------------ cargar los papeles en el propio teléfono

@pytest.fixture(scope="module")
def historial_xlsx(tmp_path_factory) -> Path:
    """Un historial como lo manda un taller: con membrete y sin empezar en A1."""
    openpyxl = pytest.importorskip("openpyxl")

    destino = tmp_path_factory.mktemp("taller") / "historial-fallas.xlsx"
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja["A1"] = "TRANSPORTES Y MAQUINARIA S.A.C."
    hoja["A2"] = "Historial de fallas — Flota de excavadoras"
    hoja.append([])
    hoja.append([])
    hoja.append(["N° OT", "Fecha", "Equipo", "Horómetro", "Código de falla",
                 "Falla reportada", "Causa raíz", "Trabajo realizado", "Repuestos"])
    for fila in [
        ["OT-2026-0311", "2026-03-04", "EX-220-01", 4820, "P0300",
         "Humo negro y pierde fuerza en la subida cargado",
         "Filtro de aire colmatado", "Cambio de filtro primario y secundario",
         "Filtro P181054"],
        ["OT-2026-0349", "2026-04-18", "EX-220-02", 5210, "",
         "Gotea aceite por el cilindro del brazo toda la noche",
         "Sello del vástago vencido", "Cambio de sellos del cilindro del brazo",
         "Kit de sellos 707-99"],
        ["OT-2026-0402", "2026-05-22", "EX-220-01", 5390, "",
         "No arranca en la mañana, el arranque gira lento",
         "Bornes de batería sulfatados", "Limpieza de bornes y ajuste a 8 N·m", ""],
    ]:
        hoja.append(fila)
    libro.save(destino)
    return destino


def _con_papeles(t, *rutas):
    with t.pg.expect_file_chooser() as elegido:
        t.pg.click("label[for='dx-archivo']")
    elegido.value.set_files([str(r) for r in rutas])
    t.pg.wait_for_selector("#dx-listo:not([hidden])", timeout=20000)


def test_el_excel_del_taller_se_carga_en_el_telefono(historial_xlsx):
    """Antes esto sólo pasaba en la oficina.

    El técnico recibía un índice ya cocinado, y cargar el historial de un
    equipo nuevo obligaba a volver a la computadora. Un .xlsx es un zip con
    XML dentro, y el navegador sabe descomprimir y leer XML de fábrica.
    """
    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            assert "Todavía no hay nada cargado" in t.pg.inner_text("#dx-sin-indice")
            _con_papeles(t, historial_xlsx)

            estado = t.pg.inner_text("#dx-estado")
            assert "3 fragmentos" in estado.lower()

            # Y contesta con lo que se acaba de cargar, con las palabras del
            # patio y no con las del encabezado del Excel.
            t.consultar("la máquina bota humo negro y no tiene fuerza")
            salida = t.pg.inner_text("#dx-salida")
            assert "Filtro de aire colmatado" in salida
            assert "OT-2026-0311" in salida
        finally:
            t.cerrar()


def test_lo_que_se_agrega_se_suma_a_lo_que_ya_habia(historial_xlsx, tmp_path):
    """Acumular experiencia es el punto: el segundo archivo no borra el primero."""
    manual = tmp_path / "manual-hidraulico.md"
    manual.write_text(
        "# Sistema hidráulico\n\n"
        "PELIGRO: el acumulador conserva presión veinte minutos después de "
        "parar el motor.\n\n"
        "Par de apriete de la tapa del cilindro: 210 N·m.\n",
        encoding="utf-8")

    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            _con_papeles(t, historial_xlsx)
            antes = t.pg.inner_text("#dx-biblio-resumen")
            t.pg.click("#dx-biblio summary")      # la biblioteca se pliega

            with t.pg.expect_file_chooser() as elegido:
                t.pg.click("label[for='dx-archivo-2']")
            elegido.value.set_files(str(manual))
            t.pg.wait_for_timeout(1500)

            despues = t.pg.inner_text("#dx-biblio-resumen")
            assert despues != antes
            fuentes = t.pg.inner_text("#dx-fuentes")
            assert "historial-fallas.xlsx" in fuentes, "borró lo que ya había"
            assert "manual-hidraulico.md" in fuentes

            # El torque del manual sale citado, y la advertencia también.
            t.consultar("qué apriete lleva la tapa del cilindro")
            salida = t.pg.inner_text("#dx-salida")
            assert "210 N·m" in salida
        finally:
            t.cerrar()


def test_un_pdf_no_se_finge_leido(tmp_path):
    """Decir «no sé abrirlo» es la respuesta correcta; cargarlo vacío, no."""
    falso = tmp_path / "manual.pdf"
    falso.write_bytes(b"%PDF-1.4\nno importa\n")

    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            with t.pg.expect_file_chooser() as elegido:
                t.pg.click("label[for='dx-archivo']")
            elegido.value.set_files(str(falso))
            t.pg.wait_for_timeout(1500)
            estado = t.pg.inner_text("#dx-estado")
            assert "PDF" in estado
            assert "oficina" in estado.lower()
        finally:
            t.cerrar()


def test_lo_cargado_sigue_ahi_al_reabrir(historial_xlsx):
    """Sin esto no sirve en faena: se carga una vez y queda."""
    with sync_playwright() as pw:
        t = Telefono(pw)
        try:
            _con_papeles(t, historial_xlsx)
            t.pg.wait_for_timeout(1200)      # que termine de guardar

            otra = t.contexto.new_page()
            otra.goto(APP.as_uri())
            otra.click("#tab-diagnostico")
            otra.wait_for_selector("#dx-listo:not([hidden])", timeout=15000)
            otra.fill("#dx-consulta", "gotea aceite del brazo")
            otra.click("#dx-buscar")
            otra.wait_for_timeout(900)
            assert "Sello del vástago" in otra.inner_text("#dx-salida")
        finally:
            t.cerrar()
