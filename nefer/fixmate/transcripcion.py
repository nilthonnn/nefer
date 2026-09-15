"""La consulta dictada: del audio del tecnico al texto que busca el motor.

En campo nadie escribe. El tecnico tiene las manos sucias, guantes puestos y
la maquina al lado haciendo ruido: habla. Hay dos caminos y los dos hacen
falta, porque fallan en sitios distintos.

**El dictado del propio telefono** es el camino de siempre y no se programa
aqui: el teclado de Android y de iPhone transcribe al campo de texto, y la
app de campo usa el reconocimiento del navegador. Funciona sin cuenta de
nadie y, en los telefonos recientes, tambien sin señal. Lo que escribe llega
al motor como cualquier consulta escrita.

**La transcripcion por servicio** es este modulo, y es para el audio que ya
quedo grabado: la nota de voz que el tecnico mando por WhatsApp desde el
socavon, donde no habia señal para nada mas. Se sube despues, cuando hay red.

Dos detalles que cambian el resultado:

- **Se le pasan las pistas de la flota.** Sin ellas, «ge cero setenta y cuatro
  guion cero uno» se transcribe como suene. Con la lista de codigos de equipo
  del propio indice delante, sale «GE074-01».
- **Lo transcrito se devuelve siempre.** El tecnico tiene que poder leer que
  entendio la maquina antes de creerle el diagnostico; una transcripcion
  equivocada que nadie ve es un diagnostico de otra falla.
"""

from __future__ import annotations

import os
from pathlib import Path

FORMATOS = {".m4a", ".mp3", ".wav", ".ogg", ".oga", ".webm", ".mp4", ".mpga",
            ".flac", ".aac", ".amr"}

# El servicio rechaza lo que pase de 25 MB. Son unos 40 minutos de nota de
# voz: mas que eso no es una consulta, es una reunion.
TAMANO_MAXIMO = 25 * 1024 * 1024


class ErrorTranscripcion(RuntimeError):
    """No se pudo convertir el audio en texto."""


def pistas_de_indice(indice, maximo: int = 60) -> str:
    """Vocabulario propio de la flota para que el modelo no lo invente."""
    terminos: list[str] = []
    for fragmento in getattr(indice, "fragmentos", []):
        for clave in ("codigo_equipo", "modelo_equipo"):
            valor = str(fragmento.metadatos.get(clave) or "").strip()
            if valor and valor not in terminos:
                terminos.append(valor)
        for codigo in fragmento.metadatos.get("codigos_dtc") or []:
            if codigo not in terminos:
                terminos.append(str(codigo))
        if len(terminos) >= maximo:
            break
    return ", ".join(terminos[:maximo])


class TranscriptorOpenAI:
    """Transcribe con la API de OpenAI. El cliente se puede inyectar."""

    def __init__(self, modelo: str = "whisper-1", clave: str | None = None,
                 idioma: str = "es", cliente=None):
        self.modelo = modelo
        self.idioma = idioma
        self.nombre = f"openai-{modelo}"
        self._cliente = cliente
        self._clave = clave or os.getenv("OPENAI_API_KEY")

    def _obtener_cliente(self):
        if self._cliente is not None:
            return self._cliente
        if not self._clave:
            raise ErrorTranscripcion(
                "falta OPENAI_API_KEY para transcribir. Mientras tanto, el "
                "dictado del teclado del telefono escribe la consulta sin "
                "depender de ningun servicio.")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise ErrorTranscripcion(
                "transcribir necesita el paquete 'openai': "
                "pip install 'nefer[fixmate-openai]'") from exc
        self._cliente = OpenAI(api_key=self._clave)
        return self._cliente

    def __call__(self, audio, pistas: str = "") -> str:
        """`audio` es una ruta o un par (nombre, bytes)."""
        nombre, datos = _leer(audio)
        cliente = self._obtener_cliente()
        try:
            respuesta = cliente.audio.transcriptions.create(
                model=self.modelo,
                file=(nombre, datos),
                language=self.idioma,
                prompt=("Terminos de la flota: " + pistas) if pistas else "",
            )
        except Exception as exc:
            raise ErrorTranscripcion(f"el servicio no transcribio el audio: {exc}") from exc

        texto = getattr(respuesta, "text", None)
        if texto is None and isinstance(respuesta, dict):
            texto = respuesta.get("text")
        texto = (texto or "").strip()
        if not texto:
            raise ErrorTranscripcion(
                "la transcripcion salio vacia. Revise que el audio se oiga y "
                "que no sean solo ruidos de taller.")
        return texto


def _leer(audio) -> tuple[str, bytes]:
    if isinstance(audio, (str, Path)):
        ruta = Path(audio)
        if not ruta.is_file():
            raise ErrorTranscripcion(f"no existe el audio {ruta}")
        if ruta.suffix.lower() not in FORMATOS:
            raise ErrorTranscripcion(
                f"{ruta.name}: formato de audio no soportado. Sirven "
                f"{', '.join(sorted(FORMATOS))}.")
        datos = ruta.read_bytes()
        nombre = ruta.name
    else:
        nombre, datos = audio
    if not datos:
        raise ErrorTranscripcion(f"{nombre}: el audio esta vacio.")
    if len(datos) > TAMANO_MAXIMO:
        raise ErrorTranscripcion(
            f"{nombre}: {len(datos) / 1048576:.1f} MB pasan del limite de "
            f"{TAMANO_MAXIMO // 1048576} MB. Recorte la nota de voz.")
    return nombre, datos


def obtener(nombre: str = "auto", **kw):
    """Transcriptor por nombre. 'auto' usa OpenAI si hay clave."""
    if nombre in ("auto", "openai"):
        return TranscriptorOpenAI(**{k: v for k, v in kw.items()
                                     if k in ("modelo", "clave", "idioma", "cliente")})
    raise ValueError(f"transcriptor desconocido: {nombre!r}")
