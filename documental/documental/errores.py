"""Jerarquía de errores del generador.

La regla es simple: cada fallo tiene un tipo que dice QUIÉN falló y si vale la
pena reintentar. Así el orquestador nunca reintenta un error de configuración
(que fallaría igual) y nunca se rinde ante un 503 pasajero.
"""

from __future__ import annotations


class DocumentalError(Exception):
    """Base de todos los errores propios."""


class ErrorTransitorio(DocumentalError):
    """Marca un fallo que puede resolverse solo: red, 429, 5xx, proceso caído.

    Se usa como mezcla (``class X(ErrorTransitorio, ErrorVoz)``) para que el
    mecanismo de reintentos lo reconozca sin conocer cada módulo.
    """


class ErrorConfiguracion(DocumentalError):
    """Falta una clave, una ruta o una herramienta. Reintentar no sirve."""


class ErrorEntrada(DocumentalError):
    """El guion no es válido. El mensaje dice qué campo y dónde."""


class ErrorVoz(DocumentalError):
    """Falló la síntesis de voz."""


class ErrorVozTransitorio(ErrorTransitorio, ErrorVoz):
    pass


class ErrorVisual(DocumentalError):
    """No se pudo obtener o generar el visual de una escena."""


class ErrorVisualTransitorio(ErrorTransitorio, ErrorVisual):
    pass


class ErrorRender(DocumentalError):
    """Un comando de ffmpeg/ffprobe/Remotion terminó mal.

    Guarda el comando y la cola de stderr: es lo único que permite diagnosticar
    un render que falla a los 40 minutos sin volver a correrlo.
    """

    def __init__(self, mensaje: str, comando: list[str] | None = None, stderr: str = "") -> None:
        self.comando = comando or []
        self.stderr = stderr
        detalle = f"\n  comando: {' '.join(self.comando)}" if self.comando else ""
        if stderr:
            cola = "\n".join(stderr.strip().splitlines()[-15:])
            detalle += f"\n  stderr (últimas líneas):\n{cola}"
        super().__init__(mensaje + detalle)


class ErrorMonetizacion(DocumentalError):
    """La auditoría encontró un bloqueo (solo con --estricto)."""
