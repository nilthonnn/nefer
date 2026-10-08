"""RCM: funcion -> falla funcional -> modo de falla -> efecto -> consecuencia.

Cuatro cosas distintas que en los planes de mantenimiento reales aparecen
revueltas en una sola columna llamada «falla». Separarlas es la mitad del
valor del metodo, asi que aqui son cuatro tipos distintos y el sistema no
deja mezclarlos:

    Funcion          lo que la maquina DEBE hacer, con su estandar
                     «Entregar 500 kW continuos a 440 V»
    Falla funcional  como deja de cumplirlo
                     «No entrega la potencia requerida»
    Modo de falla    que lo produce
                     «Radiador obstruido por acumulacion de polvo»
    Efecto           que pasa cuando ocurre
                     «Sube la temperatura, el ECM derate a 60%, se detiene»

Una funcion sin estandar no sirve: «el motor debe funcionar» no se puede
fallar de ninguna manera verificable, y de una funcion asi no sale ningun
modo de falla util. Por eso `estandar` es obligatorio.

----------------------------------------------------------------------------
EVIDENTE U OCULTA VA PRIMERO, Y NO ES UNA CONSECUENCIA MAS

La pregunta «¿el operador se entera solo de que esto fallo?» no es una
categoria al lado de seguridad o produccion: es la PRIMERA bifurcacion del
analisis, y ponerla como una opcion mas de la lista rompe la logica de
decision.

El motivo es concreto. Una falla oculta —una valvula de alivio pegada, un
detector que no detecta, un freno de emergencia que no frena— por si sola no
produce ningun efecto: la maquina sigue trabajando igual. Lo que produce es
que, cuando ocurra la segunda falla, no haya nada que la detenga. El riesgo
no es de la falla: es de la FALLA MULTIPLE. Por eso su tratamiento por
defecto no es ni predictivo ni preventivo sino busqueda de fallas —probar
periodicamente que la proteccion todavia funciona—, y por eso tiene que
decidirse antes que nada.

Aqui `evidente` es un booleano obligatorio del modo de falla, y las clases de
consecuencia describen la rama evidente.
----------------------------------------------------------------------------

Y la regla de la casa, que aqui tambien manda: un modo de falla sin evidencia
no se marca como validado. Lo que sale del historial cita su informe; lo que
sale del manual cita su seccion; lo que puso el ingeniero de confiabilidad de
memoria queda como «propuesto», que es un estado legitimo y visible.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import catalogo as _catalogo
from . import registro as _registro
from .activos import Activo, Ubicacion
from .criticidad import Criticidad, Metodo, SIN_EVALUAR, evaluar

# ------------------------------------------------------------- vocabularios

TIPOS_FUNCION = ("principal", "secundaria")

# Las clases de la rama EVIDENTE. «oculta» no esta aqui a proposito: es el
# booleano `evidente` del modo de falla. Ver el encabezado.
CLASES_CONSECUENCIA = (
    "seguridad",       # puede herir o matar a alguien
    "ambiental",       # infringe una norma ambiental
    "operacional",     # afecta la capacidad de producir (ademas del costo)
    "produccion",      # detiene o reduce produccion
    "economica",       # solo cuesta reparar, no afecta produccion
    "no-significativa",
)

CONSECUENCIAS_GRAVES = frozenset({"seguridad", "ambiental"})

# De donde salio cada afirmacion. Es la regla de evidencia de FixMate
# aplicada al analisis.
FUENTES = ("historial", "manual", "catalogo", "operador", "analisis", "inferencia")

ESTADOS_VALIDACION = ("propuesto", "validado", "descartado")

# Las clases de consecuencia de FixMate son seis; las de JA1011, cuatro. No
# es una discrepancia: la norma agrupa, y aqui se separa «produccion» de
# «operacional» y «economica» de «no significativa» porque el taller las
# distingue al decidir. Lo que NO puede faltar es el mapeo declarado: sin
# el, nadie puede auditar este analisis contra la norma, y una clase propia
# sin equivalencia es una clase que el auditor no sabe donde poner.
CONSECUENCIAS_JA1011 = {
    "seguridad": "seguridad o medio ambiente",
    "ambiental": "seguridad o medio ambiente",
    "operacional": "operacional",
    "produccion": "operacional",
    "economica": "no operacional",
    "no-significativa": "no operacional",
}
# La cuarta categoria de la norma —oculta— no esta aqui a proposito: es el
# booleano `evidente` del modo de falla. Ver el encabezado.
OCULTA_JA1011 = "oculta"

def fecha_valida(valor: str, donde: str) -> str:
    """La fecha de un registro RCM, en ISO 8601. Ver `registro.py`."""
    return _registro.fecha(valor, donde, ErrorRCM)


class ErrorRCM(ValueError):
    """El analisis no se puede construir tal como viene."""


# ------------------------------------------------------------------ piezas

@dataclass(frozen=True)
class Referencia:
    """De donde sale una afirmacion. Sin esto, el analisis es una opinion."""

    fuente: str
    # El informe, la seccion de manual, el codigo del catalogo o el nombre de
    # quien lo afirma. Lo que haga falta para ir a mirarlo.
    referencia: str = ""
    nota: str = ""

    def __post_init__(self):
        if self.fuente not in FUENTES:
            raise ErrorRCM(
                f"fuente «{self.fuente}» desconocida: use {', '.join(FUENTES)}.")

    def a_dict(self) -> dict:
        return {"fuente": self.fuente, "referencia": self.referencia,
                "nota": self.nota}


@dataclass
class Funcion:
    """Lo que el activo debe hacer, con el estandar que lo hace verificable."""

    id: str
    descripcion: str
    estandar: str
    tipo: str = "principal"
    condicion: str = ""   # en que condicion operacional aplica

    def __post_init__(self):
        if not str(self.descripcion).strip():
            raise ErrorRCM("la funcion necesita descripcion.")
        if not str(self.estandar).strip():
            raise ErrorRCM(
                f"«{self.descripcion}»: falta el estandar de desempeño. Una "
                "funcion sin estandar no se puede fallar de forma verificable, "
                "y de ella no sale ningun modo de falla util.")
        if self.tipo not in TIPOS_FUNCION:
            raise ErrorRCM(f"tipo de funcion «{self.tipo}» desconocido.")

    def a_dict(self) -> dict:
        return {"id": self.id, "descripcion": self.descripcion,
                "estandar": self.estandar, "tipo": self.tipo,
                "condicion": self.condicion}


@dataclass
class FallaFuncional:
    """Como el activo deja de cumplir una funcion. Perdida total o parcial."""

    id: str
    funcion_id: str
    descripcion: str

    def __post_init__(self):
        if not str(self.descripcion).strip():
            raise ErrorRCM("la falla funcional necesita descripcion.")

    def a_dict(self) -> dict:
        return {"id": self.id, "funcion_id": self.funcion_id,
                "descripcion": self.descripcion}


@dataclass
class Efecto:
    """Que pasa cuando el modo de falla ocurre. Responde la Q4 de JA1011.

    Todos los campos son opcionales salvo `local`, porque un efecto a medio
    describir sigue siendo util y exigirlo completo haria que se rellene con
    cualquier cosa. Lo que falta se ve en el informe de completitud.
    """

    local: str = ""              # que pasa en el equipo
    observa_operador: str = ""   # que ve, oye o huele quien esta ahi
    parametro: str = ""          # que lectura cambia, y hacia donde
    alarma: str = ""             # que codigo o luz aparece
    componente_afectado: str = ""
    como_detectarlo: str = ""    # el procedimiento que lo confirma

    @property
    def descrito(self) -> bool:
        return bool(str(self.local).strip())

    def a_dict(self) -> dict:
        return {"local": self.local, "observa_operador": self.observa_operador,
                "parametro": self.parametro, "alarma": self.alarma,
                "componente_afectado": self.componente_afectado,
                "como_detectarlo": self.como_detectarlo}


@dataclass(frozen=True)
class Consecuencia:
    """En que forma importa la falla. Responde la Q5 de JA1011."""

    clase: str
    descripcion: str = ""

    def __post_init__(self):
        if self.clase not in CLASES_CONSECUENCIA:
            raise ErrorRCM(
                f"clase de consecuencia «{self.clase}» desconocida. Si queria "
                "decir que la falla es oculta, eso va en `evidente=False` del "
                "modo de falla, no aqui: es la primera bifurcacion del "
                "analisis, no una categoria mas.")

    @property
    def grave(self) -> bool:
        return self.clase in CONSECUENCIAS_GRAVES

    def a_dict(self) -> dict:
        return {"clase": self.clase, "descripcion": self.descripcion}


@dataclass
class ModoFalla:
    """Lo que produce la falla funcional. El nivel donde se decide la tarea.

    `codigo_catalogo` es la llave hacia el catalogo de fallas que FixMate ya
    tiene —con la estructura de ISO 14224 y codigos propios—, y es lo que cose RCM con el motor de diagnostico, con el historial
    y —mas adelante— con las anomalias TPM. Cuando esta puesto, el modo
    hereda sistema, modo observable, mecanismo y causa de ahi en vez de
    repetirlos escritos distinto.
    """

    id: str
    falla_funcional_id: str
    descripcion: str
    ubicacion: Ubicacion = field(default_factory=Ubicacion)
    codigo_catalogo: str = ""
    causa: str = ""
    mecanismo: str = ""
    # La primera bifurcacion de RCM. Obligatoria: ver el encabezado.
    evidente: bool = True
    efecto: Efecto = field(default_factory=Efecto)
    consecuencias: tuple[Consecuencia, ...] = ()
    criticidad: Criticidad = SIN_EVALUAR
    evidencia: tuple[Referencia, ...] = ()
    estado: str = "propuesto"
    # Cuantas veces aparecio en el historial. Lo llena `prediccion`, no se
    # escribe a mano: un numero escrito a mano deja de ser una medicion.
    frecuencia_historica: int | None = None

    def __post_init__(self):
        if not str(self.descripcion).strip():
            raise ErrorRCM("el modo de falla necesita descripcion.")
        if self.estado not in ESTADOS_VALIDACION:
            raise ErrorRCM(f"estado «{self.estado}» desconocido.")
        if self.estado == "validado" and not self.evidencia:
            raise ErrorRCM(
                f"«{self.descripcion}»: no se puede marcar validado sin "
                "evidencia. Un modo de falla validado de memoria es una "
                "opinion con sello.")

    @property
    def grave(self) -> bool:
        """Si alguna consecuencia es de seguridad o ambiental."""
        return any(c.grave for c in self.consecuencias)

    @property
    def clases(self) -> tuple[str, ...]:
        return tuple(c.clase for c in self.consecuencias)

    def desde_catalogo(self, cat: _catalogo.Catalogo | None = None) -> "ModoFalla":
        """Completa causa, mecanismo y sistema desde el catalogo, sin pisar.

        Lo que el analista ya escribio gana: esto rellena huecos, no corrige.
        """
        if not self.codigo_catalogo:
            return self
        entrada = (cat or _catalogo.Catalogo()).get(self.codigo_catalogo)
        if entrada is None:
            raise ErrorRCM(
                f"el codigo «{self.codigo_catalogo}» no esta en el catalogo. "
                "Agreguelo con `catalogo.cargar()` antes de referenciarlo.")
        self.causa = self.causa or entrada.causa
        self.mecanismo = self.mecanismo or entrada.mecanismo
        if not self.ubicacion.sistema:
            self.ubicacion = Ubicacion(entrada.sistema, self.ubicacion.subsistema,
                                       self.ubicacion.componente)
        return self

    def evaluar_criticidad(self, metodo: Metodo | None, valores: dict) -> "ModoFalla":
        self.criticidad = evaluar(metodo, valores)
        return self

    def a_dict(self) -> dict:
        return {
            "id": self.id, "falla_funcional_id": self.falla_funcional_id,
            "descripcion": self.descripcion, "ubicacion": self.ubicacion.a_dict(),
            "codigo_catalogo": self.codigo_catalogo, "causa": self.causa,
            "mecanismo": self.mecanismo, "evidente": self.evidente,
            "efecto": self.efecto.a_dict(),
            "consecuencias": [c.a_dict() for c in self.consecuencias],
            "criticidad": self.criticidad.a_dict(),
            "evidencia": [e.a_dict() for e in self.evidencia],
            "estado": self.estado,
            "frecuencia_historica": self.frecuencia_historica,
        }


# ----------------------------------------------------------------- analisis

@dataclass
class Analisis:
    """Un analisis RCM: un activo, un contexto, y el arbol completo debajo.

    Esta amarrado al contexto operacional y no al activo solo. Ver el
    encabezado de `activos.py`: la misma bomba en dos contextos son dos
    analisis, y copiar uno sobre el otro sin reconfirmarlo es el atajo que
    llena los planes de tareas que no aplican.
    """

    activo: Activo
    contexto: str = ""
    funciones: list[Funcion] = field(default_factory=list)
    fallas: list[FallaFuncional] = field(default_factory=list)
    modos: list[ModoFalla] = field(default_factory=list)
    # Quien lo hizo y cuando. JA1011 pide que el analisis sea revisable.
    facilitador: str = ""
    participantes: tuple[str, ...] = ()
    fecha: str = ""
    metodo_criticidad: Metodo | None = None
    # --- identificacion del documento -------------------------------------
    # Un analisis sin revision ni aprobacion es un borrador que alguien va a
    # usar como si fuera definitivo. JA1011 pide que el analisis sea
    # revisable, y revisable quiere decir saber QUE version se esta mirando,
    # QUIEN la aprobo y CUANDO toca volver a mirarla —el contexto operacional
    # cambia, y con el cambian las consecuencias—.
    #
    # Van opcionales a proposito: exigirlas rompería los analisis que ya
    # existen, y un campo obligatorio que la gente rellena con «-» no
    # registra nada. Lo que hace el sistema es DECIRLO: ver `calidad()`.
    revision: str = ""
    aprobado_por: str = ""
    proxima_revision: str = ""

    def __post_init__(self):
        self.contexto = self.contexto or self.activo.contexto
        self.fecha = fecha_valida(self.fecha, "el analisis")
        self.proxima_revision = fecha_valida(
            self.proxima_revision, "la proxima revision del analisis")

    # -- altas, con las llaves cosidas para que no queden huerfanos

    def agregar_funcion(self, descripcion: str, estandar: str,
                        tipo: str = "principal", condicion: str = "") -> Funcion:
        f = Funcion(id=f"F{len(self.funciones) + 1}", descripcion=descripcion,
                    estandar=estandar, tipo=tipo, condicion=condicion)
        self.funciones.append(f)
        return f

    def agregar_falla(self, funcion_id: str, descripcion: str) -> FallaFuncional:
        if not any(f.id == funcion_id for f in self.funciones):
            raise ErrorRCM(
                f"no existe la funcion {funcion_id}. Una falla funcional "
                "huerfana no se puede leer: dice como falla algo que nadie "
                "declaro que la maquina deba hacer.")
        ff = FallaFuncional(id=f"{funcion_id}.{len(self.fallas_de(funcion_id)) + 1}",
                            funcion_id=funcion_id, descripcion=descripcion)
        self.fallas.append(ff)
        return ff

    def agregar_modo(self, falla_id: str, descripcion: str, **kw) -> ModoFalla:
        if not any(x.id == falla_id for x in self.fallas):
            raise ErrorRCM(f"no existe la falla funcional {falla_id}.")
        m = ModoFalla(id=f"{falla_id}.{len(self.modos_de(falla_id)) + 1}",
                      falla_funcional_id=falla_id, descripcion=descripcion, **kw)
        if m.codigo_catalogo:
            m.desde_catalogo()
        self.modos.append(m)
        return m

    # -- consultas

    def fallas_de(self, funcion_id: str) -> list[FallaFuncional]:
        return [f for f in self.fallas if f.funcion_id == funcion_id]

    def modos_de(self, falla_id: str) -> list[ModoFalla]:
        return [m for m in self.modos if m.falla_funcional_id == falla_id]

    def modo(self, modo_id: str) -> ModoFalla | None:
        return next((m for m in self.modos if m.id == modo_id), None)

    def modos_graves(self) -> list[ModoFalla]:
        return [m for m in self.modos if m.grave]

    def modos_ocultos(self) -> list[ModoFalla]:
        return [m for m in self.modos if not m.evidente]

    def a_dict(self) -> dict:
        return {
            "activo": self.activo.a_dict(), "contexto": self.contexto,
            "facilitador": self.facilitador,
            "participantes": list(self.participantes), "fecha": self.fecha,
            "revision": self.revision, "aprobado_por": self.aprobado_por,
            "proxima_revision": self.proxima_revision,
            "metodo_criticidad": (self.metodo_criticidad.a_dict()
                                  if self.metodo_criticidad else None),
            "funciones": [f.a_dict() for f in self.funciones],
            "fallas": [f.a_dict() for f in self.fallas],
            "modos": [m.a_dict() for m in self.modos],
        }


# -------------------------------------------- las siete preguntas de JA1011

@dataclass(frozen=True)
class Pregunta:
    numero: int
    clave: str
    texto: str
    # Que parte del modelo la responde. Sirve para explicar que falta.
    responde: str


PREGUNTAS = (
    Pregunta(1, "funciones",
             "¿Cuales son las funciones y los estandares de desempeño del "
             "activo en su contexto operacional actual?",
             "cada funcion declarada, con su estandar"),
    Pregunta(2, "fallas_funcionales",
             "¿De que maneras puede fallar en el cumplimiento de sus funciones?",
             "al menos una falla funcional por funcion"),
    Pregunta(3, "modos",
             "¿Que causa cada falla funcional?",
             "al menos un modo de falla por falla funcional"),
    Pregunta(4, "efectos",
             "¿Que sucede cuando ocurre cada modo de falla?",
             "el efecto descrito en cada modo de falla"),
    Pregunta(5, "consecuencias",
             "¿En que forma importa cada falla?",
             "evidente u oculta, y al menos una consecuencia clasificada"),
    Pregunta(6, "tareas",
             "¿Que debe hacerse para predecir o prevenir cada falla?",
             "una decision de estrategia registrada por modo de falla"),
    Pregunta(7, "acciones_por_defecto",
             "¿Que debe hacerse si no se encuentra una tarea proactiva "
             "adecuada?",
             "la accion por defecto registrada donde no hubo tarea proactiva"),
)

# Sin estas, lo que hay no es un analisis RCM incompleto: es otra cosa. Son
# las que definen la cadena funcion -> falla -> modo -> consecuencia.
CRITICAS = frozenset({"funciones", "fallas_funcionales", "modos", "consecuencias"})


@dataclass(frozen=True)
class Respuesta:
    """Si una de las siete quedo contestada, y que falta si no."""

    pregunta: Pregunta
    contestada: bool
    faltantes: tuple[str, ...] = ()

    def a_dict(self) -> dict:
        return {"numero": self.pregunta.numero, "clave": self.pregunta.clave,
                "texto": self.pregunta.texto, "contestada": self.contestada,
                "faltantes": list(self.faltantes)}


@dataclass(frozen=True)
class Completitud:
    """El estado del analisis frente a JA1011.

    `completo` es True solo con las siete contestadas. No hay porcentaje que
    redondee hacia arriba ni «practicamente completo»: el criterio de JA1011
    es binario a proposito, porque la norma nacio justamente porque se vendian
    metodologias incompletas con ese nombre.
    """

    respuestas: tuple[Respuesta, ...]
    completo: bool
    # True cuando falta alguna de las cuatro que sostienen la cadena.
    rompe_cadena: bool

    @property
    def contestadas(self) -> int:
        return sum(1 for r in self.respuestas if r.contestada)

    @property
    def pendientes(self) -> tuple[Respuesta, ...]:
        return tuple(r for r in self.respuestas if not r.contestada)

    def resumen(self) -> str:
        if self.completo:
            return "Las siete preguntas de JA1011 estan contestadas."
        falta = ", ".join(f"Q{r.pregunta.numero}" for r in self.pendientes)
        aviso = (" Falta alguna de las que sostienen la cadena funcion -> falla "
                 "-> modo -> consecuencia: esto todavia no es un analisis RCM."
                 if self.rompe_cadena else
                 " El esqueleto esta; falta decidir tareas.")
        return f"{self.contestadas}/7 contestadas; pendientes: {falta}.{aviso}"

    def a_dict(self) -> dict:
        return {"completo": self.completo, "contestadas": self.contestadas,
                "rompe_cadena": self.rompe_cadena,
                "respuestas": [r.a_dict() for r in self.respuestas]}


# ------------------------------------------- la calidad del documento

@dataclass(frozen=True)
class Hallazgo:
    """Algo que una auditoria anotaria del analisis como documento."""

    clave: str
    # «no conformidad» cuando falta algo que hace el analisis no auditable;
    # «observacion» cuando es una medida o un riesgo, no un incumplimiento.
    gravedad: str
    detalle: str
    ids: tuple[str, ...] = ()

    def a_dict(self) -> dict:
        return {"clave": self.clave, "gravedad": self.gravedad,
                "detalle": self.detalle, "ids": list(self.ids)}


@dataclass(frozen=True)
class Calidad:
    """El estado del analisis COMO REGISTRO, que no es lo mismo que su
    completitud frente a JA1011.

    Las siete preguntas dicen si el analisis esta terminado. Esto dice si se
    puede auditar dentro de dos años: quien lo aprobo, que version es, cuando
    toca revisarlo, y si los codigos de adentro son inequivocos. Un analisis
    puede tener las siete contestadas y no ser un registro valido.
    """

    hallazgos: tuple[Hallazgo, ...]
    modos: int
    codificados: int

    @property
    def conforme(self) -> bool:
        return not any(h.gravedad == "no conformidad" for h in self.hallazgos)

    @property
    def no_conformidades(self) -> tuple[Hallazgo, ...]:
        return tuple(h for h in self.hallazgos if h.gravedad == "no conformidad")

    def resumen(self) -> str:
        if self.conforme:
            return "El analisis esta identificado y es auditable."
        cuantas = len(self.no_conformidades)
        return (f"{cuantas} no conformidad(es) de registro: el analisis esta "
                "contestado pero no queda claro quien responde por el.")

    def a_dict(self) -> dict:
        return {"conforme": self.conforme, "modos": self.modos,
                "codificados": self.codificados,
                "hallazgos": [h.a_dict() for h in self.hallazgos]}


def calidad(analisis: Analisis, hoy: str = "") -> Calidad:
    """Audita el analisis como documento, no como metodo.

    `hoy` en ISO 8601 activa la comprobacion de vigencia; sin el no se mira,
    porque una funcion que cambia de respuesta segun el dia no se puede
    probar ni comparar entre dos lados.
    """
    hallazgos: list[Hallazgo] = []

    # -- identificacion. Sin esto el documento no tiene dueño ni version.
    faltan = [nombre for nombre, valor in (
        ("numero de revision", analisis.revision),
        ("quien lo aprobo", analisis.aprobado_por),
        ("fecha", analisis.fecha),
    ) if not str(valor).strip()]
    if faltan:
        hallazgos.append(Hallazgo(
            "identificacion", "no conformidad",
            "el analisis no declara " + ", ".join(faltan) + ". Un analisis "
            "sin version ni aprobacion es un borrador que alguien va a usar "
            "como si fuera definitivo."))

    # -- el equipo. RCM no lo hace una persona: la norma pide el contexto
    # operacional, y ese lo tiene quien opera la maquina, no quien la
    # mantiene.
    if not analisis.participantes:
        hallazgos.append(Hallazgo(
            "participantes", "no conformidad",
            "el analisis no declara participantes. Un analisis RCM hecho por "
            "una sola persona no tiene el contexto operacional de quien opera."))

    # -- vigencia. El contexto operacional cambia, y con el las consecuencias.
    if not analisis.proxima_revision:
        hallazgos.append(Hallazgo(
            "vigencia", "observacion",
            "no se declara cuando toca revisarlo. El contexto operacional "
            "cambia, y una consecuencia evaluada en otro contexto ya no vale."))
    elif hoy and analisis.proxima_revision < hoy:
        hallazgos.append(Hallazgo(
            "vigencia", "no conformidad",
            f"la revision vencio el {analisis.proxima_revision}."))

    # -- ambiguedad de codigo. Es la que impide enganchar una anomalia de
    # campo: `anomalia.enlazar()` se niega a elegir entre dos modos con el
    # mismo codigo, y hace bien. Pero si nadie lo dice al revisar, el
    # analisis se da por bueno y el enganche falla en silencio meses despues.
    porcodigo: dict[str, list[str]] = {}
    for m in analisis.modos:
        if m.codigo_catalogo:
            porcodigo.setdefault(m.codigo_catalogo, []).append(m.id)
    repetidos = {c: ids for c, ids in porcodigo.items() if len(ids) > 1}
    for codigo in sorted(repetidos):
        hallazgos.append(Hallazgo(
            "codigo_repetido", "no conformidad",
            f"los modos {', '.join(repetidos[codigo])} declaran el mismo "
            f"codigo «{codigo}». Una anomalia de campo con ese codigo no se "
            "puede enganchar: la ambiguedad se resuelve aqui, no al recibirla.",
            tuple(repetidos[codigo])))

    # -- cobertura. No es un defecto: es la medida de cuanto alcanza el
    # catalogo, y lo que dice si hay que agrandarlo.
    codificados = sum(1 for m in analisis.modos if m.codigo_catalogo)
    sin_codigo = [m.id for m in analisis.modos if not m.codigo_catalogo]
    if sin_codigo:
        hallazgos.append(Hallazgo(
            "sin_codificar", "observacion",
            f"{len(sin_codigo)} de {len(analisis.modos)} modos no tienen "
            "codigo de catalogo: no se agregan con los de la flota ni se "
            "enganchan con la ronda.", tuple(sin_codigo)))

    return Calidad(tuple(hallazgos), len(analisis.modos), codificados)


def completitud(analisis: Analisis, decisiones: dict | None = None) -> Completitud:
    """Que preguntas de JA1011 quedaron contestadas, y que falta en cada una.

    `decisiones` es el mapa `modo_id -> Dictamen` de `decision.py`. Va como
    argumento y no dentro del analisis porque la decision se puede rehacer
    con otro criterio sin tocar el analisis de abajo, que es lo que permite
    revisar un plan sin repetir el taller entero.
    """
    decisiones = decisiones or {}
    respuestas: list[Respuesta] = []

    # Q1 - funciones con estandar. El constructor ya exige el estandar, asi
    # que lo unico que puede faltar aqui es que no haya ninguna funcion.
    respuestas.append(Respuesta(
        PREGUNTAS[0], bool(analisis.funciones),
        () if analisis.funciones else ("no hay ninguna funcion declarada",)))

    # Q2 - cada funcion con al menos una falla funcional.
    sin_falla = [f.id for f in analisis.funciones if not analisis.fallas_de(f.id)]
    respuestas.append(Respuesta(
        PREGUNTAS[1], bool(analisis.fallas) and not sin_falla,
        tuple(f"la funcion {i} no tiene fallas funcionales" for i in sin_falla)
        or (() if analisis.fallas else ("no hay fallas funcionales",))))

    # Q3 - cada falla funcional con al menos un modo.
    sin_modo = [f.id for f in analisis.fallas if not analisis.modos_de(f.id)]
    respuestas.append(Respuesta(
        PREGUNTAS[2], bool(analisis.modos) and not sin_modo,
        tuple(f"la falla {i} no tiene modos de falla" for i in sin_modo)
        or (() if analisis.modos else ("no hay modos de falla",))))

    # Q4 - efecto descrito en cada modo.
    sin_efecto = [m.id for m in analisis.modos if not m.efecto.descrito]
    respuestas.append(Respuesta(
        PREGUNTAS[3], bool(analisis.modos) and not sin_efecto,
        tuple(f"el modo {i} no tiene efecto descrito" for i in sin_efecto)
        or (() if analisis.modos else ("no hay modos de falla",))))

    # Q5 - consecuencia clasificada en cada modo.
    sin_consec = [m.id for m in analisis.modos if not m.consecuencias]
    respuestas.append(Respuesta(
        PREGUNTAS[4], bool(analisis.modos) and not sin_consec,
        tuple(f"el modo {i} no tiene consecuencia clasificada" for i in sin_consec)
        or (() if analisis.modos else ("no hay modos de falla",))))

    # Q6 - una decision registrada por modo.
    sin_decision = [m.id for m in analisis.modos if m.id not in decisiones]
    respuestas.append(Respuesta(
        PREGUNTAS[5], bool(analisis.modos) and not sin_decision,
        tuple(f"el modo {i} no tiene decision de estrategia" for i in sin_decision)
        or (() if analisis.modos else ("no hay modos de falla",))))

    # Q7 - donde la decision fue una accion por defecto, tiene que estar
    # registrada como tal. Un modo con tarea proactiva no debe nada aqui.
    faltan_defecto = tuple(
        f"el modo {mid}: la decision es una accion por defecto y no quedo justificada"
        for mid, d in decisiones.items()
        if getattr(d, "por_defecto", False) and not getattr(d, "motivo", ""))
    contestada_q7 = bool(decisiones) and not sin_decision and not faltan_defecto
    respuestas.append(Respuesta(
        PREGUNTAS[6], contestada_q7,
        faltan_defecto or (() if decisiones and not sin_decision
                           else ("faltan decisiones por registrar",))))

    rompe = any(not r.contestada and r.pregunta.clave in CRITICAS
                for r in respuestas)
    return Completitud(respuestas=tuple(respuestas),
                       completo=all(r.contestada for r in respuestas),
                       rompe_cadena=rompe)
