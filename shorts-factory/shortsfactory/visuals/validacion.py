"""Validación de props contra el Zod de ``remotion/src/schema.ts`` desde Python.

El contrato Python↔TypeScript es uno solo: el esquema Zod. En lugar de
duplicarlo en Python, se ejecuta el mismo esquema con node
(``src/lib/validar-props.ts``, sin navegador, ~0,3 s). Lo usa la etapa
GUION para reparar el JSON del LLM antes de pagar la voz y el render.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from ..errors import ErrorConfiguracion, ErrorRender
from ..proc import ejecutar
from ..settings import Settings

SCRIPT = Path("src") / "lib" / "validar-props.ts"


def disponible(cfg: Settings) -> bool:
    return shutil.which("node") is not None and (cfg.remotion_dir / "node_modules" / "zod").is_dir()


def validar(cfg: Settings, datos: dict) -> list[str]:
    """Problemas de Zod como «ruta: mensaje». Lista vacía = props válidas."""
    if not disponible(cfg):
        raise ErrorConfiguracion(f"Para validar las props hace falta node y `npm ci` en {cfg.remotion_dir}")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    try:
        salida = ejecutar(["node", "--experimental-strip-types", "--no-warnings", str(SCRIPT), f.name],
                          "validar props (Zod)", timeout=60, cwd=cfg.remotion_dir)
    finally:
        Path(f.name).unlink(missing_ok=True)
    try:
        resultado = json.loads(salida.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as e:
        raise ErrorRender(f"el validador de props devolvió algo ilegible: {salida[:200]!r}") from e
    return [f"{p['ruta'] or '(raíz)'}: {p['mensaje']}" for p in resultado.get("problemas", [])]
