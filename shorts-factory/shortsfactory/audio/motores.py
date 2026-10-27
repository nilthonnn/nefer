"""Motores de voz con una interfaz común: una frase → WAV + tiempos por palabra.

- kokoro: modelo abierto (Apache-2.0, apto para monetizar), local, voces
  españolas ``ef_dora``, ``em_alex``, ``em_santa``. Requiere PyTorch y espeak-ng.
- edge: voces neuronales de Microsoft (es-MX, es-CO...) con tiempos exactos.
  Usa un servicio no oficial y sin licencia comercial explícita: revisa sus
  términos antes de monetizar.
- espeak: robótica, solo para desarrollo y pruebas (nunca se publica).
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Protocol

from ..errors import ErrorConfiguracion, ErrorTransitorio
from ..models import PalabraT
from ..proc import duracion, ejecutar, ffmpeg
from ..settings import Settings
from . import alineacion


class MotorVoz(Protocol):
    nombre: str
    publicable: bool

    def sintetizar(self, texto: str, destino: Path, velocidad: float) -> tuple[Path, float, list[PalabraT], bool]:
        """Devuelve (wav 48 kHz mono, duración, palabras con tiempo relativo, ¿tiempos exactos?)."""
        ...


def _a_wav48(entrada: Path, salida: Path) -> None:
    ffmpeg(["-i", str(entrada), "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(salida)], "voz→wav48")


class Kokoro:
    nombre = "kokoro"
    publicable = True

    def __init__(self, voz: str) -> None:
        try:
            from kokoro import KPipeline  # import perezoso: arrastra PyTorch
        except ImportError as e:
            raise ErrorConfiguracion("Kokoro no instalado: pip install kokoro soundfile (y espeak-ng)") from e
        self._pipeline = KPipeline(lang_code="e")
        self._voz = voz

    def sintetizar(self, texto, destino, velocidad):
        import numpy as np
        import soundfile as sf

        audios, palabras, desfase = [], [], 0.0
        for r in self._pipeline(texto, voice=self._voz, speed=velocidad, split_pattern=None):
            if r.audio is None:
                continue
            audio = r.audio.cpu().numpy()
            dur = len(audio) / 24_000
            try:
                pd = [int(x) for x in r.pred_dur.cpu().tolist()]
                parciales = alineacion.desde_fonemas(r.graphemes, r.phonemes, pd)
                exacta = True
            except (ValueError, AttributeError):
                parciales, exacta = alineacion.estimar(r.graphemes, 0.05, dur - 0.05), False
            palabras += [p.model_copy(update={"inicio": p.inicio + desfase, "fin": p.fin + desfase}) for p in parciales]
            audios.append(audio)
            desfase += dur
        if not audios:
            raise ErrorTransitorio("Kokoro no generó audio")
        crudo = destino.with_suffix(".k24.wav")
        sf.write(crudo, np.concatenate(audios), 24_000)
        wav = destino.with_suffix(".wav")
        _a_wav48(crudo, wav)
        crudo.unlink(missing_ok=True)
        return wav, duracion(wav), palabras, exacta


class Edge:
    nombre = "edge"
    publicable = True

    def __init__(self, voz: str) -> None:
        try:
            import edge_tts  # noqa: F401
        except ImportError as e:
            raise ErrorConfiguracion("pip install edge-tts") from e
        self._voz = voz

    def sintetizar(self, texto, destino, velocidad):
        import edge_tts

        async def generar() -> tuple[bytes, list[tuple[float, float, str]]]:
            com = edge_tts.Communicate(texto, self._voz, rate=f"{round((velocidad - 1) * 100):+d}%", boundary="WordBoundary")
            audio, limites = bytearray(), []
            async for parte in com.stream():
                if parte["type"] == "audio":
                    audio += parte["data"]
                elif parte["type"] == "WordBoundary":
                    limites.append((parte["offset"] / 1e7, parte["duration"] / 1e7, parte["text"]))
            return bytes(audio), limites

        try:
            audio, limites = asyncio.run(generar())
        except Exception as e:  # red/servicio: reintentable
            raise ErrorTransitorio(f"Edge TTS: {type(e).__name__}: {e}") from e
        if not audio:
            raise ErrorTransitorio("Edge TTS no devolvió audio")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir=destino.parent) as f:
            f.write(audio)
        wav = destino.with_suffix(".wav")
        _a_wav48(Path(f.name), wav)
        Path(f.name).unlink(missing_ok=True)
        return wav, duracion(wav), alineacion.desde_limites_edge(texto, limites), bool(limites)


class Espeak:
    nombre = "espeak"
    publicable = False

    def __init__(self) -> None:
        if shutil.which("espeak-ng") is None:
            raise ErrorConfiguracion("espeak-ng no está instalado")

    def sintetizar(self, texto, destino, velocidad):
        crudo = destino.with_suffix(".es.wav")
        ejecutar(["espeak-ng", "-v", "es-419", "-s", str(int(170 * velocidad)), "-w", str(crudo), texto], "espeak-ng")
        wav = destino.with_suffix(".wav")
        # espeak deja ~0,1 s de silencio a cada lado: se recorta para que el ritmo sea real.
        ffmpeg(["-i", str(crudo), "-af", "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                "silenceremove=start_periods=1:start_threshold=-50dB,areverse",
                "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)], "recortar silencios")
        crudo.unlink(missing_ok=True)
        d = duracion(wav)
        return wav, d, alineacion.estimar(texto, 0.0, d), False


def crear(cfg: Settings) -> MotorVoz:
    if cfg.tts_motor == "kokoro":
        return Kokoro(cfg.kokoro_voz)
    if cfg.tts_motor == "edge":
        return Edge(cfg.edge_voz)
    return Espeak()
