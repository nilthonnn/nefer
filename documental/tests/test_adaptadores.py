"""Adaptadores externos con dobles: MoneyPrinterTurbo y el SDK de Anthropic."""

import subprocess
import sys
import types
from dataclasses import replace
from enum import Enum
from pathlib import Path

import pytest

from documental import entrada, guionista
from documental.config import Secretos
from documental.errores import ErrorConfiguracion, ErrorVisual
from documental.visuales import mpt

from conftest import guion_minimo, requiere_ffmpeg


class _Aspecto(Enum):
    landscape = "16:9"


class _Item:
    def __init__(self, url, autor):
        self.url = url
        self.provider = "pexels"
        self.source_info = {"provider": "pexels", "creator": {"name": autor}, "source_page": url + "/pagina"}


def _material_falso(tmp_path, resultados):
    """Imita app.services.material: búsqueda + descarga a un clip de color real."""
    descargas = []

    def buscar(termino, minimo, aspecto):
        return resultados.get(termino, [])

    def save_video(url, carpeta):
        ruta = Path(carpeta) / f"{abs(hash(url))}.mp4"
        Path(carpeta).mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=640x360:r=15:d=3", str(ruta)], check=True)
        descargas.append(url)
        return str(ruta)

    material = types.SimpleNamespace(search_videos_pexels=buscar, search_videos_pixabay=buscar, save_video=save_video)
    config = types.SimpleNamespace(app={})
    return config, material, descargas


@pytest.fixture
def cfg_stock(cfg):
    return replace(cfg, secretos=Secretos(pexels_api_key="clave", mpt_dir="/no/importa"))


def test_mpt_dir_requerido(cfg):
    with pytest.raises(ErrorConfiguracion, match="PEXELS"):
        mpt.VisualStockMPT(cfg, Path("."))
    with pytest.raises(ErrorConfiguracion, match="MPT_DIR"):
        mpt._importar_mpt("")


@requiere_ffmpeg
def test_stock_concatena_atribuye_y_no_repite(tmp_path, cfg_stock, monkeypatch):
    resultados = {"sun": [_Item("https://v/1", "Ana"), _Item("https://v/2", "Luis")]}
    config_mpt, material, descargas = _material_falso(tmp_path, resultados)
    monkeypatch.setattr(mpt, "_importar_mpt", lambda d: (config_mpt, material, _Aspecto))
    proveedor = mpt.VisualStockMPT(cfg_stock, tmp_path / "cache")
    assert config_mpt.app["pexels_api_keys"] == ["clave"]

    escena = entrada.desde_dict(guion_minimo()).escenas[0]  # stock "sun"
    clip = proveedor.generar(escena, 5.0, tmp_path / "e1.mp4")
    assert not clip.propio and len(clip.ids_stock) == 2
    assert [a.autor for a in clip.atribuciones] == ["Ana", "Luis"]
    from documental.multimedia.ffmpeg import medir

    assert abs(medir(clip.ruta).duracion - 5.0) < 0.2

    # Los mismos resultados ya no sirven para otra escena: no se repiten clips.
    with pytest.raises(ErrorVisual):
        proveedor.generar(escena, 3.0, tmp_path / "e2.mp4")
    assert descargas == ["https://v/1", "https://v/2"]


def test_guionista_usa_herramienta_y_valida(monkeypatch, cfg):
    llamada = {}
    guion = guion_minimo()

    class _Mensajes:
        def create(self, **kw):
            llamada.update(kw)
            bloque = types.SimpleNamespace(type="tool_use", name="entregar_guion", input=guion)
            return types.SimpleNamespace(content=[bloque], stop_reason="tool_use")

    falso = types.ModuleType("anthropic")
    falso.Anthropic = lambda api_key: types.SimpleNamespace(messages=_Mensajes())
    for nombre in ("APIConnectionError", "RateLimitError", "InternalServerError", "APIStatusError"):
        setattr(falso, nombre, type(nombre, (Exception,), {}))
    monkeypatch.setitem(sys.modules, "anthropic", falso)

    cfg = replace(cfg, secretos=Secretos(anthropic_api_key="k", claude_model="claude-opus-5-5"))
    datos = guionista.escribir("historia del panel solar", cfg, minutos=8)
    assert entrada.desde_dict(datos).titulo == "Prueba de energía"
    assert llamada["model"] == "claude-opus-5-5"
    assert llamada["tool_choice"] == {"type": "tool", "name": "entregar_guion"}
    assert "1200 palabras" in llamada["messages"][0]["content"]


def test_guionista_sin_clave(cfg):
    with pytest.raises(ErrorConfiguracion, match="ANTHROPIC"):
        guionista.escribir("x", cfg)
