"""Metadatos de YouTube: título, descripción, etiquetas y hashtags.

Reglas de YouTube que se respetan:
- título ≤ 100 caracteres; descripción ≤ 5000; etiquetas ≤ 500 en total;
- más de 15 hashtags hace que YouTube los ignore TODOS: se usan 3–4;
- los 3 primeros hashtags de la descripción aparecen sobre el título.
Nada de hashtags genéricos tipo #viral: no aportan y rozan la política de spam.
"""

from __future__ import annotations

from ..models import Guion, Serie, Tendencia


def titulo(guion: Guion) -> str:
    base = guion.titulo.strip()
    return base if len(base) + 8 > 100 else f"{base} #Shorts"


def hashtags(guion: Guion) -> list[str]:
    vistos, salida = set(), []
    for h in [*guion.hashtags, "#Shorts"]:
        if h.lower() not in vistos:
            vistos.add(h.lower())
            salida.append(h)
    return salida[:4]


def descripcion(guion: Guion, serie: Serie, tendencia: Tendencia, creditos: list[str]) -> str:
    p0, p1 = serie.puntos[0], serie.ultimo
    partes = [
        guion.descripcion.strip(),
        f"Dato: {serie.indicador} en {serie.pais_nombre}, {p0.anio}–{p1.anio}. Fuente: {serie.fuente} ({serie.url})",
    ]
    if tendencia.url:
        partes.append(f"Contexto: {tendencia.titulo} — {tendencia.url}")
    partes += [c for c in creditos if c]
    partes.append("Contenido informativo; no es asesoría financiera.")
    partes.append(" ".join(hashtags(guion)))
    return "\n\n".join(p for p in partes if p)[:5000]


def etiquetas(guion: Guion, serie: Serie) -> list[str]:
    candidatas = [h.lstrip("#") for h in guion.hashtags] + [serie.indicador, serie.pais_nombre, "economía", "tecnología", "datos"]
    salida, total = [], 0
    for e in candidatas:
        costo = len(e) + (2 if " " in e else 0) + 1
        if e and e not in salida and total + costo <= 500:
            salida.append(e)
            total += costo
    return salida


# --- Propuesta del modelo rápido ---------------------------------------------------
#
# El modelo rápido propone título, etiquetas y una primera línea de descripción
# a partir del guion YA aprobado. Su propuesta pasa por las mismas reglas que
# un guion: ninguna cifra que no salga de la serie, nada de clickbait en
# mayúsculas ni de palabras de spam. Si algo falla, se usan las reglas fijas
# de arriba: el SEO nunca bloquea una publicación.

ESQUEMA_SEO = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "titulo": {"type": "string", "description": "≤ 70 caracteres, español latino, curiosidad honesta, sin hashtags."},
        "etiquetas": {"type": "array", "items": {"type": "string"}, "description": "6-10 etiquetas de búsqueda, sin #."},
        "gancho": {"type": "string", "description": "Primera línea de la descripción (≤ 150 caracteres)."},
    },
    "required": ["titulo", "etiquetas", "gancho"],
}

SISTEMA_SEO = """Optimizas metadatos de YouTube Shorts de economía y tecnología para público latinoamericano.
Recibes el guion aprobado y la serie de datos. Reglas:
- Solo cifras y años que aparezcan en el guion o en la serie. Si dudas, no pongas cifras.
- Sin mayúsculas sostenidas, sin emojis, sin "viral", "increíble", "no vas a creer" ni promesas de dinero.
- El título no repite literal el gancho: lo complementa. Etiquetas: lo que la gente escribe en el buscador."""

_SPAM = ("viral", "increible", "no vas a creer", "impactante", "urgente", "gratis", "gana dinero", "millonario")


def _normal(texto: str) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def revisar_propuesta(datos: dict, guion: Guion, serie: Serie) -> list[str]:
    """Problemas de una propuesta de SEO (lista vacía = aceptable)."""
    from ..scripts.heuristicas import numeros

    problemas: list[str] = []
    titulo = str(datos.get("titulo", "")).strip()
    gancho = str(datos.get("gancho", "")).strip()
    etiquetas = [str(e).strip() for e in datos.get("etiquetas", []) if str(e).strip()]
    if not 10 <= len(titulo) <= 70:
        problemas.append(f"título de {len(titulo)} caracteres (10-70)")
    if "#" in titulo:
        problemas.append("el título lleva hashtags")
    if any(len(p) > 3 and p.isupper() for p in titulo.split()):
        problemas.append("mayúsculas sostenidas en el título")
    if len(gancho) > 150:
        problemas.append("gancho de más de 150 caracteres")
    if not 3 <= len(etiquetas) <= 15 or any(len(e) > 30 or "#" in e for e in etiquetas):
        problemas.append("etiquetas fuera de formato (3-15, ≤ 30 caracteres, sin #)")
    texto = _normal(f"{titulo} {gancho}")
    if any(s in texto for s in _SPAM):
        problemas.append("palabras de spam o clickbait")
    citables = serie.valores_citables() | set(numeros(guion.texto))
    inventadas = [n for n in numeros(f"{titulo} {gancho}") if not any(abs(n - c) < 0.051 for c in citables)]
    if inventadas:
        problemas.append(f"cifras que no salen de la serie ni del guion: {inventadas}")
    return problemas


def optimizar(guion: Guion, serie: Serie, modelo: object) -> dict | None:
    """Propuesta del modelo rápido ya revisada, o None para usar las reglas fijas."""
    from ..errors import ShortsError
    from ..logs import obtener

    log = obtener("seo")
    tabla = ", ".join(f"{p.anio}: {p.valor:g}" for p in serie.puntos)
    contenido = (f"Guion aprobado (título de trabajo «{guion.titulo}»):\n{guion.texto}\n\n"
                 f"Serie: {serie.indicador} — {serie.pais_nombre} ({serie.unidad}): {tabla}")
    try:
        datos = modelo.json(SISTEMA_SEO, contenido, ESQUEMA_SEO, max_tokens=1500)  # type: ignore[attr-defined]
    except ShortsError as e:
        log.warning("SEO del modelo rápido no disponible (%s): se usan las reglas fijas", e)
        return None
    problemas = revisar_propuesta(datos, guion, serie)
    if problemas:
        log.warning("propuesta de SEO descartada: %s", "; ".join(problemas))
        return None
    return {"titulo": datos["titulo"].strip(), "etiquetas": [e.strip() for e in datos["etiquetas"]],
            "gancho": datos["gancho"].strip()}


def metadatos(guion: Guion, serie: Serie, tendencia: Tendencia, creditos: list[str],
              propuesta: dict | None = None) -> tuple[str, str, list[str]]:
    """(título, descripción, etiquetas): la propuesta revisada si la hay; si no, las reglas fijas."""
    if propuesta is None:
        return titulo(guion), descripcion(guion, serie, tendencia, creditos), etiquetas(guion, serie)
    base = guion.model_copy(update={"titulo": propuesta["titulo"],
                                    "descripcion": f"{propuesta['gancho']}\n\n{guion.descripcion}".strip()})
    unidas = list(dict.fromkeys([*propuesta["etiquetas"], *etiquetas(guion, serie)]))
    salida, total = [], 0
    for e in unidas:
        costo = len(e) + (2 if " " in e else 0) + 1
        if total + costo <= 500:
            salida.append(e)
            total += costo
    return titulo(base), descripcion(base, serie, tendencia, creditos), salida
