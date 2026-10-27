"""Infografías animadas con Remotion (proyecto en ``documental/remotion``).

Cada tipo de visual propio se corresponde con una composición de React. Los
datos de la escena viajan como props JSON y la duración la impone la voz.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from ..config import Config
from ..errores import ErrorConfiguracion, ErrorRender, ErrorVisualTransitorio
from ..modelos import ClipEscena, Escena
from ..multimedia.ffmpeg import ejecutar
from ..reintentos import reintentar
from .base import normalizar_video

COMPOSICIONES = {
    "titular": "Titular",
    "cifra": "Cifra",
    "linea_tiempo": "LineaTiempo",
    "comparativa": "Comparativa",
    "final": "PantallaFinal",
}

# Valores por defecto para que una escena con datos mínimos no rompa el render.
_DEFECTOS = {
    "titular": {"antetitulo": ""},
    "cifra": {"prefijo": "", "sufijo": "", "decimales": 0, "fuente": ""},
    "comparativa": {"unidad": "", "fuente": ""},
    "final": {"mensaje": "", "canal": ""},
}


class VisualRemotion:
    nombre = "remotion"

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._dir = config.remotion_dir
        if shutil.which("npx") is None:
            raise ErrorConfiguracion("Remotion necesita Node.js (npx no está en el PATH)")
        if not (self._dir / "node_modules" / "remotion").is_dir():
            raise ErrorConfiguracion(f"Remotion no está instalado: corre `npm install` en {self._dir}")

    def puede(self, escena: Escena) -> bool:
        return escena.visual.tipo in COMPOSICIONES

    def generar(self, escena: Escena, duracion: float, destino: Path) -> ClipEscena:
        tipo = escena.visual.tipo
        props = {**_DEFECTOS.get(tipo, {}), **escena.visual.datos, "duracionSegundos": round(duracion, 3)}
        if tipo == "final":
            props["mensaje"] = props["mensaje"] or self._cfg.canal.llamado_final
            props["canal"] = props["canal"] or self._cfg.canal.nombre
        ruta_props = destino.with_suffix(".props.json")
        ruta_props.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
        crudo = destino.with_suffix(".remotion.mp4")

        comando = [
            "npx", "--no-install", "remotion", "render", "src/index.ts", COMPOSICIONES[tipo], str(crudo),
            f"--props={ruta_props}", "--log=error", f"--concurrency={max(1, (os.cpu_count() or 2) // 2)}",
        ]
        if self._cfg.secretos.remotion_browser:
            comando.append(f"--browser-executable={self._cfg.secretos.remotion_browser}")

        def render() -> None:
            # El navegador headless a veces muere por memoria: eso sí merece reintento.
            try:
                ejecutar(comando, f"remotion {COMPOSICIONES[tipo]}", timeout=1800, cwd=self._dir)
            except ErrorRender as e:
                raise ErrorVisualTransitorio(str(e)) from e

        reintentar(render, descripcion=f"Remotion {escena.id}", intentos=2)
        normalizar_video(crudo, destino, duracion, self._cfg)
        crudo.unlink(missing_ok=True)
        return ClipEscena(ruta=destino, propio=True)

