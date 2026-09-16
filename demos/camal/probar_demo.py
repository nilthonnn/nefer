"""Ejecuta el demo del camal en Chromium y prueba las 3 funciones del PDF."""
import pathlib, sys
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _navegador import ruta_del_navegador

DEMO = pathlib.Path(__file__).resolve().parent / "demo_camal.html"
OUT = pathlib.Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

errores, consola = [], []

def resumen(p):
    return p.inner_text("#resumenTotales").replace("\n", " | ")

with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path=ruta_del_navegador())
    ctx = nav.new_context(viewport={"width": 390, "height": 844},
                          device_scale_factor=2, accept_downloads=True,
                          locale="es-PE", timezone_id="America/Lima")
    p = ctx.new_page()
    p.on("console", lambda m: consola.append(f"{m.type}: {m.text}"))
    p.on("pageerror", lambda e: errores.append(str(e)))
    p.goto(DEMO.as_uri())

    print("[0] Arranque      ->", resumen(p))
    print("    filas tabla   ->", p.locator("#cuerpoTabla tr").count())
    p.screenshot(path=OUT / "1-arranque.png", full_page=True)

    # --- 1. Conteo rapido: + Alpaca con peso 38.5 (prompt del navegador)
    p.once("dialog", lambda d: d.accept("38.5"))
    p.click("text=+ Alpaca >> nth=0")
    print("[1] +Alpaca 38.5  ->", resumen(p))
    p.screenshot(path=OUT / "2-conteo-rapido.png", full_page=True)

    # --- 2. Registro de partes: Menudencias / Panzas, 5.5 kg
    p.select_option("#tipoParte", "Menudencias / Panzas")
    p.fill("#pesoKg", "5.5")
    p.click("text=Guardar Registro")
    print("[2] Menudencias   ->", resumen(p))
    print("    campo peso    ->", repr(p.input_value("#pesoKg")))
    p.screenshot(path=OUT / "3-registro-partes.png", full_page=True)

    # --- 2b. Validacion: guardar sin peso
    avisos = []
    p.once("dialog", lambda d: (avisos.append(d.message), d.accept()))
    p.click("text=Guardar Registro")
    print("[2b] sin peso     -> alerta:", avisos)

    # --- 2c. Cancelar el prompt del conteo rapido no debe registrar nada
    antes = p.evaluate("registros.length")
    p.once("dialog", lambda d: d.dismiss())
    p.click("text=+ Llama")
    print("[2c] cancelar     -> registros antes/despues:",
          antes, p.evaluate("registros.length"))

    # --- 2d. Boton de datos demo
    p.click("text=Cargar Más Datos Demo")
    print("[2d] +datos demo  ->", resumen(p))

    # --- 3. Exportar a Excel (.CSV)
    with p.expect_download() as dl:
        p.click("text=Exportar a Excel (.CSV)")
    descarga = dl.value
    destino = OUT / descarga.suggested_filename
    descarga.save_as(destino)
    print("[3] Exportado     ->", destino.name, destino.stat().st_size, "bytes")
    p.screenshot(path=OUT / "4-final.png", full_page=True)

    # --- estado interno final, para cuadrar los totales a mano
    total = p.evaluate("registros.reduce((a,r)=>a+r.subtotal,0)")
    kg = p.evaluate("registros.reduce((a,r)=>a+r.peso,0)")
    print(f"    control JS    -> {p.evaluate('registros.length')} registros, "
          f"{kg:.1f} kg, S/ {total:.2f}")
    ctx.close(); nav.close()

print("\n--- CSV descargado ---")
print(destino.read_text(encoding="utf-8-sig"))
print("--- errores de pagina:", errores or "ninguno")
print("--- consola:", consola or "sin mensajes")
