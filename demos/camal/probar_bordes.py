"""Casos borde del demo: coma decimal, texto basura, precio vacio, recarga."""
import pathlib
import sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _navegador import ruta_del_navegador

DEMO = pathlib.Path(__file__).resolve().parent / "demo_camal.html"

with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path=ruta_del_navegador())
    p = nav.new_context(locale="es-PE").new_page()
    p.goto(DEMO.as_uri())

    def ultimo():
        return p.evaluate("registros[registros.length-1]")

    # A. El operador escribe el peso con coma, como se escribe en Peru
    p.once("dialog", lambda d: d.accept("38,5"))
    p.click("text=+ Alpaca >> nth=0")
    print("A. peso '38,5'      ->", ultimo())

    # B. El operador escribe cualquier cosa (dedo gordo, guante)
    p.once("dialog", lambda d: d.accept("asd"))
    p.click("text=+ Llama")
    print("B. peso 'asd'       ->", ultimo())

    # C. Precio por kg borrado antes de contar
    p.fill("#precioSoles", "")
    p.once("dialog", lambda d: d.accept("40"))
    p.click("text=+ Cordero")
    print("C. precio vacio     ->", ultimo())

    # D. Peso negativo en el conteo rapido (guardarEntrada si valida, este no)
    p.once("dialog", lambda d: d.accept("-12"))
    p.click("text=+ Alpaca Vieja")
    print("D. peso '-12'       ->", ultimo())
    print("   resumen          ->", p.inner_text("#resumenTotales").replace("\n", " | "))

    # E. Recargar la pagina: que sobrevive de la jornada
    p.reload()
    print("E. tras recargar    ->", p.evaluate("registros.length"), "registros |",
          p.inner_text("#resumenTotales").replace("\n", " | "))
    print("   localStorage     ->", p.evaluate("Object.keys(localStorage).length"), "claves")

    # F. Se puede corregir o borrar un registro mal tecleado?
    print("F. botones de la UI ->", p.eval_on_selector_all(
        "button", "bs => bs.map(b => b.textContent.trim())"))
    nav.close()
