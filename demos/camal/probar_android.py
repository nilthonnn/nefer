"""Comprueba que lo publicado en `docs/camal/` se comporta como app de Android.

No basta con que la página abra. Para que Android la trate como aplicación
—icono propio, sin barra de navegador, y sobre todo funcionando sin señal—
Chrome exige cuatro cosas: manifiesto con nombre, iconos de 192 y 512, arranque
en modo `standalone` y un trabajador de servicio con manejador de descargas.
Aquí se sirve la carpeta por http —como lo hará Pages—, se conduce un Chromium
emulando un teléfono con pantalla táctil, y se comprueban una por una. Después
se corta la red y se vuelve a entrar: es la prueba que de verdad importa en el
camal.

    python3 demos/camal/probar_android.py salidas/
"""

import http.server
import json
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _navegador import ruta_del_navegador

PUBLICADO = pathlib.Path(__file__).resolve().parents[2] / "docs" / "camal"
SALIDA = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "salidas")
SALIDA.mkdir(parents=True, exist_ok=True)

# Un Pixel de gama media, que es el teléfono que hay en un camal.
ANDROID = ("Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")

errores, fallos = [], []


def exigir(condicion, dicho):
    print(("  ok  " if condicion else "FALLA ") + dicho)
    if not condicion:
        fallos.append(dicho)


class Servidor(http.server.SimpleHTTPRequestHandler):
    """Sirve `docs/camal/` y calla: el registro de peticiones estorba."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLICADO), **kwargs)

    def log_message(self, *args):
        pass

    def end_headers(self):
        # Pages sirve el manifiesto con su tipo; el servidor de Python no lo
        # conoce, y sin eso Chrome lo ignora y la app no es instalable.
        if self.path.endswith(".webmanifest"):
            self.send_header("Content-Type", "application/manifest+json")
        super().end_headers()


socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", 0), Servidor) as servidor:
    puerto = servidor.server_address[1]
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    RAIZ = f"http://127.0.0.1:{puerto}/"
    print(f"sirviendo {PUBLICADO} en {RAIZ}")

    with sync_playwright() as pw:
        nav = pw.chromium.launch(executable_path=ruta_del_navegador())
        ctx = nav.new_context(
            viewport={"width": 393, "height": 851}, device_scale_factor=2.75,
            is_mobile=True, has_touch=True, user_agent=ANDROID,
            locale="es-PE", timezone_id="America/Lima", accept_downloads=True)
        p = ctx.new_page()
        p.on("pageerror", lambda e: errores.append(str(e)))
        p.goto(RAIZ, wait_until="load")

        print("\n[1] Abre como página en el teléfono")
        exigir("Jornada del camal" in p.inner_text("h1"), "carga la jornada")
        exigir(p.evaluate("navigator.maxTouchPoints > 0"), "el navegador se declara táctil")
        exigir(p.evaluate("document.querySelector('meta[name=theme-color]').content") == "#1A1E25",
               "la barra de estado toma el color de la app")
        p.screenshot(path=SALIDA / "android-1-jornada.png", full_page=True)

        print("\n[2] Lo que Android exige para instalarla")
        manifiesto = json.loads(p.evaluate("""
            fetch(document.querySelector('link[rel=manifest]').href).then(r => r.text())
        """))
        exigir(bool(manifiesto.get("name")) and bool(manifiesto.get("short_name")),
               f"manifiesto con nombre: «{manifiesto.get('name')}»")
        exigir(manifiesto.get("display") == "standalone",
               "arranca sin barra de navegador (display standalone)")
        exigir(manifiesto.get("start_url") == "./" and manifiesto.get("scope") == "./",
               "arranque y alcance dentro de su carpeta")
        medidas = {i["sizes"] for i in manifiesto.get("icons", [])}
        exigir({"192x192", "512x512"} <= medidas, f"iconos {sorted(medidas)}")
        exigir(any(i.get("purpose") == "maskable" for i in manifiesto["icons"]),
               "un icono recortable, para que Android no lo meta en un cuadro blanco")

        for icono in ("icono-192.png", "icono-512.png", "apple-touch-icon.png"):
            estado = p.evaluate(f"fetch('{icono}').then(r => r.status)")
            exigir(estado == 200, f"{icono} se sirve ({estado})")

        print("\n[3] El trabajador de servicio queda registrado")
        p.wait_for_function("navigator.serviceWorker.controller !== null", timeout=15000)
        exigir(p.evaluate("navigator.serviceWorker.controller !== null"),
               "la app quedó bajo el control del trabajador")
        exigir(p.evaluate("""
            navigator.serviceWorker.getRegistration().then(r => !!(r && r.active))
        """), "y el trabajador está activo")
        guardadas = p.evaluate("""
            caches.open('camal-2026-09-17').then(c => c.keys()).then(ks => ks.length)
        """)
        exigir(guardadas >= 5, f"guardó {guardadas} piezas para abrir sin señal")

        print("\n[4] Se registra una jornada, a dedo")
        p.fill("#operador", "Nilthon Chit")
        p.dispatch_event("#operador", "change")
        p.tap("text=Nuevo lote de pesaje")
        p.select_option("#categoriaLote", "Alpaca degollada")
        p.fill("#cantidadLote", "6")
        p.tap("text=Empezar a pesar")
        for peso in ["42,5", "39.8", "44,2"]:
            p.fill("#pesoActual", peso)
            p.tap("text=/^Registrar N°/")
        exigir(p.inner_text(".correlativo .num") == "4", "tres pesadas a dedo, toca el N° 4")
        exigir(p.evaluate("pesoLote(loteActual())") == 126.5, "suman 126.50 kg")
        p.screenshot(path=SALIDA / "android-2-pesaje.png", full_page=True)

        print("\n[5] Sin señal: se corta la red y se vuelve a entrar")
        ctx.set_offline(True)
        p.reload(wait_until="load")
        exigir("Jornada del camal" in p.inner_text("h1"), "la app abre igual, sin red")
        exigir(p.evaluate("jornada.lotes.length") == 4, "los cuatro lotes siguen ahí")
        exigir(p.evaluate("jornada.operador") == "Nilthon Chit", "y el responsable también")
        p.screenshot(path=SALIDA / "android-3-sin-senal.png", full_page=True)

        print("\n[6] Sin señal se sigue trabajando y exportando")
        p.tap(".lote >> nth=0")
        p.fill("#pesoActual", "40,6")
        p.tap("text=/^Registrar N°/")
        exigir(p.evaluate("pesoLote(loteActual())") == 167.1, "se pesa sin red: 167.10 kg")
        p.tap("button[aria-label='Volver']")
        p.tap("text=Exportar: Excel, PDF y bitácora")
        with p.expect_download() as bajada:
            p.tap("text=Descargar Excel (.xlsx)")
        libro = SALIDA / bajada.value.suggested_filename
        bajada.value.save_as(libro)
        with p.expect_download() as bajada:
            p.tap("text=Descargar el acta en PDF")
        acta = SALIDA / bajada.value.suggested_filename
        bajada.value.save_as(acta)
        exigir(libro.stat().st_size > 3000, f"el Excel baja sin señal ({libro.stat().st_size} bytes)")
        exigir(acta.stat().st_size > 2000, f"y el acta también ({acta.stat().st_size} bytes)")
        p.screenshot(path=SALIDA / "android-4-exportar.png", full_page=True)

        print("\n[7] Nada se sale de la pantalla del teléfono")
        ctx.set_offline(False)
        for destino, nombre in [("jornada", "jornada"), ("exportar", "exportar"),
                                ("bitacora", "bitácora")]:
            p.evaluate(f"ir('{destino}')")
            desborde = p.evaluate(
                "document.documentElement.scrollWidth - document.documentElement.clientWidth")
            exigir(desborde <= 0, f"la pantalla de {nombre} no se va de ancho ({desborde} px)")

        print("\n[8] Instalar como aplicación, sin APK")
        # Chrome dispara `beforeinstallprompt` cuando la app es instalable, pero
        # sólo lo hace de verdad con un usuario que ya interactuó con el sitio.
        # Se fabrica el evento con un `prompt` que apunta si lo llamaron.
        p.evaluate("ir('jornada')")
        p.evaluate("localStorage.removeItem('camal.no-ofrecer-instalar')")
        p.evaluate("""() => {
          const e = new Event('beforeinstallprompt');
          e.prompt = () => { window.__pidioInstalar = true; };
          e.userChoice = Promise.resolve({ outcome: 'accepted' });
          window.dispatchEvent(e);
        }""")
        exigir(p.locator("text=Instalar la app").count() == 1,
               "cuando Chrome la da por instalable, sale el botón de instalar")
        p.tap("text=Instalar la app")
        exigir(p.evaluate("window.__pidioInstalar === true"),
               "y tocarlo abre el diálogo de instalación de Chrome")
        p.wait_for_selector("text=Ya está en tu pantalla de inicio")
        exigir(True, "aceptado, la tarjeta dice que ya está instalada")
        p.screenshot(path=SALIDA / "android-5-instalada.png", full_page=True)

        ctx.close()

        print("\n[9] Dentro de WhatsApp: salir a Chrome")
        whatsapp = ANDROID.replace("Mobile Safari/537.36",
                                   "Mobile Safari/537.36 WhatsApp/2.24.1").replace(
                                   "Pixel 6)", "Pixel 6; wv)")
        ctx = nav.new_context(viewport={"width": 393, "height": 851}, is_mobile=True,
                              has_touch=True, user_agent=whatsapp, locale="es-PE")
        p = ctx.new_page()
        p.on("pageerror", lambda e: errores.append(str(e)))
        p.goto(RAIZ, wait_until="load")
        chrome = p.locator("text=Abrir en Chrome")
        exigir(chrome.count() == 1,
               "el navegador de WhatsApp no instala: la app lo dice y ofrece salir")
        destino = chrome.get_attribute("href") or ""
        exigir(destino.startswith("intent://") and "package=com.android.chrome" in destino,
               "con un intent que salta del WebView a Chrome")
        p.screenshot(path=SALIDA / "android-6-whatsapp.png", full_page=True)

        p.goto(RAIZ + "instalar.html", wait_until="load")
        exigir(p.locator("#interno").is_visible(),
               "la página de instalar también lo detecta")
        ctx.close()

        print("\n[10] La página de instalar da el APK del camal, no el de otra app")
        ctx = nav.new_context(viewport={"width": 393, "height": 851}, is_mobile=True,
                              has_touch=True, user_agent=ANDROID, locale="es-PE")
        p = ctx.new_page()
        p.on("pageerror", lambda e: errores.append(str(e)))

        # En el mismo repositorio publican dos apps. La de RD RENTAL sale con
        # etiquetas android-vN y es la más reciente aquí a propósito: si el
        # filtro fallara, el operario del camal se instalaría las actas.
        publicaciones = [
            {"tag_name": "android-v12", "name": "Aplicación de Android · 1.12", "draft": False,
             "assets": [{"name": "rd-rental-actas.apk", "size": 500000,
                         "browser_download_url": "https://ejemplo/android-v12/rd-rental-actas.apk"}]},
            {"tag_name": "camal-v9", "name": "Camal · Pesaje por lotes 3.9", "draft": False,
             "assets": [{"name": "camal-pesaje.apk", "size": 452477,
                         "browser_download_url": "https://ejemplo/camal-v9/camal-pesaje.apk"}]},
            {"tag_name": "camal-v10", "name": "Camal · Pesaje por lotes 3.10", "draft": False,
             "assets": [{"name": "camal-pesaje.apk", "size": 452600,
                         "browser_download_url": "https://ejemplo/camal-v10/camal-pesaje.apk"}]},
        ]
        p.route("https://api.github.com/**", lambda ruta: ruta.fulfill(
            status=200, content_type="application/json", body=json.dumps(publicaciones)))
        p.goto(RAIZ + "instalar.html", wait_until="load")
        p.wait_for_function("!document.getElementById('versionApk').textContent.startsWith('Buscando')")
        enlace = p.get_attribute("#apk", "href")
        exigir(enlace == "https://ejemplo/camal-v10/camal-pesaje.apk",
               f"elige el camal más reciente, camal-v10 —no camal-v9 por orden de texto—: {enlace}")
        exigir("rd-rental" not in enlace, "y nunca el APK de RD RENTAL, aunque sea más nuevo")
        exigir("3.10" in p.inner_text("#versionApk"), "y dice qué versión es")
        exigir(not p.locator("#interno").is_visible(), "fuera de WhatsApp no pide salir a Chrome")
        p.screenshot(path=SALIDA / "android-7-instalar.png", full_page=True)

        print("\n[11] Sin conexión con GitHub, el botón no se queda muerto")
        p.unroute("https://api.github.com/**")
        p.route("https://api.github.com/**", lambda ruta: ruta.abort())
        p.goto(RAIZ + "instalar.html", wait_until="load")
        p.wait_for_function("!document.getElementById('versionApk').textContent.startsWith('Buscando')")
        exigir(p.get_attribute("#apk", "href") == "https://github.com/nilthonnn/nefer/releases",
               "lleva a la lista de versiones, que siempre responde")
        exigir("lista de versiones" in p.inner_text("#versionApk"), "y lo explica")

        print("\n[12] La página de instalar no viaja dentro del APK")
        gradle = (PUBLICADO.parents[1] / "movil" / "android" / "app" / "build.gradle").read_text(encoding="utf-8")
        exigir("exclude 'instalar.html'" in gradle,
               "Gradle la excluye: dentro, sin permiso de Internet, sólo sabría fallar")

        ctx.close()
        nav.close()
    servidor.shutdown()

print("\n--- errores de página:", errores or "ninguno")
print("--- fallos:", fallos or "ninguno")
sys.exit(1 if (errores or fallos) else 0)
