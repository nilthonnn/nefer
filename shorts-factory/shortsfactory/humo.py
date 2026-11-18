"""Render de humo: ¿compila Remotion y pasan las props por Zod?

Para los PR: renderiza solo los primeros fotogramas (150 = 5 s a 30 fps) de
un Short de plantilla con audio mudo. No usa LLM, voz, red ni claves, y
tarda segundos. Lo que comprueba:

- que ``remotion/src`` compila y se empaqueta;
- que las props que arma Python cumplen ``schema.ts`` (Remotion las valida
  con Zod antes del primer fotograma);
- que el MP4 sale con el tamaño y el número de fotogramas esperados.
"""

from __future__ import annotations

import random
from pathlib import Path

from .errors import ErrorRender
from .logs import obtener
from .models import Serie, Tendencia
from .proc import ffmpeg, sondear
from .scripts.generador import plantilla
from .settings import RAIZ, Settings
from .visuals import provisional, render, variacion

log = obtener("humo")
SERIE_DE_PRUEBA = RAIZ / "ejemplos" / "serie-sintetica.json"


def ejecutar(cfg: Settings, salida: Path, fotogramas: int = 150, semilla: int = 7) -> Path:
    if fotogramas < 1:
        raise ValueError("fotogramas debe ser ≥ 1")
    run_id = "humo"
    serie = Serie.model_validate_json(SERIE_DE_PRUEBA.read_text(encoding="utf-8"))
    guion = plantilla(Tendencia(titulo="Prueba de humo", fuente="manual"), serie, random.Random(semilla))
    v = variacion.elegir(semilla, [])

    salida.parent.mkdir(parents=True, exist_ok=True)
    audio = salida.with_name("humo.wav")
    n = provisional.narracion_estimada(guion, audio)
    ffmpeg(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{n.duracion:.3f}", "-c:a", "pcm_s16le", str(audio)],
           "audio mudo de humo")
    datos = render.props(run_id, guion, n, serie, v, render.segmentos(guion, n, {}), cfg.fps)
    ultimo = min(fotogramas, datos["duracionFrames"]) - 1

    render.preparar_public(cfg, run_id, [audio])
    try:
        render.renderizar(cfg, datos, salida, frames=(0, ultimo))
    finally:
        render.limpiar_public(cfg, run_id)

    info = sondear(salida)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    if video is None:
        raise ErrorRender(f"el render de humo no tiene pista de video: {salida}")
    if (int(video.get("width", 0)), int(video.get("height", 0))) != (1080, 1920):
        raise ErrorRender(f"el render de humo salió de {video.get('width')}×{video.get('height')}, se esperaba 1080×1920")
    esperado = (ultimo + 1) / cfg.fps
    real = float(info.get("format", {}).get("duration", 0.0))
    if abs(real - esperado) > 2 / cfg.fps + 0.05:
        raise ErrorRender(f"el render de humo dura {real:.2f} s; se esperaban {esperado:.2f} s ({ultimo + 1} fotogramas)")
    log.info("humo ok: %d fotogramas, %.2f s → %s", ultimo + 1, real, salida)
    return salida
