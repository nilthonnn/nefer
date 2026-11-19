"""Modelo rápido y económico para tareas de estructura, no de narrativa.

El guion (gancho, bucle, remate) lo escribe el modelo principal
(``SF_LLM_MODELO``, por defecto ``claude-opus-5-5``). Las tareas mecánicas
van a un modelo más barato (``SF_LLM_MODELO_RAPIDO``, por defecto
``claude-haiku-5-5``):

- reparar el JSON de un guion que no pasa el Zod de ``remotion/src/schema.ts``;
- proponer título, etiquetas y gancho de descripción (``publisher/seo.py``).

La salida se pide con *structured outputs* (``output_config.format``): la
respuesta es JSON que cumple el esquema, sin herramientas forzadas.
"""

from __future__ import annotations

import json
from typing import Any

from ..errors import ErrorConfiguracion, ErrorContenido, ErrorTransitorio
from ..logs import obtener
from ..settings import Settings

log = obtener("llm-rapido")


def clasificar(e: Exception) -> Exception:
    """Errores del SDK → transitorio (red/429/5xx/529) o definitivo."""
    estado = getattr(e, "status_code", None)
    nombre = type(e).__name__
    if estado in (408, 409, 429, 500, 502, 503, 504, 529) or nombre in ("APIConnectionError", "APITimeoutError", "RateLimitError"):
        return ErrorTransitorio(f"{nombre}: {e}")
    if estado in (401, 403):
        return ErrorConfiguracion(f"Clave del LLM rechazada ({estado})")
    return e


def texto_json(respuesta: Any, quien: str) -> tuple[dict[str, Any], str]:
    """El JSON de una respuesta con ``output_config.format``; revisa antes el motivo de parada."""
    motivo = getattr(respuesta, "stop_reason", None)
    if motivo == "refusal":
        detalle = getattr(respuesta, "stop_details", None)
        categoria = getattr(detalle, "category", None) if detalle else None
        raise ErrorContenido(f"{quien} se negó a responder (categoría: {categoria or 'sin detalle'})")
    if motivo == "max_tokens":
        raise ErrorContenido(f"{quien}: la respuesta se cortó por max_tokens")
    texto = next((b.text for b in getattr(respuesta, "content", []) if getattr(b, "type", "") == "text"), "")
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as e:
        raise ErrorTransitorio(f"{quien} devolvió JSON incompleto") from e
    if not isinstance(datos, dict):
        raise ErrorContenido(f"{quien} devolvió JSON que no es un objeto")
    return datos, texto


class ModeloRapido:
    def __init__(self, cfg: Settings, cliente: Any = None) -> None:
        cfg.exigir("anthropic_api_key")
        if cliente is None:
            try:
                import anthropic
            except ImportError as e:
                raise ErrorConfiguracion("pip install -e '.[llm]'") from e
            cliente = anthropic.Anthropic(api_key=Settings.secreto(cfg.anthropic_api_key))
        self.cliente = cliente
        self.modelo = cfg.llm_modelo_rapido

    def json(self, sistema: str, contenido: str, esquema: dict[str, Any], max_tokens: int = 4000) -> dict[str, Any]:
        try:
            r = self.cliente.messages.create(
                model=self.modelo,
                max_tokens=max_tokens,
                system=sistema,
                messages=[{"role": "user", "content": contenido}],
                output_config={"effort": "low", "format": {"type": "json_schema", "schema": esquema}},
            )
        except Exception as e:
            raise clasificar(e) from e
        datos, _ = texto_json(r, self.modelo)
        return datos


def disponible(cfg: Settings) -> bool:
    """Hay modelo rápido si el proveedor es Anthropic y hay clave."""
    return cfg.llm_proveedor == "anthropic" and bool(cfg.anthropic_api_key)
