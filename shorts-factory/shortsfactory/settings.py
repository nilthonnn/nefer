"""Configuración tipada y validada con Pydantic.

Fuente única de verdad para todo lo configurable. Se carga de variables de
entorno (y de ``.env`` en desarrollo). Los secretos son ``SecretStr``: nunca
aparecen en logs, ``repr`` ni volcados de estado.

Las claves se validan al USARSE (``exigir``), no al cargar: así ``doctor``,
las pruebas y un render sin publicar funcionan sin credenciales de YouTube.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .errors import ErrorConfiguracion

RAIZ = Path(__file__).resolve().parent.parent


def _alias(*nombres: str) -> AliasChoices:
    return AliasChoices(*nombres)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(RAIZ / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        validate_default=True,
    )

    # --- LLM ----------------------------------------------------------------------
    llm_proveedor: Literal["anthropic", "openai", "plantilla"] = Field(
        "anthropic", validation_alias=_alias("SF_LLM", "llm_proveedor"),
        description="'plantilla' es un generador local sin LLM, solo para pruebas (nunca se publica).",
    )
    llm_modelo: str = Field("", validation_alias=_alias("SF_LLM_MODELO", "llm_modelo"))
    anthropic_api_key: SecretStr | None = Field(None, validation_alias=_alias("ANTHROPIC_API_KEY", "anthropic_api_key"))
    openai_api_key: SecretStr | None = Field(None, validation_alias=_alias("OPENAI_API_KEY", "openai_api_key"))
    llm_correcciones: int = Field(2, ge=0, le=5, validation_alias=_alias("SF_LLM_CORRECCIONES", "llm_correcciones"))

    # --- Voz ------------------------------------------------------------------------
    tts_motor: Literal["kokoro", "edge", "espeak"] = Field("kokoro", validation_alias=_alias("SF_TTS", "tts_motor"))
    kokoro_voz: str = Field("em_alex", validation_alias=_alias("SF_KOKORO_VOZ", "kokoro_voz"))
    edge_voz: str = Field("es-MX-JorgeNeural", validation_alias=_alias("SF_EDGE_VOZ", "edge_voz"))

    # --- Video ----------------------------------------------------------------------
    fps: int = Field(30, validation_alias=_alias("SF_FPS", "fps"))
    duracion_max: float = Field(15.0, ge=8, le=60, validation_alias=_alias("SF_DURACION_MAX", "duracion_max"))
    lufs: float = Field(-14.0, ge=-24, le=-9, validation_alias=_alias("SF_LUFS", "lufs"))
    pexels_api_key: SecretStr | None = Field(None, validation_alias=_alias("PEXELS_API_KEY", "pexels_api_key"))
    remotion_dir: Path = Field(RAIZ / "remotion", validation_alias=_alias("SF_REMOTION_DIR", "remotion_dir"))
    remotion_browser: str = Field("", validation_alias=_alias("SF_REMOTION_BROWSER", "remotion_browser"))
    musica_dir: Path = Field(RAIZ / "assets" / "musica", validation_alias=_alias("SF_MUSICA_DIR", "musica_dir"))

    # --- Estado ---------------------------------------------------------------------
    dir_runs: Path = Field(RAIZ / "runs", validation_alias=_alias("SF_DIR_RUNS", "dir_runs"))
    dir_estado: Path = Field(RAIZ / "estado", validation_alias=_alias("SF_DIR_ESTADO", "dir_estado"))
    semilla: int | None = Field(None, validation_alias=_alias("SF_SEMILLA", "semilla"))
    similitud_maxima: float = Field(0.35, gt=0, lt=1, validation_alias=_alias("SF_SIMILITUD_MAX", "similitud_maxima"))

    # --- YouTube --------------------------------------------------------------------
    youtube_client_secret: SecretStr | None = Field(
        None, validation_alias=_alias("YOUTUBE_CLIENT_SECRET", "youtube_client_secret"),
        description="Contenido JSON del client_secret de OAuth (tipo 'installed'/escritorio).",
    )
    youtube_refresh_token: SecretStr | None = Field(None, validation_alias=_alias("YOUTUBE_REFRESH_TOKEN", "youtube_refresh_token"))
    youtube_privacidad: Literal["private", "unlisted", "public"] = Field(
        "private", validation_alias=_alias("SF_YOUTUBE_PRIVACIDAD", "youtube_privacidad"),
    )
    youtube_categoria: str = Field("28", validation_alias=_alias("SF_YOUTUBE_CATEGORIA", "youtube_categoria"))
    youtube_cuota_diaria: int = Field(10_000, gt=0, validation_alias=_alias("SF_YOUTUBE_CUOTA", "youtube_cuota_diaria"))
    youtube_costo_subida: int = Field(1_600, gt=0, validation_alias=_alias("SF_YOUTUBE_COSTO_SUBIDA", "youtube_costo_subida"))
    youtube_contenido_sintetico: bool = Field(False, validation_alias=_alias("SF_YOUTUBE_SINTETICO", "youtube_contenido_sintetico"))

    @field_validator("fps")
    @classmethod
    def _fps_valido(cls, v: int) -> int:
        # int + validador (no Literal): así "60" leído del entorno se convierte bien.
        if v not in (30, 60):
            raise ValueError("SF_FPS debe ser 30 o 60")
        return v

    @field_validator("youtube_categoria")
    @classmethod
    def _categoria_numerica(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("debe ser un id numérico de categoría (28 = Ciencia y tecnología, 27 = Educación)")
        return v

    @model_validator(mode="after")
    def _modelo_por_defecto(self) -> "Settings":
        if not self.llm_modelo:
            if self.llm_proveedor == "anthropic":
                self.llm_modelo = "claude-opus-5-5"
            elif self.llm_proveedor == "openai":
                raise ValueError("con SF_LLM=openai hay que indicar SF_LLM_MODELO")
        return self

    # --- utilidades -----------------------------------------------------------------
    def exigir(self, *campos: str) -> None:
        """Lanza ErrorConfiguracion si falta alguno de los campos (por nombre)."""
        faltan = [c for c in campos if not getattr(self, c)]
        if faltan:
            nombres = {
                "anthropic_api_key": "ANTHROPIC_API_KEY", "openai_api_key": "OPENAI_API_KEY",
                "youtube_client_secret": "YOUTUBE_CLIENT_SECRET", "youtube_refresh_token": "YOUTUBE_REFRESH_TOKEN",
                "pexels_api_key": "PEXELS_API_KEY",
            }
            raise ErrorConfiguracion("Faltan variables de entorno: " + ", ".join(nombres.get(c, c) for c in faltan))

    @staticmethod
    def secreto(valor: SecretStr | None) -> str:
        return valor.get_secret_value() if valor else ""


@lru_cache(maxsize=1)
def cargar() -> Settings:
    try:
        return Settings()
    except Exception as e:  # ValidationError → mensaje legible
        raise ErrorConfiguracion(f"Configuración inválida:\n{e}") from e
