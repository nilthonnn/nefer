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


def test_qa_exige_datos_verificables(monkeypatch, cfg, serie, tendencia, tmp_path):
    from shortsfactory import qa

    monkeypatch.setattr(qa, "revisar", lambda *a, **k: {"duracion": 14.0, "lufs": -14.0})
    p = Pipeline(cfg)
    base = _registro(serie, tendencia, tmp_path, voz_publicable=True)
    base.artefactos["guion"]["generador"] = "editorial"
    # Serie local sin URL (la sintética): bloqueada.
    assert p.qa(base)["motivos_no_publicable"] == ["datos locales sin URL de fuente verificable"]
    # Serie del Banco Mundial: publicable.
    base.artefactos["serie_origen"] = "worldbank"
    salida = p.qa(base)
    assert salida["publicable"] is True and salida["motivos_no_publicable"] == []


def test_publicar_usa_seo_rapido_y_sube_la_miniatura(monkeypatch, cfg, serie, tendencia, tmp_path):
    from shortsfactory.models import ResultadoSubida
    from shortsfactory.publisher import youtube

    capturado, miniaturas = {}, []

    def subir(cfg_, video, meta, yt=None):
        capturado.update(meta)
        return ResultadoSubida(video_id="v9", url="https://youtube.com/shorts/v9", privacidad="private",
                               titulo=meta["snippet"]["title"], unidades_cuota=1600)

    monkeypatch.setattr(youtube, "subir", subir)
    monkeypatch.setattr(youtube, "subir_miniatura", lambda cfg_, vid, img, yt=None: miniaturas.append((vid, img)) or True)
    rapido = type("R", (), {"json": lambda self, *a, **k: {
        "titulo": "Por qué la inflación sigue lejos de 2014", "etiquetas": ["inflación", "precios", "datos"],
        "gancho": "Un dato que el gráfico deja claro."}})()
    imagen = tmp_path / "miniatura.jpg"
    imagen.write_bytes(b"\xff\xd8")
    p = Pipeline(cfg.model_copy(update={"seo_llm": True}), modelo_rapido=rapido)
    salida = p.publicar(_registro(serie, tendencia, tmp_path, miniatura=str(imagen)))
    assert capturado["snippet"]["title"].startswith("Por qué la inflación")
    assert capturado["snippet"]["tags"][0] == "inflación"
    assert miniaturas == [("v9", imagen)] and salida["miniatura_subida"] is True
