"""Contrato común de los proveedores de voz y utilidades de tiempos por palabra."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from ..modelos import Locucion, Palabra


class ProveedorVoz(Protocol):
    nombre: str
    # False = solo vista previa: su licencia o calidad no sirve para monetizar.
    comercial: bool

    def licencia(self) -> tuple[bool | None, str]:
        """(¿uso comercial permitido?, detalle). None = no se pudo verificar."""
        ...

    def huella(self) -> str:
        """Identifica voz+modelo+ajustes; si cambia, la caché de audio se invalida."""
        ...

    def sintetizar(self, texto: str, destino: Path, anterior: str = "", siguiente: str = "") -> Locucion:
        """Genera el audio de ``texto`` en ``destino`` (sin extensión; el proveedor la pone).

        ``anterior``/``siguiente`` son las frases vecinas: ElevenLabs las usa
        para que la entonación fluya entre escenas en vez de sonar a frases sueltas.
        """
        ...


def palabras_desde_caracteres(caracteres: list[str], inicios: list[float], fines: list[float]) -> list[Palabra]:
    """Convierte la alineación por carácter de ElevenLabs en tiempos por palabra."""
    if not (len(caracteres) == len(inicios) == len(fines)):
        raise ValueError("alineación inconsistente: listas de distinto largo")
    palabras: list[Palabra] = []
    actual: list[str] = []
    inicio = fin = 0.0
    for c, i, f in zip(caracteres, inicios, fines):
        if c.isspace():
            if actual:
                palabras.append(Palabra("".join(actual), inicio, fin))
                actual = []
            continue
        if not actual:
            inicio = i
        actual.append(c)
        fin = f
    if actual:
        palabras.append(Palabra("".join(actual), inicio, fin))
    return palabras


def estimar_palabras(texto: str, duracion: float, margen: float = 0.1) -> list[Palabra]:
    """Reparte la duración entre palabras según su largo (para voces sin alineación).

    Las comas y puntos suman un poco de peso: ahí la voz hace pausa.
    """
    tokens = texto.split()
    if not tokens:
        return []
    pesos = [len(t) + (3 if re.search(r"[.,;:!?…]$", t) else 0) + 1 for t in tokens]
    util = max(0.01, duracion - 2 * margen)
    total = sum(pesos)
    palabras, t = [], margen
    for token, peso in zip(tokens, pesos):
        d = util * peso / total
        palabras.append(Palabra(token, round(t, 3), round(t + d * 0.92, 3)))
        t += d
    return palabras
