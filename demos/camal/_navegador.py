"""De dónde sale el Chromium con el que se conduce el demo.

Mismo criterio que `tests/navegador.py`: si el contenedor trae un Chromium
preinstalado se usa ese, y si no se deja elegir a Playwright, que sabe dónde
dejó los suyos `playwright install`. Se resuelve aquí y en un solo sitio
porque de esto depende que el demo se pueda abrir.
"""

from __future__ import annotations

import os
from pathlib import Path

FORMAS = (
    "chromium-*/chrome-linux*/chrome",
    "chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell",
)


def ruta_del_navegador() -> str | None:
    """Ruta explícita al Chromium, o `None` para que decida Playwright."""
    explicita = os.environ.get("CHROMIUM")
    if explicita:
        return explicita
    almacen = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")) or None
    if almacen is None or not almacen.is_dir():
        return None
    for forma in FORMAS:
        for candidato in sorted(almacen.glob(forma), reverse=True):
            if candidato.exists():
                return str(candidato)
    return None
