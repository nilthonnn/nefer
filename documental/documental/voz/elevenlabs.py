"""Voz con ElevenLabs, con tiempos exactos por palabra.

Se usa el endpoint ``/with-timestamps`` en lugar del TTS de MoneyPrinterTurbo
porque este último no devuelve alineación: sin ella los subtítulos dinámicos
(palabra resaltada al ritmo de la voz) tendrían que adivinarse con Whisper.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import requests

from ..config import Config
from ..errores import ErrorConfiguracion, ErrorVoz, ErrorVozTransitorio
from ..modelos import Locucion
from ..multimedia.ffmpeg import medir
from ..registro import obtener
from ..reintentos import reintentar
from .base import palabras_desde_caracteres

log = obtener("voz.elevenlabs")
URL = "https://api.elevenlabs.io/v1/text-to-speech/{voz}/with-timestamps"
# Códigos en los que reintentar nunca ayuda (clave, permisos, validación).
_DEFINITIVOS = {400, 401, 402, 403, 404, 422}


class VozElevenLabs:
    nombre = "elevenlabs"
    comercial = True

    def __init__(self, config: Config, sesion: requests.Session | None = None) -> None:
        s = config.secretos
        if not s.elevenlabs_api_key:
            raise ErrorConfiguracion("Falta ELEVENLABS_API_KEY en .env")
        if not s.elevenlabs_voice_id:
            raise ErrorConfiguracion("Falta ELEVENLABS_VOICE_ID en .env (elige una voz latina en la Voice Library)")
        self._clave = s.elevenlabs_api_key
        self._voz = s.elevenlabs_voice_id
        self._modelo = s.elevenlabs_model
        v = config.voz
        self._ajustes = {
            "stability": v.estabilidad,
            "similarity_boost": v.similitud,
            "style": v.estilo,
            "use_speaker_boost": v.refuerzo_hablante,
            "speed": v.velocidad,
        }
        self._sesion = sesion or requests.Session()

    def licencia(self) -> tuple[bool | None, str]:
        """Consulta el plan de la cuenta: el plan gratuito no permite uso comercial.

        Sin licencia comercial, monetizar el video incumple los términos de
        ElevenLabs aunque YouTube no lo detecte; por eso es un bloqueo.
        """
        try:
            r = self._sesion.get(
                "https://api.elevenlabs.io/v1/user/subscription",
                headers={"xi-api-key": self._clave},
                timeout=(10, 30),
            )
        except (requests.ConnectionError, requests.Timeout) as e:
            return None, f"sin conexión con ElevenLabs: {type(e).__name__}"
        if r.status_code != 200:
            return None, f"ElevenLabs respondió {r.status_code} al consultar el plan"
        try:
            plan = str(r.json().get("tier", "")).lower()
        except ValueError:
            return None, "respuesta del plan ilegible"
        if not plan:
            return None, "ElevenLabs no informó el plan"
        if plan == "free":
            return False, "plan gratuito de ElevenLabs, sin licencia comercial"
        return True, f"plan {plan} de ElevenLabs"

    def describir_voz(self) -> str:
        """Nombre y etiquetas de la voz elegida (para `diagnostico`)."""
        try:
            r = self._sesion.get(f"https://api.elevenlabs.io/v1/voices/{self._voz}", headers={"xi-api-key": self._clave}, timeout=(10, 30))
        except (requests.ConnectionError, requests.Timeout) as e:
            return f"no verificada ({type(e).__name__})"
        if r.status_code == 404:
            raise ErrorConfiguracion(f"ELEVENLABS_VOICE_ID no existe en tu cuenta: {self._voz}")
        if r.status_code != 200:
            return f"no verificada ({r.status_code})"
        datos = r.json()
        etiquetas = ", ".join(f"{k}={v}" for k, v in (datos.get("labels") or {}).items())
        return f"{datos.get('name', '?')} ({etiquetas})" if etiquetas else str(datos.get("name", "?"))

    def huella(self) -> str:
        crudo = json.dumps([self._voz, self._modelo, self._ajustes], sort_keys=True)
        return hashlib.sha256(crudo.encode()).hexdigest()[:16]

    def sintetizar(self, texto: str, destino: Path, anterior: str = "", siguiente: str = "") -> Locucion:
        cuerpo = {
            "text": texto,
            "model_id": self._modelo,
            "voice_settings": self._ajustes,
        }
        # Contexto de las frases vecinas: misma entonación a lo largo del video.
        if anterior:
            cuerpo["previous_text"] = anterior[-500:]
        if siguiente:
            cuerpo["next_text"] = siguiente[:500]

        datos = reintentar(lambda: self._pedir(cuerpo), descripcion=f"ElevenLabs ({len(texto)} caracteres)")
        ruta = destino.with_suffix(".mp3")
        try:
            ruta.write_bytes(base64.b64decode(datos["audio_base64"]))
            alineacion = datos.get("alignment") or datos.get("normalized_alignment")
            palabras = palabras_desde_caracteres(
                alineacion["characters"],
                alineacion["character_start_times_seconds"],
                alineacion["character_end_times_seconds"],
            )
        except (KeyError, TypeError, ValueError) as e:
            raise ErrorVoz(f"Respuesta de ElevenLabs inesperada: {e}") from e
        if not palabras:
            raise ErrorVoz("ElevenLabs devolvió audio sin alineación de palabras")
        duracion = medir(ruta).duracion
        return Locucion(audio=ruta, duracion=duracion, palabras=palabras)

    def _pedir(self, cuerpo: dict) -> dict:
        try:
            r = self._sesion.post(
                URL.format(voz=self._voz),
                params={"output_format": "mp3_44100_128"},
                headers={"xi-api-key": self._clave, "Content-Type": "application/json"},
                json=cuerpo,
                timeout=(15, 180),
            )
        except (requests.ConnectionError, requests.Timeout) as e:
            # Nota: tras un timeout de lectura la petición pudo cobrarse; el
            # coste de reintentar una escena es pequeño frente a perder el video.
            raise ErrorVozTransitorio(f"sin conexión con ElevenLabs: {type(e).__name__}") from e
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError as e:
                raise ErrorVozTransitorio("ElevenLabs devolvió un JSON incompleto") from e
        detalle = r.text[:300]
        if r.status_code in _DEFINITIVOS:
            raise ErrorVoz(f"ElevenLabs rechazó la petición ({r.status_code}): {detalle}")
        # 429 (límite de concurrencia/cuota por minuto) y 5xx: pasajeros.
        raise ErrorVozTransitorio(f"ElevenLabs respondió {r.status_code}: {detalle}")
