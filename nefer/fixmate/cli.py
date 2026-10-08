"""Subcomandos `nefer fixmate`: indexar, consultar y servir.

Se declaran aparte de `nefer/cli.py` porque el motor de diagnostico no tiene
por que cargarse cuando alguien solo quiere construir un acta.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from . import cierre, embeddings, indexado, ingesta, prediccion
from .indice import ErrorIndice, Indice
from .motor import Consulta, Motor, SinEvidencia

INDICE_POR_DEFECTO = os.getenv("FIXMATE_INDICE", "indice-fixmate.json")
TABLA_PG = os.getenv("FIXMATE_PG_TABLA", "fixmate_fragmentos")


def _indice(args):
    """El indice con el que trabajar: el archivo, o PostgreSQL con --pg.

    Los dos cumplen la misma interfaz, asi que todo lo de abajo —consultar,
    predecir, el estado— no distingue cual tiene delante.
    """
    if getattr(args, "pg", False):
        from .almacen_pg import AlmacenPgvector, ErrorAlmacen

        almacen = AlmacenPgvector(dsn=getattr(args, "dsn", None) or None,
                                  tabla=getattr(args, "tabla", None) or TABLA_PG)
        try:
            len(almacen)       # falla pronto y con su motivo si no conecta
        except ErrorAlmacen as exc:
            print(str(exc), file=sys.stderr)
            return None
        return almacen
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


def cmd_subir(args) -> int:
    """Sube a PostgreSQL lo que ya esta indexado en el archivo."""
    from .almacen_pg import AlmacenPgvector, ErrorAlmacen, desde_indice

    try:
        indice = Indice.cargar(args.indice)
    except ErrorIndice as exc:
        print(str(exc), file=sys.stderr)
        return 1

    almacen = AlmacenPgvector(embebedor=indice.embebedor, dsn=args.dsn or None,
                              tabla=args.tabla or TABLA_PG)
    try:
        subidos = desde_indice(indice, almacen)
        total = len(almacen)
    except ErrorAlmacen as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"{subidos} fragmentos subidos a {almacen.tabla} · {total} en la base")
    print("La oficina sigue indexando en el archivo: la base guarda lo ya leido,")
    print("no lee documentos. Vuelva a subir despues de cada `indexar`.")
    return 0


def cmd_estado(args) -> int:
    """Que hay en el indice y que tan bien aprende de ello."""
    indice = _indice(args)
    if indice is None:
        return 1
    motor = Motor(indice)
    print(f"Indice:     {getattr(indice, 'tabla', None) or args.indice}")
    print(f"Fragmentos: {len(indice)}" +
          (f" de {len(indice.fuentes)} archivos" if indice.fuentes else ""))
    print(f"Embebedor:  {indice.embebedor.nombre}")

    tipos: dict[str, int] = {}
    for fragmento in indice.fragmentos:
        tipos[fragmento.tipo] = tipos.get(fragmento.tipo, 0) + 1
    print("Por tipo:   " + ", ".join(f"{n} {t}" for t, n in sorted(tipos.items())))

    # Cuanto del historial reconoce el catalogo, y sobre todo que no. Ese
    # segundo numero es la lista de lo que hay que agregarle: mientras esta
    # ahi, esas causas se agrupan por parecido y no se pueden comparar entre
    # equipos ni entre años.
    from .catalogo import POR_DEFECTO as catalogo

    cobertura = catalogo.cobertura(
        f.metadatos.get("causa_raiz", "") for f in indice.fragmentos)
    if cobertura["total"]:
        print(f"\nCatálogo de causas: {cobertura['codificadas']} de "
              f"{cobertura['total']} codificadas ({cobertura['cobertura']:.0%}), "
              f"{len(cobertura['por_codigo'])} códigos distintos")
        for codigo, casos in list(cobertura["por_codigo"].items())[:6]:
            entrada = catalogo.get(codigo)
            print(f"  {casos:>3} · {codigo:<34} {entrada.modo if entrada else ''}")
        if cobertura["faltantes"]:
            print(f"  Sin código ({cobertura['sin_codigo']}). Lo más repetido "
                  f"primero: es lo que más rinde agregar al catálogo.")
            for texto in cobertura["faltantes"][:5]:
                print(f"      · {texto[:66]}")

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
    # Antes de los pasos, siempre: quien lee esto va a tocar la maquina.
    if diagnostico.precauciones:
        print("\nANTES DE TOCAR LA MAQUINA")
        for cuidado in diagnostico.precauciones:
            sello = ("manual" if cuidado["origen"] == "manual"
                     else "regla de la herramienta")
            if cuidado.get("referencia"):
                sello += f": {cuidado['referencia']}"
            print(f"  · {cuidado['texto']}")
            print(f"    ({sello})")

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
    motor = Motor(indice)

    texto = args.consulta or ""
    if not texto.strip():
        print("Escriba la consulta.", file=sys.stderr)
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


def cmd_recibir(args) -> int:
    """Mete en el historial lo que el telefono cerro en faena."""
    historial = Path(args.historial)
    indice = None
    if Path(args.indice).is_file():
        indice = _indice(args)
        if indice is None:
            return 1
    try:
        parte = cierre.recibir(args.envio, historial, indice)
    except cierre.ErrorCierre as exc:
        print(str(exc), file=sys.stderr)
        return 1

    for informe in parte.nuevos:
        print(f"  nuevo: {informe['codigo_ot']} · {informe.get('resumen_falla', '')[:60]}")
    for codigo in parte.repetidos:
        print(f"  ya estaba: {codigo}")
    for codigo, motivo in parte.rechazados:
        print(f"  rechazado: {codigo} · {motivo}", file=sys.stderr)

    print(f"\n{parte.resumen()} · historial: {historial}")
    if indice is not None and parte.hubo_cambios:
        indice.guardar(args.indice)
        print(f"Indexado en {args.indice}: la siguiente consulta ya los encuentra.")
    elif parte.hubo_cambios:
        print(f"Reindexe para que se puedan consultar: nefer fixmate indexar {historial}")
    return 0 if not parte.rechazados else 2


def cmd_servir(args) -> int:
    try:
        import uvicorn
    except ImportError:
        print("servir necesita uvicorn: pip install nefer[fixmate-api]",
              file=sys.stderr)
        return 1
    from .api import crear_app

    app = crear_app(ruta_indice=args.indice,
                    almacen="pg" if getattr(args, "pg", False) else None)
    donde = "PostgreSQL" if getattr(args, "pg", False) else args.indice
    print(f"FixMate en http://{args.host}:{args.puerto}  (indice: {donde})")
    uvicorn.run(app, host=args.host, port=args.puerto)
    return 0


def cmd_sql(args) -> int:
    from .almacen_pg import DDL

    print(DDL)
    return 0


# ----------------------------------------------------------- RCM y TPM

def _cargar(fn, ruta):
    """Carga un documento y muestra el error legible en vez de una traza."""
    from .cargador import ErrorCargador
    try:
        return fn(ruta)
    except ErrorCargador as exc:
        print(str(exc), file=sys.stderr)
        return None


def cmd_rcm_analizar(args) -> int:
    """Valida un analisis RCM contra las siete preguntas de JA1011."""
    from . import cargador
    from .rcm import calidad, completitud

    par = _cargar(cargador.analisis_y_decisiones, args.archivo)
    if par is None:
        return 1
    analisis, decisiones = par

    print(f"Activo:   {analisis.activo.descripcion()}")
    print(f"Contexto: {analisis.contexto or '(sin declarar)'}")
    print(f"Funciones {len(analisis.funciones)} · fallas funcionales "
          f"{len(analisis.fallas)} · modos de falla {len(analisis.modos)}")
    graves, ocultos = analisis.modos_graves(), analisis.modos_ocultos()
    if graves:
        print(f"  {len(graves)} con consecuencia de seguridad o ambiental")
    if ocultos:
        print(f"  {len(ocultos)} ocultos: su tratamiento por defecto es "
              "busqueda de fallas")

    estado = completitud(analisis, decisiones.por_modo)
    print(f"\nSAE JA1011: {estado.resumen()}")
    for r in estado.pendientes:
        print(f"  Q{r.pregunta.numero} · {r.pregunta.texto}")
        for falta in r.faltantes[:4]:
            print(f"      - {falta}")

    if decisiones:
        print("\nEstrategias: " + ", ".join(
            f"{n} {k}" for k, n in decisiones.reparto().items() if n))
        bloqueados = [m for m, x in decisiones if x.bloqueado_por_seguridad]
        if bloqueados:
            print(f"  {len(bloqueados)} con rediseño OBLIGATORIO: ninguna tarea "
                  "proactiva alcanza y la falla puede herir a alguien.")

    # El analisis como REGISTRO, que no es lo mismo que su completitud. Las
    # siete preguntas dicen si esta terminado; esto, si se puede auditar
    # dentro de dos años. El codigo de salida sigue hablando solo de JA1011
    # para no cambiarle el contrato a quien ya lo use en un guion.
    reg = calidad(analisis, hoy=args.hoy or "")
    print(f"\nRegistro: {reg.resumen()}")
    for h in reg.hallazgos:
        print(f"  [{h.gravedad}] {h.detalle}")

    if args.indexar:
        indice = _indice(args)
        if indice is None:
            return 1
        n = indexado.indexar(indice, indexado.de_analisis(analisis, decisiones))
        if not getattr(args, "pg", False):
            indice.guardar(args.indice)
        print(f"\n{n} modos de falla indexados. Ahora una consulta de campo "
              "los recupera como cualquier otro antecedente.")
    return 0 if estado.completo else 2


def cmd_rcm_listar(args) -> int:
    """Los modos de falla RCM que hay en el indice."""
    indice = _indice(args)
    if indice is None:
        return 1
    filas = [(f.metadatos.get("codigo_equipo", ""), f.metadatos.get("modo_falla_id", ""),
              f.metadatos.get("sistema", ""), f.metadatos.get("estrategia_rotulo", ""),
              f.metadatos.get("criticidad", ""), f.metadatos.get("estado_validacion", ""))
             for f in indice.fragmentos if f.tipo == indexado.TIPO_RCM]
    if not filas:
        print("No hay analisis RCM en el indice. Carguelos con "
              "`nefer fixmate rcm analizar archivo.json --indexar`.")
        return 0
    print(f"{len(filas)} modos de falla analizados\n")
    print(f"{'EQUIPO':<10} {'MODO':<10} {'SISTEMA':<14} {'ESTRATEGIA':<32} "
          f"{'CRITICIDAD':<14} ESTADO")
    for fila in sorted(filas):
        print("{:<10} {:<10} {:<14} {:<32} {:<14} {}".format(*(x or "-" for x in fila)))
    return 0


def cmd_rcm_matriz(args) -> int:
    """Exporta la matriz FMEA/FMECA en CSV."""
    from . import cargador, fmeca
    from .plan import generar

    par = _cargar(cargador.analisis_y_decisiones, args.archivo)
    if par is None:
        return 1
    analisis, decisiones = par
    plan = generar(analisis, decisiones)
    csv = fmeca.a_csv(analisis, decisiones, plan, delimitador=args.delimitador)
    if args.salida:
        Path(args.salida).write_text(csv, encoding="utf-8")
        print(f"{args.salida} · {len(analisis.modos)} filas")
    else:
        print(csv, end="")
    return 0


def cmd_rcm_tareas(args) -> int:
    """El plan de tareas que sale del analisis, con los huecos a la vista."""
    from . import cargador
    from .plan import falta_por_completar, generar

    par = _cargar(cargador.analisis_y_decisiones, args.archivo)
    if par is None:
        return 1
    analisis, decisiones = par
    plan = generar(analisis, decisiones)
    if not plan.tareas and not plan.sin_tarea:
        print("El analisis no tiene decisiones registradas todavia, asi que no "
              "hay plan. Responda la Q6 antes de pedir tareas.")
        return 2
    print(f"{len(plan.tareas)} tareas · {len(plan.completas)} listas · "
          f"{len(plan.borradores)} en borrador")
    for t in plan.tareas:
        print(f"\n{t.id} · {t.estrategia} ({t.disparador})")
        print(f"   modo {t.modo_falla_id} · {t.componente}")
        for falta in falta_por_completar(t):
            print(f"   falta: {falta}")
    if plan.sin_tarea:
        print(f"\nSin tarea a proposito (operar hasta la falla): "
              f"{', '.join(plan.sin_tarea)}")
    return 0


def cmd_tpm_checklist(args) -> int:
    """Valida una pauta de mantenimiento autonomo."""
    from . import cargador

    pauta = _cargar(cargador.checklist, args.archivo)
    if pauta is None:
        return 1
    print(f"{pauta.id} · {pauta.activo_codigo} · {pauta.nombre}")
    print(f"{len(pauta.puntos)} puntos · {pauta.frecuencia} · "
          f"presupuesto {pauta.presupuesto_seg} s")
    for p in pauta.puntos:
        alcance = "operador" if p.alcance_operador else "TECNICO"
        print(f"  {p.id:<8} {p.clase:<14} {p.punto:<34} [{alcance}] {p.criterio}")
    sin_criterio = [p.id for p in pauta.puntos if not p.criterio.strip()]
    if sin_criterio:
        print(f"Sin criterio: {', '.join(sin_criterio)}", file=sys.stderr)
        return 2
    if args.indexar:
        indice = _indice(args)
        if indice is None:
            return 1
        indexado.indexar(indice, [indexado.de_checklist(pauta)])
        if not getattr(args, "pg", False):
            indice.guardar(args.indice)
        print("Pauta indexada.")
    return 0


def cmd_tpm_ejecutar(args) -> int:
    """Registra una ronda y levanta las anomalias que haya."""
    from . import cargador
    from .anomalia import desde_ejecucion
    from .tpm import estado as estado_ronda

    pauta = _cargar(cargador.checklist, args.pauta)
    ejecucion = _cargar(cargador.ejecucion, args.archivo)
    if pauta is None or ejecucion is None:
        return 1

    analisis = None
    if args.rcm:
        par = _cargar(cargador.analisis_y_decisiones, args.rcm)
        if par is None:
            return 1
        analisis = par[0]

    e = estado_ronda(ejecucion, pauta)
    print(f"{ejecucion.id} · {pauta.activo_codigo} · {ejecucion.operador}")
    print(f"{e.respondidos}/{e.total} puntos · {e.ok} OK · {e.nok} NOK · "
          f"{e.sin_acceso} sin ver · {e.segundos} s de {e.presupuesto_seg}")
    print("Ronda COMPLETA" if e.completa else "Ronda INCOMPLETA")
    if e.sin_acceso:
        print("  Un punto que no se pudo ver no cuenta como visto: la ronda no "
              "vale como completa aunque esten los demas.")
    if e.sospechosa_de_firma:
        print("  AVISO: demasiado rapida para haber sido ejecutada. Criterio "
              "configurable de la planta, no una norma.")

    anomalias = desde_ejecucion(ejecucion, pauta, analisis)
    if not anomalias:
        print("\nSin anomalias.")
    for a in anomalias:
        enlace = (f"modo {a.modo_falla_id}" if a.enlazada
                  else ("sin enlazar a RCM" if not a.codigo_catalogo
                        else f"codigo {a.codigo_catalogo}, sin modo que lo declare"))
        print(f"\n{a.id} · {a.severidad} · {a.descripcion}")
        print(f"   {enlace}")

    if args.salida:
        Path(args.salida).write_text(
            json.dumps({"ejecucion": ejecucion.a_dict(),
                        "anomalias": [a.a_dict() for a in anomalias]},
                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n{args.salida}")
    return 0


def cmd_tpm_pendientes(args) -> int:
    """Las anomalias abiertas que hay en el indice."""
    indice = _indice(args)
    if indice is None:
        return 1
    abiertas = [f for f in indice.fragmentos
                if f.tipo == indexado.TIPO_ANOMALIA and f.metadatos.get("abierta")]
    if not abiertas:
        print("No hay anomalias abiertas en el indice.")
        return 0
    print(f"{len(abiertas)} anomalias abiertas\n")
    for f in sorted(abiertas, key=lambda x: str(x.metadatos.get("fecha") or "")):
        m = f.metadatos
        print(f"{m.get('fecha',''):<12} {m.get('codigo_equipo',''):<10} "
              f"{m.get('severidad',''):<13} {m.get('resumen_falla','')}")
    return 0


def cmd_tablero(args) -> int:
    """Los indicadores de confiabilidad que el historial permite calcular."""
    from . import tablero as _tablero

    indice = _indice(args)
    if indice is None:
        return 1
    datos = _tablero.confiabilidad(indice)
    print(f"Equipos con historial: {datos.equipos}")
    print(f"Fallas registradas:    {datos.fallas}")
    if datos.mtbf_dias:
        print("\nMTBF por equipo (dias entre fallas, base calendario):")
        for codigo, dias in sorted(datos.mtbf_dias.items()):
            print(f"  {codigo:<10} {dias:>5} d")
    faltan = datos.equipos - len(datos.mtbf_dias)
    if faltan > 0:
        print(f"  ({faltan} sin MTBF: con una sola aparicion no hay intervalo, "
              "hay una fecha)")
    print("\nMTTR y disponibilidad: sin dato. FixMate registra cuando ocurrio "
          "una falla,\nno cuanto duro la reparacion. Un MTTR inventado se usa "
          "para dimensionar\nun taller, asi que no se calcula.")
    if datos.reincidencias_vencidas:
        print(f"\nReincidencias vencidas: {datos.reincidencias_vencidas}")
    return 0


def agregar_subcomando(sub) -> None:
    """Cuelga `fixmate` y sus ordenes del parser principal de nefer."""
    f = sub.add_parser(
        "fixmate",
        help="asistente de diagnostico sobre el historial de fallas y los manuales")
    f.add_argument("-i", "--indice", default=INDICE_POR_DEFECTO,
                   help=f"archivo de indice (por defecto, {INDICE_POR_DEFECTO})")
    ordenes = f.add_subparsers(dest="orden", required=True)

    def con_pg(sub):
        """Las ordenes que pueden trabajar contra la base en vez del archivo."""
        sub.add_argument("--pg", action="store_true",
                         help="usar PostgreSQL con pgvector en vez del archivo")
        sub.add_argument("--dsn", help="cadena de conexion; por defecto, FIXMATE_PG_DSN")
        sub.add_argument("--tabla", help=f"tabla o vista (por defecto, {TABLA_PG})")
        return sub

    i = ordenes.add_parser("indexar",
                           help="historial, manuales y actas -> indice")
    i.add_argument("rutas", nargs="+",
                   help="archivos o carpetas (.json, .xlsx, .pdf, .docx, .md, .txt)")
    i.add_argument("-o", "--salida", help="ruta del indice a escribir")
    i.add_argument("--embebedor", default="local", choices=["local"],
                   help="el motor corre en esta maquina; no sale a ningun servicio")
    i.add_argument("--completo", action="store_true",
                   help="rehacer el indice entero en vez de solo lo que cambio")
    i.add_argument("--sin-podar", action="store_true",
                   help="conservar en el indice los archivos que ya no existen")
    i.set_defaults(func=cmd_indexar)

    u = ordenes.add_parser(
        "subir", help="subir el indice a PostgreSQL con pgvector")
    u.add_argument("--dsn", help="cadena de conexion; por defecto, FIXMATE_PG_DSN")
    u.add_argument("--tabla", help=f"tabla de destino (por defecto, {TABLA_PG})")
    u.set_defaults(func=cmd_subir)

    t = con_pg(ordenes.add_parser(
        "estado", help="que hay en el indice y que tan bien aprende"))
    t.add_argument("--archivos", action="store_true",
                   help="listar tambien los archivos indexados")
    t.set_defaults(func=cmd_estado)

    c = con_pg(ordenes.add_parser("consultar", help="preguntar por una falla"))
    c.add_argument("consulta", nargs="?",
                   help="la falla, como la describiria el tecnico")
    c.add_argument("--dtc", help="codigo de falla, si el tablero da uno")
    c.add_argument("-e", "--equipo", help="codigo del equipo de la flota")
    c.add_argument("--categoria", help="familia del equipo")
    c.add_argument("-n", "--limite", type=int, default=3,
                   help="cuantos antecedentes recuperar (1 a 10)")
    c.add_argument("--json", action="store_true", help="salida en JSON")
    c.set_defaults(func=cmd_consultar)

    d = con_pg(ordenes.add_parser(
        "predecir", help="que le va a pasar a un equipo, segun lo que ya le paso"))
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

    b = ordenes.add_parser(
        "recibir", help="meter en el historial lo que el telefono cerro en faena")
    b.add_argument("envio", help="archivo que exporto la app de campo")
    b.add_argument("--historial", default=os.getenv("FIXMATE_HISTORIAL",
                                                    "historial-fallas.json"),
                   help="historial donde anotarlos")
    b.set_defaults(func=cmd_recibir)

    s = con_pg(ordenes.add_parser("servir", help="levantar la API HTTP"))
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--puerto", type=int, default=8000)
    s.set_defaults(func=cmd_servir)

    q = ordenes.add_parser("sql", help="imprimir el esquema de PostgreSQL con pgvector")
    q.set_defaults(func=cmd_sql)

    # ---------------------------------------------------------- RCM
    rcm = ordenes.add_parser(
        "rcm", help="analisis de confiabilidad: JA1011, matriz FMECA y tareas")
    rcm_sub = rcm.add_subparsers(dest="accion", required=True)

    ra = con_pg(rcm_sub.add_parser(
        "analizar", help="validar un analisis contra las siete preguntas"))
    ra.add_argument("archivo", help="el analisis en JSON")
    ra.add_argument("--indexar", action="store_true",
                    help="meterlo al indice para que el motor lo recupere")
    # La vigencia solo se mira si se dice contra que dia. Una salida que
    # cambia sola con el calendario no se puede comparar ni probar.
    ra.add_argument("--hoy", default="", metavar="AAAA-MM-DD",
                    help="comprobar tambien si la revision esta vencida")
    ra.set_defaults(func=cmd_rcm_analizar)

    rl = con_pg(rcm_sub.add_parser("listar", help="los modos de falla del indice"))
    rl.set_defaults(func=cmd_rcm_listar)

    rm = rcm_sub.add_parser("matriz", help="exportar la matriz FMEA/FMECA en CSV")
    rm.add_argument("archivo", help="el analisis en JSON")
    rm.add_argument("-o", "--salida", help="archivo CSV a escribir")
    rm.add_argument("--delimitador", default=";",
                    help="por defecto «;», que es lo que Excel en es-PE espera")
    rm.set_defaults(func=cmd_rcm_matriz)

    rt = rcm_sub.add_parser("tareas", help="el plan que sale del analisis")
    rt.add_argument("archivo", help="el analisis en JSON")
    rt.set_defaults(func=cmd_rcm_tareas)

    # ---------------------------------------------------------- TPM
    tpm = ordenes.add_parser(
        "tpm", help="mantenimiento autonomo: pautas, rondas y anomalias")
    tpm_sub = tpm.add_subparsers(dest="accion", required=True)

    tc = con_pg(tpm_sub.add_parser("checklist", help="validar una pauta"))
    tc.add_argument("archivo", help="la pauta en JSON")
    tc.add_argument("--indexar", action="store_true", help="meterla al indice")
    tc.set_defaults(func=cmd_tpm_checklist)

    te = tpm_sub.add_parser("ejecutar", help="registrar una ronda")
    te.add_argument("archivo", help="la ejecucion en JSON")
    te.add_argument("-p", "--pauta", required=True, help="la pauta en JSON")
    te.add_argument("--rcm", help="el analisis, para enlazar las anomalias")
    te.add_argument("-o", "--salida", help="archivo JSON con el resultado")
    te.set_defaults(func=cmd_tpm_ejecutar)

    tp = con_pg(tpm_sub.add_parser("pendientes", help="anomalias abiertas"))
    tp.set_defaults(func=cmd_tpm_pendientes)

    # ------------------------------------------------------ indicadores
    tb = con_pg(ordenes.add_parser(
        "tablero", help="MTBF y recurrencia sobre el historial cargado"))
    tb.set_defaults(func=cmd_tablero)
