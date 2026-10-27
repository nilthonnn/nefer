"""Orquestación de un video completo, por etapas y reanudable.

    guion ─► voz (por escena) ─► línea de tiempo ─► visuales (por escena)
          ─► audio (voz+música, -14 LUFS) ─► subtítulos ─► montaje ─► MP4
          ─► miniatura + metadatos + auditoría

Cada resultado intermedio se guarda en ``<salida>/<slug>/trabajo`` con una
clave de contenido. Si el proceso se corta (o se cambia una sola escena),
volver a ejecutar reutiliza todo lo que sigue siendo válido: no se paga dos
veces la misma voz ni se renderiza dos veces la misma infografía.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import Config, exigir_herramientas
from .errores import ErrorMonetizacion
from .modelos import Atribucion, ClipEscena, Escena, Guion, Locucion, Palabra, Tramo, Visual
from .monetizacion import (
    Hallazgo,
    auditar_guion,
    auditar_render,
    informe,
    leer_registro,
    registrar,
    registrar_stock,
    stock_de_otros_videos,
)
from .multimedia import audio as m_audio
from .multimedia import montaje, subtitulos
from .multimedia.ffmpeg import es_valido, ffmpeg, verificar
from .publicacion import escribir_paquete, miniatura
from .registro import a_archivo, de_escena, obtener, quitar
from .visuales.selector import Selector
from .voz.base import ProveedorVoz

log = obtener("pipeline")
# Respiro tras cada frase: sin él la narración suena atropellada entre escenas.
RESPIRO = 0.25
# Se sube cuando cambia CÓMO se dibuja un visual: invalida la caché de clips
# aunque el guion no haya cambiado (si no, se reutilizarían dibujos viejos).
VERSION_VISUALES = 2


@dataclass
class Opciones:
    usar_remotion: bool = True
    usar_stock: bool = True
    # Detener si la auditoría encuentra bloqueos. La parte del guion se revisa
    # ANTES de sintetizar la voz: no se paga ElevenLabs por un video que no
    # se podrá monetizar.
    estricto: bool = False


@dataclass
class Resultado:
    carpeta: Path
    video: Path
    duracion: float
    hallazgos: list[Hallazgo] = field(default_factory=list)


def _clave(*partes: object) -> str:
    return hashlib.sha256(json.dumps(partes, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()[:20]


def secuencia(guion: Guion, cfg: Config) -> list[tuple[str, Escena]]:
    """Escenas en orden con su capítulo.

    Añade una tarjeta animada sin narración al inicio de cada capítulo (salvo
    el gancho, que debe enganchar sin pausas) y la pantalla final si falta.
    Las tarjetas son visual propio puro y marcan el ritmo del documental.
    """
    escenas: list[tuple[str, Escena]] = []
    m = cfg.monetizacion
    for i, c in enumerate(guion.capitulos):
        if i > 0 and m.tarjetas_capitulo and c.escenas[0].visual.tipo != "titular":
            tarjeta = Escena(
                id=f"capitulo{i:02d}",
                narracion="",
                visual=Visual(tipo="titular", datos={"antetitulo": f"Capítulo {i}", "titulo": c.titulo}),
            )
            escenas.append((c.titulo, tarjeta))
        escenas += [(c.titulo, e) for e in c.escenas]
    if cfg.video.pantalla_final_segundos > 0 and escenas and escenas[-1][1].visual.tipo != "final":
        final = Escena(id="final", narracion=cfg.canal.llamado_final, visual=Visual(tipo="final"))
        escenas.append((escenas[-1][0], final))
    return escenas


# --- Etapa 1: voz -----------------------------------------------------------------


def _silencio(destino: Path, segundos: float) -> Locucion:
    """Audio vacío para las escenas sin narración (tarjetas de capítulo)."""
    ruta = destino.with_suffix(".wav")
    if not es_valido(ruta, duracion=segundos, audio=True, tolerancia=0.05):
        ffmpeg(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", f"{segundos:.3f}", str(ruta)], "silencio")
    return Locucion(ruta, verificar(ruta, audio=True).duracion, [])


def _vecina(escenas: list[tuple[str, Escena]], i: int, paso: int) -> str:
    """Narración no vacía más cercana (contexto de entonación para ElevenLabs)."""
    j = i + paso
    while 0 <= j < len(escenas):
        if escenas[j][1].narracion:
            return escenas[j][1].narracion
        j += paso
    return ""


def _voz(escenas: list[tuple[str, Escena]], voz: ProveedorVoz, carpeta: Path, cfg: Config) -> dict[str, Locucion]:
    carpeta.mkdir(parents=True, exist_ok=True)
    resultado: dict[str, Locucion] = {}
    for i, (_, escena) in enumerate(escenas):
        slog = de_escena(log, escena.id)
        if not escena.narracion:
            resultado[escena.id] = _silencio(carpeta / escena.id, cfg.monetizacion.segundos_tarjeta_capitulo)
            continue
        clave = _clave(escena.narracion, voz.huella())
        meta = carpeta / f"{escena.id}.json"
        if meta.is_file():
            datos = json.loads(meta.read_text(encoding="utf-8"))
            ruta = Path(datos["audio"])
            if datos.get("clave") == clave and es_valido(ruta, audio=True):
                resultado[escena.id] = Locucion(ruta, datos["duracion"], [Palabra(**p) for p in datos["palabras"]])
                slog.debug("voz reutilizada")
                continue
        anterior, siguiente = _vecina(escenas, i, -1), _vecina(escenas, i, 1)
        slog.info("voz %d/%d (%s, %d caracteres)", i + 1, len(escenas), voz.nombre, len(escena.narracion))
        loc = voz.sintetizar(escena.narracion, carpeta / escena.id, anterior, siguiente)
        meta.write_text(json.dumps({
            "clave": clave, "audio": str(loc.audio), "duracion": loc.duracion,
            "palabras": [asdict(p) for p in loc.palabras],
        }, ensure_ascii=False), encoding="utf-8")
        resultado[escena.id] = loc
    return resultado


# --- Etapa 2: línea de tiempo ------------------------------------------------------


def linea_de_tiempo(escenas: list[tuple[str, Escena]], voces: dict[str, Locucion], cfg: Config) -> list[Tramo]:
    tramos: list[Tramo] = []
    inicio = 0.0
    for capitulo, escena in escenas:
        loc = voces[escena.id]
        duracion = loc.duracion + escena.pausa + (RESPIRO if escena.narracion else 0.0)
        if escena.visual.tipo == "final":
            duracion = max(duracion, cfg.video.pantalla_final_segundos)
        tramos.append(Tramo(escena=escena, capitulo=capitulo, inicio=round(inicio, 3), duracion=round(duracion, 3), locucion=loc))
        inicio += round(duracion, 3)
    return tramos


# --- Etapa 3: visuales -------------------------------------------------------------


def _visuales(tramos: list[Tramo], selector: Selector, carpeta: Path, cfg: Config) -> dict[str, ClipEscena]:
    carpeta.mkdir(parents=True, exist_ok=True)
    T = cfg.video.transicion_segundos
    clips: dict[str, ClipEscena] = {}
    for i, tramo in enumerate(tramos):
        escena = tramo.escena
        slog = de_escena(log, escena.id)
        # Todas menos la última duran T de más: es el solape del fundido.
        duracion = round(tramo.duracion + (T if i + 1 < len(tramos) else 0.0), 3)
        clave = _clave(VERSION_VISUALES, asdict(escena.visual), escena.narracion if escena.visual.tipo == "stock" else "",
                       duracion, asdict(cfg.video))
        destino = carpeta / f"{escena.id}.mp4"
        meta = carpeta / f"{escena.id}.json"
        if meta.is_file() and es_valido(destino, duracion=duracion, video=True, tolerancia=0.15):
            datos = json.loads(meta.read_text(encoding="utf-8"))
            if datos.get("clave") == clave:
                clip = ClipEscena(destino, datos["propio"], [Atribucion(**a) for a in datos["atribuciones"]], datos["ids_stock"])
                if selector.stock is not None:
                    selector.stock.usados.update(clip.ids_stock)
                clips[escena.id] = clip
                if datos.get("respaldo"):
                    selector.respaldos[escena.id] = datos["respaldo"]
                slog.debug("visual reutilizado")
                continue
        slog.info("visual %d/%d: %s (%.1f s)", i + 1, len(tramos), escena.visual.tipo, duracion)
        clip = selector.generar(escena, duracion, destino)
        meta.write_text(json.dumps({
            "clave": clave, "propio": clip.propio, "ids_stock": clip.ids_stock,
            "atribuciones": [asdict(a) for a in clip.atribuciones],
            "respaldo": selector.respaldos.get(escena.id, ""),
        }, ensure_ascii=False), encoding="utf-8")
        clips[escena.id] = clip
    return clips


# --- Orquestación ------------------------------------------------------------------


def producir(guion: Guion, cfg: Config, voz: ProveedorVoz, opciones: Opciones | None = None) -> Resultado:
    """Produce el video completo y su paquete de publicación."""
    opciones = opciones or Opciones()
    exigir_herramientas("ffmpeg", "ffprobe")
    carpeta = cfg.salida / guion.slug
    trabajo = carpeta / "trabajo"
    trabajo.mkdir(parents=True, exist_ok=True)
    manejador = a_archivo(carpeta / "render.log.jsonl")
    historial = leer_registro(cfg.salida / "registro.jsonl")
    ruta_stock = cfg.salida / "stock_usados.jsonl"
    t0 = time.monotonic()
    try:
        log.info("«%s» → %s", guion.titulo, carpeta)

        # 0. Auditoría del guion y de la licencia de la voz, antes de gastar nada.
        licencia = voz.licencia()
        previa = licencia[0] is False
        hallazgos = auditar_guion(guion, historial, cfg)
        if opciones.estricto:
            bloqueos = [h.mensaje for h in hallazgos if h.nivel == "bloqueo"]
            if licencia[0] is False and not previa_permitida(voz):
                bloqueos.append(f"voz sin licencia comercial: {licencia[1]}")
            if bloqueos:
                (carpeta / "auditoria.md").write_text(informe(hallazgos), encoding="utf-8")
                raise ErrorMonetizacion("guion no monetizable, no se sintetiza la voz:\n- " + "\n- ".join(bloqueos))
        log.info("voz: %s", licencia[1] or voz.nombre)

        escenas = secuencia(guion, cfg)
        voces = _voz(escenas, voz, trabajo / "voz", cfg)
        tramos = linea_de_tiempo(escenas, voces, cfg)
        total = tramos[-1].inicio + tramos[-1].duracion
        log.info("duración: %.1f min en %d escenas", total / 60, len(tramos))

        stock_otros = stock_de_otros_videos(ruta_stock, guion.slug) if cfg.monetizacion.stock_unico_en_canal else {}
        selector = Selector(cfg, trabajo / "stock", opciones.usar_remotion, opciones.usar_stock, set(stock_otros))
        clips = _visuales(tramos, selector, trabajo / "visual", cfg)
        for t in tramos:
            t.clip = clips[t.escena.id]

        hallazgos += auditar_render(guion, tramos, clips, selector.respaldos, licencia, stock_otros, cfg)
        (carpeta / "auditoria.md").write_text(informe(hallazgos), encoding="utf-8")
        for h in hallazgos:
            (log.warning if h.nivel == "bloqueo" else log.info)("auditoría %s: %s", h.nivel, h.mensaje)
        if opciones.estricto and any(h.nivel == "bloqueo" and h.fase == "render" for h in hallazgos if not previa):
            raise ErrorMonetizacion(f"bloqueos de monetización en el render; ver {carpeta / 'auditoria.md'}")

        # Audio
        voz_unida = trabajo / "voz.wav"
        m_audio.unir_voz([(t.locucion.audio, t.duracion) for t in tramos], voz_unida)
        pista = m_audio.elegir_musica(cfg.carpeta_musica, guion.slug)
        if pista is None:
            log.warning("sin música de fondo (pon pistas con licencia en %s)", cfg.carpeta_musica)
        audio_final = trabajo / "audio.wav"
        m_audio.mezclar(voz_unida, pista, audio_final, total, cfg)

        # Subtítulos con tiempo global
        palabras = [Palabra(p.texto, round(t.inicio + p.inicio, 3), round(t.inicio + p.fin, 3))
                    for t in tramos if t.escena.visual.tipo != "final" for p in t.locucion.palabras]
        ass = trabajo / "subtitulos.ass"
        ass.write_text(subtitulos.a_ass(palabras, cfg), encoding="utf-8")
        (carpeta / "subtitulos.srt").write_text(subtitulos.a_srt(palabras), encoding="utf-8")

        # Video. Una vista previa lleva marca de agua y otro nombre de archivo:
        # así es imposible subirla por error creyendo que es la versión final.
        mudo = trabajo / "video_mudo.mp4"
        montaje.encadenar([clips[t.escena.id].ruta for t in tramos], [t.duracion for t in tramos], mudo, cfg)
        video = carpeta / (f"{guion.slug}.previa.mp4" if previa else f"{guion.slug}.mp4")
        montaje.exportar(mudo, audio_final, video, cfg, ass if cfg.subtitulos.quemados else None,
                         marca="VISTA PREVIA - NO PUBLICAR" if previa else "")

        # Publicación
        fotograma = _fotograma_miniatura(tramos, trabajo)
        miniatura(guion.miniatura or guion.titulo, fotograma, carpeta / "miniatura.jpg", cfg)
        atribuciones = [a for t in tramos for a in clips[t.escena.id].atribuciones]
        escribir_paquete(carpeta, guion, tramos, atribuciones, m_audio.creditos_musica(pista), sintetica=True, previa=previa)
        registrar(cfg.salida / "registro.jsonl", guion, total, previa=previa)
        registrar_stock(ruta_stock, guion.slug, [i for c in clips.values() for i in c.ids_stock])

        log.info("listo en %.0f s: %s", time.monotonic() - t0, video)
        return Resultado(carpeta=carpeta, video=video, duracion=total, hallazgos=hallazgos)
    except ErrorMonetizacion:
        raise
    except Exception:
        log.exception("el render falló; los intermedios quedan en %s para reanudar", trabajo)
        raise
    finally:
        quitar(manejador)


def previa_permitida(voz: ProveedorVoz) -> bool:
    """Una voz local declarada como vista previa no bloquea: su salida va marcada."""
    return not getattr(voz, "comercial", True)


def _fotograma_miniatura(tramos: list[Tramo], trabajo: Path) -> Path | None:
    """Toma un fotograma del primer clip de stock (suele ser el más llamativo)."""
    for t in tramos:
        if t.clip is not None and not t.clip.propio:
            salida = trabajo / "fotograma.jpg"
            try:
                ffmpeg(["-ss", f"{t.duracion / 2:.2f}", "-i", str(t.clip.ruta), "-frames:v", "1", "-q:v", "2", str(salida)], "fotograma miniatura")
                return salida
            except Exception as e:  # la miniatura no debe tumbar un render terminado
                log.warning("no se pudo extraer el fotograma para la miniatura: %s", e)
                return None
    return None
