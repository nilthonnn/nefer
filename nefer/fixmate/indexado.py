"""RCM y TPM como fragmentos: por que el §6 sale casi gratis.

Toda la persistencia de FixMate es un solo tipo —`Fragmento`— que vive en un
archivo JSON que se copia al telefono o en una tabla de PostgreSQL. Meter
tablas relacionales para RCM habria roto la propiedad que sostiene el
producto: el indice viaja al bolsillo del tecnico y funciona sin red.

El efecto secundario es el que importa. Un analisis RCM convertido en
fragmento queda BUSCABLE por el mismo motor: preguntar «el motor se
recalienta» recupera el modo de falla del radiador sin que nadie escriba una
linea de integracion, porque ya es evidencia como cualquier otra.

----------------------------------------------------------------------------
QUE TEXTO SE INDEXA, Y POR QUE ESE

El texto del fragmento es lo que se busca, asi que decide si el analisis se
encuentra o no. Aqui se escribe con las palabras del TECNICO y no con las
del analista: el campo `resumen_falla` de los informes dice «se recalienta
en pendiente», no «perdida de la funcion de disipacion termica». Un
fragmento RCM redactado en lenguaje de norma no se parece a ninguna consulta
real y no sale nunca.

Por eso el texto lleva, en este orden: la falla funcional y el modo de falla
—que es como se describe la averia—, despues el efecto —que es lo que el
operador observa— y al final la funcion y el estandar, que es contexto.

Y lleva ademas las PISTAS DEL CATALOGO de la entrada que el modo referencia.
Esas pistas —«radiador», «obstruid», «panal», «tierra», «sobrecalient»— son
exactamente el vocabulario con el que el taller escribe la averia: estan ahi
para reconocer texto libre de campo, que es el mismo problema. Sin ellas, un
analisis redactado en lenguaje de norma puntuaba 0,000 contra una consulta
real, medido. Reutilizarlas no inventa nada: es el mismo dato que ya
clasifica las causas.

EL LIMITE, MEDIDO Y NO ESTIMADO. Con las pistas dentro, «radiador tapado con
tierra» recupera el analisis con 0,558 y «temperatura alta y el panal sucio»
con 0,591, contra 0,000 sin ellas. Pero «el motor sobrecalienta» sigue en
0,016, y la razon no esta aqui: el propio catalogo tampoco codifica ese
texto —sus pistas son raices para su comparador por prefijo, y dos palabras
genericas no alcanzan el minimo de pistas—. Es el mismo techo de cobertura
del catalogo, heredado, no uno nuevo. Se agranda agrandando el catalogo, que
es lo que `catalogo.cargar()` existe para hacer.

LO QUE **NO** SE INDEXA COMO PROCEDIMIENTO. Un fragmento RCM no lleva
`pasos`. El motor usa `metadatos["pasos"]` para armar el procedimiento de la
respuesta, y un analisis RCM no tiene procedimiento: tiene estrategia. Si
los llevara, el motor podria responder «cambie el radiador» citando un
analisis que nunca dijo como. Los pasos siguen saliendo de los informes y de
los manuales, que es donde estan escritos.
----------------------------------------------------------------------------
"""

from __future__ import annotations

from . import catalogo as _catalogo
from .indice import Fragmento

TIPO_RCM = "rcm"
TIPO_TPM = "tpm"
TIPO_ANOMALIA = "anomalia"


def _lineas(*pares) -> str:
    return "\n".join(f"{k}: {v}" for k, v in pares if str(v or "").strip())


def de_modo_falla(analisis, modo, decision=None, fuente: str = "") -> Fragmento:
    """Un modo de falla del analisis -> un fragmento buscable.

    La unidad es el MODO, no el analisis entero: es el nivel al que se decide
    la tarea y al que apunta la anomalia TPM, y un analisis completo en un
    solo fragmento recuperaria la bomba entera cuando se pregunta por el
    radiador.
    """
    activo = analisis.activo
    falla = next((f for f in analisis.fallas
                  if f.id == modo.falla_funcional_id), None)
    funcion = next((f for f in analisis.funciones
                    if falla and f.id == falla.funcion_id), None)
    efecto = modo.efecto

    # El vocabulario de campo, cuando el modo declara su entrada de catalogo.
    entrada = (_catalogo.Catalogo().get(modo.codigo_catalogo)
               if modo.codigo_catalogo else None)

    # El orden importa: primero como se describe la averia, que es lo que se
    # parece a una consulta real.
    cuerpo = _lineas(
        ("ANALISIS RCM", f"{activo.codigo} · modo {modo.id}"),
        ("Modo de falla", modo.descripcion),
        ("Falla funcional", falla.descripcion if falla else ""),
        ("Causa", modo.causa),
        ("Mecanismo", modo.mecanismo),
        ("Componente", str(modo.ubicacion)),
        ("Lo que se observa", efecto.observa_operador),
        ("Efecto", efecto.local),
        ("Parametro", efecto.parametro),
        ("Alarma", efecto.alarma),
        ("Como detectarlo", efecto.como_detectarlo),
        ("Funcion", funcion.descripcion if funcion else ""),
        ("Estandar", funcion.estandar if funcion else ""),
        ("Contexto operacional", analisis.contexto),
        ("Consecuencia", ", ".join(
            f"{c.clase}{': ' + c.descripcion if c.descripcion else ''}"
            for c in modo.consecuencias)),
        ("Falla oculta", "si" if not modo.evidente else ""),
        ("Criticidad", modo.criticidad.etiqueta),
        ("Estrategia", decision.rotulo if decision else ""),
        ("Motivo de la estrategia", decision.motivo if decision else ""),
        # Al final: es vocabulario para que la busqueda lo encuentre, no algo
        # que un humano necesite leer.
        ("Se observa como", entrada.modo if entrada else ""),
        ("Como se describe en campo", ", ".join(entrada.pistas) if entrada else ""),
    )

    metadatos = {
        # Las mismas claves que usan los informes: asi los filtros y las
        # preferencias del motor funcionan sin tocar el motor.
        "codigo_equipo": activo.codigo,
        "categoria": activo.categoria,
        "modelo_equipo": activo.modelo,
        # Las propias del analisis.
        "modo_falla_id": modo.id,
        "codigo_catalogo": modo.codigo_catalogo,
        "sistema": modo.ubicacion.sistema,
        "componente": modo.ubicacion.componente,
        "evidente": modo.evidente,
        "consecuencias": [c.clase for c in modo.consecuencias],
        "grave": modo.grave,
        "criticidad": modo.criticidad.etiqueta,
        "estado_validacion": modo.estado,
        # `causa_raiz` con el mismo nombre que en los informes: el motor la
        # lee para armar la evidencia y para cruzarla con el clasificador.
        "causa_raiz": modo.causa or modo.descripcion,
        "resumen_falla": falla.descripcion if falla else modo.descripcion,
        # Sin `pasos` a proposito. Ver el encabezado.
    }
    if decision is not None:
        metadatos["estrategia"] = decision.estrategia
        metadatos["estrategia_rotulo"] = decision.rotulo

    return Fragmento(id=f"rcm:{activo.codigo}:{modo.id}", texto=cuerpo,
                     fuente=fuente or f"RCM {activo.codigo}",
                     tipo=TIPO_RCM, metadatos=metadatos)


def de_analisis(analisis, decisiones=None, fuente: str = "") -> list[Fragmento]:
    """Un fragmento por modo de falla."""
    get = getattr(decisiones, "get", lambda _: None) if decisiones else (lambda _: None)
    return [de_modo_falla(analisis, m, get(m.id), fuente) for m in analisis.modos]


def de_checklist(checklist, fuente: str = "") -> Fragmento:
    """La pauta autonoma -> un fragmento.

    Sirve para que una consulta sobre un sintoma encuentre tambien el punto
    de la ronda que lo vigila: eso es lo que el §6 pide cuando dice
    «inspecciones autonomas relevantes».
    """
    cuerpo = _lineas(
        ("PAUTA DE MANTENIMIENTO AUTONOMO", f"{checklist.activo_codigo} · {checklist.nombre}"),
        ("Frecuencia", checklist.frecuencia),
        ("Origen", checklist.origen),
    )
    if checklist.puntos:
        cuerpo += "\n" + "\n".join(
            f"- {p.clase}: {p.punto} — {p.criterio}" for p in checklist.puntos)

    return Fragmento(
        id=f"tpm:{checklist.id}", texto=cuerpo,
        fuente=fuente or f"Pauta {checklist.id}", tipo=TIPO_TPM,
        metadatos={
            "codigo_equipo": checklist.activo_codigo,
            "checklist_id": checklist.id,
            "frecuencia": checklist.frecuencia,
            "puntos": [p.punto for p in checklist.puntos],
            "codigos_catalogo": [p.codigo_catalogo for p in checklist.puntos
                                 if p.codigo_catalogo],
            "modos_falla": [p.modo_falla_id for p in checklist.puntos
                            if p.modo_falla_id],
            "resumen_falla": f"Pauta autonoma de {checklist.activo_codigo}",
        })


def de_anomalia(a, fuente: str = "") -> Fragmento:
    """Una anomalia -> un fragmento.

    Se indexa aunque este abierta: una anomalia abierta es justamente la que
    conviene que aparezca cuando alguien consulta por ese sintoma, porque
    puede ser la misma que ya esta reportada.
    """
    cuerpo = _lineas(
        ("ANOMALIA TPM", f"{a.activo_codigo} · {a.id}"),
        ("Lo que se vio", a.descripcion),
        ("Componente", a.componente),
        ("Criterio que no cumple", a.condicion_observada),
        ("Severidad", a.severidad),
        ("Detectada por", a.detectada_por),
        ("Fecha", a.fecha),
        ("Estado", a.estado),
        ("Accion", a.accion),
    )
    return Fragmento(
        id=f"anomalia:{a.id}", texto=cuerpo,
        fuente=fuente or f"Anomalia {a.id}", tipo=TIPO_ANOMALIA,
        metadatos={
            "codigo_equipo": a.activo_codigo,
            "anomalia_id": a.id,
            "codigo_catalogo": a.codigo_catalogo,
            "modo_falla_id": a.modo_falla_id,
            "severidad": a.severidad,
            "estado": a.estado,
            "fecha": a.fecha,
            "abierta": a.abierta,
            "resumen_falla": a.descripcion,
            "causa_raiz": "",   # una anomalia NO trae causa confirmada
            "codigo_ot": a.codigo_ot,
        })


def indexar(indice, fragmentos) -> int:
    """Mete los fragmentos en un indice ya cargado. Devuelve cuantos."""
    fragmentos = list(fragmentos)
    indice.agregar(fragmentos)
    return len(fragmentos)
