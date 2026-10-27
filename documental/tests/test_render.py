"""Pruebas de integración con ffmpeg real (rápidas: 320×180)."""

import json
import subprocess
from pathlib import Path

import pytest

from documental import entrada
from documental.multimedia.ffmpeg import medir, verificar
from documental.multimedia.montaje import encadenar
from documental.errores import ErrorRender
from documental.pipeline import Opciones, producir

from conftest import guion_minimo, requiere_espeak, requiere_ffmpeg


def _color(ruta: Path, color: str, duracion: float):
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color={color}:s=320x180:r=15:d={duracion}",
                    "-pix_fmt", "yuv420p", str(ruta)], check=True)


@requiere_ffmpeg
def test_encadenar_conserva_sincronia(tmp_path, cfg):
    tramos = [2.0, 1.5, 2.5]
    T = cfg.video.transicion_segundos
    clips = []
    for i, (d, c) in enumerate(zip(tramos, ["red", "green", "blue"])):
        ruta = tmp_path / f"{i}.mp4"
        _color(ruta, c, d + (T if i < 2 else 0))
        clips.append(ruta)
    salida = tmp_path / "out.mp4"
    encadenar(clips, tramos, salida, cfg)
    assert abs(medir(salida).duracion - sum(tramos)) < 0.2


@requiere_ffmpeg
def test_verificar_detecta_duracion_incorrecta(tmp_path):
    ruta = tmp_path / "c.mp4"
    _color(ruta, "red", 1)
    with pytest.raises(ErrorRender, match="dura"):
        verificar(ruta, duracion=5)
    with pytest.raises(ErrorRender, match="audio"):
        verificar(ruta, audio=True)


@requiere_ffmpeg
@requiere_espeak
def test_render_completo_sin_servicios_externos(tmp_path, cfg):
    datos = guion_minimo(fuentes=["F"])
    datos["capitulos"].append({"titulo": "Dos", "escenas": [
        {"narracion": "Una línea de tiempo.", "visual": {"tipo": "linea_tiempo", "datos": {"titulo": "T", "hitos": [{"anio": "1954", "texto": "Bell"}]}}},
    ]})
    g = entrada.desde_dict(datos)
    from documental.voz.espeak import VozEspeak

    r = producir(g, cfg, VozEspeak(), Opciones(usar_remotion=False, usar_stock=False))
    m = verificar(r.video, video=True, audio=True)
    assert (m.ancho, m.alto) == (320, 180)
    assert abs(m.duracion - r.duracion) < 0.3
    for nombre in ("miniatura.jpg", "descripcion.txt", "subtitulos.srt", "metadatos.json", "auditoria.md", "render.log.jsonl"):
        assert (r.carpeta / nombre).is_file(), nombre
    meta = json.loads((r.carpeta / "metadatos.json").read_text(encoding="utf-8"))
    assert meta["capitulos"][0]["inicio"] == "00:00"
    # La escena de stock sin proveedor queda registrada como respaldo.
    assert "c01e01" in (r.carpeta / "auditoria.md").read_text(encoding="utf-8")

    # Segunda corrida: todo se reutiliza (no se regenera voz ni visuales).
    voz_antes = {p: p.stat().st_mtime for p in (r.carpeta / "trabajo" / "voz").glob("*.wav")}
    producir(g, cfg, VozEspeak(), Opciones(usar_remotion=False, usar_stock=False))
    assert voz_antes == {p: p.stat().st_mtime for p in (r.carpeta / "trabajo" / "voz").glob("*.wav")}


@requiere_ffmpeg
@requiere_espeak
def test_mejoras_de_monetizacion_en_el_pipeline(tmp_path, cfg):
    from dataclasses import replace

    from documental.errores import ErrorMonetizacion
    from documental.pipeline import secuencia
    from documental.voz.espeak import VozEspeak

    datos = guion_minimo(fuentes=["IRENA 2023"])
    datos["capitulos"].append({"titulo": "Dos", "escenas": [
        {"narracion": "Segunda parte.", "visual": {"tipo": "stock", "busqueda": ["wind"]}}]})
    g = entrada.desde_dict(datos)

    # Tarjeta de capítulo automática (no en el gancho).
    ids = [e.id for _, e in secuencia(g, cfg)]
    assert ids == ["c01e01", "c01e02", "capitulo01", "c02e01"]

    # La vista previa sale marcada y con otro nombre: imposible confundirla.
    r = producir(g, cfg, VozEspeak(), Opciones(usar_remotion=False, usar_stock=False))
    assert r.video.name == "prueba-de-energia.previa.mp4"
    meta = json.loads((r.carpeta / "metadatos.json").read_text(encoding="utf-8"))
    assert meta["previa"] is True
    assert [c["titulo"] for c in meta["capitulos"]] == ["Uno", "Dos"]
    assert "licencia comercial" in (r.carpeta / "auditoria.md").read_text(encoding="utf-8")

    # --estricto con un guion copiado de otro video del canal se detiene ANTES
    # de sintetizar la voz. (Las vistas previas no cuentan como publicadas.)
    from documental.monetizacion import registrar

    otro = replace(g, slug="copia", titulo="Copia")

    registrar(cfg.salida / "registro.jsonl", g, 60, previa=False)
    with pytest.raises(ErrorMonetizacion, match="se parece"):
        producir(otro, cfg, VozEspeak(), Opciones(usar_remotion=False, usar_stock=False, estricto=True))
    assert not (cfg.salida / "copia" / "trabajo" / "voz").exists()
