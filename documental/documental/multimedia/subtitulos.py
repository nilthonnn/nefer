"""Subtítulos: ASS dinámico para quemar en el video y SRT para YouTube.

- ASS: frases cortas (≤ N palabras) con la palabra que se está diciendo
  resaltada en ámbar. Es el estilo que más retiene en documentales virales.
- SRT: frases completas, 2 líneas máximo; se sube aparte como subtítulos
  del idioma del video (YouTube los indexa: ayuda al SEO y a la accesibilidad).
"""

from __future__ import annotations

import re
import textwrap

from ..config import Config
from ..modelos import Palabra

_FIN_FRASE = re.compile(r"[.!?…]$")
_PAUSA = re.compile(r"[,;:]$")


def agrupar(palabras: list[Palabra], max_palabras: int = 5, max_caracteres: int = 32, hueco: float = 0.45) -> list[list[Palabra]]:
    """Corta en grupos legibles: por puntuación, silencios, número de palabras y largo."""
    grupos: list[list[Palabra]] = []
    actual: list[Palabra] = []
    for p in palabras:
        if actual:
            largo = sum(len(x.texto) + 1 for x in actual) + len(p.texto)
            silencio = p.inicio - actual[-1].fin
            if len(actual) >= max_palabras or largo > max_caracteres or silencio > hueco:
                grupos.append(actual)
                actual = []
        actual.append(p)
        if _FIN_FRASE.search(p.texto) or (_PAUSA.search(p.texto) and len(actual) >= 3):
            grupos.append(actual)
            actual = []
    if actual:
        grupos.append(actual)
    return grupos


def _t_ass(segundos: float) -> str:
    cs = max(0, round(segundos * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _escapar_ass(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def a_ass(palabras: list[Palabra], cfg: Config) -> str:
    """Genera el archivo ASS completo a partir de las palabras con tiempo global."""
    s, v = cfg.subtitulos, cfg.video
    cabecera = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {v.ancho}
PlayResY: {v.alto}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Voz,{s.fuente},{s.tamano},{s.color},{s.color},&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,120,120,{int(v.alto * 0.09)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lineas = []
    for grupo in agrupar(palabras, s.max_palabras):
        fin_grupo = grupo[-1].fin + 0.15
        for k, p in enumerate(grupo):
            inicio = grupo[0].inicio if k == 0 else p.inicio
            fin = grupo[k + 1].inicio if k + 1 < len(grupo) else fin_grupo
            if fin <= inicio:
                continue
            partes = [
                f"{{\\c{s.resaltado}&}}{_escapar_ass(x.texto)}{{\\c{s.color}&}}" if i == k else _escapar_ass(x.texto)
                for i, x in enumerate(grupo)
            ]
            lineas.append(f"Dialogue: 0,{_t_ass(inicio)},{_t_ass(fin)},Voz,,0,0,0,,{' '.join(partes)}")
    return cabecera + "\n".join(lineas) + "\n"


def _t_srt(segundos: float) -> str:
    ms = max(0, round(segundos * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def a_srt(palabras: list[Palabra], max_caracteres: int = 84, max_segundos: float = 7.0) -> str:
    """Subtítulos clásicos: frases de hasta 2 líneas de 42 caracteres."""
    bloques: list[list[Palabra]] = []
    actual: list[Palabra] = []
    for p in palabras:
        if actual:
            largo = sum(len(x.texto) + 1 for x in actual) + len(p.texto)
            if largo > max_caracteres or p.fin - actual[0].inicio > max_segundos:
                bloques.append(actual)
                actual = []
        actual.append(p)
        if _FIN_FRASE.search(p.texto):
            bloques.append(actual)
            actual = []
    if actual:
        bloques.append(actual)

    salida = []
    for n, b in enumerate(bloques, 1):
        texto = "\n".join(textwrap.wrap(" ".join(x.texto for x in b), 42)[:2])
        salida.append(f"{n}\n{_t_srt(b[0].inicio)} --> {_t_srt(b[-1].fin + 0.2)}\n{texto}\n")
    return "\n".join(salida)
