"""Montaje: encadena los clips con transiciones y produce el MP4 final.

Sincronía con la voz
--------------------
La escena *i* empieza en ``inicio_i = Σ tramo_j (j < i)``. Su clip dura
``tramo_i + T`` (T = transición) salvo el último, y el fundido hacia la
siguiente comienza exactamente en ``inicio_{i+1}``. Así la transición nunca
desplaza la imagen respecto de la voz y el video dura ``Σ tramo``.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from .ffmpeg import ffmpeg, verificar


def encadenar(clips: list[Path], tramos: list[float], salida: Path, cfg: Config) -> None:
    """Une los clips de escena (ya normalizados) con fundidos ``xfade``."""
    if len(clips) != len(tramos) or not clips:
        raise ValueError("clips y tramos deben tener el mismo largo (y no estar vacíos)")
    T = cfg.video.transicion_segundos
    total = sum(tramos)
    if len(clips) == 1 or T <= 0:
        lista = salida.with_suffix(".lista.txt")
        lista.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
        ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(salida)], "concatenar escenas")
        lista.unlink(missing_ok=True)
    else:
        entradas: list[str] = []
        for c in clips:
            entradas += ["-i", str(c)]
        filtros = []
        anterior = "0:v"
        inicio = 0.0
        for k in range(1, len(clips)):
            inicio += tramos[k - 1]
            etiqueta = f"x{k}"
            filtros.append(
                f"[{anterior}][{k}:v]xfade=transition={cfg.video.transicion}:duration={T}:offset={inicio:.3f}[{etiqueta}]"
            )
            anterior = etiqueta
        ffmpeg(
            [*entradas, "-filter_complex", ";".join(filtros), "-map", f"[{anterior}]",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", str(salida)],
            f"encadenar {len(clips)} escenas",
        )
    verificar(salida, duracion=total, video=True, tolerancia=0.2)


def exportar(video: Path, audio: Path, salida: Path, cfg: Config, subtitulos_ass: Path | None = None, marca: str = "") -> None:
    """Codificación final con los parámetros recomendados por YouTube.

    H.264 High, yuv420p, GOP cerrado de medio segundo de cuadros, AAC 48 kHz
    a 384 kbps estéreo y ``faststart`` para que el procesamiento empiece antes.
    """
    v = cfg.video
    filtros = []
    carpeta = None
    if subtitulos_ass is not None:
        # Ruta relativa + cwd: evita escapar ':' y comillas dentro del filtro.
        carpeta = subtitulos_ass.parent
        filtros.append(f"ass={subtitulos_ass.name}")
    if marca:
        # Marca de agua de vista previa: grande, arriba y semitransparente.
        from ..visuales.tarjetas import ruta_fuente

        texto = marca.replace(":", " ").replace("'", " ")
        filtros.append(
            f"drawtext=fontfile='{ruta_fuente()}':text='{texto}':fontsize={int(v.alto * 0.045)}"
            f":fontcolor=white@0.55:box=1:boxcolor=red@0.45:boxborderw=18:x=(w-text_w)/2:y=h*0.05"
        )
    argumentos = ["-i", str(video.resolve()), "-i", str(audio.resolve())]
    if filtros:
        argumentos += ["-vf", ",".join(filtros)]
    argumentos += [
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", v.preset, "-crf", str(v.crf), "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-r", str(v.fps), "-g", str(v.fps // 2), "-bf", "2",
        "-c:a", "aac", "-b:a", "384k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(salida.resolve()),
    ]
    ffmpeg(argumentos, "exportar MP4 final", cwd=carpeta)
    duracion = verificar(video, video=True).duracion
    verificar(salida, duracion=duracion, video=True, audio=True, tolerancia=0.3)


# --- Render por tramos ---------------------------------------------------------
#
# Un documental largo se divide en tramos contiguos de escenas que se
# renderizan en paralelo (un job de CI por tramo). Cada tramo sale con los
# MISMOS parámetros de codificación y el número exacto de fotogramas que le
# toca en la línea de tiempo global, así se unen con ``-c copy`` (sin volver
# a codificar el video). El audio no se corta: se codifica una sola vez sobre
# el video unido; cortar AAC en tramos deja chasquidos en cada unión.


def _codificacion_video(cfg: Config) -> list[str]:
    v = cfg.video
    return [
        "-c:v", "libx264", "-preset", v.preset, "-crf", str(v.crf), "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-r", str(v.fps), "-g", str(v.fps // 2), "-bf", "2",
    ]


def exportar_tramo(video: Path, salida: Path, cfg: Config, inicio_global: float, fotogramas: int,
                   subtitulos_ass: Path | None = None, marca: str = "") -> None:
    """Codifica un tramo (solo video) listo para unirse con ``-c copy``.

    Los subtítulos se queman con la línea de tiempo GLOBAL: se adelantan los
    tiempos del tramo a su posición real, se aplica el ASS completo y se
    devuelven a cero. Así cada tramo muestra exactamente lo que mostraría el
    render de una sola pieza, incluidas las frases que cruzan la unión.
    """
    if fotogramas < 1:
        raise ValueError("un tramo necesita al menos un fotograma")
    v = cfg.video
    filtros: list[str] = []
    carpeta = None
    if subtitulos_ass is not None:
        carpeta = subtitulos_ass.parent
        filtros += [f"setpts=PTS+{inicio_global:.6f}/TB", f"ass={subtitulos_ass.name}", f"setpts=PTS-{inicio_global:.6f}/TB"]
    if marca:
        from ..visuales.tarjetas import ruta_fuente

        texto = marca.replace(":", " ").replace("'", " ")
        filtros.append(
            f"drawtext=fontfile='{ruta_fuente()}':text='{texto}':fontsize={int(v.alto * 0.045)}"
            f":fontcolor=white@0.55:box=1:boxcolor=red@0.45:boxborderw=18:x=(w-text_w)/2:y=h*0.05"
        )
    # Si al tramo le falta medio fotograma por redondeo, se repite el último.
    filtros.append("tpad=stop_mode=clone:stop_duration=1")
    ffmpeg(
        ["-i", str(video.resolve()), "-vf", ",".join(filtros), "-an", *_codificacion_video(cfg),
         "-frames:v", str(fotogramas), str(salida.resolve())],
        f"exportar tramo ({fotogramas} fotogramas)", cwd=carpeta,
    )
    verificar(salida, duracion=fotogramas / v.fps, video=True, tolerancia=1.5 / v.fps + 0.02)


def unir_tramos(tramos: list[Path], audio: Path, salida: Path, duracion: float) -> None:
    """Une los tramos sin recodificar el video y añade el audio (AAC, una sola pasada)."""
    if not tramos:
        raise ValueError("no hay tramos que unir")
    lista = salida.with_suffix(".tramos.txt")
    lista.write_text("".join(f"file '{t.resolve()}'\n" for t in tramos), encoding="utf-8")
    mudo = salida.with_suffix(".mudo.mp4")
    try:
        ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(mudo)], f"unir {len(tramos)} tramos (-c copy)")
        ffmpeg(
            ["-i", str(mudo), "-i", str(audio.resolve()), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "384k", "-ar", "48000", "-movflags", "+faststart", "-shortest", str(salida.resolve())],
            "añadir audio al video unido",
        )
    finally:
        lista.unlink(missing_ok=True)
        mudo.unlink(missing_ok=True)
    verificar(salida, duracion=duracion, video=True, audio=True, tolerancia=0.3)
