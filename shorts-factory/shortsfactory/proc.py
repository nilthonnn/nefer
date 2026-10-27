"""Ejecución de procesos externos que nunca falla en silencio."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .errors import ErrorRender
from .logs import obtener

log = obtener("proc")


def ejecutar(comando: list[str], descripcion: str, timeout: float = 1800, cwd: Path | None = None) -> str:
    log.debug("%s: %s", descripcion, " ".join(comando))
    try:
        p = subprocess.run(comando, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except FileNotFoundError as e:
        raise ErrorRender(f"{descripcion}: no se encontró '{comando[0]}'", comando) from e
    except subprocess.TimeoutExpired as e:
        raise ErrorRender(f"{descripcion}: superó {timeout:.0f} s", comando) from e
    if p.returncode != 0:
        raise ErrorRender(f"{descripcion}: código {p.returncode}", comando, p.stderr or p.stdout)
    return p.stdout


def ffmpeg(args: list[str], descripcion: str, timeout: float = 1800) -> None:
    ejecutar(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "error", *args], descripcion, timeout)


def sondear(ruta: Path) -> dict:
    """ffprobe en JSON: formato y pistas."""
    if not ruta.is_file() or ruta.stat().st_size == 0:
        raise ErrorRender(f"no existe o está vacío: {ruta}")
    salida = ejecutar(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate",
         "-of", "json", str(ruta)],
        f"ffprobe {ruta.name}", timeout=120,
    )
    return json.loads(salida or "{}")


def duracion(ruta: Path) -> float:
    try:
        return float(sondear(ruta).get("format", {}).get("duration", 0.0))
    except (TypeError, ValueError):
        return 0.0
