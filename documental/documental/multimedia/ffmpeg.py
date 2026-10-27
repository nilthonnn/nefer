"""Envoltorio de ffmpeg/ffprobe que NUNCA falla en silencio.

Cada salida se comprueba dos veces: por el código de retorno y midiendo el
archivo resultante con ffprobe (existe, tiene las pistas esperadas, dura lo
que debe). Un MP4 de 0 bytes o con 2 s en vez de 2 min se detecta aquí, no
cuando el video ya está publicado.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..errores import ErrorRender
from ..registro import obtener

log = obtener("ffmpeg")


def ejecutar(comando: list[str], descripcion: str, timeout: float = 3600, cwd: Path | None = None) -> str:
    """Ejecuta un comando y devuelve stdout; lanza ErrorRender con stderr si falla."""
    log.debug("%s: %s", descripcion, " ".join(comando))
    try:
        proceso = subprocess.run(comando, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except FileNotFoundError as e:
        raise ErrorRender(f"{descripcion}: no se encontró '{comando[0]}'", comando) from e
    except subprocess.TimeoutExpired as e:
        raise ErrorRender(f"{descripcion}: superó {timeout:.0f} s", comando, str(e.stderr or "")) from e
    if proceso.returncode != 0:
        raise ErrorRender(f"{descripcion}: código {proceso.returncode}", comando, proceso.stderr)
    return proceso.stdout


def ffmpeg(argumentos: list[str], descripcion: str, timeout: float = 3600, cwd: Path | None = None) -> str:
    """Ejecuta ffmpeg sin banner ni preguntas; lanza ErrorRender si falla."""
    return ejecutar(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-loglevel", "error", *argumentos], descripcion, timeout, cwd)


@dataclass(frozen=True)
class Medida:
    duracion: float
    video: bool
    audio: bool
    ancho: int = 0
    alto: int = 0


def medir(ruta: Path) -> Medida:
    """Duración y pistas de un archivo multimedia."""
    if not ruta.is_file() or ruta.stat().st_size == 0:
        raise ErrorRender(f"El archivo no existe o está vacío: {ruta}")
    salida = ejecutar(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(ruta)],
        f"medir {ruta.name}",
        timeout=120,
    )
    datos = json.loads(salida or "{}")
    streams = datos.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    try:
        duracion = float(datos.get("format", {}).get("duration", 0))
    except (TypeError, ValueError):
        duracion = 0.0
    return Medida(
        duracion=duracion,
        video=video is not None,
        audio=any(s.get("codec_type") == "audio" for s in streams),
        ancho=int(video.get("width", 0)) if video else 0,
        alto=int(video.get("height", 0)) if video else 0,
    )


def verificar(
    ruta: Path,
    *,
    duracion: float | None = None,
    tolerancia: float = 0.25,
    video: bool | None = None,
    audio: bool | None = None,
) -> Medida:
    """Comprueba que el archivo cumple lo esperado; lanza ErrorRender si no."""
    m = medir(ruta)
    problemas = []
    if duracion is not None and abs(m.duracion - duracion) > tolerancia:
        problemas.append(f"dura {m.duracion:.2f} s y se esperaban {duracion:.2f} s")
    if video is not None and m.video != video:
        problemas.append("falta la pista de video" if video else "tiene video y no debería")
    if audio is not None and m.audio != audio:
        problemas.append("falta la pista de audio" if audio else "tiene audio y no debería")
    if problemas:
        raise ErrorRender(f"{ruta.name}: " + "; ".join(problemas))
    return m


def es_valido(ruta: Path, **kwargs) -> bool:
    """Igual que verificar() pero devuelve bool (para reanudar trabajos)."""
    try:
        verificar(ruta, **kwargs)
        return True
    except ErrorRender:
        return False
