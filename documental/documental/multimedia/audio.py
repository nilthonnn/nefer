"""Pista de audio final: voz continua + música con ducking + sonoridad de YouTube.

- La voz de cada escena se rellena con silencio hasta la duración del tramo,
  así el audio y la línea de tiempo de video coinciden al milisegundo.
- La música baja sola cuando habla la voz (sidechain) y sube en los silencios.
- Normalización en dos pasadas a -14 LUFS: YouTube baja el volumen de lo que
  suena más fuerte, y lo que suena más bajo se percibe "pobre".
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from ..config import Config
from ..errores import ErrorRender
from ..multimedia.ffmpeg import ffmpeg, verificar
from ..registro import obtener

log = obtener("audio")
EXTENSIONES = (".mp3", ".wav", ".m4a", ".ogg", ".flac")


def unir_voz(segmentos: list[tuple[Path, float]], salida: Path) -> None:
    """Concatena (audio, duración_del_tramo); rellena o recorta cada uno a su tramo."""
    entradas: list[str] = []
    filtros: list[str] = []
    for i, (ruta, duracion) in enumerate(segmentos):
        entradas += ["-i", str(ruta)]
        filtros.append(
            f"[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=mono,"
            f"apad=whole_dur={duracion:.3f},atrim=duration={duracion:.3f}[a{i}]"
        )
    union = "".join(f"[a{i}]" for i in range(len(segmentos)))
    filtros.append(f"{union}concat=n={len(segmentos)}:v=0:a=1[voz]")
    ffmpeg([*entradas, "-filter_complex", ";".join(filtros), "-map", "[voz]", "-c:a", "pcm_s16le", str(salida)], "unir voz")
    verificar(salida, duracion=sum(d for _, d in segmentos), audio=True, tolerancia=0.1)


def elegir_musica(carpeta: Path, semilla: str) -> Path | None:
    """Elige una pista de forma estable por video (mismo guion → misma música)."""
    if not carpeta.is_dir():
        return None
    pistas = sorted(p for p in carpeta.iterdir() if p.suffix.lower() in EXTENSIONES)
    if not pistas:
        return None
    indice = int(hashlib.sha1(semilla.encode()).hexdigest(), 16) % len(pistas)
    return pistas[indice]


def creditos_musica(pista: Path | None) -> str:
    """Texto de atribución que acompaña a la pista (archivo .txt homónimo), si existe."""
    if pista is None:
        return ""
    txt = pista.with_suffix(".txt")
    return txt.read_text(encoding="utf-8").strip() if txt.is_file() else ""


def mezclar(voz: Path, musica: Path | None, salida: Path, duracion: float, cfg: Config) -> None:
    """Mezcla voz y música (opcional) y normaliza a la sonoridad configurada."""
    a = cfg.audio
    if musica is not None:
        desvanecer = max(0.0, duracion - 4)
        grafo = (
            "[0:a]aformat=channel_layouts=stereo,asplit=2[voz][llave];"
            f"[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,atrim=duration={duracion:.3f},"
            f"volume={a.musica_db}dB,afade=t=in:d=2,afade=t=out:st={desvanecer:.3f}:d=4[mus];"
            "[mus][llave]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=450[ducked];"
            "[voz][ducked]amix=inputs=2:normalize=0:duration=first[mezcla]"
        )
        entradas = ["-i", str(voz), "-stream_loop", "-1", "-i", str(musica)]
    else:
        grafo = "[0:a]aformat=channel_layouts=stereo[mezcla]"
        entradas = ["-i", str(voz)]

    previa = salida.with_suffix(".previa.wav")
    ffmpeg([*entradas, "-filter_complex", grafo, "-map", "[mezcla]", "-t", f"{duracion:.3f}", "-c:a", "pcm_s16le", str(previa)], "mezclar audio")
    normalizar_sonoridad(previa, salida, a.lufs, a.pico_db)
    previa.unlink(missing_ok=True)
    verificar(salida, duracion=duracion, audio=True, tolerancia=0.1)


def normalizar_sonoridad(entrada: Path, salida: Path, lufs: float, pico: float) -> None:
    """loudnorm en dos pasadas: medir y luego corregir con los valores medidos."""
    filtro = f"loudnorm=I={lufs}:TP={pico}:LRA=11"
    comando = ["ffmpeg", "-hide_banner", "-nostdin", "-i", str(entrada), "-af", f"{filtro}:print_format=json", "-f", "null", "-"]
    # loudnorm escribe su medición en stderr, por eso no se usa ejecutar() aquí.
    proceso = subprocess.run(comando, capture_output=True, text=True, timeout=3600)
    if proceso.returncode != 0:
        raise ErrorRender("medir sonoridad: ffmpeg falló", comando, proceso.stderr)
    bloque = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", proceso.stderr)
    medida = json.loads(bloque.group(0)) if bloque else {}
    claves = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
    if all(k in medida for k in claves) and medida["input_i"] != "-inf":
        filtro += (
            f":measured_I={medida['input_i']}:measured_TP={medida['input_tp']}:measured_LRA={medida['input_lra']}"
            f":measured_thresh={medida['input_thresh']}:offset={medida['target_offset']}:linear=true"
        )
        log.info("sonoridad medida %s LUFS → objetivo %s LUFS", medida["input_i"], lufs)
    else:
        log.warning("no se pudo medir la sonoridad (¿audio en silencio?); uso loudnorm de una pasada")
    ffmpeg(["-i", str(entrada), "-af", filtro, "-ar", "48000", "-c:a", "pcm_s16le", str(salida)], "normalizar sonoridad")
