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
                "titular: {antetitulo, titulo}. cifra: {valor:number, prefijo, sufijo, decimales, etiqueta, fuente (OBLIGATORIA)}. "
                "linea_tiempo: {titulo, hitos:[{anio, texto}] (3-5)}. "
                "comparativa: {titulo, unidad, barras:[{etiqueta, valor:number}], fuente (OBLIGATORIA), "
                "destacar: 'menor' si menos es mejor (costos, pérdidas)}. "
                "La 'fuente' debe coincidir con una entrada de 'fuentes'."
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
        "fuentes": {"type": "array", "items": {"type": "string"}, "description": "Fuentes reales y verificables de TODAS las cifras dichas o mostradas: organismo, título del informe, año y URL si existe."},
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
- Al menos el 40 % del tiempo con visual propio (cifra, linea_tiempo, comparativa): toda escena que diga un número o una fecha clave lleva su infografía, no stock. Las tarjetas de capítulo las añade el sistema; no pongas titulares.
- Cada cifra dicha en la narración aparece en "fuentes"; cada visual de datos lleva su "fuente".
- Las escenas de stock piden planos filmables y variados; nunca el mismo término dos veces en el guion.
- Aporta valor propio: un cálculo, una comparación o una conclusión que no esté en la primera página de un buscador.
- Español latino neutro: "ustedes", sin modismos de un solo país, sin "vosotros"."""


# Estructuras narrativas: alternarlas evita que todos los videos del canal
# sigan la misma plantilla (señal clásica de "producido en masa").
ESTRUCTURAS = {
    "cronologica": "Relato cronológico: de los orígenes al presente, con un salto final al futuro.",
    "misterio": "Investigación: abre con una paradoja o enigma y cada capítulo descarta una explicación hasta la respuesta.",
    "mitos": "Mitos contra datos: cada capítulo toma una creencia popular y la contrasta con evidencia.",
    "caso": "Caso de estudio: sigue a un lugar, empresa o persona real y extrae de su historia los principios generales.",
    "comparacion": "Duelo: enfrenta dos tecnologías, ideas o personajes capítulo a capítulo y cierra con un veredicto razonado.",
}


def elegir_estructura(historial: list[dict], pedida: str = "") -> str:
    """La pedida, o la que menos se ha usado en los últimos videos del canal."""
    if pedida:
        if pedida not in ESTRUCTURAS:
            raise ErrorConfiguracion(f"estructura desconocida '{pedida}'; usa una de {', '.join(ESTRUCTURAS)}")
        return pedida
    recientes = [h.get("estructura") for h in historial if not h.get("previa")][-6:]

    def antiguedad(e: str) -> int:
        # Cuántos videos han pasado desde que se usó (nunca usada = muchísimos).
        return len(recientes) - max(i for i, r in enumerate(recientes) if r == e) if e in recientes else 999

    return min(ESTRUCTURAS, key=lambda e: (recientes.count(e), -antiguedad(e)))


def _contexto_canal(historial: list[dict]) -> str:
    previos = [h for h in historial if not h.get("previa")][-30:]
    if not previos:
        return ""
    lista = "\n".join(f"- {h.get('titulo')}" for h in previos)
    return (
        "\nVideos ya publicados en el canal (NO repitas su enfoque, sus ejemplos ni sus frases; "
        f"si el tema se cruza, aborda un ángulo nuevo y menciona el otro video como complemento):\n{lista}\n"
    )


def escribir(
    tema: str,
    cfg: Config,
    minutos: float = 10.0,
    notas: str = "",
    historial: list[dict] | None = None,
    estructura: str = "",
) -> dict[str, Any]:
    """Escribe el guion y lo corrige contra la auditoría de monetización.

    Tras la primera versión se audita (duración, fuentes, visuales propios,
    parecido con el canal). Si hay problemas, se le devuelven a Claude con
    su propio guion para que los corrija, hasta ``correcciones_guion`` veces.
    Devuelve el dict del guion (con la clave ``estructura``).
    """
    if not cfg.secretos.anthropic_api_key:
        raise ErrorConfiguracion("Falta ANTHROPIC_API_KEY en .env para escribir guiones")
    try:
        import anthropic
    except ImportError as e:
        raise ErrorConfiguracion("Instala el extra de guion: pip install -e '.[guion]'") from e
    from .entrada import desde_dict
    from .errores import ErrorEntrada as _ErrorEntrada
    from .monetizacion import auditar_guion

    historial = historial or []
    estructura = elegir_estructura(historial, estructura)
    minutos = max(minutos, cfg.monetizacion.minutos_minimos + 1)
    cliente = anthropic.Anthropic(api_key=cfg.secretos.anthropic_api_key)
    palabras = int(minutos * 150)
    pedido = (
        f"Tema: {tema}\n\nDuración objetivo: {minutos:.0f} minutos (unas {palabras} palabras de narración en total; "
        f"nunca menos de {int(cfg.monetizacion.minutos_minimos * 150)}).\n"
        f"Estructura narrativa: {ESTRUCTURAS[estructura]}\n"
        + _contexto_canal(historial)
        + (f"\nNotas del autor del canal (respétalas):\n{notas}\n" if notas else "")
        + "\nEntrega el guion con la herramienta entregar_guion."
    )
    mensajes: list[dict[str, Any]] = [{"role": "user", "content": pedido}]

    def llamar() -> dict[str, Any]:
        try:
            respuesta = cliente.messages.create(
                model=cfg.secretos.claude_model,
                max_tokens=16000,
                system=SISTEMA,
                tools=[{"name": "entregar_guion", "description": "Entrega el guion final estructurado.", "input_schema": ESQUEMA}],
                tool_choice={"type": "tool", "name": "entregar_guion"},
                messages=mensajes,
            )
        except (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError) as e:
            raise ErrorTransitorio(f"Claude no disponible: {e}") from e
        except anthropic.APIStatusError as e:
            if e.status_code == 529:  # sobrecarga temporal
                raise ErrorTransitorio(f"Claude sobrecargado: {e}") from e
            raise
        for bloque in respuesta.content:
            if bloque.type == "tool_use" and bloque.name == "entregar_guion":
                return {"id": bloque.id, "guion": dict(bloque.input)}
        raise ErrorEntrada(f"Claude no devolvió el guion (stop_reason={respuesta.stop_reason})")

    for ronda in range(cfg.monetizacion.correcciones_guion + 1):
        entrega = reintentar(llamar, descripcion=f"guion con Claude (ronda {ronda + 1})", intentos=3)
        guion = entrega["guion"]
        guion["estructura"] = estructura
        try:
            problemas = [
                h.mensaje for h in auditar_guion(desde_dict(guion), historial, cfg)
                # Solo lo que Claude puede corregir escribiendo (no la estructura repetida: la elige el sistema).
                if h.nivel == "bloqueo" or "Duración" in h.mensaje or "Visual propio" in h.mensaje
                or "fuente" in h.mensaje or "se repite" in h.mensaje or "capítulo" in h.mensaje.lower()
            ]
        except _ErrorEntrada as e:
            problemas = [f"El guion no cumple el formato: {e}"]
        if not problemas:
            break
        log.warning("guion ronda %d: %d problema(s): %s", ronda + 1, len(problemas), "; ".join(problemas))
        if ronda == cfg.monetizacion.correcciones_guion:
            log.warning("se agotaron las correcciones; revisa a mano los problemas listados")
            break
        mensajes += [
            {"role": "assistant", "content": [{"type": "tool_use", "id": entrega["id"], "name": "entregar_guion", "input": guion}]},
            {"role": "user", "content": [{
                "type": "tool_result",
                "tool_use_id": entrega["id"],
                "content": "Corrige estos problemas y vuelve a entregar el guion COMPLETO (no solo los cambios):\n- "
                           + "\n- ".join(problemas),
            }]},
        ]

    log.info("guion «%s» (%s): %d capítulos", guion.get("titulo"), estructura, len(guion.get("capitulos", [])))
    return guion


def guardar(guion: dict[str, Any], ruta) -> None:
    ruta.write_text(json.dumps(guion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
