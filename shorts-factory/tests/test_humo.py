from __future__ import annotations

import os
from pathlib import Path

import pytest

from shortsfactory.visuals import provisional, variacion

from conftest import guion_bueno, requiere_ffmpeg

# Se lee al importar: el fixture autouse limpia las variables SF_* antes de cada prueba.
NAVEGADOR = os.environ.get("SF_REMOTION_BROWSER", "")
RENDER = os.environ.get("SF_TEST_RENDER") == "1"


def test_narracion_estimada_ordenada_y_sin_huecos_negativos():
    g = guion_bueno()
    n = provisional.narracion_estimada(g, Path("x.wav"))
    assert len(n.frases) == len(g.frases)
    inicios = [a for a, _ in n.frases]
    assert inicios == sorted(inicios)
    assert all(b > a for a, b in n.frases)
    assert all(p.fin >= p.inicio for p in n.palabras)
    assert n.duracion >= n.frases[-1][1]
    assert any(p.enfasis for p in n.palabras)


def test_props_provisionales_tienen_el_contrato_del_render(serie):
    g = guion_bueno()
    v = variacion.elegir(3, [])
    datos = provisional.props_provisionales("r1", g, serie, v, 30)
    assert datos["duracionFrames"] > 0
    assert len(datos["segmentos"]) == len(g.frases)
    for s in datos["segmentos"]:
        assert s["hasta"] > s["desde"]
        assert s["tipo"] != "broll"  # sin b-roll, el render usa texto
    assert datos["paginas"] and all(pg["palabras"] for pg in datos["paginas"])


@pytest.mark.render
@requiere_ffmpeg
@pytest.mark.skipif(not RENDER, reason="render real: SF_TEST_RENDER=1")
def test_humo_renderiza_150_fotogramas(cfg, tmp_path):
    from shortsfactory.humo import ejecutar

    cfg = cfg.model_copy(update={"remotion_browser": NAVEGADOR})
    salida = ejecutar(cfg, tmp_path / "humo.mp4", fotogramas=150)
    assert salida.is_file() and salida.stat().st_size > 0
