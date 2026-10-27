"""CLI de ShortsFactory.

    shortsfactory run --topic "La crisis de los semiconductores" [--publicar private]
    shortsfactory run --auto-trend --publicar private
    shortsfactory reanudar <run_id>
    shortsfactory estado [<run_id>]
    shortsfactory tendencias          # ver qué elegiría --auto-trend
    shortsfactory doctor              # binarios, claves y Remotion
    shortsfactory auth                # obtener YOUTUBE_REFRESH_TOKEN (una vez, en local)
    shortsfactory cuota               # unidades usadas hoy

Códigos de salida: 0 ok · 1 run fallido · 2 configuración · 3 cuota agotada ·
4 no publicable (con --exigir-publicable).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys

from . import logs
from .core.fsm import Estado, MaquinaEstados
from .errors import ErrorAutenticacion, ErrorConfiguracion, ErrorCuota, ShortsError
from .settings import Settings, cargar

log = logs.obtener("cli")


def _resumen(r) -> int:
    a = r.artefactos
    print(f"\nrun {r.run_id}: {r.estado}")
    if "tendencia" in a:
        print(f"  tema:     {a['tendencia']['titulo']}")
    if "serie" in a:
        print(f"  dato:     {a['serie']['indicador']} · {a['serie']['pais_nombre']}")
    if "guion" in a:
        print(f"  título:   {a['guion']['titulo']}  (puntaje {a.get('evaluacion', {}).get('puntaje', '?')})")
    if "video" in a:
        print(f"  video:    {a['video']}  ({a.get('qa', {}).get('duracion', '?')} s)")
    if a.get("motivos_no_publicable"):
        print(f"  NO publicable: {'; '.join(a['motivos_no_publicable'])}")
    if a.get("subida"):
        print(f"  YouTube:  {a['subida']['url']} ({a['subida']['privacidad']})")
    if r.estado == Estado.FALLIDO:
        print(f"  error en {r.estado_fallido}: {r.error}\n  reanudar: shortsfactory reanudar {r.run_id}")
    if r.estado == Estado.FALLIDO and "ErrorCuota" in r.error:
        return 3
    return 0 if r.estado == Estado.COMPLETADO else 1


def cmd_run(args, cfg: Settings) -> int:
    from .core.pipeline import Pipeline

    if not args.topic and not args.auto_trend:
        raise ErrorConfiguracion("Indica --topic \"...\" o --auto-trend")
    if args.guion and args.auto_trend:
        raise ErrorConfiguracion("Un guion editorial va con --topic, no con --auto-trend")
    opciones = {"tema": args.topic, "publicar": args.publicar, "semilla": args.seed, "serie_archivo": args.serie,
                "guion_archivo": args.guion}
    r = Pipeline(cfg).ejecutar(opciones)
    codigo = _resumen(r)
    if codigo == 0 and args.exigir_publicable and not r.artefactos.get("publicable"):
        log.error("el Short NO pasa el filtro de publicación: %s", "; ".join(r.artefactos.get("motivos_no_publicable", [])))
        return 4
    return codigo


def cmd_reanudar(args, cfg: Settings) -> int:
    from .core.pipeline import Pipeline

    return _resumen(Pipeline(cfg).reanudar(args.run_id))


def cmd_estado(args, cfg: Settings) -> int:
    if args.run_id:
        r = MaquinaEstados.cargar(cfg.dir_runs / args.run_id / "estado.json")
        print(r.model_dump_json(indent=2, exclude={"traza"}))
        return 0
    for ruta in sorted(cfg.dir_runs.glob("*/estado.json"))[-20:]:
        r = MaquinaEstados.cargar(ruta)
        print(f"{r.run_id}  {r.estado:<11} {r.artefactos.get('guion', {}).get('titulo', '')[:60]}")
    return 0


def cmd_tendencias(args, cfg: Settings) -> int:
    from .memory import Memoria
    from .sources import tendencias, worldbank

    cubiertos = [e.get("tema", "") for e in Memoria(cfg.dir_estado).entradas(60)]
    t = tendencias.buscar(cubiertos)
    ind, pais = worldbank.elegir(t.titulo)
    print(json.dumps({"tendencia": t.model_dump(), "indicador": ind.id, "pais": pais}, ensure_ascii=False, indent=2))
    return 0


def cmd_doctor(args, cfg: Settings) -> int:
    filas = []
    for b in ("ffmpeg", "ffprobe", "node", "npx", "espeak-ng"):
        filas.append((b, shutil.which(b) is not None, "obligatorio" if b != "espeak-ng" else "kokoro/espeak"))
    filas.append(("Remotion", (cfg.remotion_dir / "node_modules" / "remotion").is_dir(), str(cfg.remotion_dir)))
    filas.append((f"LLM ({cfg.llm_proveedor})",
                  cfg.llm_proveedor == "plantilla" or bool(cfg.anthropic_api_key if cfg.llm_proveedor == "anthropic" else cfg.openai_api_key),
                  cfg.llm_modelo or "-"))
    try:
        if cfg.tts_motor == "kokoro":
            import kokoro  # noqa: F401
        elif cfg.tts_motor == "edge":
            import edge_tts  # noqa: F401
        nota = {"kokoro": cfg.kokoro_voz, "edge": cfg.edge_voz, "espeak": "solo desarrollo, no publicable"}[cfg.tts_motor]
        filas.append((f"Voz ({cfg.tts_motor})", True, nota))
    except ImportError:
        filas.append((f"Voz ({cfg.tts_motor})", False, "paquete no instalado"))
    filas.append(("Pexels (b-roll)", bool(cfg.pexels_api_key), "opcional"))
    filas.append(("YouTube OAuth", bool(cfg.youtube_client_secret and cfg.youtube_refresh_token), f"privacidad: {cfg.youtube_privacidad}"))
    for nombre, ok, nota in filas:
        print(f"  {'✔' if ok else '✘'} {nombre:<22} {nota}")
    return 0 if all(ok for n, ok, _ in filas if n in ("ffmpeg", "ffprobe", "node", "npx", "Remotion")) else 2


def cmd_auth(args, cfg: Settings) -> int:
    from .publisher.auth import autorizar

    token = autorizar(cfg)
    print("\nGuarda este valor como secreto YOUTUBE_REFRESH_TOKEN (GitHub → Settings → Secrets):\n")
    print(token)
    return 0


def cmd_cuota(args, cfg: Settings) -> int:
    from .publisher.cuota import Cuota

    c = Cuota(cfg.dir_estado, cfg.youtube_cuota_diaria)
    print(f"{c.hoy()}: {c.usadas()}/{c.limite} unidades · una subida cuesta {cfg.youtube_costo_subida}")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="shortsfactory", description="ShortsFactory-Enterprise")
    p.add_argument("--log", help="DEBUG, INFO, WARNING")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="producir un Short")
    grupo = r.add_mutually_exclusive_group()
    grupo.add_argument("--topic", help="tema concreto")
    grupo.add_argument("--auto-trend", action="store_true", help="elegir una tendencia en tiempo real")
    r.add_argument("--publicar", choices=["no", "private", "unlisted", "public"], default="no",
                   help="destino en YouTube (por defecto no se sube)")
    r.add_argument("--seed", type=int, help="semilla del diseño (reproducible)")
    r.add_argument("--serie", help="JSON de una Serie local en lugar del Banco Mundial")
    r.add_argument("--guion", help="guion editorial (JSON con huecos {ultimo}, {anio_ultimo}...) en lugar del LLM")
    r.add_argument("--exigir-publicable", action="store_true", help="salir con código 4 si el Short no es publicable")
    r.set_defaults(fn=cmd_run)

    s = sub.add_parser("reanudar", help="continuar un run fallido o interrumpido")
    s.add_argument("run_id")
    s.set_defaults(fn=cmd_reanudar)

    s = sub.add_parser("estado", help="estado de los runs")
    s.add_argument("run_id", nargs="?")
    s.set_defaults(fn=cmd_estado)

    sub.add_parser("tendencias", help="tendencia que elegiría --auto-trend").set_defaults(fn=cmd_tendencias)
    sub.add_parser("doctor", help="comprobar el entorno").set_defaults(fn=cmd_doctor)
    sub.add_parser("auth", help="autorizar YouTube y obtener el refresh token").set_defaults(fn=cmd_auth)
    sub.add_parser("cuota", help="cuota de YouTube usada hoy").set_defaults(fn=cmd_cuota)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    logs.configurar(args.log)
    try:
        return args.fn(args, cargar())
    except (ErrorConfiguracion, ErrorAutenticacion) as e:
        log.error("%s", e)
        return 2
    except ErrorCuota as e:
        log.error("%s", e)
        return 3
    except ShortsError as e:
        log.error("%s", e)
        return 1
    except KeyboardInterrupt:
        log.warning("interrumpido: `shortsfactory reanudar <run_id>` continúa donde quedó")
        return 130


if __name__ == "__main__":
    sys.exit(main())
