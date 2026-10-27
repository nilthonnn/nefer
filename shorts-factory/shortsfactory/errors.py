"""Errores tipados: QUIÉN falló y si tiene sentido reintentar.

La máquina de estados solo reintenta ``ErrorTransitorio``. Todo lo demás
(configuración, guion inválido, cuota agotada) detiene la ejecución con un
mensaje claro: reintentar un 401 o una cuota agotada solo quema tiempo.
"""

from __future__ import annotations


class ShortsError(Exception):
    """Base de todos los errores propios."""


class ErrorTransitorio(ShortsError):
    """Red, 429, 5xx, proceso que murió. Reintentable."""


class ErrorConfiguracion(ShortsError):
    """Falta una clave, una herramienta o un archivo. No reintentable."""


class ErrorContenido(ShortsError):
    """El guion o el video no cumple las reglas (calidad, YPP, datos)."""


class ErrorRender(ShortsError):
    """Un comando externo (ffmpeg, Remotion) terminó mal. Guarda comando y stderr."""

    def __init__(self, mensaje: str, comando: list[str] | None = None, stderr: str = "") -> None:
        self.comando = comando or []
        self.stderr = stderr
        detalle = ""
        if self.comando:
            detalle += "\n  comando: " + " ".join(self.comando)
        if stderr:
            detalle += "\n  stderr:\n" + "\n".join(stderr.strip().splitlines()[-15:])
        super().__init__(mensaje + detalle)


class ErrorRenderTransitorio(ErrorTransitorio, ErrorRender):
    """El navegador headless o ffmpeg murió por recursos: vale reintentar."""


class ErrorCuota(ShortsError):
    """Cuota diaria de la YouTube Data API agotada. Se reintenta mañana, no ahora."""


class ErrorAutenticacion(ShortsError):
    """Token de OAuth revocado o caducado: hay que volver a autorizar."""
