"""Subcomandos `nefer fixmate`: indexar, consultar y servir.

Se declaran aparte de `nefer/cli.py` porque el motor de diagnostico no tiene
por que cargarse cuando alguien solo quiere construir un acta.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from . import cierre, embeddings, ingesta, prediccion, transcripcion
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
    """Historiales, manuales y actas -> un archivo de indice.

    Por omision solo se relee lo que cambio. El manual de cuatrocientas
    paginas no se vuelve a vectorizar porque se haya añadido una orden de
    trabajo al historial.
    """
    from . import actualizar

    destino = Path(args.salida or args.indice)
    indice = None
    if not args.completo and destino.is_file():
        try:
            indice = Indice.cargar(destino)
        except ErrorIndice as exc:
            print(f"  aviso: {exc}", file=sys.stderr)
            print("  aviso: se reconstruye el indice entero.", file=sys.stderr)
    if indice is None:
        indice = Indice(embeddings.obtener(args.embebedor))

    try:
        parte = actualizar(indice, [Path(r) for r in args.rutas],
                           podar=not args.sin_podar)
    except (ingesta.ErrorIngesta, ErrorIndice) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not indice.fragmentos:
        print("No hay documentos indexables en esas rutas "
              f"({', '.join(sorted(ingesta.EXTENSIONES))}).", file=sys.stderr)
        return 1

    for etiqueta, lista in (("nuevo", parte.nuevos), ("actualizado", parte.cambiados),
                            ("eliminado", parte.eliminados)):
        for origen in lista:
            print(f"  {etiqueta}: {origen}")
    if parte.iguales:
        print(f"  sin cambios: {len(parte.iguales)} archivos")

    # Se mide aqui, donde hay computadora y tiempo: el telefono lee el
    # resultado, que es lo que acompana a cada porcentaje que ensena.
    motor = Motor(indice)
    indice.medicion = motor.medicion()
    guardado = indice.guardar(destino)
    print(f"\nIndice escrito: {guardado} ({len(indice)} fragmentos de "
          f"{len(indice.fuentes)} archivos, embebedor {indice.embebedor.nombre})")
    return 0


def cmd_estado(args) -> int:
    """Que hay en el indice y que tan bien aprende de ello."""
    indice = _indice(args)
    if indice is None:
        return 1
    motor = Motor(indice)
    print(f"Indice:     {args.indice}")
    print(f"Fragmentos: {len(indice)} de {len(indice.fuentes)} archivos")
    print(f"Embebedor:  {indice.embebedor.nombre}")

    tipos: dict[str, int] = {}
    for fragmento in indice.fragmentos:
        tipos[fragmento.tipo] = tipos.get(fragmento.tipo, 0) + 1
    print("Por tipo:   " + ", ".join(f"{n} {t}" for t, n in sorted(tipos.items())))

    clasificador = motor.clasificador
    print(f"\nClasificador de causas: {clasificador.motivo}")
    if clasificador.entrenado:
        medicion = motor.medicion()
        for causa, casos in sorted(clasificador.casos_por_causa.items(),
                                   key=lambda kv: -kv[1]):
            print(f"  {casos:>3} casos · {causa}")
        if medicion:
            print(f"\n  {clasificador.evaluar().resumen()}")
    if args.archivos:
        print("\nArchivos indexados:")
        for origen in sorted(indice.fuentes):
            print(f"  {origen}")
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
    if diagnostico.causas_probables:
        print("\nLO QUE DICE EL HISTORIAL COMPLETO")
        for causa in diagnostico.causas_probables:
            print(f"  {causa['probabilidad'] * 100:>5.0f}%  {causa['causa']} "
                  f"({causa['casos']} casos)")
        medida = diagnostico.precision_medida
        if medida:
            print(f"         (el clasificador acierta el "
                  f"{medida['precision'] * 100:.0f}% sobre {medida['casos']} casos; "
                  f"la causa mas comun sola daria {medida['linea_base'] * 100:.0f}%)")
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

    texto = args.consulta or ""
    if args.audio:
        # La nota de voz que el tecnico grabo en el socavon. Lo transcrito se
        # imprime antes del diagnostico: si la maquina oyo otra cosa, tiene
        # que verse.
        try:
            texto = transcripcion.obtener("auto")(
                args.audio, pistas=transcripcion.pistas_de_indice(indice))
        except transcripcion.ErrorTranscripcion as exc:
            print(str(exc), file=sys.stderr)
            return 4
        print(f"Transcrito: «{texto}»")
    if not texto.strip():
        print("Escriba la consulta o pase --audio con la nota de voz.",
              file=sys.stderr)
        return 1

    try:
        consulta = Consulta(texto=texto, codigo_dtc=args.dtc,
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


def _fecha(valor):
    import datetime as dt

    return dt.date.fromisoformat(valor) if valor else None


def cmd_predecir(args) -> int:
    """Que le va a pasar a este equipo, segun lo que ya le paso."""
    indice = _indice(args)
    if indice is None:
        return 1
    hoy = _fecha(args.hoy)

    if args.flota or not args.equipo:
        resumen = prediccion.flota(indice, hoy)
        if args.json:
            print(json.dumps(resumen, ensure_ascii=False, indent=2))
            return 0
        print(f"FLOTA · {resumen['eventos']} eventos fechados\n")
        print("Equipos con mas eventos")
        for equipo in resumen["equipos"]:
            mtbf = (f"{equipo['mtbf_dias']} dias entre fallas"
                    if equipo["mtbf_dias"] else "sin intervalo medible")
            print(f"  {equipo['equipo']:<12} {equipo['eventos']:>3} eventos · "
                  f"{mtbf} · ultimo {equipo['ultima']}")
        print("\nCausas que mas vuelven")
        for causa in resumen["causas"]:
            cada = (f"cada ~{causa['intervalo_medio_dias']} dias"
                    if causa["intervalo_medio_dias"] else "sin intervalo aun")
            print(f"  {causa['casos']:>3} casos · {cada} · {causa['causa']}")
        for aviso in resumen["avisos"]:
            print(f"\n  aviso: {aviso}", file=sys.stderr)
        return 0

    parte = prediccion.pronostico(indice, args.equipo, hoy)
    if args.json:
        print(json.dumps(parte.a_dict(), ensure_ascii=False, indent=2))
        return 0

    print(f"EQUIPO {parte.equipo} · {parte.eventos} registros fechados")
    if parte.uso:
        print(f"\nUSO\n  {parte.uso.ritmo_horas_dia} h/dia "
              f"({parte.uso.lecturas} lecturas en {parte.uso.dias_observados} dias); "
              f"horometro {parte.uso.horometro} al {parte.uso.fecha}")
    if parte.servicio:
        print(f"\nPROXIMO SERVICIO\n  {parte.servicio.proximo_intervalo_horas} h: "
              f"faltan {parte.servicio.horas_faltantes} h "
              f"(~{parte.servicio.dias_estimados} dias, {parte.servicio.fecha_estimada})")
    if parte.mtbf_dias:
        print(f"\nMTBF\n  {parte.mtbf_dias} dias entre fallas, en promedio")
    if parte.reincidencias:
        print("\nLO QUE LE VUELVE A PASAR")
        for r in parte.reincidencias:
            cada = (f"cada ~{r.intervalo_medio_dias} dias" if r.intervalo_medio_dias
                    else "sin intervalo aun")
            marca = "VENCIDA · " if r.vencida else ""
            print(f"  {marca}{r.causa}")
            print(f"      {r.casos} casos · {cada} · ultima {r.ultima} "
                  f"(hace {r.dias_desde_la_ultima} dias)")
    if parte.repuestos_sugeridos:
        print("\nREPUESTOS QUE CONVIENE TENER")
        for repuesto in parte.repuestos_sugeridos:
            print(f"  · {repuesto}")
    for aviso in parte.avisos:
        print(f"\n  aviso: {aviso}", file=sys.stderr)
    return 0


def cmd_cerrar(args) -> int:
    """Registra la falla resuelta: manana es el antecedente de otro."""
    historial = Path(args.historial)
    indice = None
    if Path(args.indice).is_file():
        indice = _indice(args)
        if indice is None:
            return 1

    informe = {
        "resumen_falla": args.falla,
        "causa_raiz": args.causa,
        "solucion_aplicada": args.solucion,
        "codigo_equipo": args.equipo,
        "codigo_ot": args.ot,
        "categoria": args.categoria,
        "codigos_dtc": [args.dtc] if args.dtc else [],
        "pasos": args.paso or [],
        "herramientas": args.herramienta or [],
        "repuestos": args.repuesto or [],
        "horometro": args.horometro,
    }
    informe = {k: v for k, v in informe.items() if v}
    try:
        guardado = cierre.registrar(informe, historial, indice)
    except cierre.ErrorCierre as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Registrado {guardado['codigo_ot']} en {historial}")
    if indice is not None:
        indice.guardar(args.indice)
        print(f"Indexado en {args.indice}: ya lo encuentra la siguiente consulta.")
    else:
        print("Sin indice cargado; reindexe con: nefer fixmate indexar "
              f"{historial}")
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
                   help="archivos o carpetas (.json, .xlsx, .pdf, .docx, .md, .txt)")
    i.add_argument("-o", "--salida", help="ruta del indice a escribir")
    i.add_argument("--embebedor", default="local", choices=["local", "openai", "auto"],
                   help="'local' no usa red; 'auto' usa OpenAI si hay clave")
    i.add_argument("--completo", action="store_true",
                   help="rehacer el indice entero en vez de solo lo que cambio")
    i.add_argument("--sin-podar", action="store_true",
                   help="conservar en el indice los archivos que ya no existen")
    i.set_defaults(func=cmd_indexar)

    t = ordenes.add_parser("estado",
                           help="que hay en el indice y que tan bien aprende")
    t.add_argument("--archivos", action="store_true",
                   help="listar tambien los archivos indexados")
    t.set_defaults(func=cmd_estado)

    c = ordenes.add_parser("consultar", help="preguntar por una falla")
    c.add_argument("consulta", nargs="?",
                   help="la falla, como la describiria el tecnico")
    c.add_argument("--audio",
                   help="nota de voz a transcribir en vez de escribir la consulta")
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

    d = ordenes.add_parser(
        "predecir", help="que le va a pasar a un equipo, segun lo que ya le paso")
    d.add_argument("equipo", nargs="?", help="codigo del equipo; sin el, la flota")
    d.add_argument("--flota", action="store_true", help="resumen de toda la flota")
    d.add_argument("--hoy", help="fecha de referencia (YYYY-MM-DD), para reproducir")
    d.add_argument("--json", action="store_true", help="salida en JSON")
    d.set_defaults(func=cmd_predecir)

    r = ordenes.add_parser(
        "cerrar", help="registrar la falla resuelta en el historial y en el indice")
    r.add_argument("--falla", required=True, help="como se describio la falla")
    r.add_argument("--causa", required=True, help="causa raiz confirmada")
    r.add_argument("--solucion", required=True, help="que se hizo")
    r.add_argument("-e", "--equipo", help="codigo del equipo")
    r.add_argument("--categoria", help="familia del equipo")
    r.add_argument("--dtc", help="codigo de falla del tablero")
    r.add_argument("--ot", help="codigo de orden; por defecto, correlativo del año")
    r.add_argument("--horometro", type=float, help="horometro al momento de la falla")
    r.add_argument("--paso", action="append", help="un paso del procedimiento (repetible)")
    r.add_argument("--herramienta", action="append", help="repetible")
    r.add_argument("--repuesto", action="append", help="repetible")
    r.add_argument("--historial", default=os.getenv("FIXMATE_HISTORIAL",
                                                    "historial-fallas.json"),
                   help="archivo de historial donde anotarlo")
    r.set_defaults(func=cmd_cerrar)

    s = ordenes.add_parser("servir", help="levantar la API HTTP")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--puerto", type=int, default=8000)
    s.add_argument("--llm", action="store_true",
                   help="redactar con modelo de lenguaje si hay clave")
    s.set_defaults(func=cmd_servir)

    q = ordenes.add_parser("sql", help="imprimir el esquema de PostgreSQL con pgvector")
    q.set_defaults(func=cmd_sql)
