"""Sistema de diseño generativo: cada Short sale con una combinación distinta.

Se sortean paleta, tipografía, estilo de subtítulos, fondo, gráfico,
transición, intensidad de movimiento y ritmo de voz. El sorteo:
- es reproducible (semilla por run, guardada en el estado),
- evita las combinaciones de los Shorts recientes: se generan varias
  candidatas y se elige la que MÁS difiere de las últimas producidas,
- solo usa paletas con contraste legible (WCAG ≥ 4.5 entre texto y fondo).

Importante: la variación visual hace el canal más atractivo, pero NO
convierte en "original" un contenido que no aporta nada. Lo que sostiene
la monetización es el dato real y el guion propio; esto evita además
la monotonía que sí penaliza la retención.
"""

from __future__ import annotations

import random

from ..models import Variacion

# fondo1, fondo2, texto, acento (énfasis/gráfico), resaltado (palabra activa)
PALETAS: dict[str, dict[str, str]] = {
    "medianoche": {"fondo1": "#0b1020", "fondo2": "#1b2a4a", "texto": "#ffffff", "acento": "#4cc9f0", "resaltado": "#ffd60a"},
    "bolsa": {"fondo1": "#05140c", "fondo2": "#0e3b24", "texto": "#f1fff6", "acento": "#2ee59d", "resaltado": "#ff5d5d"},
    "brasa": {"fondo1": "#1a0b07", "fondo2": "#4a1608", "texto": "#fff5ee", "acento": "#ff8a3d", "resaltado": "#ffe066"},
    "neon": {"fondo1": "#0d0221", "fondo2": "#2a0a4a", "texto": "#ffffff", "acento": "#f72585", "resaltado": "#4cc9f0"},
    "papel": {"fondo1": "#f4efe6", "fondo2": "#e3d8c3", "texto": "#141414", "acento": "#d62828", "resaltado": "#1d3557"},
    "pizarra": {"fondo1": "#1e2329", "fondo2": "#2f3640", "texto": "#f5f6fa", "acento": "#fbc531", "resaltado": "#00d2d3"},
    "oceano": {"fondo1": "#001219", "fondo2": "#005f73", "texto": "#e9fbff", "acento": "#94d2bd", "resaltado": "#ee9b00"},
    "lima": {"fondo1": "#111111", "fondo2": "#232323", "texto": "#ffffff", "acento": "#c6f432", "resaltado": "#c6f432"},
    "coral": {"fondo1": "#fff1ea", "fondo2": "#ffd9c7", "texto": "#1b1b1b", "acento": "#e4572e", "resaltado": "#2e86ab"},
    "acero": {"fondo1": "#0f1720", "fondo2": "#33475b", "texto": "#ffffff", "acento": "#9ad1ff", "resaltado": "#ffb703"},
}
# Familias de Google Fonts cargadas por Remotion (@remotion/google-fonts).
FUENTES = ("Inter", "Montserrat", "Anton", "BebasNeue", "Poppins", "Oswald")
ESTILOS_SUBTITULOS = ("caja", "pop", "subrayado")
FONDOS = ("degradado", "reticula", "orbitas")
GRAFICOS = ("linea", "barras")
TRANSICIONES = ("deslizar", "zoom", "barrido")


def _luminancia(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contraste(a: str, b: str) -> float:
    la, lb = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def sortear(rng: random.Random, semilla: int) -> Variacion:
    paleta = rng.choice(sorted(PALETAS))
    return Variacion(
        paleta=paleta,
        colores=PALETAS[paleta],
        fuente=rng.choice(FUENTES),
        estilo_subtitulos=rng.choice(ESTILOS_SUBTITULOS),
        palabras_por_pagina=rng.choice((1, 2, 2, 3)),
        mayusculas=rng.random() < 0.6,
        posicion_subtitulos=round(rng.uniform(0.55, 0.72), 3),
        fondo=rng.choice(FONDOS),
        estilo_grafico=rng.choice(GRAFICOS),
        transicion=rng.choice(TRANSICIONES),
        intensidad_movimiento=round(rng.uniform(0.04, 0.10), 3),
        velocidad_voz=round(rng.uniform(0.96, 1.08), 3),
        pausa_gancho=round(rng.uniform(0.12, 0.32), 3),
        semilla=semilla,
    )


def distancia(a: dict[str, str], b: dict[str, str]) -> int:
    return sum(a.get(k) != b.get(k) for k in a)


def elegir(semilla: int, recientes: list[dict[str, str]], candidatas: int = 24) -> Variacion:
    """La candidata cuya distancia mínima a los diseños recientes es mayor."""
    rng = random.Random(semilla)
    opciones = [sortear(rng, semilla) for _ in range(candidatas)]
    if not recientes:
        return opciones[0]
    return max(opciones, key=lambda v: (min(distancia(v.firma(), r) for r in recientes),
                                         sum(distancia(v.firma(), r) for r in recientes)))
