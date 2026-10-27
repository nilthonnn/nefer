"""Línea de comandos: ``python -m documental <comando>``.

    diagnostico                 qué está listo y qué falta (herramientas, claves, MPT, Remotion)
    guion "tema" -o g.json      escribe un guion con Claude para revisarlo
    validar g.json              comprueba el guion y estima la duración
    render g.json [--previa]    produce el video (--previa: voz local, sin gastar créditos)
    cola agregar|procesar|estado|reintentar
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from . import config as m_config
from . import entrada, registro
from .errores import DocumentalError, ErrorConfiguracion
from .pipeline import Opciones, producir

log = registro.obtener("cli")


def _voz(cfg: m_config.Config, previa: bool):
    if previa:
        from .voz.espeak import VozEspeak

        return VozEspeak()
    from .voz.elevenlabs import VozElevenLabs

    return VozElevenLabs(cfg)


def _opciones(args: argparse.Namespace) -> Opciones:
    return Opciones(usar_remotion=not args.sin_remotion, usar_stock=not args.sin_stock, estricto=args.estricto)


def _historial(cfg) -> list[dict]:
    from .monetizacion import leer_registro

    return leer_registro(cfg.salida / "registro.jsonl")


def cmd_validar(args, cfg) -> int:
    """Revisa el guion contra las reglas de monetización sin gastar nada."""
    from .monetizacion import auditar_guion, estimar_duracion, proporcion_propia_estimada

    g = entrada.cargar(Path(args.guion))
    palabras = sum(len(e.narracion.split()) for e in g.escenas)
    print(f"«{g.titulo}» ({g.slug})" + (f"  estructura: {g.estructura}" if g.estructura else ""))
    print(f"  capítulos: {len(g.capitulos)}   escenas: {len(g.escenas)}   palabras: {palabras}")
    print(f"  duración estimada: {estimar_duracion(g, cfg) / 60:.1f} min (mínimo {cfg.monetizacion.minutos_minimos:.0f})")
    print(f"  visual propio: ~{proporcion_propia_estimada(g, cfg):.0%} del tiempo (mínimo {cfg.monetizacion.proporcion_visual_propio:.0%})")
    print(f"  fuentes citadas: {len(g.fuentes)}")
    hallazgos = auditar_guion(g, _historial(cfg), cfg)
    for h in hallazgos:
        print(f"  {'✘ BLOQUEO' if h.nivel == 'bloqueo' else '! aviso  '} {h.mensaje}")
    if not hallazgos:
        print("  ✔ listo para producir")
    return 1 if any(h.nivel == "bloqueo" for h in hallazgos) else 0


def cmd_guion(args, cfg) -> int:
    from . import guionista

    notas = Path(args.notas).read_text(encoding="utf-8") if args.notas else ""
    datos = guionista.escribir(args.tema, cfg, minutos=args.minutos, notas=notas,
                               historial=_historial(cfg), estructura=args.estructura or "")
    entrada.desde_dict(datos)  # valida antes de guardar
    destino = Path(args.salida)
    guionista.guardar(datos, destino)
    print(f"Guion guardado en {destino} (estructura: {datos.get('estructura')}).")
    print("Revísalo (datos, tono, tu experiencia propia) y luego: documental validar", destino)
    return 0


def cmd_render(args, cfg) -> int:
    g = entrada.cargar(Path(args.guion))
    r = producir(g, cfg, _voz(cfg, args.previa), _opciones(args))
    bloqueos = sum(1 for h in r.hallazgos if h.nivel == "bloqueo")
    print(f"\nVideo: {r.video}  ({r.duracion / 60:.1f} min)")
    if r.video.name.endswith(".previa.mp4"):
        print("Es una VISTA PREVIA con marca de agua: no se puede publicar. Quita --previa para la versión final.")
    print(f"Paquete: {r.carpeta} (miniatura.jpg, descripcion.txt, subtitulos.srt, metadatos.json, auditoria.md)")
    if bloqueos:
        print(f"ATENCIÓN: {bloqueos} bloqueo(s) de monetización, ver auditoria.md")
    return 0


def cmd_cola(args, cfg) -> int:
    from .cola import Cola

    cola = Cola(Path(args.carpeta))
    if args.accion == "agregar":
        for ruta in args.guiones:
            entrada.cargar(Path(ruta))  # no encolar guiones inválidos
            print(cola.agregar(Path(ruta)))
    elif args.accion == "estado":
        for estado, trabajos in cola.estado().items():
            print(f"{estado:<10} {len(trabajos)}")
            for t in trabajos:
                print(f"  {t['id']}  {Path(t['guion']).name}  {t.get('error', '')[:100]}")
    elif args.accion == "reintentar":
        print(f"{cola.reintentar_fallidos()} trabajo(s) devueltos a pendiente")
    elif args.accion == "procesar":
        voz = _voz(cfg, args.previa)
        opciones = _opciones(args)

        def ejecutar(ruta: Path) -> dict:
            r = producir(entrada.cargar(ruta), cfg, voz, opciones)
            return {"video": str(r.video), "duracion": r.duracion, "bloqueos": sum(h.nivel == "bloqueo" for h in r.hallazgos)}

        hechos = cola.procesar(ejecutar, args.max)
        print(f"{hechos} video(s) producidos")
    return 0


def cmd_diagnostico(args, cfg) -> int:
    s = cfg.secretos
    filas: list[tuple[str, bool, str]] = []
    for h in ("ffmpeg", "ffprobe", "node", "npx", "espeak-ng"):
        filas.append((h, shutil.which(h) is not None, "necesaria" if h.startswith("ff") else "opcional"))
    filas.append(("ELEVENLABS_API_KEY", bool(s.elevenlabs_api_key), "voz para publicar"))
    filas.append(("ELEVENLABS_VOICE_ID", bool(s.elevenlabs_voice_id), "voz latina elegida"))
    if s.elevenlabs_api_key and s.elevenlabs_voice_id:
        from .voz.elevenlabs import VozElevenLabs

        voz = VozElevenLabs(cfg)
        comercial, detalle = voz.licencia()
        filas.append(("Licencia de la voz", bool(comercial), detalle))
        filas.append(("Voz elegida", True, voz.describir_voz()))
    filas.append(("PEXELS/PIXABAY", bool(s.pexels_api_key or s.pixabay_api_key), "video de stock"))
    filas.append(("ANTHROPIC_API_KEY", bool(s.anthropic_api_key), "guiones con Claude (opcional)"))
    try:
        from .visuales.mpt import _importar_mpt

        _importar_mpt(s.mpt_dir)
        filas.append(("MoneyPrinterTurbo", True, s.mpt_dir))
    except ErrorConfiguracion as e:
        filas.append(("MoneyPrinterTurbo", False, str(e)[:110]))
    remotion_ok = (cfg.remotion_dir / "node_modules" / "remotion").is_dir()
    filas.append(("Remotion", remotion_ok, str(cfg.remotion_dir) if remotion_ok else f"npm install en {cfg.remotion_dir}"))
    musica = any(p.suffix.lower() in (".mp3", ".wav", ".m4a") for p in cfg.carpeta_musica.glob("*"))
    filas.append(("Música", musica, str(cfg.carpeta_musica)))
    for nombre, ok, nota in filas:
        print(f"  {'✔' if ok else '✘'} {nombre:<20} {nota}")
    necesarias_ok = all(ok for n, ok, _ in filas if n in ("ffmpeg", "ffprobe"))
    return 0 if necesarias_ok else 2


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="documental", description="Generador de documentales para YouTube.")
    p.add_argument("--config", help="ruta a canal.toml (por defecto config/canal.toml)")
    p.add_argument("--log", help="nivel de log en consola (DEBUG, INFO, WARNING)")
    sub = p.add_subparsers(dest="comando", required=True)

    def flags_render(sp):
        sp.add_argument("--previa", action="store_true", help="voz local espeak-ng (no publicable, sin costo)")
        sp.add_argument("--sin-remotion", action="store_true", help="infografías con Pillow en vez de Remotion")
        sp.add_argument("--sin-stock", action="store_true", help="no buscar video de stock")
        sp.add_argument("--estricto", action="store_true", help="abortar si la auditoría encuentra bloqueos")

    sub.add_parser("diagnostico", help="revisa herramientas y claves").set_defaults(fn=cmd_diagnostico)

    sp = sub.add_parser("guion", help="escribe un guion con Claude")
    sp.add_argument("tema")
    sp.add_argument("-o", "--salida", required=True)
    sp.add_argument("--minutos", type=float, default=10.0)
    sp.add_argument("--notas", help="archivo con indicaciones propias (experiencia, enfoque)")
    sp.add_argument("--estructura", help="cronologica, misterio, mitos, caso o comparacion (por defecto, la menos usada)")
    sp.set_defaults(fn=cmd_guion)

    sp = sub.add_parser("validar", help="valida un guion y estima su duración")
    sp.add_argument("guion")
    sp.set_defaults(fn=cmd_validar)

    sp = sub.add_parser("render", help="produce el video de un guion")
    sp.add_argument("guion")
    flags_render(sp)
    sp.set_defaults(fn=cmd_render)

    sp = sub.add_parser("cola", help="cola de trabajos en disco")
    sp.add_argument("accion", choices=["agregar", "procesar", "estado", "reintentar"])
    sp.add_argument("guiones", nargs="*")
    sp.add_argument("--carpeta", default=str(m_config.RAIZ / "trabajos"))
    sp.add_argument("--max", type=int)
    flags_render(sp)
    sp.set_defaults(fn=cmd_cola)
    return p


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    registro.configurar(args.log)
    try:
        cfg = m_config.cargar(Path(args.config) if args.config else None)
        return args.fn(args, cfg)
    except ErrorConfiguracion as e:
        log.error("configuración: %s", e)
        return 2
    except DocumentalError as e:
        log.error("%s", e)
        return 1
    except KeyboardInterrupt:
        log.warning("interrumpido; vuelve a ejecutar el mismo comando para reanudar")
        return 130


if __name__ == "__main__":
    sys.exit(main())
