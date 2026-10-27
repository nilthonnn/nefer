"""Guionista con Claude: de un tema a un guion JSON listo para revisar.

El guion SIEMPRE se guarda para revisión humana antes de producir: corregir
datos, ajustar el tono y añadir experiencia propia es lo que separa un canal
monetizable de uno de "contenido producido en masa".

Se fuerza la salida estructurada con una herramienta (``tool_choice``), así
la respuesta llega como JSON válido según el esquema y no como texto libre.
"""

from __future__ import annotations

import json
from typing import Any

from .config import Config
from .errores import ErrorConfiguracion, ErrorEntrada, ErrorTransitorio
from .registro import obtener
from .reintentos import reintentar

log = obtener("guionista")

_VISUAL = {
    "type": "object",
    "properties": {
        "tipo": {"type": "string", "enum": ["stock", "titular", "cifra", "linea_tiempo", "comparativa"]},
        "busqueda": {"type": "array", "items": {"type": "string"}, "description": "Solo stock: 2-3 términos EN INGLÉS, concretos y filmables (p. ej. 'solar panels on cabin roof')."},
        "datos": {
            "type": "object",
            "description": (
                "titular: {antetitulo, titulo}. cifra: {valor:number, prefijo, sufijo, decimales, etiqueta, fuente}. "
                "linea_tiempo: {titulo, hitos:[{anio, texto}] (3-5)}. comparativa: {titulo, unidad, barras:[{etiqueta, valor:number}], fuente}."
            ),
        },
    },
    "required": ["tipo"],
}

ESQUEMA = {
    "type": "object",
    "properties": {
        "titulo": {"type": "string", "description": "≤ 70 caracteres, genera curiosidad sin mentir (sin clickbait falso)."},
        "miniatura": {"type": "string", "description": "2 a 4 palabras en mayúsculas para la miniatura; distintas del título."},
        "descripcion": {"type": "string", "description": "2 párrafos: de qué trata y qué aprenderá quien lo vea. Sin enlaces."},
        "etiquetas": {"type": "array", "items": {"type": "string"}, "description": "8-15 etiquetas; las 3 primeras se usan como hashtags."},
        "fuentes": {"type": "array", "items": {"type": "string"}, "description": "Fuentes reales y verificables de los datos citados (organismo, informe, año)."},
        "capitulos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string"},
                    "escenas": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "narracion": {"type": "string", "description": "1-3 frases habladas (15-45 palabras)."},
                                "visual": _VISUAL,
                                "pausa": {"type": "number", "description": "0 salvo tras un dato que impacte (0.5-1.0)."},
                            },
                            "required": ["narracion", "visual"],
                        },
                    },
                },
                "required": ["titulo", "escenas"],
            },
        },
    },
    "required": ["titulo", "miniatura", "descripcion", "etiquetas", "fuentes", "capitulos"],
}

SISTEMA = """Eres guionista jefe de un canal de documentales de YouTube en español latino neutro, \
sobre energía renovable, vida off-grid, independencia energética e historia de la tecnología. \
Escribes temas atemporales (que sigan vigentes en 5 años) con rigor y ritmo.

Estructura obligatoria:
1. Gancho (primeros 20-30 s): una pregunta o paradoja concreta; promete lo que el video cumplirá. Nada de "hola, bienvenidos".
2. 4-6 capítulos con un arco narrativo: contexto histórico → problema → cómo funciona → números reales → consecuencias para quien lo ve.
3. Bucles de curiosidad: al final de cada capítulo, adelanta algo que se resuelve más adelante.
4. Cierre: idea memorable + invitación natural a ver otro video del canal (sin pedir likes de forma genérica).

Reglas:
- Narración para el oído: frases cortas, voz activa, cifras redondeadas y dichas en palabras cuando ayuden ("casi nueve de cada diez").
- Solo datos verificables, con su fuente en "fuentes". Si no estás seguro de un número, no lo uses.
- Al menos el 30 % de las escenas con visual propio (cifra, linea_tiempo, comparativa o titular) y un titular al inicio de cada capítulo excepto el gancho.
- Las escenas de stock piden planos filmables y variados; nunca el mismo término dos veces.
- Español latino neutro: "ustedes", sin modismos de un solo país, sin "vosotros"."""


def escribir(tema: str, cfg: Config, minutos: float = 10.0, notas: str = "") -> dict[str, Any]:
    """Devuelve el guion como dict (validarlo con entrada.desde_dict)."""
    if not cfg.secretos.anthropic_api_key:
        raise ErrorConfiguracion("Falta ANTHROPIC_API_KEY en .env para escribir guiones")
    try:
        import anthropic
    except ImportError as e:
        raise ErrorConfiguracion("Instala el extra de guion: pip install -e '.[guion]'") from e

    cliente = anthropic.Anthropic(api_key=cfg.secretos.anthropic_api_key)
    palabras = int(minutos * 150)
    pedido = (
        f"Tema: {tema}\n\nDuración objetivo: {minutos:.0f} minutos (unas {palabras} palabras de narración en total).\n"
        + (f"\nNotas del autor del canal (respétalas):\n{notas}\n" if notas else "")
        + "\nEntrega el guion con la herramienta entregar_guion."
    )

    def llamar() -> dict[str, Any]:
        try:
            respuesta = cliente.messages.create(
                model=cfg.secretos.claude_model,
                max_tokens=16000,
                system=SISTEMA,
                tools=[{"name": "entregar_guion", "description": "Entrega el guion final estructurado.", "input_schema": ESQUEMA}],
                tool_choice={"type": "tool", "name": "entregar_guion"},
                messages=[{"role": "user", "content": pedido}],
            )
        except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError) as e:
            raise ErrorTransitorio(f"Claude no disponible: {e}") from e
        except anthropic.APIStatusError as e:
            if e.status_code == 529:  # sobrecarga temporal
                raise ErrorTransitorio(f"Claude sobrecargado: {e}") from e
            raise
        for bloque in respuesta.content:
            if bloque.type == "tool_use" and bloque.name == "entregar_guion":
                return dict(bloque.input)
        raise ErrorEntrada(f"Claude no devolvió el guion (stop_reason={respuesta.stop_reason})")

    guion = reintentar(llamar, descripcion="guion con Claude", intentos=3)
    log.info("guion «%s»: %d capítulos", guion.get("titulo"), len(guion.get("capitulos", [])))
    return guion


def guardar(guion: dict[str, Any], ruta) -> None:
    ruta.write_text(json.dumps(guion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
