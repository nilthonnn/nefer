"""Configuración: ``config/canal.toml`` (identidad y técnica) + ``.env`` (secretos).

Los secretos solo se leen del entorno. El ``.env`` se carga sin dependencias
externas y nunca pisa variables ya definidas en el entorno real, de modo que
en CI o en un servidor manda lo que inyecte el operador.
"""

from __future__ import annotations

import os
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .errores import ErrorConfiguracion

# Raíz del proyecto ``documental/`` (la carpeta que contiene pyproject.toml).
RAIZ = Path(__file__).resolve().parent.parent


def cargar_env(ruta: Path) -> None:
    """Carga ``CLAVE=valor`` de un .env. Ignora comentarios y líneas vacías."""
    if not ruta.is_file():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        clave = clave.strip().removeprefix("export ").strip()
        valor = valor.strip().strip('"').strip("'")
        if clave and clave not in os.environ:
            os.environ[clave] = valor


def _env(clave: str, defecto: str = "") -> str:
    return os.environ.get(clave, "").strip() or defecto


@dataclass(frozen=True)
class Video:
    ancho: int = 1920
    alto: int = 1080
    fps: int = 30
    crf: int = 18
    preset: str = "medium"
    transicion: str = "fade"
    transicion_segundos: float = 0.5
    pantalla_final_segundos: float = 20.0


@dataclass(frozen=True)
class Voz:
    estabilidad: float = 0.42
    similitud: float = 0.8
    estilo: float = 0.3
    refuerzo_hablante: bool = True
    velocidad: float = 1.04


@dataclass(frozen=True)
class Audio:
    lufs: float = -14.0
    pico_db: float = -1.0
    musica_db: float = -20.0
    musica: str = "assets/musica"


@dataclass(frozen=True)
class Subtitulos:
    quemados: bool = True
    fuente: str = "Inter"
    tamano: int = 76
    max_palabras: int = 5
    color: str = "&H00FFFFFF"
    resaltado: str = "&H0001B3F5"


@dataclass(frozen=True)
class Monetizacion:
    minutos_minimos: float = 8.0
    proporcion_visual_propio: float = 0.25
    similitud_maxima: float = 0.45


@dataclass(frozen=True)
class Canal:
    nombre: str = ""
    llamado_final: str = "¿Seguimos investigando?"
    idioma: str = "es-419"


@dataclass(frozen=True)
class Secretos:
    """Todo lo que viene del entorno. Nunca se escribe a disco ni a logs."""

    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_model: str = "eleven_multilingual_v2"
    mpt_dir: str = ""
    pexels_api_key: str = ""
    pixabay_api_key: str = ""
    remotion_dir: str = ""
    remotion_browser: str = ""
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5-5"


@dataclass(frozen=True)
class Config:
    canal: Canal = field(default_factory=Canal)
    video: Video = field(default_factory=Video)
    voz: Voz = field(default_factory=Voz)
    audio: Audio = field(default_factory=Audio)
    subtitulos: Subtitulos = field(default_factory=Subtitulos)
    monetizacion: Monetizacion = field(default_factory=Monetizacion)
    secretos: Secretos = field(default_factory=Secretos)
    salida: Path = RAIZ / "salidas"

    @property
    def remotion_dir(self) -> Path:
        return Path(self.secretos.remotion_dir) if self.secretos.remotion_dir else RAIZ / "remotion"

    @property
    def carpeta_musica(self) -> Path:
        ruta = Path(self.audio.musica)
        return ruta if ruta.is_absolute() else RAIZ / ruta


def _seccion(cls, datos: dict, nombre: str):
    """Construye la dataclass ``cls`` validando que no haya claves desconocidas."""
    valores = datos.get(nombre, {})
    validas = set(cls.__dataclass_fields__)
    sobrantes = set(valores) - validas
    if sobrantes:
        raise ErrorConfiguracion(f"[{nombre}] tiene claves desconocidas: {', '.join(sorted(sobrantes))}")
    return cls(**valores)


def cargar(ruta_toml: Path | None = None, ruta_env: Path | None = None) -> Config:
    """Lee .env (cwd y raíz del proyecto) y canal.toml, y devuelve la configuración."""
    for candidato in filter(None, [ruta_env, Path.cwd() / ".env", RAIZ / ".env"]):
        cargar_env(candidato)

    ruta_toml = ruta_toml or RAIZ / "config" / "canal.toml"
    datos: dict = {}
    if ruta_toml.is_file():
        try:
            datos = tomllib.loads(ruta_toml.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as e:
            raise ErrorConfiguracion(f"{ruta_toml}: TOML inválido: {e}") from e

    secretos = Secretos(
        elevenlabs_api_key=_env("ELEVENLABS_API_KEY"),
        elevenlabs_voice_id=_env("ELEVENLABS_VOICE_ID"),
        elevenlabs_model=_env("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
        mpt_dir=_env("MPT_DIR"),
        pexels_api_key=_env("PEXELS_API_KEY"),
        pixabay_api_key=_env("PIXABAY_API_KEY"),
        remotion_dir=_env("REMOTION_DIR"),
        remotion_browser=_env("REMOTION_BROWSER"),
        anthropic_api_key=_env("ANTHROPIC_API_KEY"),
        claude_model=_env("CLAUDE_MODEL", "claude-opus-5-5"),
    )
    salida = Path(_env("DOCUMENTAL_SALIDA")) if _env("DOCUMENTAL_SALIDA") else RAIZ / "salidas"
    return Config(
        canal=_seccion(Canal, datos, "canal"),
        video=_seccion(Video, datos, "video"),
        voz=_seccion(Voz, datos, "voz"),
        audio=_seccion(Audio, datos, "audio"),
        subtitulos=_seccion(Subtitulos, datos, "subtitulos"),
        monetizacion=_seccion(Monetizacion, datos, "monetizacion"),
        secretos=secretos,
        salida=salida,
    )


def exigir_herramientas(*nombres: str) -> None:
    """Falla pronto y claro si falta un ejecutable (mejor que a mitad del render)."""
    faltan = [n for n in nombres if shutil.which(n) is None]
    if faltan:
        raise ErrorConfiguracion(f"Faltan herramientas en el PATH: {', '.join(faltan)}")
