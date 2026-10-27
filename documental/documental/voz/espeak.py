"""Voz local con espeak-ng, solo para vista previa.

Sirve para revisar ritmo, cortes y subtítulos sin gastar créditos de
ElevenLabs. Suena robótica: NO se debe publicar con ella (``comercial=False``
hace que la auditoría lo marque como bloqueo).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import exigir_herramientas
from ..modelos import Locucion
from ..multimedia.ffmpeg import ejecutar, medir
from .base import estimar_palabras


class VozEspeak:
    nombre = "espeak-ng"
    comercial = False

    def __init__(self, voz: str = "es-419", palabras_por_minuto: int = 165) -> None:
        exigir_herramientas("espeak-ng")
        self._voz = voz
        self._ppm = palabras_por_minuto

    def huella(self) -> str:
        return hashlib.sha256(f"espeak:{self._voz}:{self._ppm}".encode()).hexdigest()[:16]

    def sintetizar(self, texto: str, destino: Path, anterior: str = "", siguiente: str = "") -> Locucion:
        ruta = destino.with_suffix(".wav")
        ejecutar(["espeak-ng", "-v", self._voz, "-s", str(self._ppm), "-w", str(ruta), texto], "espeak-ng")
        duracion = medir(ruta).duracion
        return Locucion(audio=ruta, duracion=duracion, palabras=estimar_palabras(texto, duracion))
