"""Narración completa: frases + pausas estratégicas + música + sonoridad.

- Cada frase se sintetiza por separado: el límite de cada frase es exacto
  (el visual cambia justo cuando cambia la idea) y las pausas se controlan
  aquí, no las decide el motor.
- La velocidad y la pausa tras el gancho vienen de la ``Variacion`` del run:
  dos Shorts del canal nunca tienen exactamente el mismo ritmo.
- Si la voz se pasa de la duración máxima, se acelera hasta un 12 % (sin
  cambiar el tono); si aun así no cabe, el guion es demasiado largo.
- La música (opcional) se atenúa bajo la voz y se normaliza todo a -14 LUFS.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from ..errors import ErrorContenido, ErrorRender
from ..logs import obtener
from ..models import Guion, Narracion, PalabraT, Variacion
from ..proc import duracion, ffmpeg
from ..settings import Settings
from .motores import MotorVoz

log = obtener("audio")
ACELERACION_MAXIMA = 1.12
COLA_LOOP = 0.15  # sin silencio final largo: el loop debe sentirse continuo


def narrar(guion: Guion, motor: MotorVoz, variacion: Variacion, cfg: Settings, carpeta: Path) -> Narracion:
    carpeta.mkdir(parents=True, exist_ok=True)
    piezas: list[tuple[Path, float]] = []
    palabras: list[PalabraT] = []
    frases: list[tuple[float, float]] = []
    exacta = True
    t = 0.0
    for i, frase in enumerate(guion.frases):
        wav, d, rel, ex = motor.sintetizar(frase.texto, carpeta / f"frase{i:02d}", variacion.velocidad_voz)
        exacta &= ex
        enfasis = {_norm(p) for p in frase.enfasis}
        palabras += [p.model_copy(update={"inicio": round(p.inicio + t, 3), "fin": round(p.fin + t, 3),
                                          "enfasis": _norm(p.texto) in enfasis}) for p in rel]
        pausa = frase.pausa_despues + (variacion.pausa_gancho if i == 0 else 0.0)
        if i == len(guion.frases) - 1:
            pausa = COLA_LOOP
        frases.append((round(t, 3), round(t + d, 3)))
        piezas.append((wav, d + pausa))
        t += d + pausa

    voz = carpeta / "voz.wav"
    _concatenar(piezas, voz)
    total = duracion(voz)

    factor = 1.0
    if total > cfg.duracion_max:
        factor = total / cfg.duracion_max
        if factor > ACELERACION_MAXIMA:
            raise ErrorContenido(f"La voz dura {total:.1f} s; ni acelerando un {ACELERACION_MAXIMA - 1:.0%} cabe en "
                                 f"{cfg.duracion_max:.0f} s. Acorta el guion.")
        log.info("voz de %.2f s → acelero x%.3f para caber en %.0f s", total, factor, cfg.duracion_max)
        acelerada = carpeta / "voz_rapida.wav"
        ffmpeg(["-i", str(voz), "-af", f"atempo={factor:.4f}", str(acelerada)], "acelerar voz")
        voz, total = acelerada, duracion(acelerada)
        palabras = [p.model_copy(update={"inicio": round(p.inicio / factor, 3), "fin": round(p.fin / factor, 3)}) for p in palabras]
        frases = [(round(a / factor, 3), round(b / factor, 3)) for a, b in frases]

    final = carpeta / "narracion.wav"
    _mezclar(voz, _musica(cfg.musica_dir, variacion.semilla), final, total, cfg.lufs)
    return Narracion(audio=final, duracion=duracion(final), palabras=palabras, frases=frases,
                     motor=motor.nombre, exacta=exacta)


def _norm(t: str) -> str:
    return re.sub(r"[^\w]", "", t.lower())


def _concatenar(piezas: list[tuple[Path, float]], salida: Path) -> None:
    entradas, filtros = [], []
    for i, (ruta, d) in enumerate(piezas):
        entradas += ["-i", str(ruta)]
        filtros.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=mono,apad=whole_dur={d:.3f},atrim=duration={d:.3f}[a{i}]")
    filtros.append("".join(f"[a{i}]" for i in range(len(piezas))) + f"concat=n={len(piezas)}:v=0:a=1[voz]")
    ffmpeg([*entradas, "-filter_complex", ";".join(filtros), "-map", "[voz]", "-c:a", "pcm_s16le", str(salida)], "unir frases")


def _musica(carpeta: Path, semilla: int) -> Path | None:
    if not carpeta.is_dir():
        return None
    pistas = sorted(p for p in carpeta.iterdir() if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg"))
    return pistas[semilla % len(pistas)] if pistas else None


def creditos_musica(cfg: Settings, semilla: int) -> str:
    pista = _musica(cfg.musica_dir, semilla)
    txt = pista.with_suffix(".txt") if pista else None
    return txt.read_text(encoding="utf-8").strip() if txt and txt.is_file() else ""


def _mezclar(voz: Path, musica: Path | None, salida: Path, total: float, lufs: float) -> None:
    previa = salida.with_suffix(".previa.wav")
    if musica is None:
        ffmpeg(["-i", str(voz), "-ac", "2", str(previa)], "voz estéreo")
    else:
        grafo = (
            "[0:a]aformat=channel_layouts=stereo,asplit=2[v][k];"
            f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=duration={total:.3f},volume=-18dB[m];"
            "[m][k]sidechaincompress=threshold=0.02:ratio=10:attack=10:release=300[d];"
            "[v][d]amix=inputs=2:normalize=0:duration=first[o]"
        )
        ffmpeg(["-i", str(voz), "-stream_loop", "-1", "-i", str(musica), "-filter_complex", grafo, "-map", "[o]",
                "-t", f"{total:.3f}", str(previa)], "mezclar música")
    _loudnorm(previa, salida, lufs)
    previa.unlink(missing_ok=True)


def _loudnorm(entrada: Path, salida: Path, lufs: float) -> None:
    filtro = f"loudnorm=I={lufs}:TP=-1.0:LRA=11"
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-i", str(entrada), "-af", filtro + ":print_format=json", "-f", "null", "-"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise ErrorRender("medir sonoridad", cmd, p.stderr)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr)
    datos = json.loads(m.group(0)) if m else {}
    if datos.get("input_i") not in (None, "-inf"):
        filtro += (f":measured_I={datos['input_i']}:measured_TP={datos['input_tp']}:measured_LRA={datos['input_lra']}"
                   f":measured_thresh={datos['input_thresh']}:offset={datos['target_offset']}:linear=true")
    ffmpeg(["-i", str(entrada), "-af", filtro, "-ar", "48000", "-c:a", "pcm_s16le", str(salida)], "normalizar sonoridad")

