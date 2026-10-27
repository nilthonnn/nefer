"""Fixtures: configuración aislada (sin .env ni variables reales) y datos de prueba."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from shortsfactory.models import Guion, Serie, Tendencia
from shortsfactory.settings import Settings

RAIZ = Path(__file__).resolve().parent.parent
requiere_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg no instalado")
requiere_espeak = pytest.mark.skipif(shutil.which("espeak-ng") is None, reason="espeak-ng no instalado")


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    for clave in list(os.environ):
        if clave.startswith(("SF_", "YOUTUBE_", "ANTHROPIC_", "OPENAI_", "PEXELS_")):
            monkeypatch.delenv(clave, raising=False)


@pytest.fixture
def cfg(tmp_path) -> Settings:
    return Settings(_env_file=None, llm_proveedor="plantilla", tts_motor="espeak",
                    dir_runs=tmp_path / "runs", dir_estado=tmp_path / "estado", musica_dir=tmp_path / "musica")


@pytest.fixture
def serie() -> Serie:
    return Serie.model_validate_json((RAIZ / "ejemplos" / "serie-sintetica.json").read_text(encoding="utf-8"))


@pytest.fixture
def tendencia() -> Tendencia:
    return Tendencia(titulo="La inflación vuelve a subir", fuente="manual")


def guion_bueno(**cambios) -> Guion:
    datos = {
        "titulo": "La inflación que nadie vio venir",
        "frases": [
            {"texto": "Nadie habla de este 4,4%", "visual": "cifra", "enfasis": ["4,4%"]},
            {"texto": "La razón está en este gráfico.", "visual": "grafico", "enfasis": ["razón"]},
            {"texto": "En 2014 estaba en 3,1%. En 2022 llegó a 9,5%.", "visual": "grafico", "enfasis": ["9,5%"]},
            {"texto": "Hoy bajó, pero sigue por encima de hace diez años.", "visual": "broll", "broll_busqueda": "supermarket prices"},
            {"texto": "Y eso explica por qué", "visual": "texto"},
        ],
        "hashtags": ["#inflacion", "economia"],
        "descripcion": "Prueba",
    }
    datos.update(cambios)
    return Guion.model_validate(datos)
