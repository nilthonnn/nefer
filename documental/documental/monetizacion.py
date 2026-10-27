"""Auditoría de monetización en dos fases.

YouTube (Programa de Socios) no monetiza el contenido "no auténtico":
producido en masa, repetitivo o que reutiliza material ajeno sin aportar
nada. Esta auditoría no garantiza la aprobación —la decide una persona en
YouTube— pero detecta de forma objetiva lo que más suele provocar el rechazo.

1. ``auditar_guion``: antes de gastar en voz o render. Duración estimada,
   parecido con videos anteriores, fuentes de cada dato y proporción de
   visuales propios planificada. La usan ``validar``, el guionista (para
   pedir correcciones a Claude) y ``render --estricto`` (para no pagar la voz
   de un guion que no se podrá monetizar).
2. ``auditar_render``: con el video hecho. Licencia de la voz, duración real,
   capítulos, tiempo real en pantalla de visuales propios, clips repetidos
   dentro del video o con otros videos del canal, y respaldos.

Niveles: ``bloqueo`` (no publicar así; ``--estricto`` detiene) y ``aviso``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import Config
from .modelos import ClipEscena, Guion, Tramo
from .publicacion import capitulos, problemas_capitulos

PALABRAS_POR_MINUTO = 150

# Narración que afirma una cantidad: necesita una fuente citada.
_CIFRA = re.compile(
    r"\d|por ciento|\bmillones?\b|\bmil\b|\bmiles\b|kilovatios?|megavatios?|gigavatios?|toneladas?|dólares|centavos",
    re.IGNORECASE,
)


@dataclass
class Hallazgo:
    nivel: str  # "bloqueo" | "aviso"
    mensaje: str
    fase: str = "guion"  # "guion" | "render"


# --- utilidades ------------------------------------------------------------------


def _palabras(texto: str) -> list[str]:
    return re.findall(r"\w+", texto.lower())


def similitud(a: str, b: str) -> float:
    """Jaccard de bigramas de palabras (0 = nada en común, 1 = idénticos)."""
    pa, pb = _palabras(a), _palabras(b)
    x, y = set(zip(pa, pa[1:])), set(zip(pb, pb[1:]))
    if not x or not y:
        return 0.0
    return len(x & y) / len(x | y)


def similitud_titulo(a: str, b: str) -> float:
    """Jaccard de palabras con significado (de 4+ letras) entre dos títulos."""
    x = {p for p in _palabras(a) if len(p) >= 4}
    y = {p for p in _palabras(b) if len(p) >= 4}
    return len(x & y) / len(x | y) if x and y else 0.0


def texto_narrado(guion: Guion) -> str:
    return " ".join(e.narracion for e in guion.escenas)


def estimar_duracion(guion: Guion, cfg: Config) -> float:
    """Segundos estimados: narración a 150 palabras/min + tarjetas + pantalla final."""
    palabras = sum(len(e.narracion.split()) for e in guion.escenas)
    pausas = sum(e.pausa for e in guion.escenas)
    m = cfg.monetizacion
    tarjetas = sum(
        m.segundos_tarjeta_capitulo
        for i, c in enumerate(guion.capitulos)
        if i > 0 and m.tarjetas_capitulo and c.escenas[0].visual.tipo != "titular"
    )
    final = cfg.video.pantalla_final_segundos
    escenas = guion.escenas
    if escenas and escenas[-1].visual.tipo == "final":
        # La pantalla final ya está en el guion: solo se alarga hasta su mínimo.
        final = max(0.0, final - len(escenas[-1].narracion.split()) / PALABRAS_POR_MINUTO * 60)
    return palabras / PALABRAS_POR_MINUTO * 60 + pausas + tarjetas + final


def proporcion_propia_estimada(guion: Guion, cfg: Config) -> float:
    """Fracción del tiempo estimado con visual propio (por palabras de cada escena)."""
    m = cfg.monetizacion
    propio = total = 0.0
    for i, c in enumerate(guion.capitulos):
        if i > 0 and m.tarjetas_capitulo and c.escenas[0].visual.tipo != "titular":
            propio += m.segundos_tarjeta_capitulo
            total += m.segundos_tarjeta_capitulo
        for e in c.escenas:
            d = len(e.narracion.split()) / PALABRAS_POR_MINUTO * 60 + e.pausa
            total += d
            propio += d if e.visual.es_propio else 0
    return propio / total if total else 0.0


# --- historial del canal --------------------------------------------------------


def leer_registro(ruta: Path) -> list[dict]:
    if not ruta.is_file():
        return []
    entradas = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        try:
            entradas.append(json.loads(linea))
        except json.JSONDecodeError:
            continue
    return entradas


def registrar(ruta: Path, guion: Guion, duracion: float, previa: bool) -> None:
    """Añade el video al historial del canal (para detectar repeticiones futuras)."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "slug": guion.slug,
            "titulo": guion.titulo,
            "estructura": guion.estructura,
            "duracion": round(duracion, 1),
            "previa": previa,
            "narracion": texto_narrado(guion),
        }, ensure_ascii=False) + "\n")


def stock_de_otros_videos(ruta: Path, slug: str) -> dict[str, str]:
    """Clips de stock ya usados por OTROS videos del canal: id → slug."""
    usados: dict[str, str] = {}
    for e in leer_registro(ruta):
        if e.get("slug") != slug:
            for i in e.get("ids", []):
                usados.setdefault(i, e.get("slug", "?"))
    return usados


def registrar_stock(ruta: Path, slug: str, ids: list[str]) -> None:
    if not ids:
        return
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"slug": slug, "ids": sorted(set(ids))}) + "\n")


# --- fase 1: guion -----------------------------------------------------------------


def auditar_guion(guion: Guion, historial: list[dict], cfg: Config) -> list[Hallazgo]:
    m = cfg.monetizacion
    h: list[Hallazgo] = []

    estimada = estimar_duracion(guion, cfg)
    if estimada < m.minutos_minimos * 60:
        faltan = int((m.minutos_minimos * 60 - estimada) / 60 * PALABRAS_POR_MINUTO)
        h.append(Hallazgo("aviso", f"Duración estimada {estimada / 60:.1f} min (< {m.minutos_minimos:.0f}): sin anuncios a mitad del video. "
                                   f"Faltan unas {faltan} palabras de narración."))

    if len(guion.capitulos) < 3:
        h.append(Hallazgo("aviso", f"Solo {len(guion.capitulos)} capítulo(s): YouTube exige al menos 3 para mostrar capítulos."))

    propia = proporcion_propia_estimada(guion, cfg)
    if propia < m.proporcion_visual_propio:
        h.append(Hallazgo("aviso", f"Visual propio en ~{propia:.0%} del tiempo (mínimo {m.proporcion_visual_propio:.0%}): "
                                   "convierte escenas de stock con datos en cifras, comparativas o líneas de tiempo."))

    # Fuentes: cualquier cantidad dicha o mostrada necesita respaldo citado.
    con_cifras = [e.id for e in guion.escenas if _CIFRA.search(e.narracion) or e.visual.tipo in ("cifra", "comparativa")]
    if con_cifras and not guion.fuentes:
        h.append(Hallazgo("bloqueo", f"{len(con_cifras)} escena(s) afirman cifras ({', '.join(con_cifras[:5])}) y el guion no cita ninguna fuente."))
    citadas = " ".join(guion.fuentes).lower()
    for e in guion.escenas:
        fuente = str(e.visual.datos.get("fuente", "")).strip()
        if fuente and guion.fuentes and not any(p in citadas for p in _palabras(fuente) if len(p) >= 4 or p.isdigit()):
            h.append(Hallazgo("aviso", f"Escena {e.id}: la fuente «{fuente}» no aparece en la lista de fuentes de la descripción."))

    # Stock: términos repetidos dentro del guion acaban en planos casi iguales.
    vistos: dict[str, str] = {}
    for e in guion.escenas:
        for t in e.visual.busqueda:
            clave = t.strip().lower()
            if clave in vistos:
                h.append(Hallazgo("aviso", f"El término de stock «{t}» se repite en {vistos[clave]} y {e.id}: usa planos distintos."))
            vistos.setdefault(clave, e.id)

    # Contenido repetitivo frente al resto del canal.
    actual = texto_narrado(guion)
    for previo in historial:
        if previo.get("previa") or previo.get("slug") == guion.slug:
            continue
        s = similitud(actual, previo.get("narracion", ""))
        if s > m.similitud_maxima:
            h.append(Hallazgo("bloqueo", f"La narración se parece un {s:.0%} a «{previo.get('titulo')}»: YouTube lo trataría como contenido repetitivo."))
        st = similitud_titulo(guion.titulo, previo.get("titulo", ""))
        if st > 0.6:
            h.append(Hallazgo("aviso", f"El título se parece un {st:.0%} a «{previo.get('titulo')}»: diferéncialo."))
    if guion.estructura:
        recientes = [p.get("estructura") for p in historial[-3:] if not p.get("previa")]
        if recientes and all(r == guion.estructura for r in recientes):
            h.append(Hallazgo("aviso", f"Los últimos videos también usan la estructura «{guion.estructura}»: alterna para no parecer plantilla."))

    if len(guion.titulo) > 100:
        h.append(Hallazgo("aviso", "El título supera 100 caracteres y YouTube lo cortará."))
    return h


# --- fase 2: render ---------------------------------------------------------------


def auditar_render(
    guion: Guion,
    tramos: list[Tramo],
    clips: dict[str, ClipEscena],
    respaldos: dict[str, str],
    licencia_voz: tuple[bool | None, str],
    stock_otros: dict[str, str],
    cfg: Config,
) -> list[Hallazgo]:
    m = cfg.monetizacion
    h: list[Hallazgo] = []
    total = tramos[-1].inicio + tramos[-1].duracion if tramos else 0.0

    comercial, detalle = licencia_voz
    if comercial is False:
        h.append(Hallazgo("bloqueo", f"Voz sin licencia comercial ({detalle}). Genera con ElevenLabs en un plan de pago.", "render"))
    elif comercial is None:
        h.append(Hallazgo("aviso", f"No se pudo verificar la licencia de la voz ({detalle}).", "render"))

    if total < m.minutos_minimos * 60:
        h.append(Hallazgo("aviso", f"Dura {total / 60:.1f} min: con menos de {m.minutos_minimos:.0f} min no se pueden poner anuncios a mitad del video.", "render"))

    for p in problemas_capitulos(capitulos(tramos), total):
        h.append(Hallazgo("aviso", f"Capítulos: {p}.", "render"))

    # Tiempo real en pantalla con visual propio. Una escena de stock que cayó
    # a la tarjeta de respaldo NO cuenta como propia: era stock en el plan.
    propio = sum(t.duracion for t in tramos if t.escena.visual.es_propio)
    if total and propio / total < m.proporcion_visual_propio:
        h.append(Hallazgo("aviso", f"Visual propio en {propio / total:.0%} del tiempo (mínimo {m.proporcion_visual_propio:.0%}).", "render"))

    vistos: dict[str, str] = {}
    for escena, c in clips.items():
        for i in c.ids_stock:
            if i in vistos:
                h.append(Hallazgo("bloqueo", f"El clip de stock {i} se repite en {vistos[i]} y {escena}.", "render"))
            if i in stock_otros:
                h.append(Hallazgo("bloqueo", f"El clip de stock {i} ({escena}) ya se usó en el video «{stock_otros[i]}».", "render"))
            vistos[i] = escena

    # Respaldos agrupados por causa: 30 líneas iguales esconden lo importante.
    por_motivo: dict[str, list[str]] = {}
    for escena, motivo in respaldos.items():
        causa = re.sub(r"\[.*?\]", "[…]", motivo)  # sin los términos de búsqueda concretos
        por_motivo.setdefault(causa, []).append(escena)
    for causa, escenas in por_motivo.items():
        h.append(Hallazgo("aviso", f"{len(escenas)} escena(s) usaron un visual de respaldo ({causa}): {', '.join(escenas)}.", "render"))

    # Ritmo: muy lento aburre, muy rápido suena a resumen automático.
    hablados = [t for t in tramos if t.escena.narracion and t.locucion.palabras]
    palabras = sum(len(t.locucion.palabras) for t in hablados)
    habla = sum(t.locucion.duracion for t in hablados)
    if habla > 0:
        ppm = palabras / habla * 60
        if not 120 <= ppm <= 185:
            h.append(Hallazgo("aviso", f"Ritmo de narración {ppm:.0f} palabras/min (lo habitual en documental: 130–170).", "render"))
    return h


# Compatibilidad: auditoría completa en una llamada.
def auditar(guion, tramos, clips, respaldos, voz_comercial, historial, cfg, stock_otros=None) -> list[Hallazgo]:
    licencia = (voz_comercial, "voz local de vista previa" if voz_comercial is False else "")
    return auditar_guion(guion, historial, cfg) + auditar_render(guion, tramos, clips, respaldos, licencia, stock_otros or {}, cfg)


def informe(hallazgos: list[Hallazgo]) -> str:
    filas = ["# Auditoría de monetización", ""]
    if not hallazgos:
        filas += ["Sin observaciones.", ""]
    for nivel, titulo in (("bloqueo", "Bloqueos (no publicar así)"), ("aviso", "Avisos")):
        grupo = [x for x in hallazgos if x.nivel == nivel]
        if grupo:
            filas += [f"## {titulo}", ""] + [f"- [{x.fase}] {x.mensaje}" for x in grupo] + [""]
    filas += [
        "## Recordatorios al subir",
        "",
        "- En YouTube Studio, marca «Contenido alterado o sintético» solo si muestras personas, lugares o hechos realistas que no ocurrieron.",
        "- Sube `subtitulos.srt` como subtítulos en español (Latinoamérica).",
        "- Añade los elementos de pantalla final en los últimos 20 s.",
        "- Coloca los anuncios a mitad del video en las pausas sugeridas de `metadatos.json` (inicio de capítulo).",
        "",
    ]
    return "\n".join(filas)
