"""De donde sale el Chromium con el que se conducen las pruebas de la app.

Se resuelve una sola vez y en un solo sitio, porque de esto depende que las
pruebas de navegador corran o se salten. Una ruta que no existe las salta sin
ruido, y una suite que se salta sola pasa igual: es la peor forma de fallar.

Lo de aqui decide si se saltan, y para eso basta con mirar el disco. Lo que de
verdad prueba que hay navegador es abrirlo, y eso lo hace la comprobacion
automatica antes de correr la suite: ver `.github/workflows/pruebas.yml`.
"""

from __future__ import annotations

import os
from pathlib import Path

# El contenedor de desarrollo trae el navegador preinstalado aqui.
CONTENEDOR = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

# Como queda un Chromium recien instalado por `playwright install`. Son dos
# binarios: el completo y el que Playwright usa sin ventana. Los comodines
# cubren las formas que ha tenido la carpeta —`chrome-linux` antes,
# `chrome-linux64` desde que empaqueta Chrome for Testing—, y basta con
# encontrar uno para saber que ahi hay un navegador instalado.
FORMAS = (
    "chromium-*/chrome-linux*/chrome",
    "chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell",
)


def _almacen_de_playwright() -> Path:
    """Donde deja `playwright install` los navegadores que descarga."""
    ruta = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    return Path(ruta) if ruta else Path.home() / ".cache" / "ms-playwright"


def _lo_que_declara_playwright() -> bool:
    """Ultimo recurso: preguntarselo a Playwright.

    Cuesta arrancar y parar su proceso auxiliar, y al pararlo escupe un aviso
    de asyncio por la salida de error, asi que solo se llega aqui si la forma
    conocida de la carpeta no aparecio: es decir, si Playwright volvio a
    cambiarla. Vale la pena el ruido a cambio de no saltarse la suite.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            return Path(pw.chromium.executable_path).exists()
    except Exception:
        return False


def _resolver() -> tuple[str | None, bool]:
    """(ruta explicita o None, hay navegador).

    `None` no significa que no lo haya: significa que se deja elegir a
    Playwright, que es lo que hace falta cuando el navegador lo instalo
    `playwright install chromium` en su propio almacen.
    """
    for ruta in (os.environ.get("NEFER_CHROMIUM"), CONTENEDOR):
        if ruta and Path(ruta).exists():
            return ruta, True

    almacen = _almacen_de_playwright()
    if almacen.is_dir() and any(any(almacen.glob(f)) for f in FORMAS):
        return None, True
    return None, _lo_que_declara_playwright()


CHROME, HAY_CHROMIUM = _resolver()
