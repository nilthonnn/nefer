"""De donde sale el Chromium con el que se conducen las pruebas de la app.

Se resuelve una sola vez y en un solo sitio, porque de esto depende que las
pruebas de navegador corran o se salten. Una ruta que no existe las salta sin
ruido, y una suite que se salta sola pasa igual: es la peor forma de fallar.
"""

from __future__ import annotations

import os
from pathlib import Path

# El contenedor de desarrollo trae el navegador preinstalado aqui.
CONTENEDOR = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def _almacen_de_playwright() -> Path:
    """Donde deja `playwright install` los navegadores que descarga."""
    ruta = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if ruta:
        return Path(ruta)
    return Path.home() / ".cache" / "ms-playwright"


def _resolver() -> tuple[str | None, bool]:
    """(ruta explicita o None, hay navegador).

    `None` no significa que no lo haya: significa que se deja elegir a
    Playwright, que es lo que hace falta cuando el navegador lo instalo
    `playwright install chromium` en su propio almacen. Si ahi hay un
    Chromium de otra version, `launch()` falla y lo dice, que es justo lo
    que se quiere: mejor un error que una prueba saltada en silencio.
    """
    for ruta in (os.environ.get("NEFER_CHROMIUM"), CONTENEDOR):
        if ruta and Path(ruta).exists():
            return ruta, True

    almacen = _almacen_de_playwright()
    hay = any(almacen.glob("chromium*/chrome-linux/chrome")) if almacen.is_dir() else False
    return None, hay


CHROME, HAY_CHROMIUM = _resolver()
