"""Subcomandos `nefer fixmate`: indexar, consultar y servir.

Se declaran aparte de `nefer/cli.py` porque el motor de diagnostico no tiene
por que cargarse cuando alguien solo quiere construir un acta.
"""

from __future__ import annotations

import json
import os
import sys

from . import embeddings, ingesta
from .indice import ErrorIndice, Indice
from .motor import Consulta, Motor, RedactorLLM, SinEvidencia

INDICE_POR_DEFECTO = os.getenv("FIXMATE_INDICE", "indice-fixmate.json")


def _indice(args) -> Indice | None:
    try:
        return Indice.cargar(args.indice)
    except ErrorIndice as exc:
        print(str(exc), file=sys.stderr)
        return None


def cmd_indexar(args) -> int:
    """Historiales, manuales y actas -> un archivo de indice."""
    try:
        archivos = ingesta.recorrer(args.rutas)
    except ingesta.ErrorIngesta as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not archivos:
        print("No hay documentos indexables en esas rutas "
              f"({', '.join(sorted(ingesta.EXTENSIONES))}).", file=sys.stderr)
        return 1

    # Se leen todos y se agregan de una sola vez: cada `agregar` rehace las
    # cuentas del BM25, y hacerlo una vez por archivo es cuadratico.
    todos = []
    for archivo in archivos:
        try:
            fragmentos = ingesta.de_archivo(archivo)
        except ingesta.ErrorIngesta as exc:
            print(str(exc), file=sys.stderr)
            return 1
        todos.extend(fragmentos)
        print(f"  {archivo}: {len(fragmentos)} fragmentos")

    indice = Indice(embeddings.obtener(args.embebedor))
    indice.agregar(todos)
    destino = indice.guardar(args.salida or args.indice)
    repetidos = len(todos) - len(indice)
    if repetidos:
        print(f"  ({repetidos} fragmentos repetidos, indexados una sola vez)")
    print(f"\nIndice escrito: {destino} ({len(indice)} fragmentos, "
          f"embebedor {indice.embebedor.nombre})")
    return 0


def _imprimir(diagnostico) -> None:
    print(f"\nDIAGNOSTICO (confianza {diagnostico.confianza}, "
          f"redactor {diagnostico.redactor})")
    print(f"  {diagnostico.diagnostico_probabilistico}")
    print(f"\nCAUSA RAIZ MAS PROBABLE\n  {diagnostico.causa_raiz_mas_probable}")
    if diagnostico.pasos_recomendados:
        print("\nPASOS")
        for n, paso in enumerate(diagnostico.pasos_recomendados, 1):
            print(f"  {n}. {paso}")
    if diagnostico.herramientas_y_repuestos:
        print("\nHERRAMIENTAS Y REPUESTOS")
        for cosa in diagnostico.herramientas_y_repuestos:
            print(f"  · {cosa}")
    if diagnostico.torques:
        print("\nTORQUES CITADOS EN LA FUENTE")
        for torque in diagnostico.torques:
            print(f"  · {torque}")
    print("\nEVIDENCIA")
    for e in diagnostico.evidencia_historica:
        etiqueta = e.codigo_ot or e.id
        print(f"  {etiqueta} ({e.tipo}, {e.similitud * 100:.0f}%) — {e.fuente}")
        if e.causa_raiz:
            print(f"      causa: {e.causa_raiz}")
        elif e.resumen_falla:
            print(f"      registra: {e.resumen_falla}")
    for aviso in diagnostico.avisos:
        print(f"\n  aviso: {aviso}", file=sys.stderr)


def cmd_consultar(args) -> int:
    indice = _indice(args)
    if indice is None:
        return 1
    redactor = RedactorLLM(modelo=args.modelo) if args.llm else None
    motor = Motor(indice, redactor=redactor)
    try:
        consulta = Consulta(texto=args.consulta, codigo_dtc=args.dtc,
                            codigo_equipo=args.equipo, categoria=args.categoria,
                            limite=args.limite)
        diagnostico = motor.consultar(consulta)
    except SinEvidencia as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(diagnostico.a_dict(), ensure_ascii=False, indent=2))
    else:
        _imprimir(diagnostico)
    return 0


def cmd_servir(args) -> int:
    try:
        import uvicorn
    except ImportError:
        print("servir necesita uvicorn: pip install nefer[fixmate-api]",
              file=sys.stderr)
        return 1
    from .api import crear_app

    app = crear_app(ruta_indice=args.indice, con_llm=args.llm or None)
    print(f"FixMate en http://{args.host}:{args.puerto}  (indice: {args.indice})")
    uvicorn.run(app, host=args.host, port=args.puerto)
    return 0


def cmd_sql(args) -> int:
    from .almacen_pg import DDL

    print(DDL)
    return 0


def agregar_subcomando(sub) -> None:
    """Cuelga `fixmate` y sus ordenes del parser principal de nefer."""
    f = sub.add_parser(
        "fixmate",
        help="asistente de diagnostico sobre el historial de fallas y los manuales")
    f.add_argument("-i", "--indice", default=INDICE_POR_DEFECTO,
                   help=f"archivo de indice (por defecto, {INDICE_POR_DEFECTO})")
    ordenes = f.add_subparsers(dest="orden", required=True)

    i = ordenes.add_parser("indexar",
                           help="historial, manuales y actas -> indice")
    i.add_argument("rutas", nargs="+",
                   help="archivos o carpetas (.json, .md, .txt, .xlsx)")
    i.add_argument("-o", "--salida", help="ruta del indice a escribir")
    i.add_argument("--embebedor", default="local", choices=["local", "openai", "auto"],
                   help="'local' no usa red; 'auto' usa OpenAI si hay clave")
    i.set_defaults(func=cmd_indexar)

    c = ordenes.add_parser("consultar", help="preguntar por una falla")
    c.add_argument("consulta", help="la falla, como la describiria el tecnico")
    c.add_argument("--dtc", help="codigo de falla, si el tablero da uno")
    c.add_argument("-e", "--equipo", help="codigo del equipo de la flota")
    c.add_argument("--categoria", help="familia del equipo")
    c.add_argument("-n", "--limite", type=int, default=3,
                   help="cuantos antecedentes recuperar (1 a 10)")
    c.add_argument("--json", action="store_true", help="salida en JSON")
    c.add_argument("--llm", action="store_true",
                   help="redactar con modelo de lenguaje (necesita OPENAI_API_KEY)")
    c.add_argument("--modelo", default="gpt-4o-mini", help="modelo para --llm")
    c.set_defaults(func=cmd_consultar)

    s = ordenes.add_parser("servir", help="levantar la API HTTP")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--puerto", type=int, default=8000)
    s.add_argument("--llm", action="store_true",
                   help="redactar con modelo de lenguaje si hay clave")
    s.set_defaults(func=cmd_servir)

    q = ordenes.add_parser("sql", help="imprimir el esquema de PostgreSQL con pgvector")
    q.set_defaults(func=cmd_sql)
