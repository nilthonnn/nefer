"""Recorre la app de lotes de punta a punta, como una jornada de verdad."""
import pathlib
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _navegador import ruta_del_navegador

APP = pathlib.Path(__file__).resolve().parent / "app-camal.html"
SALIDA = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "salidas")
SALIDA.mkdir(parents=True, exist_ok=True)

errores, fallos = [], []

def exigir(condicion, dicho):
    print(("  ok  " if condicion else "FALLA ") + dicho)
    if not condicion:
        fallos.append(dicho)

with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path=ruta_del_navegador())
    ctx = nav.new_context(viewport={"width": 390, "height": 844},
                          device_scale_factor=2, locale="es-PE",
                          timezone_id="America/Lima")
    p = ctx.new_page()
    p.on("pageerror", lambda e: errores.append(str(e)))
    p.goto(APP.as_uri())

    print("\n[1] La jornada abre con datos de ejemplo")
    exigir("Jornada del camal" in p.inner_text("h1"), "se ve la jornada")
    exigir(p.locator(".lote").count() == 3, "tres lotes de demostración")
    p.screenshot(path=SALIDA / "1-jornada.png", full_page=True)

    print("\n[2] Lote nuevo de pesaje: 40 cabezas de alpaca")
    p.click("text=Nuevo lote de pesaje")
    p.select_option("#categoriaLote", "Alpaca")
    exigir(p.input_value("#cantidadLote") == "40", "la cantidad propuesta es 40")
    p.click("text=Empezar a pesar")
    exigir("de 40" in p.inner_text(".correlativo"), "arranca en el correlativo 1 de 40")
    p.screenshot(path=SALIDA / "2-pesaje-inicio.png", full_page=True)

    print("\n[3] Se pesa y salta solo al siguiente correlativo")
    for peso in ["42.5", "39,8", "44.2"]:      # el segundo va con coma, a propósito
        p.fill("#pesoActual", peso)
        p.click("text=/^Registrar N°/")
    correl = p.inner_text(".correlativo .num")
    exigir(correl == "4", f"tras tres pesadas toca el N° 4 (dice {correl})")
    exigir(p.evaluate("loteActual().pesos[1]") == 39.8, "«39,8» con coma entra como 39.8")
    exigir("126.50" in p.inner_text(".tiras"), "acumula 126.50 kg")
    p.screenshot(path=SALIDA / "3-pesaje-tres.png", full_page=True)

    print("\n[4] Lo que no es un peso no entra")
    for malo in ["asd", "-12", "0", "980"]:
        p.fill("#pesoActual", malo)
        p.click("text=/^Registrar N°/")
        exigir(p.locator(".aviso").count() == 1 and p.evaluate("loteActual().pesos.length") == 3,
               f"«{malo}» se rechaza con aviso")

    print("\n[5] La cantidad del lote se amplía y no baja de lo pesado")
    p.click("button[aria-label='Sumar una cabeza']")
    exigir(p.evaluate("loteActual().cantidad") == 41, "sube a 41")
    p.fill("#cantidadEnCurso", "2")
    p.dispatch_event("#cantidadEnCurso", "change")
    exigir(p.evaluate("loteActual().cantidad") == 3, "no baja de las 3 pesadas")
    p.fill("#cantidadEnCurso", "5")
    p.dispatch_event("#cantidadEnCurso", "change")

    print("\n[6] Una pesada mal tecleada se corrige y se borra")
    p.click(".pesada >> nth=0")
    p.fill("#pesoEditado", "41,0")
    p.click("text=Guardar")
    exigir(p.evaluate("loteActual().pesos[0]") == 41.0, "la N° 1 queda en 41.0")
    p.click(".pesada >> nth=2")
    p.click("text=Eliminar")
    exigir(p.evaluate("loteActual().pesos.length") == 2, "quedan dos pesadas")
    exigir(p.inner_text(".correlativo .num") == "3", "el correlativo vuelve al 3")

    print("\n[7] Se termina el lote y recién ahí se pone el precio")
    p.click("text=Terminar lote")
    exigir("Lote culminado" in p.inner_text("h1"), "el lote queda culminado")
    exigir("80.80" in p.inner_text(".tiras"), "suma 80.80 kg")
    exigir(p.input_value("#precioLote") == "14.00", "propone el precio de referencia")
    p.fill("#precioLote", "15,50")
    p.dispatch_event("#precioLote", "change")
    exigir("S/ 1252.40" in p.inner_text("body"), "80.80 kg × S/ 15.50 = S/ 1252.40")
    p.screenshot(path=SALIDA / "4-culminado.png", full_page=True)

    print("\n[8] Lote de menudencias: por unidad, no por peso")
    p.click("text=Volver a la jornada")
    p.click("text=Nuevo lote de menudencias")
    p.select_option("#categoriaLote", "Menudencia de Cordero")
    p.fill("#cantidadLote", "12")
    p.click("text=Abrir el lote")
    p.fill("#precioUnidad", "18.50")
    p.dispatch_event("#precioUnidad", "change")
    exigir("S/ 222.00" in p.inner_text("body"), "12 und × S/ 18.50 = S/ 222.00")
    p.click("button[aria-label='Sumar una']")
    exigir("S/ 240.50" in p.inner_text("body"), "sube a 13 und y recalcula")
    p.screenshot(path=SALIDA / "5-menudencias.png", full_page=True)
    p.click("text=Cerrar el lote")
    p.click("text=Volver a la jornada")

    print("\n[9] La jornada sobrevive a recargar el teléfono")
    antes = p.inner_text(".tiras")
    p.reload()
    exigir(p.inner_text(".tiras") == antes, "los totales siguen ahí tras recargar")
    exigir(p.locator(".lote").count() == 5, "los cinco lotes siguen ahí")
    p.screenshot(path=SALIDA / "6-jornada-final.png", full_page=True)

    print("\n[10] Las dos hojas de Excel")
    p.click("text=Exportar a Excel")
    detalle = p.input_value("#textoCSV")
    p.click("text=Resumen por lote")
    resumen = p.input_value("#textoCSV")
    exigir(detalle.startswith("Fecha,Lote,Categoria,N,Peso (kg)"), "el detalle lleva correlativo")
    exigir(len(detalle.strip().split("\n")) == 1 + 8 + 5 + 2, "una fila por cabeza pesada")
    exigir("Menudencia,\"Menudencia de Cordero\",13,unidades" in resumen, "las menudencias van por unidad")
    p.screenshot(path=SALIDA / "7-exportar.png", full_page=True)
    (SALIDA / "Camal_detalle.csv").write_text(detalle, encoding="utf-8")
    (SALIDA / "Camal_resumen.csv").write_text(resumen, encoding="utf-8")
    print("\n--- resumen por lote ---\n" + resumen)

    ctx.close(); nav.close()

print("--- errores de página:", errores or "ninguno")
print("--- fallos:", fallos or "ninguno")
sys.exit(1 if (errores or fallos) else 0)
