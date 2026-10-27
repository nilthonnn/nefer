"""Puente con Remotion: arma las props (validadas por Zod en TypeScript) y renderiza.

Los archivos del run (narración y b-roll) se copian a
``remotion/public/runs/<run_id>/`` porque Remotion solo sirve archivos
de ``public/``. El MP4 sale en H.264 + AAC, 1080×1920.
"""

from __future__ import annotations

import json
import math
import os
import shutil
from pathlib import Path

from ..errors import ErrorConfiguracion, ErrorRender, ErrorRenderTransitorio
from ..models import Frase, Guion, Narracion, Segmento, Serie, Variacion
from ..proc import ejecutar
from ..settings import Settings
from .subtitulos import paginar


def segmentos(guion: Guion, narracion: Narracion, brolls: dict[int, str]) -> list[Segmento]:
    """Una escena por frase: empieza cuando empieza la frase y dura hasta la siguiente."""
    salida = []
    for i, (frase, (inicio, _)) in enumerate(zip(guion.frases, narracion.frases)):
        fin = narracion.frases[i + 1][0] if i + 1 < len(guion.frases) else narracion.duracion
        tipo = frase.visual if not (frase.visual == "broll" and i not in brolls) else "texto"
        salida.append(Segmento(inicio=0.0 if i == 0 else inicio, fin=fin, tipo=tipo,
                               texto=_titular(frase), archivo=brolls.get(i, "")))
    return salida


def _titular(frase: Frase) -> str:
    return frase.texto.rstrip(".…")


def props(run_id: str, guion: Guion, narracion: Narracion, serie: Serie, variacion: Variacion,
          segs: list[Segmento], fps: int) -> dict:
    v = variacion
    return {
        "fps": fps,
        "duracionFrames": math.ceil(narracion.duracion * fps),
        "audio": f"runs/{run_id}/{narracion.audio.name}",
        "diseno": {
            "colores": v.colores, "fuente": v.fuente, "estiloSubtitulos": v.estilo_subtitulos,
            "mayusculas": v.mayusculas, "posicionSubtitulos": v.posicion_subtitulos, "fondo": v.fondo,
            "estiloGrafico": v.estilo_grafico, "transicion": v.transicion, "intensidad": v.intensidad_movimiento,
        },
        "segmentos": [
            {"desde": round(s.inicio * fps), "hasta": round(s.fin * fps), "tipo": s.tipo, "texto": s.texto,
             "video": s.archivo}
            for s in segs
        ],
        "serie": {"titulo": serie.indicador, "pais": serie.pais_nombre, "unidad": serie.unidad,
                  "puntos": [{"x": p.anio, "y": p.valor} for p in serie.puntos]},
        "paginas": [
            {"desde": pg.inicio, "hasta": pg.fin,
             "palabras": [{"texto": w.texto, "inicio": w.inicio, "fin": w.fin, "enfasis": w.enfasis} for w in pg.palabras]}
            for pg in paginar(narracion.palabras, v.palabras_por_pagina)
        ],
        "fuente": f"Fuente: {serie.fuente} · {serie.indicador_id}",
    }


def preparar_public(cfg: Settings, run_id: str, archivos: list[Path]) -> Path:
    destino = cfg.remotion_dir / "public" / "runs" / run_id
    destino.mkdir(parents=True, exist_ok=True)
    for a in archivos:
        shutil.copy2(a, destino / a.name)
    return destino


def limpiar_public(cfg: Settings, run_id: str) -> None:
    shutil.rmtree(cfg.remotion_dir / "public" / "runs" / run_id, ignore_errors=True)


def renderizar(cfg: Settings, datos: dict, salida: Path) -> None:
    if not (cfg.remotion_dir / "node_modules" / "remotion").is_dir():
        raise ErrorConfiguracion(f"Remotion sin instalar: cd {cfg.remotion_dir} && npm ci")
    ruta_props = salida.with_suffix(".props.json")
    ruta_props.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    cmd = ["npx", "--no-install", "remotion", "render", "src/index.ts", "Short", str(salida.resolve()),
           f"--props={ruta_props.resolve()}", "--codec=h264", "--crf=18", "--audio-codec=aac",
           "--log=error", f"--concurrency={max(1, (os.cpu_count() or 2) // 2)}"]
    if cfg.remotion_browser:
        cmd.append(f"--browser-executable={cfg.remotion_browser}")
    try:
        ejecutar(cmd, "remotion render", timeout=1800, cwd=cfg.remotion_dir)
    except ErrorRender as e:
        # El navegador headless muere a veces por memoria: la FSM reintenta la etapa.
        raise ErrorRenderTransitorio(str(e), e.comando, e.stderr) from e
