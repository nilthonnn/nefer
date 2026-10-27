"""Heurísticas de retención y cumplimiento para guiones de 15 s.

Cada regla es objetiva y explicable; el resultado alimenta la corrección
automática del LLM ("corrige estos problemas") y bloquea guiones malos.

Retención (VTR):
- Gancho en 0–3 s: ≤ 10 palabras y con detonante (cifra, pregunta, contraste).
  Prohibidos los arranques gastados ("hola", "en este video", "¿sabías que…").
- Bucle abierto: en las 2 primeras frases se promete algo que se resuelve después.
- Loop infinito: la última frase queda abierta y se completa con la primera,
  así la repetición automática del Short se siente continua (más reproducciones).
- Densidad: palabras acordes a la duración (≈ 2,75 palabras/s como máximo).

Cumplimiento (YPP y veracidad):
- Toda cifra dicha debe salir de la serie real o del titular de la noticia.
- Al menos un visual de datos (gráfico o cifra): aporte propio, no solo b-roll.
- Nada de consejos de inversión ni promesas de ganancias.
- Parecido con Shorts anteriores del canal por debajo del umbral.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..memory import Memoria
from ..models import Guion, Serie, Tendencia
from ..sources.worldbank import normalizar

PALABRAS_POR_SEGUNDO_MAX = 2.75
PALABRAS_POR_SEGUNDO_MIN = 1.9

_ARRANQUES_GASTADOS = ("hola", "bienvenidos", "en este video", "hoy te", "sabias que", "sabias", "hey", "que tal")
_CONTRASTE = ("nadie", "nunca", "pero", "mentira", "error", "secreto", "realmente", "por que", "cuidado", "mito",
              "nadie te", "en realidad", "sin embargo", "peor", "mejor", "verdad")
_PROMESA = ("al final", "la razon", "lo que nadie", "te explico", "spoiler", "pero hay", "no es lo que", "mira esto",
            "atento", "fijate", "el detalle", "la clave", "por que")
_CONECTORES_FINALES = ("porque", "y", "que", "por eso", "asi que", "mientras", "cuando", "hasta", "como", "pero", "o")
_CTA = ("suscribete", "dale like", "comenta", "sigueme", "activa la campana")
_CONSEJO_FINANCIERO = (
    "compra", "compren", "compres", "invierte", "inviertan", "invertir ya", "vende", "vendan", "garantizado",
    "garantizada", "haste rico", "hazte rico", "te haras rico", "ganancias seguras", "recomendacion de inversion",
)

_NUMERO = re.compile(r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+|\d+(?:,\d+)?|\d+(?:\.\d+)?)(?![\w])")


@dataclass
class Evaluacion:
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errores

    @property
    def puntaje(self) -> int:
        return max(0, 100 - 25 * len(self.errores) - 5 * len(self.avisos))


def numeros(texto: str) -> list[float]:
    """Cifras del texto en notación es-419/es-ES: '4,5' → 4.5; '12.500' → 12500."""
    salida = []
    for m in _NUMERO.finditer(texto):
        crudo = m.group(1)
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", crudo):
            salida.append(float(crudo.replace(".", "")))
        else:
            salida.append(float(crudo.replace(",", ".")))
    return salida


def _coincide(valor: float, citables: set[float]) -> bool:
    return any(abs(valor - c) <= max(0.051, abs(c) * 0.01) for c in citables)


def _tiene(texto_norm: str, frases: tuple[str, ...]) -> bool:
    t = f" {texto_norm} "
    return any(f" {f} " in t for f in frases)


def evaluar(
    guion: Guion,
    serie: Serie | None,
    tendencia: Tendencia | None,
    duracion_max: float,
    memoria: Memoria | None = None,
    similitud_maxima: float = 0.35,
) -> Evaluacion:
    ev = Evaluacion()
    frases = guion.frases
    gancho = normalizar(frases[0].texto)
    palabras = guion.palabras

    maximo = int(duracion_max * PALABRAS_POR_SEGUNDO_MAX)
    minimo = int(duracion_max * PALABRAS_POR_SEGUNDO_MIN)
    if palabras > maximo:
        ev.errores.append(f"Tiene {palabras} palabras; para {duracion_max:.0f} s el máximo es {maximo}. Recorta.")
    elif palabras < minimo:
        ev.avisos.append(f"Tiene {palabras} palabras; con menos de {minimo} quedará lento para {duracion_max:.0f} s.")

    # --- gancho (0–3 s)
    n_gancho = len(frases[0].texto.split())
    if n_gancho > 10:
        ev.errores.append(f"El gancho tiene {n_gancho} palabras; debe tener 10 o menos para caber en 3 s.")
    if any(gancho.startswith(a) for a in _ARRANQUES_GASTADOS):
        ev.errores.append("El gancho empieza con una fórmula gastada (saludo, 'en este video', '¿sabías que…?').")
    if not (numeros(frases[0].texto) or "?" in frases[0].texto or _tiene(gancho, _CONTRASTE)):
        ev.errores.append("El gancho no tiene detonante: añade una cifra, una pregunta o un contraste.")

    # --- bucle abierto en las dos primeras frases
    inicio = " ".join(f.texto for f in frases[:2])
    if not ("?" in inicio or _tiene(normalizar(inicio), _PROMESA)):
        ev.errores.append("Falta un bucle abierto en las 2 primeras frases (una promesa o pregunta que se resuelva después).")

    # --- loop: la última frase debe quedar abierta y enlazar con el gancho
    ultima = frases[-1].texto.strip()
    ultima_norm = normalizar(ultima).split()
    abierta = ultima.endswith(("…", "...", ",", ":")) or not ultima.endswith((".", "!", "?")) \
        or (ultima_norm and ultima_norm[-1] in _CONECTORES_FINALES)
    if not abierta:
        ev.errores.append("La última frase cierra el video; déjala abierta para que enlace con el gancho (loop).")

    # --- CTA y consejo financiero
    texto_norm = normalizar(guion.texto)
    if _tiene(normalizar(" ".join(f.texto for f in frases[:3])), _CTA):
        ev.errores.append("No pidas suscripción/like al inicio: rompe la retención.")
    elif _tiene(texto_norm, _CTA):
        ev.avisos.append("Un llamado a la acción en 15 s rompe el loop; mejor quitarlo.")
    if _tiene(texto_norm, _CONSEJO_FINANCIERO):
        ev.errores.append("Suena a consejo de inversión o promesa de ganancias: prohibido (políticas de YouTube y legales).")

    # --- datos reales
    if not any(f.visual in ("grafico", "cifra") for f in frases):
        ev.errores.append("Ninguna frase muestra el dato (visual 'grafico' o 'cifra'): el Short no aporta valor propio.")
    if serie is not None:
        citables = serie.valores_citables()
        if tendencia is not None:
            citables.update(numeros(tendencia.titulo))
        inventadas = [n for n in numeros(guion.texto) if not _coincide(n, citables)]
        if inventadas:
            ev.errores.append(
                "Cifras que no salen de los datos: " + ", ".join(f"{n:g}" for n in inventadas)
                + ". Usa solo valores de la serie (o variaciones calculadas de ella)."
            )

    # --- coherencia del guion
    for i, f in enumerate(frases):
        if f.visual == "broll" and not f.broll_busqueda.strip():
            ev.errores.append(f"La frase {i + 1} es b-roll pero no tiene 'broll_busqueda'.")
        faltan = [p for p in f.enfasis if normalizar(p) not in normalizar(f.texto)]
        if faltan:
            ev.avisos.append(f"Frase {i + 1}: las palabras de énfasis {faltan} no aparecen en el texto.")
    if len(guion.titulo) > 60:
        ev.errores.append(f"Título de {len(guion.titulo)} caracteres; máximo 60 (se añade #Shorts).")

    # --- contenido repetitivo
    if memoria is not None:
        parecido, fila = memoria.mas_parecido(guion.texto)
        if fila is not None and parecido > similitud_maxima:
            ev.errores.append(f"Se parece un {parecido:.0%} al Short «{fila.get('titulo')}»: cambia el ángulo y las frases.")
    return ev
