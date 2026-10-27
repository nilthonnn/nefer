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
    medido = _lufs(video) if a is not None else None
    if medido is not None and abs(medido - lufs) > 1.5:
        problemas.append(f"sonoridad {medido:.1f} LUFS (objetivo {lufs:.0f})")
    if problemas:
        raise ErrorContenido("QA del video: " + "; ".join(problemas))
    return {"duracion": round(dur, 3), "lufs": medido}


def _lufs(video: Path) -> float | None:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(video), "-af", "ebur128=framelog=quiet",
                        "-f", "null", "-"], capture_output=True, text=True, timeout=600)
    m = re.findall(r"I:\s+(-?\d+(?:\.\d+)?) LUFS", p.stderr)
    return float(m[-1]) if m else None
