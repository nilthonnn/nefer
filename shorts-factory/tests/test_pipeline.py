"""Pipeline: publicación con dobles y run completo real (SF_TEST_RENDER=1)."""

import os
import shutil
from pathlib import Path

import pytest

from shortsfactory.core.fsm import Estado, Registro
from shortsfactory.core.pipeline import Pipeline
from shortsfactory.errors import ErrorContenido
from shortsfactory.memory import Memoria
from shortsfactory.visuals.variacion import elegir

from conftest import RAIZ, guion_bueno

# Se lee al importar: el fixture autouse limpia las variables SF_* antes de cada prueba.
NAVEGADOR = os.environ.get("SF_REMOTION_BROWSER", "")
RENDER = os.environ.get("SF_TEST_RENDER") == "1"


def _registro(serie, tendencia, tmp_path, **extra) -> Registro:
    video = tmp_path / "short.mp4"
    video.write_bytes(b"\x00" * 100)
    return Registro(run_id="r1", opciones={"publicar": "private"}, artefactos={
        "tendencia": tendencia.model_dump(), "serie": serie.model_dump(), "guion": guion_bueno().model_dump(),
        "variacion": elegir(1, []).model_dump(), "video": str(video), "publicable": True, **extra,
    })


def test_publicar_registra_en_la_memoria(monkeypatch, cfg, serie, tendencia, tmp_path):
    from shortsfactory.models import ResultadoSubida
    from shortsfactory.publisher import youtube

    capturado = {}

    def subir(cfg_, video, meta, yt=None):
        capturado.update(meta)
        return ResultadoSubida(video_id="v1", url="https://youtube.com/shorts/v1", privacidad="private",
                               titulo=meta["snippet"]["title"], unidades_cuota=1600)

    monkeypatch.setattr(youtube, "subir", subir)
    p = Pipeline(cfg)
    salida = p.publicar(_registro(serie, tendencia, tmp_path, broll_ids=["pexels:1"]))
    assert salida["publicado"] and capturado["snippet"]["title"].endswith("#Shorts")
    fila = Memoria(cfg.dir_estado).entradas()[-1]
    assert fila["video_id"] == "v1" and fila["broll"] == ["pexels:1"] and "variacion" in fila


def test_no_publica_lo_no_publicable(cfg, serie, tendencia, tmp_path):
    r = _registro(serie, tendencia, tmp_path, publicable=False, motivos_no_publicable=["voz de desarrollo (espeak)"])
    with pytest.raises(ErrorContenido, match="espeak"):
        Pipeline(cfg).publicar(r)


@pytest.mark.render
@pytest.mark.skipif(not RENDER, reason="render real: SF_TEST_RENDER=1")
def test_run_completo_real(cfg, tmp_path):
    if not (cfg.remotion_dir / "node_modules" / "remotion").is_dir() or shutil.which("espeak-ng") is None:
        pytest.skip("falta Remotion o espeak-ng")
    from shortsfactory.settings import Settings

    cfg = Settings(_env_file=None, llm_proveedor="plantilla", tts_motor="espeak", dir_runs=tmp_path / "runs",
                   dir_estado=tmp_path / "estado", remotion_browser=NAVEGADOR)
    r = Pipeline(cfg).ejecutar({"tema": "Inflación", "publicar": "no", "semilla": 5,
                                "serie_archivo": str(RAIZ / "ejemplos" / "serie-sintetica.json")})
    assert r.estado == Estado.COMPLETADO, r.error
    assert r.artefactos["qa"]["duracion"] <= 15.1 and r.artefactos["publicable"] is False
    assert not (cfg.remotion_dir / "public" / "runs" / r.run_id).exists()  # limpieza
