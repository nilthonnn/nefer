"""Fixtures comunes. Las pruebas que necesitan ffmpeg o espeak-ng se saltan solas si faltan."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from documental.config import Config, Video

requiere_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg no instalado")
requiere_espeak = pytest.mark.skipif(shutil.which("espeak-ng") is None, reason="espeak-ng no instalado")


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    """Config pequeña y rápida: 320×180, sin pantalla final, salida en tmp."""
    base = Config()
    return replace(
        base,
        video=replace(Video(), ancho=320, alto=180, fps=15, preset="ultrafast", pantalla_final_segundos=0, transicion_segundos=0.3),
        audio=replace(base.audio, musica=str(tmp_path / "sin-musica")),
        salida=tmp_path / "salidas",
    )


@pytest.fixture
def mp3_corto(tmp_path: Path) -> bytes:
    """Un MP3 real de 1 s (para simular la respuesta de ElevenLabs)."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg no instalado")
    ruta = tmp_path / "tono.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=f=440:d=1", str(ruta)], check=True)
    return ruta.read_bytes()


def guion_minimo(**extra) -> dict:
    datos = {
        "titulo": "Prueba de energía",
        "capitulos": [
            {"titulo": "Uno", "escenas": [
                {"narracion": "La energía solar es abundante.", "visual": {"tipo": "stock", "busqueda": ["sun"]}},
                {"narracion": "Y cada vez más barata.", "visual": {"tipo": "cifra", "datos": {"valor": 89, "etiqueta": "menos", "fuente": "IRENA 2023"}}},
            ]},
        ],
    }
    datos.update(extra)
    return datos
