"""De modo de falla a estrategia de mantenimiento. Explicito y auditable.

Un plan que dice «hacer mantenimiento preventivo» sin decir por que es un
plan que nadie puede discutir, y por lo tanto nadie puede mejorar. Aqui cada
decision sale de una secuencia de preguntas con respuesta registrada, y el
dictamen viaja con el camino que lo produjo.

EL ORDEN DE LAS PREGUNTAS NO ES ARBITRARIO. Es el que hace que la decision
sea defendible:

  1. ¿La falla es EVIDENTE para quien opera?
     Si no lo es, el riesgo no es de esta falla sino de la falla multiple
     —la proteccion no responde el dia que hace falta—, y el tratamiento por
     defecto es busqueda de fallas, no predictivo ni preventivo.

  2. ¿Hay consecuencia de SEGURIDAD o ambiental?
     Cambia el criterio de aceptacion de la tarea. Con consecuencia grave la
     tarea tiene que reducir el riesgo a un nivel tolerable; sin ella, basta
     con que cueste menos que la falla.

  3. ¿Se puede DETECTAR la degradacion con aviso suficiente? -> CBM
     Primera en el orden de preferencia porque aprovecha la vida util
     completa y no interviene una maquina que esta sana.

  4. ¿Hay INTERVALO DE EDAD identificable? -> restauracion o descarte
     Esta pregunta es la que mas planes OEM no pasan, y conviene saber por
     que: el estudio de Nowlan y Heap para United Airlines (1978) encontro
     que el 89 % de los items no tiene zona de desgaste identificable
     —patrones D, E y F—, de modo que un limite de edad no previene nada en
     la gran mayoria de los casos. Solo el 11 % lo justifica.

  5. ¿La tarea es VIABLE y COSTO-EFECTIVA?

Y la guarda que no se negocia, igual que en el resto de FixMate:

    CON CONSECUENCIA DE SEGURIDAD O AMBIENTAL, «OPERAR HASTA LA FALLA» NO ES
    UNA SALIDA LEGAL.

Si ninguna tarea proactiva sirve y la falla puede herir a alguien, la salida
es REDISEÑO, y en RCM el rediseño ahi es obligatorio, no una sugerencia. Un
arbol de decision que permita cerrar un modo de falla de seguridad con
«operar hasta la falla» es peor que no tener arbol, porque firma la omision.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .rcm import Analisis, ModoFalla

# Las seis estrategias. Los nombres en espanol son los que ve el tecnico; la
# clave es la que viaja en los datos y se exporta a la matriz FMECA.
ESTRATEGIAS = {
    "cbm": "Mantenimiento segun condicion",
    "restauracion": "Restauracion programada",
    "descarte": "Descarte programado",
    "busqueda_fallas": "Busqueda de fallas",
    "operar_hasta_falla": "Operar hasta la falla",
    "rediseno": "Rediseño o cambio de ingenieria",
}

# Las que son «acciones por defecto» de JA1011 (Q7): lo que se hace cuando NO
# hay tarea proactiva adecuada. Importa marcarlas porque la Q7 pide
# justificarlas aparte.
POR_DEFECTO = frozenset({"busqueda_fallas", "operar_hasta_falla", "rediseno"})

PROACTIVAS = frozenset({"cbm", "restauracion", "descarte"})


class ErrorDecision(ValueError):
    """La decision no se puede tomar con lo que hay."""


@dataclass(frozen=True)
class Respuestas:
    """Lo que el equipo de analisis contesta. Todo tri-estado a proposito.

    `None` significa «no se evaluo», y no es lo mismo que «no». Un plan donde
    nadie se pregunto si la degradacion era detectable no es un plan donde se
    decidio que no lo era, y tratarlos igual esconde el trabajo que falta.
    """

    # ¿Existe una tarea a condicion que detecte la degradacion con aviso
    # suficiente para actuar? (la ventana P-F tiene que dar tiempo)
    detectable: bool | None = None
    # ¿Hay una edad a la que la probabilidad condicional de falla sube de
    # forma marcada? Sin esto, restauracion y descarte no previenen nada.
    intervalo_edad: bool | None = None
    # ¿La restauracion devuelve la resistencia original del item?
    restaurable: bool | None = None
    # ¿Existe tarea tecnicamente viable (herramienta, acceso, repuesto)?
    viable: bool | None = None
    # ¿Cuesta menos que la consecuencia de la falla? `None` cuando no hay
    # datos economicos, que es el caso normal: ver `costo_evaluable`.
    costo_efectiva: bool | None = None
    # Para fallas ocultas: ¿se puede probar periodicamente que la proteccion
    # todavia funciona, sin dañarla?
    probable: bool | None = None

    def a_dict(self) -> dict:
        return {"detectable": self.detectable, "intervalo_edad": self.intervalo_edad,
                "restaurable": self.restaurable, "viable": self.viable,
                "costo_efectiva": self.costo_efectiva, "probable": self.probable}


@dataclass(frozen=True)
class Paso:
    """Una pregunta del arbol, con lo que se contesto y a donde llevo."""

    pregunta: str
    respuesta: str
    consecuencia: str

    def a_dict(self) -> dict:
        return {"pregunta": self.pregunta, "respuesta": self.respuesta,
                "consecuencia": self.consecuencia}


@dataclass(frozen=True)
class Dictamen:
    """La estrategia elegida, con el camino que la produjo."""

    estrategia: str
    motivo: str
    camino: tuple[Paso, ...] = ()
    # True cuando es una accion por defecto de JA1011 (Q7).
    por_defecto: bool = False
    # True cuando la guarda de seguridad impidio «operar hasta la falla».
    bloqueado_por_seguridad: bool = False
    # True cuando falto informacion y la decision quedo del lado conservador.
    incompleta: bool = False
    avisos: tuple[str, ...] = ()

    @property
    def rotulo(self) -> str:
        return ESTRATEGIAS[self.estrategia]

    @property
    def proactiva(self) -> bool:
        return self.estrategia in PROACTIVAS

    def a_dict(self) -> dict:
        return {"estrategia": self.estrategia, "rotulo": self.rotulo,
                "motivo": self.motivo, "por_defecto": self.por_defecto,
                "bloqueado_por_seguridad": self.bloqueado_por_seguridad,
                "incompleta": self.incompleta, "avisos": list(self.avisos),
                "camino": [p.a_dict() for p in self.camino]}


SIN_DATOS_ECONOMICOS = (
    "Informacion economica insuficiente para determinar costo-efectividad. La "
    "tarea se conserva; no se declara ahorro.")

AVISO_SIN_EVALUAR = (
    "Quedaron preguntas sin evaluar. La decision salio del lado conservador: "
    "revisela antes de llevarla al plan.")

AVISO_89 = (
    "Sin intervalo de edad identificable, un limite por horas no previene la "
    "falla: Nowlan y Heap (1978) encontraron que el 89 % de los items no tiene "
    "zona de desgaste. Verifique el dato antes de descartar la restauracion.")


def _p(camino, pregunta, respuesta, consecuencia):
    camino.append(Paso(pregunta, respuesta, consecuencia))


def _si_no(v) -> str:
    return "si" if v is True else "no" if v is False else "sin evaluar"


def decidir(modo: ModoFalla, r: Respuestas) -> Dictamen:
    """La estrategia para un modo de falla. Nunca devuelve «preventivo» a secas.

    No consulta el analisis completo ni el historial: decide con el modo de
    falla y las respuestas del equipo. Eso la hace reproducible — la misma
    entrada da la misma salida — y comprobable una por una.
    """
    camino: list[Paso] = []
    avisos: list[str] = []
    grave = modo.grave
    sin_evaluar = [k for k, v in r.a_dict().items()
                   if v is None and k != "costo_efectiva"]

    # ---- 1. ¿Es evidente? Primera bifurcacion, antes que nada.
    if not modo.evidente:
        _p(camino, "¿La perdida de funcion es evidente para quien opera?", "no",
           "falla oculta: el riesgo es la falla multiple, no esta falla sola")
        if r.probable is True:
            _p(camino, "¿Se puede probar periodicamente que la proteccion responde?",
               "si", "busqueda de fallas")
            return Dictamen(
                "busqueda_fallas",
                "La falla es oculta: por si sola no produce efecto, pero deja "
                "sin proteccion a la siguiente. El riesgo que se trata aqui no "
                "es esta falla sino la falla multiple, asi que la tarea no "
                "previene nada: comprueba periodicamente que la funcion oculta "
                "todavia responde.",
                tuple(camino), por_defecto=True,
                incompleta=bool(sin_evaluar),
                avisos=tuple(avisos + ([AVISO_SIN_EVALUAR] if sin_evaluar else [])))
        _p(camino, "¿Se puede probar periodicamente que la proteccion responde?",
           _si_no(r.probable),
           "no hay forma de verificar la funcion oculta")
        return Dictamen(
            "rediseno",
            "Falla oculta que no se puede verificar: no hay tarea que confirme "
            "que la proteccion sigue ahi, y entonces nada acota el riesgo de la "
            "falla multiple. Lo que corresponde es cambiar el diseño para "
            "hacerla evidente o verificable.",
            tuple(camino), por_defecto=True,
            bloqueado_por_seguridad=grave,
            incompleta=bool(sin_evaluar),
            avisos=tuple(avisos + ([AVISO_SIN_EVALUAR] if sin_evaluar else [])))

    _p(camino, "¿La perdida de funcion es evidente para quien opera?", "si",
       "sigue por la rama de fallas evidentes")

    # ---- 2. ¿Consecuencia grave? Cambia el criterio de aceptacion.
    _p(camino, "¿Tiene consecuencia de seguridad o ambiental?",
       "si" if grave else "no",
       "la tarea debe reducir el riesgo a un nivel tolerable" if grave
       else "basta con que la tarea cueste menos que la falla")

    # ---- 3. CBM primero: aprovecha la vida util y no abre una maquina sana.
    if r.detectable is True:
        _p(camino, "¿La degradacion se detecta con aviso suficiente para actuar?",
           "si", "mantenimiento segun condicion")
        if r.viable is False:
            _p(camino, "¿La tarea a condicion es tecnicamente viable?", "no",
               "se descarta CBM y se sigue buscando")
        else:
            motivo = ("La degradacion se puede detectar con aviso suficiente: se "
                      "vigila la condicion y se interviene cuando el parametro lo "
                      "pide, no cuando lo diga el calendario.")
            if not grave and r.costo_efectiva is None:
                avisos.append(SIN_DATOS_ECONOMICOS)
            return Dictamen("cbm", motivo, tuple(camino),
                            incompleta=bool(sin_evaluar),
                            avisos=tuple(avisos +
                                         ([AVISO_SIN_EVALUAR] if sin_evaluar else [])))
    else:
        _p(camino, "¿La degradacion se detecta con aviso suficiente para actuar?",
           _si_no(r.detectable), "no hay tarea a condicion aplicable")

    # ---- 4. Edad: sin zona de desgaste, un limite por horas no previene nada.
    if r.intervalo_edad is True:
        _p(camino, "¿Hay una edad a la que la probabilidad de falla sube?", "si",
           "una tarea por intervalo puede servir")
        if r.restaurable is True and r.viable is not False:
            return Dictamen(
                "restauracion",
                "Hay una edad identificable a la que la falla se vuelve probable, "
                "y restaurar devuelve la resistencia original: se restaura antes "
                "de ese punto.",
                tuple(camino + [Paso("¿Restaurar devuelve la resistencia original?",
                                     "si", "restauracion programada")]),
                incompleta=bool(sin_evaluar),
                avisos=tuple(avisos + ([AVISO_SIN_EVALUAR] if sin_evaluar else [])))
        if r.viable is not False:
            return Dictamen(
                "descarte",
                "Hay una edad identificable y el item no se restaura: se descarta "
                "y se reemplaza antes de ese punto.",
                tuple(camino + [Paso("¿Restaurar devuelve la resistencia original?",
                                     _si_no(r.restaurable), "descarte programado")]),
                incompleta=bool(sin_evaluar),
                avisos=tuple(avisos + ([AVISO_SIN_EVALUAR] if sin_evaluar else [])))
        _p(camino, "¿La tarea por intervalo es tecnicamente viable?", "no",
           "no hay tarea proactiva aplicable")
    else:
        _p(camino, "¿Hay una edad a la que la probabilidad de falla sube?",
           _si_no(r.intervalo_edad),
           "restauracion y descarte no previenen nada aqui")
        if r.intervalo_edad is False:
            avisos.append(AVISO_89)

    # ---- 5. No hay tarea proactiva. Aqui manda la guarda.
    if grave:
        _p(camino, "Sin tarea proactiva y con consecuencia de seguridad: "
                   "¿operar hasta la falla?", "no",
           "la guarda lo impide: el rediseño es obligatorio")
        return Dictamen(
            "rediseno",
            "Ninguna tarea proactiva reduce el riesgo a un nivel tolerable y la "
            "falla tiene consecuencia de seguridad o ambiental: operar hasta la "
            "falla no es una salida legal. Corresponde cambiar el diseño, el "
            "contexto operacional o el procedimiento.",
            tuple(camino), por_defecto=True, bloqueado_por_seguridad=True,
            incompleta=bool(sin_evaluar),
            avisos=tuple(avisos + ([AVISO_SIN_EVALUAR] if sin_evaluar else [])))

    if r.costo_efectiva is False:
        _p(camino, "¿Alguna tarea cuesta menos que la consecuencia de la falla?",
           "no", "operar hasta la falla")
        return Dictamen(
            "operar_hasta_falla",
            "Sin consecuencia grave, sin degradacion detectable y sin edad "
            "identificable: ninguna tarea programada se paga. Se repara cuando "
            "falle, a conciencia y no por omision.",
            tuple(camino), por_defecto=True,
            incompleta=bool(sin_evaluar),
            avisos=tuple(avisos + ([AVISO_SIN_EVALUAR] if sin_evaluar else [])))

    if r.costo_efectiva is None:
        avisos.append(SIN_DATOS_ECONOMICOS)
    _p(camino, "¿Alguna tarea cuesta menos que la consecuencia de la falla?",
       _si_no(r.costo_efectiva), "operar hasta la falla, sin declarar ahorro")
    return Dictamen(
        "operar_hasta_falla",
        "No hay tarea proactiva aplicable y la consecuencia no es de seguridad. "
        "Se opera hasta la falla; si aparece un dato economico que lo cambie, se "
        "revisa.",
        tuple(camino), por_defecto=True,
        incompleta=bool(sin_evaluar),
        avisos=tuple(avisos + ([AVISO_SIN_EVALUAR] if sin_evaluar else [])))


@dataclass
class Decisiones:
    """Las decisiones de un analisis, por modo de falla."""

    por_modo: dict[str, Dictamen] = field(default_factory=dict)

    def registrar(self, modo: ModoFalla, respuestas: Respuestas) -> Dictamen:
        d = decidir(modo, respuestas)
        self.por_modo[modo.id] = d
        return d

    def get(self, modo_id: str) -> Dictamen | None:
        return self.por_modo.get(modo_id)

    def __len__(self) -> int:
        return len(self.por_modo)

    def __contains__(self, modo_id: str) -> bool:
        return modo_id in self.por_modo

    def __iter__(self):
        return iter(self.por_modo.items())

    def reparto(self) -> dict[str, int]:
        """Cuantos modos por estrategia. Es la linea del tablero del §16."""
        cuenta = {k: 0 for k in ESTRATEGIAS}
        for d in self.por_modo.values():
            cuenta[d.estrategia] += 1
        return cuenta

    def a_dict(self) -> dict:
        return {mid: d.a_dict() for mid, d in self.por_modo.items()}


def resumen(analisis: Analisis, decisiones: Decisiones) -> dict:
    """Lo que un jefe de mantenimiento mira primero."""
    reparto = decisiones.reparto()
    return {
        "activo": analisis.activo.codigo,
        "modos": len(analisis.modos),
        "decididos": len(decisiones),
        "graves": len(analisis.modos_graves()),
        "ocultos": len(analisis.modos_ocultos()),
        "reparto": reparto,
        "rediseños_obligatorios": sum(
            1 for d in decisiones.por_modo.values() if d.bloqueado_por_seguridad),
        "decisiones_incompletas": sum(
            1 for d in decisiones.por_modo.values() if d.incompleta),
    }
