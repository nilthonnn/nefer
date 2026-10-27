"""Auditoría de monetización antes de publicar.

YouTube (Programa de Socios) no monetiza el contenido "no auténtico":
producido en masa, repetitivo o que reutiliza material ajeno sin aportar
nada. Esta auditoría no garantiza la aprobación —la decide una persona en
YouTube— pero detecta de forma objetiva lo que más suele provocar el rechazo.

Niveles:
- ``bloqueo``: no publicar así (con ``--estricto`` detiene el render).
- ``aviso``: se puede publicar, pero se pierde alcance o ingresos.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import Config
from .modelos import ClipEscena, Guion, Tramo
from .publicacion import capitulos, problemas_capitulos


@dataclass
class Hallazgo:
    nivel: str  # "bloqueo" | "aviso"
    mensaje: str


def _bigramas(texto: str) -> set[tuple[str, str]]:
    palabras = re.findall(r"\w+", texto.lower())
    return set(zip(palabras, palabras[1:]))


def similitud(a: str, b: str) -> float:
    """Jaccard de bigramas de palabras (0 = nada en común, 1 = idénticos)."""
    x, y = _bigramas(a), _bigramas(b)
    if not x or not y:
        return 0.0
    return len(x & y) / len(x | y)


def texto_narrado(guion: Guion) -> str:
    return " ".join(e.narracion for e in guion.escenas)


def leer_registro(ruta: Path) -> list[dict]:
    if not ruta.is_file():
        return []
    entradas = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        try:
            entradas.append(json.loads(linea))
        except json.JSONDecodeError:
            continue
    return entradas


def registrar(ruta: Path, guion: Guion, duracion: float, previa: bool) -> None:
    """Añade el video al historial del canal (para detectar repeticiones futuras)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "slug": guion.slug,
            "titulo": guion.titulo,
            "duracion": round(duracion, 1),
            "previa": previa,
            "narracion": texto_narrado(guion),
        }, ensure_ascii=False) + "\n")


def auditar(
    guion: Guion,
    tramos: list[Tramo],
    clips: dict[str, ClipEscena],
    respaldos: dict[str, str],
    voz_comercial: bool,
    historial: list[dict],
    cfg: Config,
) -> list[Hallazgo]:
    m = cfg.monetizacion
    h: list[Hallazgo] = []
    total = tramos[-1].inicio + tramos[-1].duracion if tramos else 0.0

    if not voz_comercial:
        h.append(Hallazgo("bloqueo", "La voz es de vista previa (espeak-ng): genera con ElevenLabs antes de publicar."))

    if total < m.minutos_minimos * 60:
        h.append(Hallazgo("aviso", f"Dura {total / 60:.1f} min: con menos de {m.minutos_minimos:.0f} min no se pueden poner anuncios a mitad del video."))

    for p in problemas_capitulos(capitulos(tramos), total):
        h.append(Hallazgo("aviso", f"Capítulos: {p}."))

    # Originalidad visual: proporción de escenas con visual propio.
    if clips:
        propios = sum(1 for c in clips.values() if c.propio)
        proporcion = propios / len(clips)
        if proporcion < m.proporcion_visual_propio:
            h.append(Hallazgo("aviso", f"Solo {proporcion:.0%} de las escenas tiene visual propio (mínimo recomendado {m.proporcion_visual_propio:.0%}); "
                                       "añade cifras, líneas de tiempo o comparativas."))
        vistos: dict[str, str] = {}
        for escena, c in clips.items():
            for i in c.ids_stock:
                if i in vistos:
                    h.append(Hallazgo("bloqueo", f"El clip de stock {i} se repite en {vistos[i]} y {escena}."))
                vistos[i] = escena

    for escena, motivo in respaldos.items():
        h.append(Hallazgo("aviso", f"Escena {escena} usó un visual de respaldo ({motivo})."))

    if not guion.fuentes:
        h.append(Hallazgo("aviso", "El guion no cita fuentes: los datos sin respaldo restan credibilidad (y la revisión humana lo nota)."))

    # Ritmo de narración: muy lento aburre, muy rápido suena a resumen automático.
    palabras = sum(len(t.locucion.palabras) for t in tramos)
    habla = sum(t.locucion.duracion for t in tramos)
    if habla > 0:
        ppm = palabras / habla * 60
        if not 120 <= ppm <= 185:
            h.append(Hallazgo("aviso", f"Ritmo de narración {ppm:.0f} palabras/min (lo habitual en documental: 130–170)."))

    # Contenido repetitivo frente al resto del canal.
    actual = texto_narrado(guion)
    for previo in historial:
        if previo.get("previa") or previo.get("slug") == guion.slug:
            continue
        s = similitud(actual, previo.get("narracion", ""))
        if s > m.similitud_maxima:
            h.append(Hallazgo("bloqueo", f"El guion se parece un {s:.0%} a «{previo.get('titulo')}»: YouTube lo trataría como contenido repetitivo."))

    if len(guion.titulo) > 100:
        h.append(Hallazgo("aviso", "El título supera 100 caracteres y YouTube lo cortará."))
    return h


def informe(hallazgos: list[Hallazgo]) -> str:
    if not hallazgos:
        return "# Auditoría de monetización\n\nSin observaciones.\n"
    filas = ["# Auditoría de monetización", ""]
    for nivel, titulo in (("bloqueo", "Bloqueos (no publicar así)"), ("aviso", "Avisos")):
        grupo = [x for x in hallazgos if x.nivel == nivel]
        if grupo:
            filas += [f"## {titulo}", ""] + [f"- {x.mensaje}" for x in grupo] + [""]
    filas += [
        "## Recordatorios al subir",
        "",
        "- En YouTube Studio, marca «Contenido alterado o sintético» solo si muestras personas, lugares o hechos realistas que no ocurrieron.",
        "- Sube `subtitulos.srt` como subtítulos en español (Latinoamérica).",
        "- Añade los elementos de pantalla final en los últimos 20 s.",
        "",
    ]
    return "\n".join(filas)
