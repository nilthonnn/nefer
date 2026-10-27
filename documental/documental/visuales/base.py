"""Contrato de los proveedores de visuales y normalización de clips.

Todo clip de escena sale de aquí con el mismo formato (resolución, fps,
píxel, sin audio y duración exacta). Así el montaje final puede encadenar
transiciones sin sorpresas de formato.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..config import Config
from ..modelos import ClipEscena, Escena
from ..multimedia.ffmpeg import ffmpeg, verificar


class ProveedorVisual(Protocol):
    nombre: str

    def puede(self, escena: Escena) -> bool:
        """True si este proveedor sabe generar el visual de la escena."""
        ...

    def generar(self, escena: Escena, duracion: float, destino: Path) -> ClipEscena:
        """Crea ``destino`` (mp4 normalizado) con exactamente ``duracion`` segundos."""
        ...


def _codec(cfg: Config) -> list[str]:
    # Los intermedios se codifican rápido y casi sin pérdida; la calidad final
    # la fija el montaje. Mantener el mismo códec evita recodificar dos veces mal.
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-an"]


# Gradación del canal para el stock: un poco más de contraste y color y una
# viñeta suave. Junto con el movimiento de cámara, convierte el clip genérico
# en un plano con identidad propia (y no idéntico al original de Pexels).
GRADACION = "eq=contrast=1.06:saturation=1.12:gamma=0.98,vignette=PI/5"


def normalizar_video(entrada: Path, salida: Path, duracion: float, cfg: Config, movimiento: str = "") -> None:
    """Escala+recorta al lienzo, fija fps, quita audio y ajusta la duración (repite si es corto).

    ``movimiento`` ("acercar" o "alejar") aplica un zoom lento del 8 % y la
    gradación del canal; se usa en el stock, no en las infografías.
    """
    v = cfg.video
    filtro = f"scale={v.ancho}:{v.alto}:force_original_aspect_ratio=increase,crop={v.ancho}:{v.alto},fps={v.fps}"
    if movimiento:
        d = max(duracion, 0.1)
        z = f"1+0.08*in_time/{d:.3f}" if movimiento == "acercar" else f"1.08-0.08*in_time/{d:.3f}"
        filtro += (
            f",zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={v.ancho}x{v.alto}:fps={v.fps},{GRADACION}"
        )
    filtro += ",setsar=1,format=yuv420p"
    ffmpeg(
        ["-stream_loop", "-1", "-i", str(entrada), "-t", f"{duracion:.3f}", "-vf", filtro, *_codec(cfg), str(salida)],
        f"normalizar {entrada.name}",
    )
    verificar(salida, duracion=duracion, video=True, tolerancia=0.15)


def imagen_a_clip(imagen: Path, salida: Path, duracion: float, cfg: Config, acercar: bool = True) -> None:
    """Imagen fija → clip con un acercamiento lento (efecto Ken Burns).

    Se amplía al doble antes de ``zoompan`` porque a resolución nativa el
    redondeo de píxeles produce un temblor visible.
    """
    v = cfg.video
    cuadros = max(1, round(duracion * v.fps))
    if acercar:
        paso = 0.10 / cuadros  # 10 % de acercamiento a lo largo de la escena
        filtro = (
            f"scale={v.ancho * 2}:{v.alto * 2}:force_original_aspect_ratio=increase,crop={v.ancho * 2}:{v.alto * 2},"
            f"zoompan=z='min(zoom+{paso:.6f},1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={cuadros}:s={v.ancho}x{v.alto}:fps={v.fps},setsar=1,format=yuv420p"
        )
        entrada = ["-i", str(imagen)]
    else:
        filtro = f"scale={v.ancho}:{v.alto},fps={v.fps},setsar=1,format=yuv420p"
        entrada = ["-loop", "1", "-i", str(imagen)]
    ffmpeg([*entrada, "-t", f"{duracion:.3f}", "-vf", filtro, *_codec(cfg), str(salida)], f"imagen→clip {imagen.name}")
    verificar(salida, duracion=duracion, video=True, tolerancia=0.15)
