"""Generación de guiones con LLM (Anthropic u OpenAI) y autocorrección.

1. Se le da al modelo la tendencia, la serie REAL de datos y las reglas.
2. La respuesta llega estructurada (tool use / JSON Schema), nunca texto libre.
3. Se evalúa con ``heuristicas.evaluar``. Si hay errores, se le devuelven al
   modelo con su propio guion para que lo corrija (``SF_LLM_CORRECCIONES``).

``plantilla`` genera guiones sin LLM a partir de la serie. Sirve para
pruebas y para CI sin claves; esos guiones se marcan y NUNCA se publican
(son justo el contenido de plantilla que YouTube no monetiza).
"""

from __future__ import annotations

import json
import random
from typing import Any, Protocol

from ..core.retry import reintentar
from ..errors import ErrorConfiguracion, ErrorContenido, ErrorTransitorio
from ..logs import obtener
from ..memory import Memoria
from ..models import Guion, Serie, Tendencia
from ..settings import Settings
from .heuristicas import Evaluacion, evaluar

log = obtener("guion")

_FRASE = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "texto": {"type": "string", "description": "Lo que dice la voz. Cifras con dígitos y coma decimal (4,5)."},
        "visual": {"type": "string", "enum": ["broll", "grafico", "cifra", "texto"]},
        "broll_busqueda": {"type": "string", "description": "Solo si visual=broll: 2-4 palabras EN INGLÉS, filmables, verticales."},
        "enfasis": {"type": "array", "items": {"type": "string"}, "description": "1-2 palabras de la frase a resaltar."},
        "pausa_despues": {"type": "number", "description": "Segundos de silencio tras la frase (0 a 0.5). Úsala antes del dato clave."},
    },
    "required": ["texto", "visual", "broll_busqueda", "enfasis", "pausa_despues"],
}
ESQUEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "titulo": {"type": "string", "description": "≤ 55 caracteres, curiosidad honesta, sin mayúsculas sostenidas."},
        "frases": {"type": "array", "items": _FRASE, "description": "4 a 7 frases. La 1.ª es el gancho; la última enlaza con la 1.ª."},
        "hashtags": {"type": "array", "items": {"type": "string"}, "description": "2-3 hashtags específicos del tema (sin #Shorts)."},
        "descripcion": {"type": "string", "description": "1-2 frases de contexto para la descripción del video."},
    },
    "required": ["titulo", "frases", "hashtags", "descripcion"],
}

SISTEMA = """Eres guionista de YouTube Shorts sobre tecnología y economía para público latinoamericano.
Escribes en español latino neutro. Cada Short dura como máximo {duracion:.0f} segundos ({palabras} palabras como máximo).

Estructura obligatoria:
1. Gancho (0–3 s, ≤ 10 palabras): una cifra sorprendente, una pregunta o un contraste. Prohibido saludar, "en este video" o "¿sabías que…?".
2. Bucle abierto en las 2 primeras frases: promete algo que se revela después ("la razón está en este gráfico").
3. El dato: al menos una frase con visual "grafico" o "cifra" usando SOLO los números de la serie que te paso
   (o variaciones calculadas de ella: diferencia, porcentaje de cambio, cuántas veces).
4. Remate y LOOP: la última frase queda abierta y se completa con el gancho al repetirse el video
   (ej.: última "…y por eso" → gancho "el 68 % ya no ahorra"). Sin punto final.

Reglas:
- Ninguna cifra fuera de la serie o del titular. Si no estás seguro, no la digas.
- Nunca consejos de inversión ("compra", "invierte", "vende") ni promesas de ganancias.
- No pidas likes ni suscripción.
- Varía el ángulo: no repitas la estructura de frases de Shorts anteriores del canal."""


class Proveedor(Protocol):
    nombre: str

    def pedir(self, sistema: str, mensajes: list[dict[str, Any]]) -> tuple[dict[str, Any], Any]:
        """Devuelve (guion_dict, contexto_para_corregir)."""
        ...

    def corregir(self, mensajes: list[dict[str, Any]], contexto: Any, guion: dict, problemas: list[str]) -> None:
        """Añade a ``mensajes`` el turno que pide la corrección."""
        ...


class ProveedorAnthropic:
    nombre = "anthropic"

    def __init__(self, cfg: Settings, cliente: Any = None) -> None:
        cfg.exigir("anthropic_api_key")
        if cliente is None:
            try:
                import anthropic
            except ImportError as e:
                raise ErrorConfiguracion("pip install -e '.[llm]'") from e
            cliente = anthropic.Anthropic(api_key=Settings.secreto(cfg.anthropic_api_key))
        self.cliente = cliente
        self.modelo = cfg.llm_modelo

    def pedir(self, sistema, mensajes):
        try:
            r = self.cliente.messages.create(
                model=self.modelo, max_tokens=4000, system=sistema, messages=mensajes,
                tools=[{"name": "entregar_guion", "description": "Entrega el guion del Short.", "input_schema": ESQUEMA}],
                tool_choice={"type": "tool", "name": "entregar_guion"},
            )
        except Exception as e:
            raise _clasificar(e) from e
        for b in r.content:
            if getattr(b, "type", "") == "tool_use":
                return dict(b.input), b.id
        raise ErrorContenido(f"El modelo no entregó el guion (stop_reason={getattr(r, 'stop_reason', '?')})")

    def corregir(self, mensajes, contexto, guion, problemas):
        mensajes += [
            {"role": "assistant", "content": [{"type": "tool_use", "id": contexto, "name": "entregar_guion", "input": guion}]},
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": contexto,
                                          "content": "Corrige y entrega el guion COMPLETO:\n- " + "\n- ".join(problemas)}]},
        ]


class ProveedorOpenAI:
    nombre = "openai"

    def __init__(self, cfg: Settings, cliente: Any = None) -> None:
        cfg.exigir("openai_api_key")
        if cliente is None:
            try:
                import openai
            except ImportError as e:
                raise ErrorConfiguracion("pip install -e '.[llm]'") from e
            cliente = openai.OpenAI(api_key=Settings.secreto(cfg.openai_api_key))
        self.cliente = cliente
        self.modelo = cfg.llm_modelo

    def pedir(self, sistema, mensajes):
        try:
            r = self.cliente.chat.completions.create(
                model=self.modelo,
                messages=[{"role": "system", "content": sistema}, *mensajes],
                response_format={"type": "json_schema", "json_schema": {"name": "guion", "strict": True, "schema": ESQUEMA}},
            )
        except Exception as e:
            raise _clasificar(e) from e
        contenido = r.choices[0].message.content or ""
        try:
            return json.loads(contenido), contenido
        except json.JSONDecodeError as e:
            raise ErrorTransitorio("OpenAI devolvió JSON incompleto") from e

    def corregir(self, mensajes, contexto, guion, problemas):
        mensajes += [
            {"role": "assistant", "content": contexto},
            {"role": "user", "content": "Corrige y entrega el guion COMPLETO:\n- " + "\n- ".join(problemas)},
        ]


def _clasificar(e: Exception) -> Exception:
    """Errores del SDK → transitorio (red/429/5xx/529) o definitivo."""
    estado = getattr(e, "status_code", None)
    nombre = type(e).__name__
    if estado in (408, 409, 429, 500, 502, 503, 504, 529) or nombre in ("APIConnectionError", "APITimeoutError", "RateLimitError"):
        return ErrorTransitorio(f"{nombre}: {e}")
    if estado in (401, 403):
        return ErrorConfiguracion(f"Clave del LLM rechazada ({estado})")
    return e


def _tabla(serie: Serie) -> str:
    filas = "\n".join(f"{p.anio}: {p.valor:.2f}".replace(".", ",") for p in serie.puntos)
    return f"{serie.indicador} — {serie.pais_nombre} ({serie.unidad}), fuente {serie.fuente}:\n{filas}"


def escribir(
    cfg: Settings,
    tendencia: Tendencia,
    serie: Serie,
    memoria: Memoria,
    proveedor: Proveedor | None = None,
    rng: random.Random | None = None,
) -> tuple[Guion, Evaluacion]:
    """Guion validado. Lanza ErrorContenido si tras las correcciones sigue mal."""
    if cfg.llm_proveedor == "plantilla" and proveedor is None:
        guion = plantilla(tendencia, serie, rng or random.Random())
        return guion, evaluar(guion, serie, tendencia, cfg.duracion_max, memoria, cfg.similitud_maxima)

    proveedor = proveedor or (ProveedorAnthropic(cfg) if cfg.llm_proveedor == "anthropic" else ProveedorOpenAI(cfg))
    maximo = int(cfg.duracion_max * 2.75)
    sistema = SISTEMA.format(duracion=cfg.duracion_max, palabras=maximo)
    recientes = [e.get("titulo", "") for e in memoria.entradas(15)]
    pedido = (
        f"Noticia del momento: «{tendencia.titulo}» ({tendencia.fuente}).\n"
        "No afirmes nada de la noticia más allá de su titular: úsala como puerta de entrada al dato.\n\n"
        f"Serie de datos reales:\n{_tabla(serie)}\n"
        + ("\nShorts recientes del canal (no repitas su ángulo):\n" + "\n".join(f"- {t}" for t in recientes if t) if recientes else "")
    )
    mensajes: list[dict[str, Any]] = [{"role": "user", "content": pedido}]
    ultimo: Evaluacion | None = None
    for ronda in range(cfg.llm_correcciones + 1):
        crudo, contexto = reintentar(lambda: proveedor.pedir(sistema, mensajes), f"guion {proveedor.nombre}")
        try:
            guion = Guion.model_validate({**crudo, "generador": "llm"})
            ultimo = evaluar(guion, serie, tendencia, cfg.duracion_max, memoria, cfg.similitud_maxima)
            problemas = ultimo.errores
        except ValueError as e:  # ValidationError de Pydantic
            guion, problemas = None, [f"El guion no cumple el esquema: {e}"]
        if not problemas:
            log.info("guion aprobado en la ronda %d (puntaje %d)", ronda + 1, ultimo.puntaje if ultimo else 0)
            return guion, ultimo  # type: ignore[return-value]
        log.warning("guion ronda %d con %d problema(s): %s", ronda + 1, len(problemas), " | ".join(problemas))
        proveedor.corregir(mensajes, contexto, crudo, problemas)
    raise ErrorContenido("El guion no pasó las heurísticas tras las correcciones:\n- " + "\n- ".join(problemas))


# --- generador local (solo pruebas) ------------------------------------------------


def _fmt(valor: float) -> str:
    texto = f"{valor:.1f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def plantilla(tendencia: Tendencia, serie: Serie, rng: random.Random) -> Guion:
    """Guion determinista a partir de la serie. Marcado como 'plantilla': no publicable."""
    p0, p1 = serie.puntos[0], serie.ultimo
    u = "%" if serie.unidad.startswith("%") else f" {serie.unidad}"
    sube = p1.valor >= p0.valor
    ganchos = [f"{_fmt(p1.valor)}{u}: el dato que nadie mira", f"Nadie habla de este {_fmt(p1.valor)}{u}"]
    promesas = ["La razón está en este gráfico.", "Pero hay un detalle que cambia todo.", "Te explico con un solo dato."]
    cierres = ["Y por eso", "Y eso explica por qué", "Así que la pregunta es"]
    return Guion(
        titulo=f"{serie.indicador} en {serie.pais_nombre}: {p0.anio} vs {p1.anio}"[:60],
        frases=[
            {"texto": rng.choice(ganchos), "visual": "cifra", "enfasis": [_fmt(p1.valor)], "pausa_despues": 0.2},
            {"texto": rng.choice(promesas), "visual": "texto", "enfasis": []},
            {"texto": f"En {p0.anio} estaba en {_fmt(p0.valor)}{u}.", "visual": "grafico", "enfasis": [str(p0.anio)]},
            {"texto": f"En {p1.anio} {'subió' if sube else 'bajó'} a {_fmt(p1.valor)}{u}.", "visual": "grafico",
             "enfasis": ["subió" if sube else "bajó"], "pausa_despues": 0.3},
            {"texto": rng.choice(cierres), "visual": "broll", "broll_busqueda": "city skyline night", "enfasis": []},
        ],
        hashtags=["#economia", "#datos"],
        descripcion=f"{serie.indicador} en {serie.pais_nombre} según el {serie.fuente}.",
        generador="plantilla",
    )
