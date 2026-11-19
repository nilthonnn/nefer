"""Control de calidad del MP4 antes de publicar: nada sale sin pasar por aquí."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .errors import ErrorContenido
from .proc import sondear


def revisar(video: Path, duracion_max: float, fps: int, lufs: float) -> dict:
    info = sondear(video)
    problemas: list[str] = []
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    dur = float(info.get("format", {}).get("duration", 0) or 0)
    if v is None:
        problemas.append("sin pista de video")
    else:
        if (v.get("width"), v.get("height")) != (1080, 1920):
            problemas.append(f"resolución {v.get('width')}x{v.get('height')} (se espera 1080x1920)")
        num, _, den = str(v.get("r_frame_rate", "0/1")).partition("/")
        if den and abs(float(num) / float(den) - fps) > 0.5:
            problemas.append(f"{v.get('r_frame_rate')} fps (se esperan {fps})")
    if a is None:
        problemas.append("sin pista de audio")
    if not 5 <= dur <= duracion_max + 0.1:
        problemas.append(f"dura {dur:.2f} s (máximo {duracion_max:.0f} s)")
    medido, pico = _sonoridad(video) if a is not None else (None, None)
    if medido is not None and abs(medido - lufs) > 1.5:
        problemas.append(f"sonoridad {medido:.1f} LUFS (objetivo {lufs:.0f})")
    # El objetivo es -1 dBTP; la codificación AAC puede subir el pico unas décimas.
    if pico is not None and pico > PICO_MAXIMO + 0.5:
        problemas.append(f"pico real {pico:.1f} dBTP (máximo {PICO_MAXIMO:.0f} dBTP)")
    if problemas:
        raise ErrorContenido("QA del video: " + "; ".join(problemas))
    return {"duracion": round(dur, 3), "lufs": medido, "pico_dbtp": pico}


PICO_MAXIMO = -1.0


def _sonoridad(video: Path) -> tuple[float | None, float | None]:
    """(sonoridad integrada en LUFS, pico real en dBTP) con el medidor EBU R128."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(video), "-af", "ebur128=framelog=quiet:peak=true",
                        "-f", "null", "-"], capture_output=True, text=True, timeout=600)
    integrada = re.findall(r"I:\s+(-?\d+(?:\.\d+)?) LUFS", p.stderr)
    pico = re.findall(r"Peak:\s+(-?(?:\d+(?:\.\d+)?|inf)) dBFS", p.stderr)
    lufs = float(integrada[-1]) if integrada else None
    tp = float(pico[-1]) if pico and pico[-1] not in ("-inf", "inf") else None
    return lufs, tp
