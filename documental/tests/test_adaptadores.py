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


def guion_largo(titulo="Historia de la batería") -> dict:
    """Guion que pasa la auditoría: 4 capítulos, ~10 min, 50 % visual propio, con fuentes."""
    frase = " ".join(f"palabra{i}" for i in range(80)) + "."
    capitulos = []
    for c in range(4):
        escenas = []
        for e in range(4):
            if e % 2:
                visual = {"tipo": "cifra", "datos": {"valor": 1, "etiqueta": "x", "fuente": "IRENA 2023"}}
            else:
                visual = {"tipo": "stock", "busqueda": [f"plano {c} {e}"]}
            escenas.append({"narracion": f"Capítulo {c} escena {e}. {frase}", "visual": visual})
        capitulos.append({"titulo": f"Capítulo {c}", "escenas": escenas})
    return {"titulo": titulo, "miniatura": "X", "descripcion": "d", "etiquetas": ["a"],
            "fuentes": ["IRENA, Renewable Power Generation Costs 2023"], "capitulos": capitulos}


def _anthropic_falso(monkeypatch, entregas):
    llamadas = []

    class _Mensajes:
        def create(self, **kw):
            llamadas.append({**kw, "messages": list(kw["messages"])})
            bloque = types.SimpleNamespace(type="tool_use", name="entregar_guion", id=f"t{len(llamadas)}",
                                           input=entregas[len(llamadas) - 1])
            return types.SimpleNamespace(content=[bloque], stop_reason="tool_use")

    falso = types.ModuleType("anthropic")
    falso.Anthropic = lambda api_key: types.SimpleNamespace(messages=_Mensajes())
    for nombre in ("APIConnectionError", "RateLimitError", "InternalServerError", "APIStatusError"):
        setattr(falso, nombre, type(nombre, (Exception,), {}))
    monkeypatch.setitem(sys.modules, "anthropic", falso)
    return llamadas


def test_guionista_corrige_contra_la_auditoria(monkeypatch, cfg):
    # 1.ª entrega: corta y sin fuentes → se devuelve con los problemas; 2.ª: correcta.
    llamadas = _anthropic_falso(monkeypatch, [guion_minimo(), guion_largo()])
    cfg = replace(cfg, video=replace(cfg.video, pantalla_final_segundos=20),
                  secretos=Secretos(anthropic_api_key="k", claude_model="claude-opus-5-5"))
    historial = [{"titulo": "Viejo", "estructura": "cronologica", "narracion": "nada que ver"}]
    datos = guionista.escribir("historia de la batería", cfg, minutos=8, historial=historial)

    assert len(llamadas) == 2
    assert datos["titulo"] == "Historia de la batería"
    assert datos["estructura"] != "cronologica"  # la usada en el último video
    primera = llamadas[0]
    assert primera["model"] == "claude-opus-5-5"
    assert primera["tool_choice"] == {"type": "tool", "name": "entregar_guion"}
    assert "1350 palabras" in primera["messages"][0]["content"]  # se sube a 9 min (mínimo 8 + 1)
    assert "Viejo" in primera["messages"][0]["content"]  # conoce lo ya publicado
    correccion = llamadas[1]["messages"][-1]["content"][0]
    assert correccion["type"] == "tool_result" and correccion["tool_use_id"] == "t1"
    assert "Duración" in correccion["content"]


def test_guionista_rechaza_copia_del_canal(monkeypatch, cfg):
    largo = guion_largo()
    narracion = " ".join(e["narracion"] for c in largo["capitulos"] for e in c["escenas"])
    llamadas = _anthropic_falso(monkeypatch, [largo, largo, largo])
    cfg = replace(cfg, video=replace(cfg.video, pantalla_final_segundos=20), secretos=Secretos(anthropic_api_key="k"))
    guionista.escribir("x", cfg, historial=[{"slug": "otro", "titulo": "Otro", "narracion": narracion}])
    # Se agotan las 2 correcciones porque sigue siendo una copia.
    assert len(llamadas) == 3
    assert "se parece" in llamadas[1]["messages"][-1]["content"][0]["content"]


def test_estructura_rota_entre_videos():
    historial = [{"estructura": e} for e in ("cronologica", "misterio", "mitos", "caso")]
    assert guionista.elegir_estructura(historial) == "comparacion"
    historial.append({"estructura": "comparacion"})
    assert guionista.elegir_estructura(historial) == "cronologica"  # la más antigua
    with pytest.raises(ErrorConfiguracion):
        guionista.elegir_estructura([], "inventada")


def test_guionista_sin_clave(cfg):
    with pytest.raises(ErrorConfiguracion, match="ANTHROPIC"):
        guionista.escribir("x", cfg)


@requiere_ffmpeg
def test_stock_no_reutiliza_clips_de_otros_videos(tmp_path, cfg_stock, monkeypatch):
    resultados = {"sun": [_Item("https://v/1", "Ana"), _Item("https://v/2", "Luis")]}
    config_mpt, material, descargas = _material_falso(tmp_path, resultados)
    monkeypatch.setattr(mpt, "_importar_mpt", lambda d: (config_mpt, material, _Aspecto))
    proveedor = mpt.VisualStockMPT(cfg_stock, tmp_path / "cache", prohibidos={mpt.huella("https://v/1")})
    escena = entrada.desde_dict(guion_minimo()).escenas[0]
    clip = proveedor.generar(escena, 3.0, tmp_path / "e1.mp4")
    assert descargas == ["https://v/2"]
    assert [a.autor for a in clip.atribuciones] == ["Luis"]
