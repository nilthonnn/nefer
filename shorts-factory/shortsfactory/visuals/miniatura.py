"""Miniatura propia (1280×720) renderizada con Remotion (`remotion still`).

El protagonista es el dato más impactante DEL GUION: la primera cifra que
dice la narración (el gancho, por diseño) que además se pueda trazar a la
serie. Si el guion no dice ninguna, el último valor de la serie. Nunca se
inventa un número para la miniatura.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..errors import ErrorConfiguracion, ErrorRender
from ..models import Guion, Serie, Variacion
from ..proc import ejecutar
from ..scripts.editorial import cifra
from ..scripts.heuristicas import numeros
from ..settings import Settings

LIMITE_BYTES = 2 * 1024 * 1024  # YouTube rechaza miniaturas de más de 2 MB


def _con_unidad(valor: float, unidad: str) -> str:
    return f"{cifra(valor)} %" if unidad.strip().startswith("%") else cifra(valor)


def dato_impactante(guion: Guion, serie: Serie) -> tuple[str, str]:
    """(cifra, contexto) para la miniatura."""
    p0, p1 = serie.puntos[0], serie.ultimo
    candidatos: list[tuple[float, str, str]] = [
        (p.valor, _con_unidad(p.valor, serie.unidad), f"{serie.pais_nombre} · {p.anio}") for p in reversed(serie.puntos)
    ]
    if p0.valor:
        cambio = (p1.valor - p0.valor) / abs(p0.valor) * 100
        signo = "+" if cambio > 0 else "−"
        for dec in (0, 1):
            v = round(abs(cambio), dec)
            candidatos.append((v, f"{signo}{cifra(v)} %", f"{serie.pais_nombre} · {p0.anio}–{p1.anio}"))
    anios = {float(p.anio) for p in serie.puntos}
    for n in numeros(guion.texto):
        if n in anios:
            continue
        for valor, texto, contexto in candidatos:
            if abs(valor - n) < 0.051:
                return texto, contexto
    return _con_unidad(p1.valor, serie.unidad), f"{serie.pais_nombre} · {p1.anio}"


def props(guion: Guion, serie: Serie, variacion: Variacion, titulo: str | None = None) -> dict:
    valor, contexto = dato_impactante(guion, serie)
    return {
        "titulo": (titulo or guion.titulo)[:100],
        "cifra": valor[:16],
        "contexto": contexto[:80],
        "fuente": f"Fuente: {serie.fuente}"[:120],
        "colores": variacion.colores,
        "tipografia": variacion.fuente,
    }


def renderizar(cfg: Settings, datos: dict, salida: Path) -> Path:
    if not (cfg.remotion_dir / "node_modules" / "remotion").is_dir():
        raise ErrorConfiguracion(f"Remotion sin instalar: cd {cfg.remotion_dir} && npm ci")
    salida.parent.mkdir(parents=True, exist_ok=True)
    ruta_props = salida.with_suffix(".props.json")
    ruta_props.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    cmd = ["npx", "--no-install", "remotion", "still", "src/index.ts", "Miniatura", str(salida.resolve()),
           f"--props={ruta_props.resolve()}", "--image-format=jpeg", "--jpeg-quality=90", "--log=error"]
    if cfg.remotion_browser:
        cmd.append(f"--browser-executable={cfg.remotion_browser}")
    ejecutar(cmd, "remotion still (miniatura)", timeout=300, cwd=cfg.remotion_dir)
    if not salida.is_file() or salida.stat().st_size == 0:
        raise ErrorRender(f"la miniatura no se generó: {salida}")
    if salida.stat().st_size > LIMITE_BYTES:
        raise ErrorRender(f"la miniatura pesa {salida.stat().st_size / 1e6:.1f} MB (YouTube admite hasta 2 MB)")
    return salida
