"""Narración y props PROVISIONALES: sin sintetizar voz.

Sirven para dos cosas que deben ser baratas:
- el render de humo de los PR (``humo.py``): comprueba que Remotion compila
  y que las props pasan Zod, con audio mudo;
- la validación temprana del guion contra ``remotion/src/schema.ts`` antes de
  pagar la voz y el render (``scripts/generador.py``).

Los tiempos se reparten por peso silábico (``alineacion.estimar``) a un
ritmo de locución normal; no son los reales, pero respetan las mismas
restricciones (orden, duración positiva, palabras no vacías).
"""

from __future__ import annotations

from pathlib import Path

from ..audio import alineacion
from ..models import Guion, Narracion, PalabraT, Serie, Variacion
from . import render

SEGUNDOS_POR_PALABRA = 0.36  # ~2,8 palabras/s: locución de Short
PAUSA_ENTRE_FRASES = 0.15


def narracion_estimada(guion: Guion, audio: Path) -> Narracion:
    palabras: list[PalabraT] = []
    frases: list[tuple[float, float]] = []
    t = 0.0
    for frase in guion.frases:
        n = max(1, len(frase.texto.split()))
        d = n * SEGUNDOS_POR_PALABRA
        enfasis = {p.lower() for p in frase.enfasis}
        palabras += [p.model_copy(update={"enfasis": p.texto.lower() in enfasis})
                     for p in alineacion.estimar(frase.texto, t, t + d)]
        frases.append((round(t, 3), round(t + d, 3)))
        t += d + frase.pausa_despues + PAUSA_ENTRE_FRASES
    return Narracion(audio=audio, duracion=round(t, 3), palabras=palabras, frases=frases, motor="estimada", exacta=False)


def props_provisionales(run_id: str, guion: Guion, serie: Serie, variacion: Variacion, fps: int,
                        audio: Path | None = None) -> dict:
    """Las mismas props que el render real, con tiempos estimados y sin b-roll."""
    n = narracion_estimada(guion, audio or Path("provisional.wav"))
    segs = render.segmentos(guion, n, {})
    return render.props(run_id, guion, n, serie, variacion, segs, fps)
