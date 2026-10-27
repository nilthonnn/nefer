"""Metadatos de YouTube: título, descripción, etiquetas y hashtags.

Reglas de YouTube que se respetan:
- título ≤ 100 caracteres; descripción ≤ 5000; etiquetas ≤ 500 en total;
- más de 15 hashtags hace que YouTube los ignore TODOS: se usan 3–4;
- los 3 primeros hashtags de la descripción aparecen sobre el título.
Nada de hashtags genéricos tipo #viral: no aportan y rozan la política de spam.
"""

from __future__ import annotations

from ..models import Guion, Serie, Tendencia


def titulo(guion: Guion) -> str:
    base = guion.titulo.strip()
    return base if len(base) + 8 > 100 else f"{base} #Shorts"


def hashtags(guion: Guion) -> list[str]:
    vistos, salida = set(), []
    for h in [*guion.hashtags, "#Shorts"]:
        if h.lower() not in vistos:
            vistos.add(h.lower())
            salida.append(h)
    return salida[:4]


def descripcion(guion: Guion, serie: Serie, tendencia: Tendencia, creditos: list[str]) -> str:
    p0, p1 = serie.puntos[0], serie.ultimo
    partes = [
        guion.descripcion.strip(),
        f"Dato: {serie.indicador} en {serie.pais_nombre}, {p0.anio}–{p1.anio}. Fuente: {serie.fuente} ({serie.url})",
    ]
    if tendencia.url:
        partes.append(f"Contexto: {tendencia.titulo} — {tendencia.url}")
    partes += [c for c in creditos if c]
    partes.append("Contenido informativo; no es asesoría financiera.")
    partes.append(" ".join(hashtags(guion)))
    return "\n\n".join(p for p in partes if p)[:5000]


def etiquetas(guion: Guion, serie: Serie) -> list[str]:
    candidatas = [h.lstrip("#") for h in guion.hashtags] + [serie.indicador, serie.pais_nombre, "economía", "tecnología", "datos"]
    salida, total = [], 0
    for e in candidatas:
        costo = len(e) + (2 if " " in e else 0) + 1
        if e and e not in salida and total + costo <= 500:
            salida.append(e)
            total += costo
    return salida
