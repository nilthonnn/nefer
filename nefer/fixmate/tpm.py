"""TPM · mantenimiento autonomo: la pauta que hace el operador.

Esto cubre el primer pilar del TPM —Jishu Hozen— y nada mas. Decirlo asi de
temprano importa: TPM tiene ocho pilares, y llamar «TPM implementado» a una
lista de verificacion es exactamente la clase de afirmacion que vuelve
inservible la palabra.

La pauta autonoma es la herramienta de mantenimiento con mejor relacion
costo/beneficio que existe, y tambien la que se degrada mas rapido, siempre
igual: deja de ejecutarse y empieza a firmarse. A los tres meses la planilla
esta impecable y la maquina igual de sucia. Todo lo de aqui esta escrito
contra esa degradacion concreta.

----------------------------------------------------------------------------
CINCO CLASES, NO SIETE

El encargo pedia siete categorias: limpiar, inspeccionar, lubricar, ajustar,
verificar, detectar anomalias y registrar anomalia. Las dos ultimas no son
clases de punto: son lo que PASA cuando un punto sale NOK. Un punto cuya
actividad es «detectar anomalias» no tiene criterio de aceptacion posible
—¿cuando esta OK detectar anomalias?— y en campo se marca OK siempre.

Las cinco que quedan tienen todas un criterio verificable, que es lo que
hace que la pauta mida algo.
----------------------------------------------------------------------------

TRES RESULTADOS, NO DOS. `sin_acceso` existe porque la alternativa real es
que el operador marque OK en un punto que no pudo ver —guarda cerrada,
maquina en marcha, andamio desarmado— y entonces la ronda completa deja de
valer. Un «no pude» registrado es un dato; un OK falso es una mentira que se
arrastra meses. Una ejecucion con un punto sin ver NO esta completa.

EL TIEMPO SE MIDE, NO SE DECLARA. Cada punto guarda los segundos que llevo.
Una pauta de treinta segundos despachada en cuatro no se ejecuto: se firmo.
Eso se detecta y se dice, al supervisor y no al operador a mitad de la
maquina.

Y la llave: cada punto puede declarar `codigo_catalogo`. Ahi es donde la
ronda del operador se cose con el analisis RCM y con el historial de fallas,
sin que nadie tenga que escribir dos veces «radiador obstruido».
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from . import catalogo as _catalogo

# Las cinco que tienen criterio de aceptacion verificable. Ver el encabezado.
CLASES = {
    "limpiar": "La mugre esconde la fuga y la grieta: limpiar es inspeccionar",
    "inspeccionar": "Mirar, oir o tocar en un punto fijo",
    "lubricar": "Nivel o engrase en el punto marcado",
    "ajustar": "Apriete o regulacion dentro del alcance del operador",
    "verificar": "Comprobar que una funcion responde",
}

FRECUENCIAS = ("por_turno", "diaria", "semanal", "quincenal", "mensual", "por_horas")

RESULTADOS = {
    "ok": "Cumple el criterio",
    "nok": "No cumple: hay anomalia",
    "sin_acceso": "No se pudo ver",
}

# Por debajo de esta fraccion del presupuesto declarado, la ejecucion es
# sospechosa de firma. CRITERIO CONFIGURABLE DE PLANTA, no normativo: 0,4
# sale de que mirar un punto y decidir cuesta al menos un par de segundos, y
# de que conviene errar por no acusar.
FRACCION_SOSPECHOSA = 0.4


class ErrorTPM(ValueError):
    """La pauta o su ejecucion no se pueden registrar tal como vienen."""


@dataclass(frozen=True)
class PuntoChecklist:
    """Un punto de la pauta: un sitio fisico con un criterio observable.

    `punto` es un SITIO, no un sistema. «Revisar lubricacion» no es un punto;
    «visor de nivel del reductor» si, porque el operador sabe donde pararse.

    `criterio` tiene que decidirse sin instrumento. Si para decidir hace
    falta un medidor, el punto pertenece a la ruta predictiva y no a la ronda
    autonoma, y mezclarlos hace que la ronda no se cumpla.

    `alcance_operador` se decide AL ESCRIBIR LA PAUTA, en frio, por quien
    conoce el bloqueo, la herramienta y el repuesto. Preguntarselo al
    operador en campo, con la maquina parada, garantiza la respuesta comoda.
    """

    id: str
    clase: str
    punto: str
    criterio: str
    alcance_operador: bool = True
    # Presupuesto en segundos. Opcional: sin el no se puede juzgar si la
    # ejecucion fue demasiado rapida, y eso se declara en vez de suponerse.
    segundos: int = 0
    # La llave hacia el catalogo ISO 14224 y, por el, hacia RCM.
    codigo_catalogo: str = ""
    # El modo de falla concreto del analisis, cuando se sabe cual es.
    modo_falla_id: str = ""

    def __post_init__(self):
        if self.clase not in CLASES:
            raise ErrorTPM(
                f"clase «{self.clase}» desconocida: use {', '.join(CLASES)}. "
                "«Detectar anomalias» no es una clase de punto: es lo que pasa "
                "cuando un punto sale NOK.")
        if not str(self.punto).strip():
            raise ErrorTPM("el punto necesita un sitio fisico donde pararse.")
        if not str(self.criterio).strip():
            raise ErrorTPM(
                f"«{self.punto}»: falta el criterio de aceptacion. Sin criterio, "
                "cada operador juzga otra cosa y la pauta no mide nada.")
        if self.codigo_catalogo and self.codigo_catalogo not in _catalogo.Catalogo():
            raise ErrorTPM(
                f"el codigo «{self.codigo_catalogo}» no esta en el catalogo.")

    def a_dict(self) -> dict:
        return {"id": self.id, "clase": self.clase, "punto": self.punto,
                "criterio": self.criterio, "alcance_operador": self.alcance_operador,
                "segundos": self.segundos, "codigo_catalogo": self.codigo_catalogo,
                "modo_falla_id": self.modo_falla_id}


@dataclass
class Checklist:
    """La pauta de un activo. Es la plantilla, no la ejecucion."""

    id: str
    activo_codigo: str
    nombre: str
    frecuencia: str = "diaria"
    puntos: list[PuntoChecklist] = field(default_factory=list)
    # De donde sale la pauta: OEM, RCM, experiencia del taller.
    origen: str = ""

    def __post_init__(self):
        if self.frecuencia not in FRECUENCIAS:
            raise ErrorTPM(
                f"frecuencia «{self.frecuencia}» desconocida: "
                f"use {', '.join(FRECUENCIAS)}.")

    def agregar(self, clase: str, punto: str, criterio: str, **kw) -> PuntoChecklist:
        p = PuntoChecklist(id=f"{self.id}.{len(self.puntos) + 1}", clase=clase,
                           punto=punto, criterio=criterio, **kw)
        self.puntos.append(p)
        return p

    def punto(self, punto_id: str) -> PuntoChecklist | None:
        return next((p for p in self.puntos if p.id == punto_id), None)

    @property
    def presupuesto_seg(self) -> int:
        return sum(max(0, p.segundos) for p in self.puntos)

    def a_dict(self) -> dict:
        return {"id": self.id, "activo_codigo": self.activo_codigo,
                "nombre": self.nombre, "frecuencia": self.frecuencia,
                "origen": self.origen, "presupuesto_seg": self.presupuesto_seg,
                "puntos": [p.a_dict() for p in self.puntos]}


@dataclass(frozen=True)
class ItemEjecutado:
    """Lo que se respondio en un punto, con el tiempo que llevo."""

    punto_id: str
    resultado: str
    observacion: str = ""
    segundos: int = 0

    def __post_init__(self):
        if self.resultado not in RESULTADOS:
            raise ErrorTPM(
                f"resultado «{self.resultado}» desconocido: "
                f"use {', '.join(RESULTADOS)}.")

    def a_dict(self) -> dict:
        return {"punto_id": self.punto_id, "resultado": self.resultado,
                "observacion": self.observacion, "segundos": self.segundos}


@dataclass
class Ejecucion:
    """Una pasada de la pauta por la maquina."""

    id: str
    checklist_id: str
    activo_codigo: str
    operador: str
    fecha: str = ""
    items: list[ItemEjecutado] = field(default_factory=list)
    # Ids de las anomalias que esta ronda genero. Ver `anomalia.py`.
    anomalias: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.fecha = self.fecha or _dt.date.today().isoformat()
        if not str(self.operador).strip():
            raise ErrorTPM(
                "la ejecucion necesita responsable. Una ronda sin responsable "
                "no se puede discutir despues.")

    def registrar(self, punto_id: str, resultado: str, observacion: str = "",
                  segundos: int = 0) -> ItemEjecutado:
        """Anota un punto. Re-anotar el mismo REEMPLAZA en su sitio.

        El orden de la pauta es el recorrido fisico por la maquina: si
        corregir el segundo punto lo manda al final, el proximo operador
        camina de mas.
        """
        item = ItemEjecutado(punto_id, resultado, observacion,
                             max(0, int(segundos)))
        for i, x in enumerate(self.items):
            if x.punto_id == punto_id:
                self.items[i] = item
                return item
        self.items.append(item)
        return item

    def a_dict(self) -> dict:
        return {"id": self.id, "checklist_id": self.checklist_id,
                "activo_codigo": self.activo_codigo, "operador": self.operador,
                "fecha": self.fecha, "anomalias": list(self.anomalias),
                "items": [i.a_dict() for i in self.items]}


@dataclass(frozen=True)
class EstadoEjecucion:
    """Como quedo una ronda. `completa` es lo que mide el cumplimiento."""

    total: int
    respondidos: int
    ok: int
    nok: int
    sin_acceso: int
    pendientes: tuple[str, ...]
    segundos: int
    presupuesto_seg: int
    completa: bool
    sospechosa_de_firma: bool

    def a_dict(self) -> dict:
        return {"total": self.total, "respondidos": self.respondidos,
                "ok": self.ok, "nok": self.nok, "sin_acceso": self.sin_acceso,
                "pendientes": list(self.pendientes), "segundos": self.segundos,
                "presupuesto_seg": self.presupuesto_seg,
                "completa": self.completa,
                "sospechosa_de_firma": self.sospechosa_de_firma}


def estado(ejecucion: Ejecucion, checklist: Checklist) -> EstadoEjecucion:
    """Lo que hay que saber de una ronda para contarla o descartarla."""
    respondidos = {i.punto_id for i in ejecucion.items}
    cuenta = {r: sum(1 for i in ejecucion.items if i.resultado == r)
              for r in RESULTADOS}
    segundos = sum(i.segundos for i in ejecucion.items)
    presupuesto = checklist.presupuesto_seg
    todos = len(ejecucion.items) == len(checklist.puntos)

    return EstadoEjecucion(
        total=len(checklist.puntos),
        respondidos=len(ejecucion.items),
        ok=cuenta["ok"], nok=cuenta["nok"], sin_acceso=cuenta["sin_acceso"],
        pendientes=tuple(p.id for p in checklist.puntos
                         if p.id not in respondidos),
        segundos=segundos,
        presupuesto_seg=presupuesto,
        # Un punto sin ver no es una ronda completa con una nota: es una
        # ronda incompleta.
        completa=todos and cuenta["sin_acceso"] == 0,
        # Solo tiene sentido juzgar la velocidad de una ronda terminada, y
        # solo si la pauta declaro presupuesto.
        sospechosa_de_firma=(todos and presupuesto > 0
                             and segundos < presupuesto * FRACCION_SOSPECHOSA),
    )


# ------------------------------------------------- cumplimiento del pilar 1

@dataclass(frozen=True)
class Cumplimiento:
    """El indicador del pilar 1. Cuenta rondas COMPLETAS, no rondas firmadas."""

    ejecuciones: int
    completas: int
    sospechosas: int
    # Fraccion de rondas completas. `None` sin ejecuciones: cero se leeria
    # como «lo hicieron mal», y lo que pasa es que no hay dato.
    cumplimiento: float | None
    # Puntos que en NINGUNA ronda se pudieron ver. Es el hallazgo mas valioso
    # y el que nadie mira: un punto inaccesible no es descuido del operador,
    # es un defecto de la maquina o de la pauta.
    nunca_vistos: tuple[str, ...]
    por_clase: dict[str, int] = field(default_factory=dict)

    def a_dict(self) -> dict:
        return {"ejecuciones": self.ejecuciones, "completas": self.completas,
                "sospechosas": self.sospechosas, "cumplimiento": self.cumplimiento,
                "nunca_vistos": list(self.nunca_vistos),
                "por_clase": dict(self.por_clase)}


def cumplimiento(ejecuciones, checklist: Checklist) -> Cumplimiento:
    """Como va el mantenimiento autonomo de este activo."""
    ejecuciones = list(ejecuciones)
    estados = [estado(e, checklist) for e in ejecuciones]

    vistos = {i.punto_id for e in ejecuciones for i in e.items
              if i.resultado != "sin_acceso"}
    completas = sum(1 for s in estados if s.completa)

    # Cuantas veces se ejecuto cada clase con resultado distinto de sin ver.
    # Es lo que responde «¿se esta lubricando de verdad?» por separado.
    por_clase = {c: 0 for c in CLASES}
    for e in ejecuciones:
        for i in e.items:
            p = checklist.punto(i.punto_id)
            if p and i.resultado != "sin_acceso":
                por_clase[p.clase] += 1

    return Cumplimiento(
        ejecuciones=len(ejecuciones),
        completas=completas,
        sospechosas=sum(1 for s in estados if s.sospechosa_de_firma),
        cumplimiento=(completas / len(ejecuciones)) if ejecuciones else None,
        nunca_vistos=tuple(p.id for p in checklist.puntos if p.id not in vistos),
        por_clase=por_clase,
    )
