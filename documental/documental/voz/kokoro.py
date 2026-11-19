"""Voz local con Kokoro (modelo abierto, licencia Apache-2.0: apta para monetizar).

No necesita clave ni cuenta: el modelo (~330 MB) se descarga de Hugging Face
la primera vez. Voces en español: ``em_alex``, ``em_santa`` (masculinas) y
``ef_dora`` (femenina).

Tiempos por palabra: en español Kokoro no los entrega, pero sí la duración
predicha de cada fonema (``pred_dur``, en unidades de 1/40 s). Con ella se
reconstruye el inicio y el fin de cada palabra para los subtítulos.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..errores import ErrorConfiguracion, ErrorVoz
from ..modelos import Locucion, Palabra
from ..multimedia.ffmpeg import ffmpeg, medir
from ..registro import obtener
from .base import estimar_palabras

log = obtener("voz.kokoro")
UNIDAD = 1 / 40  # segundos por unidad de pred_dur (24 kHz, salto de 600 muestras)


def palabras_desde_fonemas(texto: str, fonemas: str, pred_dur: list[int], vocab: dict | None = None) -> list[Palabra]:
    """Tiempos por palabra a partir de la duración de cada fonema.

    Kokoro descarta los caracteres fonéticos que no están en su vocabulario
    antes de predecir duraciones: se aplica el mismo filtro para que las dos
    secuencias coincidan. Los espacios del texto fonético separan palabras.
    """
    if vocab:
        fonemas = "".join(c for c in fonemas if c in vocab)
    if len(pred_dur) != len(fonemas) + 2:
        raise ValueError(f"pred_dur ({len(pred_dur)}) no corresponde a los fonemas ({len(fonemas)}+2)")
    t = max(0, pred_dur[0] - 3) * UNIDAD
    grupos: list[tuple[float, float]] = []
    inicio: float | None = None
    for i, ch in enumerate(fonemas):
        if ch == " ":
            if inicio is not None:
                grupos.append((inicio, t))
                inicio = None
        elif inicio is None:
            inicio = t
        t += pred_dur[i + 1] * UNIDAD
    if inicio is not None:
        grupos.append((inicio, t))
    escritas = texto.split()
    if not grupos or not escritas:
        return []
    if len(escritas) == len(grupos):
        return [Palabra(p, round(a, 3), round(b, 3)) for p, (a, b) in zip(escritas, grupos)]
    # Cifras y siglas se pronuncian en varias palabras: se reparte el tramo real.
    return [Palabra(p.texto, round(p.inicio + grupos[0][0], 3), round(p.fin + grupos[0][0], 3))
            for p in estimar_palabras(texto, grupos[-1][1] - grupos[0][0], margen=0.0)]


class VozKokoro:
    nombre = "kokoro"
    comercial = True

    def __init__(self, voz: str = "em_alex", velocidad: float = 1.0) -> None:
        try:
            from kokoro import KPipeline  # import perezoso: arrastra PyTorch
        except ImportError as e:
            raise ErrorConfiguracion(
                "Kokoro no está instalado: pip install --extra-index-url https://download.pytorch.org/whl/cpu "
                "kokoro soundfile (y espeak-ng en el sistema)"
            ) from e
        self._pipeline = KPipeline(lang_code="e", repo_id="hexgrad/Kokoro-82M")
        self._vocab: dict | None = getattr(getattr(self._pipeline, "model", None), "vocab", None)
        self._voz = voz
        self._velocidad = velocidad

    def licencia(self) -> tuple[bool | None, str]:
        return True, "Kokoro-82M (Apache-2.0)"

    def huella(self) -> str:
        return hashlib.sha256(f"kokoro:{self._voz}:{self._velocidad}".encode()).hexdigest()[:16]

    def sintetizar(self, texto: str, destino: Path, anterior: str = "", siguiente: str = "") -> Locucion:
        import numpy as np
        import soundfile as sf

        audios, palabras, desfase = [], [], 0.0
        for r in self._pipeline(texto, voice=self._voz, speed=self._velocidad, split_pattern=None):
            if r.audio is None:
                continue
            audio = r.audio.cpu().numpy()
            dur = len(audio) / 24_000
            try:
                pd = [int(x) for x in r.pred_dur.cpu().tolist()]
                parciales = palabras_desde_fonemas(r.graphemes, r.phonemes, pd, self._vocab)
            except (ValueError, AttributeError) as e:
                log.warning("tiempos por estimación (%s)", e)
                parciales = estimar_palabras(r.graphemes, dur)
            palabras += [Palabra(p.texto, round(p.inicio + desfase, 3), round(p.fin + desfase, 3)) for p in parciales]
            audios.append(audio)
            desfase += dur
        if not audios:
            raise ErrorVoz("Kokoro no generó audio")
        crudo = destino.with_suffix(".k24.wav")
        sf.write(crudo, np.concatenate(audios), 24_000)
        ruta = destino.with_suffix(".wav")
        ffmpeg(["-i", str(crudo), "-ar", "48000", "-ac", "1", str(ruta)], "kokoro → wav 48 kHz")
        crudo.unlink(missing_ok=True)
        return Locucion(audio=ruta, duracion=medir(ruta).duracion, palabras=palabras)
