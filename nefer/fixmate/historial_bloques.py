"""El historial tal como lo exporta el sistema del taller: por bloques.

Todo lo demas de FixMate asume un historial de una fila por orden de trabajo,
con una columna de causa raiz. Eso es lo que se pide en una plantilla, y no es
lo que sale de un sistema de mantenimiento de verdad.

Lo que sale de verdad es esto: un encabezado por orden —«ORDEN TRABAJO ·
TRABAJOS REALIZADOS · HOROMETRO · FECHA · SUMINISTROS · SERVICIOS TERCEROS ·
OBSERVACIONES»— repetido cuarenta veces en la misma hoja, y debajo de cada uno
una fila con el numero de orden y la fecha, seguida de veinte, cincuenta o
noventa filas de material y servicio. Lo que no sale es la causa: en trece anos
de historia de un manlift, nadie escribio nunca por que fallo.

Asi que no se le pide. Ese era el requisito equivocado: una herramienta que
exige una columna que el taller no llena no se usa, se abandona. **Lo que se
cambio es el registro de lo que fallo**, y eso si esta escrito. Un kit de
sellos mas un «rectificado de hilo de vastago de cilindro pendular» dice que
se fue el cilindro pendular, lo diga alguien o no. Noventa y siete lineas de
suministro en una sola orden dicen que eso no fue una reparacion, fue una
reconstruccion.

Dos cosas que este lector separa y que venian pegadas:

**El nombre del tecnico.** Cada linea de suministro acaba en «  -  APELLIDOS,
NOMBRE». Es dato util —quien lo hizo— y es basura dentro de la descripcion de
una pieza: con el nombre pegado, «ACEITE 15W40 RIMULA R4X SHELL» son seis
repuestos distintos en vez de uno. Se parte en dos y no se pierde ninguno.

**La fecha del despacho.** Las lineas vienen con «22/06/2026 - » delante, que
es cuando se entrego el material, no cuando se abrio la orden. Tambien se
separa.

Lo que no se sabe no se rellena. La causa raiz queda vacia y `cobertura()` la
cuenta como sin codificar, que es la medida honesta de cuanto falta.
"""

from __future__ import annotations

import re
from pathlib import Path

# SEIS DOCUMENTOS, NO UNO.
#
# Esto se escribio creyendo que el export traia ordenes de trabajo y nada mas.
# Medido sobre el historial de trece anos de un manlift real: de 245 bloques,
# solo 40 eran «ORDEN TRABAJO» o «CONTROL_EXTRACCIONES». Los otros 205 se
# descartaban en silencio —el 84 % del historial de la maquina—, y entre ellos
# los 114 INFORME TECNICO CAMPO, que es justamente el documento donde el
# tecnico escribe que encontro.
#
# El sintoma no era un error: era la app diciendo «40 fragmentos, 0 casos con
# causa confirmada» sobre un archivo de 1.674 filas, y respondiendo una
# consulta del manlift con el manual de un grupo electrogeno. Un lector que
# descarta cuatro de cada cinco documentos no da error en ninguna parte.
_DOCUMENTOS = {
    "orden trabajo": "orden de trabajo",
    "orden de trabajo": "orden de trabajo",
    "nro orden": "orden de trabajo",
    "n orden": "orden de trabajo",
    "control_extracciones": "control de extracciones",
    "informe tecnico campo": "informe tecnico de campo",
    "informe tecnico de campo": "informe tecnico de campo",
    "hoja de servicio": "hoja de servicio",
    "acta de recepcion": "acta de recepcion",
    "guia de remision": "guia de remision",
}

# Los cuatro que pueden traer una falla descrita. Los otros dos son logistica
# —la maquina entrando o saliendo— y se leen igual, pero por otra razon: su
# fecha y su horometro son una LECTURA, y de las lecturas sale el ritmo de uso
# y el proximo servicio. Tratar un acta de recepcion como una averia inflaria
# la cuenta de fallas de una flota de alquiler, que se despacha y se recibe
# varias veces al ano sin que se le rompa nada.
_DOCUMENTOS_DE_INTERVENCION = frozenset({
    "orden de trabajo", "control de extracciones",
    "informe tecnico de campo", "hoja de servicio",
})

# La cabecera que se repite. Hace falta la del documento y al menos una de las
# que fechan el bloque: con solo una palabra, cualquier hoja con la columna
# «fecha» pasaria por un historial por bloques.
_ENCABEZADO_ORDEN = tuple(_DOCUMENTOS)
_ENCABEZADO_APOYO = ("horometro", "fecha", "suministros")

# El numero de orden tal como lo escribe el sistema: 001-0042245, 031-0022835.
_RE_ORDEN = re.compile(r"^\d{2,4}-\d{3,}$")

# «22/06/2026 - » o «15/07/2026, 25/06/2026 - » al principio de la linea.
_RE_FECHA_DELANTE = re.compile(r"^\s*((?:\d{2}/\d{2}/\d{4}\s*,?\s*)+)-\s*")

# «  -  CARDENAS OCHOA, KEVIN SANDRO» al final. Dos espacios tras el guion es
# lo que lo distingue de una marca: «SPRAY AFLOJATODO 10 ONZ - VISTONY» lleva
# uno solo, y VISTONY es el fabricante, no quien lo instalo.
_RE_QUIEN = re.compile(r"\s+-\s{2,}([A-ZÁÉÍÓÚÑ][^-]{4,})$")

# «... TECNICO : PICHA CALCINA, ANDRE». En la columna de trabajos realizados
# el nombre no va al final tras dos espacios —como en una linea de material—
# sino rotulado, y a veces seguido de otro texto. Medido: 27 de los 83
# hallazgos del archivo real lo llevaban pegado, y asi el nombre de un tecnico
# se indexaba como si fuera parte del sintoma. Un nombre no es un sintoma: no
# ayuda a recuperar nada y es dato personal de su gente.
# El nombre puede venir VACIO —«... TECNICO : » y nada mas—, y entonces hay
# que quitar igual la etiqueta suelta: deja «TECNICO :» dentro del sintoma.
# Sin re.S a proposito: en una celda de varias lineas, el rotulo se quita de
# la ultima y no se arrastra el resto del texto con el.
_RE_TECNICO = re.compile(r"\s*T[EÉ]CNICOS?\s*:\s*(.*)$", re.I)

# «HISTORIAL EQUIPO : MLAD041-02»
_RE_TITULO = re.compile(r"HISTORIAL\s+EQUIPO\s*:\s*([A-Z0-9][A-Z0-9/.-]*)", re.I)

# Lo que la columna de observaciones dice cuando no dice nada. Se compara por
# el principio, no por la celda entera: la plantilla del taller escribe «EQUIPO
# OPERATIVO POR EL TECNICO FULANO Y MENGANO», que sigue sin ser un hallazgo.
_SIN_HALLAZGO = ("equipo operativo", "operativo", "sin observacion", "ninguna",
                 "observacion", "conforme", "ok",
                 # El estado del documento. «CERRADO» no dice nada de la
                 # maquina, y colarlo como hallazgo llenaria el historial de
                 # fallas llamadas «cerrado».
                 "cerrado", "abierto", "pendiente", "anulado", "atendido")

# Celdas de relleno: guiones y espacios, nada mas.
_RE_RELLENO = re.compile(r"^[\s.\-_·]*$")


def _vacio(valor: str) -> bool:
    """Si la celda no dice nada: vacia, o solo guiones de relleno."""
    return not valor or bool(_RE_RELLENO.match(valor))


def _es_plantilla(valor: str) -> bool:
    """Si la celda es la frase hecha que el taller pone cuando no hubo nada.

    Se busca «operativ» en cualquier parte y no la frase exacta, porque el
    archivo de verdad trae «EQUIOPO OPERATIVO» —con la errata— y «EQUIPO
    OPERATIVO POR EL TECNICO FULANO Y MENGANO». Perseguir erratas una por una
    no acaba nunca.

    Y una celda de dos letras («OP») no es un hallazgo aunque no case con
    nada: no alcanza para decir nada. Al reves de lo habitual, aqui el error
    caro es pasarse de listo: dar por plantilla algo que si era un hallazgo lo
    borra del historial, asi que solo se descarta lo que es inequivocamente
    relleno.
    """
    limpio = re.sub(r"[^a-z]+", " ", valor.lower()).strip()
    if len(limpio.replace(" ", "")) < 4:
        return True
    if "operativ" in limpio:
        return True
    return any(limpio.startswith(f) for f in _SIN_HALLAZGO)


def _limpio(celda) -> str:
    return "" if celda is None else str(celda).strip()


def partir_linea(linea: str) -> tuple[str, str, str]:
    """Una linea de suministro en sus tres cosas: pieza, fecha y quien.

        >>> partir_linea(" 22/06/2026 - SOLDADURA 7018  -  PEREZ, JUAN")
        ('SOLDADURA 7018', '22/06/2026', 'PEREZ, JUAN')
    """
    resto = str(linea or "")
    fecha = ""
    m = _RE_FECHA_DELANTE.match(resto)
    if m:
        fecha = m.group(1).strip().rstrip(",").strip()
        resto = resto[m.end():]
    quien = ""
    m = _RE_QUIEN.search(resto)
    if m:
        quien = m.group(1).strip()
        resto = resto[:m.start()]
    else:
        m = _RE_TECNICO.search(resto)
        if m:
            quien = " ".join(m.group(1).split())
            resto = resto[:m.start()]
    return resto.strip(), fecha, quien


def es_por_bloques(filas) -> bool:
    """Si la hoja trae la cabecera repetida en vez de una sola arriba.

    Se piden dos cabeceras: una hoja normal con una fila de titulos que
    casualmente dice «orden de trabajo» no es esto, y tratarla como si lo
    fuera le perderia todas las filas menos la primera.
    """
    vistas = 0
    for fila in filas:
        celdas = [_limpio(c).lower() for c in fila]
        if any(c in _ENCABEZADO_ORDEN for c in celdas) and \
           any(c in _ENCABEZADO_APOYO for c in celdas):
            vistas += 1
            if vistas >= 2:
                return True
    return False


def _columnas(celdas: list[str]) -> dict[str, int]:
    """Donde esta cada cosa en este bloque. Cada export las pone en su sitio."""
    donde: dict[str, int] = {}
    for i, c in enumerate(celdas):
        clave = c.lower()
        if clave in _ENCABEZADO_ORDEN:
            donde["orden"] = i
        elif clave in ("horometro", "horómetro"):
            donde["horometro"] = i
        elif clave == "fecha":
            donde["fecha"] = i
        elif clave in ("suministros", "repuestos", "materiales"):
            donde["suministros"] = i
        elif clave in ("servicios terceros", "servicios de terceros", "servicio terceros"):
            donde["terceros"] = i
        elif clave in ("observaciones", "observacion", "observación"):
            donde["obs"] = i
        elif clave in ("cantidad", "cant"):
            donde["cantidad"] = i
        elif clave in ("codigo", "código", "cod"):
            donde["codigo"] = i
        elif clave in ("trabajos realizados", "trabajo realizado"):
            donde.setdefault("trabajos", i)
        # «ESTADO» es el estado del documento, no lo que se hizo. Estaba
        # mapeado como «trabajos realizados» y por eso «CERRADO» habria
        # entrado como descripcion de la falla.
        elif clave == "estado":
            donde["estado"] = i
        # El cliente y la obra ocupan, en los documentos de logistica, la
        # misma columna que «TRABAJOS REALIZADOS» en una orden. Si no se
        # nombra, el nombre del cliente acaba dentro de la descripcion de la
        # falla y se indexa como si fuera un sintoma.
        elif clave in ("cliente / obra", "cliente/obra", "cliente", "obra"):
            donde["cliente"] = i
    return donde


def leer_filas(filas, equipo: str = "", modelo: str = "") -> list[dict]:
    """Las filas de la hoja -> un informe por orden de trabajo.

    `filas` es una lista de listas, como las entrega `openpyxl` con
    `values_only=True`.
    """
    informes: list[dict] = []
    actual: dict | None = None
    donde: dict[str, int] = {}

    for fila in filas:
        celdas = [_limpio(c) for c in fila]
        if not any(celdas):
            continue

        if not equipo:
            for c in celdas:
                m = _RE_TITULO.search(c)
                if m:
                    equipo = m.group(1).strip()
                    break

        bajas = [c.lower() for c in celdas]
        documento = next((_DOCUMENTOS[c] for c in bajas if c in _DOCUMENTOS), "")
        if documento and any(c in _ENCABEZADO_APOYO for c in bajas):
            if actual is not None:
                informes.append(actual)
            donde = _columnas(celdas)
            actual = {"repuestos": [], "terceros": [], "hallazgos": [],
                      "fechas_material": [], "quienes": [], "codigos": [],
                      "documento": documento, "cliente": ""}
            continue

        if actual is None:
            continue

        def dato(nombre: str) -> str:
            i = donde.get(nombre)
            return celdas[i] if i is not None and i < len(celdas) else ""

        orden = dato("orden")
        if orden and _RE_ORDEN.match(orden):
            actual["codigo_ot"] = orden
            if dato("fecha"):
                actual["fecha"] = dato("fecha")
            if dato("horometro"):
                actual["horometro"] = dato("horometro")

        sumin = dato("suministros")
        # Dentro de un bloque el export repite «SUMINISTROS | CODIGO» cada
        # cierto numero de filas. Eso es cabecera, no material.
        if sumin.lower() in ("suministros", "repuestos", "materiales"):
            sumin = ""
        if sumin and not _vacio(sumin):
            pieza, fecha, quien = partir_linea(sumin)
            codigo = dato("codigo")
            if pieza and not _vacio(pieza):
                actual["repuestos"].append(
                    f"{pieza} ({codigo})" if codigo and not _vacio(codigo)
                    else pieza)
            if fecha:
                actual["fechas_material"].append(fecha)
            if quien and quien not in actual["quienes"]:
                actual["quienes"].append(quien)
            if codigo and codigo not in actual["codigos"]:
                actual["codigos"].append(codigo)

        tercero = dato("terceros")
        if tercero and not _vacio(tercero) and not _es_plantilla(tercero):
            pieza, _, quien = partir_linea(tercero)
            if pieza and pieza not in actual["terceros"]:
                actual["terceros"].append(pieza)
            if quien and quien not in actual["quienes"]:
                actual["quienes"].append(quien)

        # El cliente y la obra: dato del documento, nunca parte de la falla.
        # La obra es, ademas, el nivel 3 de la taxonomia de ISO 14224.
        cliente = dato("cliente")
        if cliente and not _vacio(cliente) and not actual["cliente"]:
            actual["cliente"] = cliente

        if dato("estado") and not _vacio(dato("estado")):
            actual.setdefault("estado", dato("estado"))

        # «TRABAJOS REALIZADOS» se mapeaba y NO SE LEIA: la columna que lleva
        # la descripcion de lo que se hizo se descartaba despues de haberla
        # localizado. Solo cuenta en los documentos de intervencion.
        hallazgos_aqui = []
        if actual["documento"] in _DOCUMENTOS_DE_INTERVENCION:
            hallazgos_aqui.append(dato("trabajos"))
            # «EQUIPO OPERATIVO» no es un hallazgo; lo que no es eso, si lo
            # es. En el INFORME TECNICO CAMPO esta columna es la unica que
            # describe la falla, y son 114 de esos en el archivo real.
            hallazgos_aqui.append(dato("obs"))

        for h in hallazgos_aqui:
            if not h or _vacio(h):
                continue
            # El mismo separador que una linea de material: la fecha de
            # delante y el nombre del tecnico salen del texto y van a su
            # campo. Lo que queda es la descripcion de lo que pasó.
            texto, _, quien = partir_linea(h)
            if quien and quien not in actual["quienes"]:
                actual["quienes"].append(quien)
            if texto and not _vacio(texto) and not _es_plantilla(texto) \
                    and texto not in actual["hallazgos"]:
                actual["hallazgos"].append(texto)

    if actual is not None:
        informes.append(actual)

    return [i for i in (_armar(b, equipo, modelo) for b in informes) if i]


def _armar(bruto: dict, equipo: str, modelo: str) -> dict | None:
    """Un bloque leido -> el informe que `de_informe` sabe indexar."""
    repuestos = bruto["repuestos"]
    terceros = bruto["terceros"]
    hallazgos = bruto["hallazgos"]
    fechada = bool(bruto.get("fecha") and bruto.get("horometro"))
    # Una orden en la que no se cambio nada no esta vacia: su fecha y su
    # horometro son una lectura, y de las lecturas sale el ritmo de uso y el
    # proximo servicio. Tirarla porque no trae repuestos perdia, en este
    # archivo, dos lecturas de un historial de trece anos.
    if not (repuestos or terceros or hallazgos or fechada):
        return None

    informe: dict = {}
    for campo in ("codigo_ot", "fecha", "horometro"):
        if bruto.get(campo):
            informe[campo] = bruto[campo]
    if equipo:
        informe["codigo_equipo"] = equipo
    if modelo:
        informe["modelo_equipo"] = modelo
    if repuestos:
        informe["repuestos"] = repuestos
    if hallazgos:
        informe["resumen_falla"] = " · ".join(hallazgos)
    # Lo que hizo un tercero es lo que de verdad se hizo: «rectificado de hilo
    # de vastago de cilindro pendular» dice mas de la falla que cualquier
    # columna de este archivo. Va de solucion aplicada, que es lo que es.
    if terceros:
        informe["solucion_aplicada"] = " · ".join(terceros)

    otros: dict[str, str] = {}
    # De que documento salio. Sin esto, un acta de recepcion y un informe
    # tecnico de campo se ven iguales en el indice, y no son lo mismo: el
    # primero dice que la maquina llego, el segundo que algo le pasaba.
    if bruto.get("documento"):
        otros["Documento"] = bruto["documento"]
    if bruto.get("cliente"):
        otros["Cliente / obra"] = bruto["cliente"]
    if bruto.get("estado"):
        otros["Estado"] = bruto["estado"]
    if bruto["quienes"]:
        otros["Tecnicos"] = ", ".join(bruto["quienes"])
    if bruto["fechas_material"]:
        fechas = sorted(set(bruto["fechas_material"]))
        otros["Material despachado"] = f"{len(bruto['fechas_material'])} lineas, " \
                                       f"{fechas[0]} a {fechas[-1]}"
    # El tamano de la intervencion, que es la senal mas clara del archivo: una
    # orden de noventa lineas no fue una reparacion, fue una reconstruccion.
    otros["Alcance"] = (
        f"{len(repuestos)} lineas de material, {len(terceros)} servicios de "
        "terceros" if (repuestos or terceros)
        else "revision sin cambio de material")
    if otros:
        informe["otros_campos"] = otros
    # La causa raiz no se rellena: nadie la escribio, y ponerle una deducida
    # la convertiria en un dato que no es. Se cuenta como sin codificar.
    return informe


def leer(ruta: str | Path, hoja: str | None = None,
         modelo: str = "") -> list[dict]:
    """Lee un historial por bloques de un Excel. Lista vacia si no lo es.

    Se prueban todas las hojas: el export trae una sola, pero un taller que
    exporta tres equipos a tres hojas del mismo libro es lo siguiente que pasa.
    """
    from . import documentos

    hojas = documentos.filas_xlsx(Path(ruta))
    informes: list[dict] = []
    for nombre, filas in hojas.items():
        if hoja and nombre != hoja:
            continue
        if es_por_bloques(filas):
            informes.extend(leer_filas(filas, modelo=modelo))
    return informes
