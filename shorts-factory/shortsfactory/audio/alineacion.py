"""Tiempos por palabra: del motor (exactos) o estimados por fonemas.

Kokoro en español no devuelve tiempos por palabra (solo lo hace en inglés),
pero sí la duración predicha de cada FONEMA (``pred_dur``, en unidades de
1/40 s; los espacios del texto fonético separan palabras). Con eso se
reconstruyen los tiempos de cada palabra con precisión de ~25 ms, que es lo
que permite resaltar la palabra exacta en los subtítulos.
"""

from __future__ import annotations

import re

from ..models import PalabraT

UNIDAD_KOKORO = 1 / 40  # segundos por unidad de pred_dur (hop 600 a 24 kHz)


def _palabras(texto: str) -> list[str]:
    return [p for p in texto.split() if re.search(r"\w", p)]


def desde_fonemas(texto: str, fonemas: str, pred_dur: list[int]) -> list[PalabraT]:
    """Kokoro: ``pred_dur`` tiene len(fonemas)+2 elementos (inicio y fin de secuencia)."""
    if len(pred_dur) != len(fonemas) + 2:
        raise ValueError(f"pred_dur ({len(pred_dur)}) no corresponde a los fonemas ({len(fonemas)}+2)")
    t = max(0, pred_dur[0] - 3) * UNIDAD_KOKORO  # mismo desfase que usa Kokoro en inglés
    grupos: list[tuple[float, float]] = []
    inicio: float | None = None
    for i, ch in enumerate(fonemas):
        d = pred_dur[i + 1] * UNIDAD_KOKORO
        if ch == " ":
            if inicio is not None:
                grupos.append((inicio, t))
                inicio = None
        elif inicio is None:
            inicio = t
        t += d
    if inicio is not None:
        grupos.append((inicio, t))
    return _asignar(_palabras(texto), grupos)


def _asignar(palabras: list[str], grupos: list[tuple[float, float]]) -> list[PalabraT]:
    """Empareja palabras escritas con grupos fonéticos.

    Si coinciden en número, 1:1. Si no (p. ej. "2024" se pronuncia en 4
    palabras), se reparte el tramo total proporcionalmente al largo de cada
    palabra dentro de los grupos, sin perder el inicio y el fin reales.
    """
    if not palabras or not grupos:
        return []
    if len(palabras) == len(grupos):
        return [PalabraT(texto=p, inicio=round(a, 3), fin=round(b, 3)) for p, (a, b) in zip(palabras, grupos)]
    return estimar(palabras, grupos[0][0], grupos[-1][1])


def _peso(palabra: str) -> float:
    """Aproximación a sílabas: grupos vocálicos (los números pesan por dígitos)."""
    digitos = sum(c.isdigit() for c in palabra)
    vocales = len(re.findall(r"[aeiouáéíóúü]+", palabra.lower()))
    return max(1.0, vocales + digitos * 1.5) + (0.6 if re.search(r"[.,;:!?…]$", palabra) else 0)


def estimar(palabras: list[str] | str, inicio: float, fin: float) -> list[PalabraT]:
    """Reparte [inicio, fin] entre las palabras según su peso silábico."""
    lista = _palabras(palabras) if isinstance(palabras, str) else palabras
    if not lista:
        return []
    pesos = [_peso(p) for p in lista]
    total = sum(pesos)
    salida, t = [], inicio
    for p, w in zip(lista, pesos):
        d = (fin - inicio) * w / total
        salida.append(PalabraT(texto=p, inicio=round(t, 3), fin=round(t + d * 0.94, 3)))
        t += d
    return salida


def desde_limites_edge(texto: str, limites: list[tuple[float, float, str]]) -> list[PalabraT]:
    """Edge TTS: eventos WordBoundary (inicio, duración, texto) → palabras con puntuación original."""
    palabras = _palabras(texto)
    if len(palabras) == len(limites):
        return [PalabraT(texto=p, inicio=round(a, 3), fin=round(a + d, 3)) for p, (a, d, _) in zip(palabras, limites)]
    if not limites:
        return []
    return estimar(palabras, limites[0][0], limites[-1][0] + limites[-1][1])
