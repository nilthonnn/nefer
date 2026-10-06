"""Del dictamen RCM a la tarea ejecutable, y de vuelta a la pauta TPM.

Una estrategia no se puede ejecutar. «Mantenimiento segun condicion» no le
dice a nadie que hacer el martes. Aqui la decision se convierte en una tarea
con intervalo o condicion, responsable y procedimiento — y, cuando
corresponde, en un punto de la pauta del operador.

----------------------------------------------------------------------------
LO QUE ESTE MODULO SE NIEGA A RELLENAR

Una tarea generada automaticamente con intervalo, herramienta y repuesto
inventados se ve terminada y no lo esta. En campo eso se ejecuta: alguien
lleva la llave equivocada a 40 km de distancia.

Asi que la tarea nace con los campos que SI se derivan del analisis
—estrategia, modo de falla, activo, sistema, responsable por defecto— y con
los demas vacios. `falta_por_completar()` los enumera, y `aplicable()` se
niega a dar por lista una tarea a la que le falta lo que la hace ejecutable.

El intervalo es el caso mas claro. De «hay una edad a la que la probabilidad
sube» no sale un numero: sale que existe un numero y que hay que medirlo.
Ponerle 500 h porque suena razonable es inventar el dato que justificaba
toda la tarea.
----------------------------------------------------------------------------

EL CAMINO DE VUELTA A TPM. Un dictamen de CBM cuya verificacion es sensorial
—mirar, oir, tocar— y que cae dentro del alcance del operador puede bajar a
la ronda autonoma en vez de ocupar una ruta del tecnico. Eso lo decide
`punto_tpm()`, que tambien devuelve un borrador incompleto a proposito: el
criterio de aceptacion no sale del analisis, porque el analisis dice que hay
que mirar y no que significa que este bien.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .decision import ESTRATEGIAS, Dictamen
from .rcm import Analisis, ModoFalla

# Como se expresa el «cuando» de cada estrategia. No son intercambiables:
# una tarea a condicion con intervalo de calendario deja de ser a condicion.
DISPARADORES = {
    "cbm": "condicion",          # un parametro cruza un limite
    "restauracion": "intervalo",
    "descarte": "intervalo",
    "busqueda_fallas": "intervalo",
    "operar_hasta_falla": "ninguno",
    "rediseno": "proyecto",
}

# Quien la hace, por defecto. Se puede cambiar; esto solo evita que el campo
# nazca vacio con la respuesta mas comun ya escrita.
RESPONSABLE = {
    "cbm": "predictivo",
    "restauracion": "mantenimiento",
    "descarte": "mantenimiento",
    "busqueda_fallas": "mantenimiento",
    "operar_hasta_falla": "",
    "rediseno": "ingenieria",
}


class ErrorPlan(ValueError):
    """La tarea no se puede construir tal como viene."""


@dataclass
class Tarea:
    """Una linea del plan de mantenimiento, con su trazabilidad hacia atras."""

    id: str
    activo_codigo: str
    modo_falla_id: str
    estrategia: str
    descripcion: str = ""
    # «condicion», «intervalo», «ninguno» o «proyecto». Lo fija la estrategia.
    disparador: str = ""
    # Para disparador «intervalo»: cada cuanto. Vacio hasta que se mida.
    intervalo_dias: int | None = None
    intervalo_horas: int | None = None
    # Para disparador «condicion»: que se mide y con que limite. El limite
    # tiene que venir del OEM o de un estandar, nunca de esta herramienta.
    parametro: str = ""
    limite: str = ""
    fuente_limite: str = ""
    responsable: str = ""
    duracion_horas: float | None = None
    herramientas: tuple[str, ...] = ()
    repuestos: tuple[str, ...] = ()
    procedimiento: str = ""
    fuente_procedimiento: str = ""
    seguridad: str = ""
    sistema: str = ""
    componente: str = ""
    estado: str = "borrador"
    ultima_ejecucion: str = ""
    proxima_ejecucion: str = ""
    # El motivo del dictamen, copiado. Una tarea sin el por que no se revisa.
    motivo: str = ""

    def a_dict(self) -> dict:
        return {
            "id": self.id, "activo_codigo": self.activo_codigo,
            "modo_falla_id": self.modo_falla_id, "estrategia": self.estrategia,
            "rotulo": ESTRATEGIAS.get(self.estrategia, self.estrategia),
            "descripcion": self.descripcion, "disparador": self.disparador,
            "intervalo_dias": self.intervalo_dias,
            "intervalo_horas": self.intervalo_horas,
            "parametro": self.parametro, "limite": self.limite,
            "fuente_limite": self.fuente_limite, "responsable": self.responsable,
            "duracion_horas": self.duracion_horas,
            "herramientas": list(self.herramientas),
            "repuestos": list(self.repuestos),
            "procedimiento": self.procedimiento,
            "fuente_procedimiento": self.fuente_procedimiento,
            "seguridad": self.seguridad, "sistema": self.sistema,
            "componente": self.componente, "estado": self.estado,
            "ultima_ejecucion": self.ultima_ejecucion,
            "proxima_ejecucion": self.proxima_ejecucion, "motivo": self.motivo,
        }


def falta_por_completar(t: Tarea) -> tuple[str, ...]:
    """Que le falta a la tarea para ser ejecutable. Lo que no se deriva.

    No incluye herramientas ni repuestos: hay tareas que no llevan ninguno, y
    exigirlos haria que se rellenen con cualquier cosa.
    """
    falta: list[str] = []
    if not str(t.descripcion).strip():
        falta.append("que se hace, en una frase imperativa")

    if t.disparador == "intervalo" and not (t.intervalo_dias or t.intervalo_horas):
        falta.append("cada cuanto: el analisis dice que existe un intervalo, "
                     "no cual es. Hay que medirlo")
    if t.disparador == "condicion":
        if not str(t.parametro).strip():
            falta.append("que parametro se mide")
        if not str(t.limite).strip():
            falta.append("el limite y su fuente: tiene que venir del OEM o de "
                         "un estandar, no de esta herramienta")
        elif not str(t.fuente_limite).strip():
            falta.append("de donde sale el limite")
    if t.disparador not in ("ninguno", "proyecto") and not str(t.procedimiento).strip():
        falta.append("el procedimiento, o la referencia al del OEM")
    return tuple(falta)


def aplicable(t: Tarea) -> bool:
    """Si la tarea se puede poner en un calendario sin inventar nada."""
    return not falta_por_completar(t)


def desde_dictamen(modo: ModoFalla, d: Dictamen, activo_codigo: str,
                   idx: int = 1) -> Tarea | None:
    """La tarea que corresponde a un dictamen. `None` para operar hasta la falla.

    Operar hasta la falla no genera tarea, y eso es el punto: la decision fue
    NO programar nada. Crear una tarea vacia «para que figure» devolveria al
    plan justo lo que el analisis sacó de el.
    """
    if d.estrategia == "operar_hasta_falla":
        return None

    return Tarea(
        id=f"T{idx:03d}-{modo.id}",
        activo_codigo=activo_codigo,
        modo_falla_id=modo.id,
        estrategia=d.estrategia,
        disparador=DISPARADORES[d.estrategia],
        responsable=RESPONSABLE[d.estrategia],
        sistema=modo.ubicacion.sistema,
        componente=modo.ubicacion.componente or modo.descripcion,
        motivo=d.motivo,
    )


@dataclass
class Plan:
    """Las tareas de un activo, con lo que falta a la vista."""

    activo_codigo: str
    tareas: list[Tarea] = field(default_factory=list)
    # Modos que el analisis decidio NO programar. Se listan a proposito: un
    # plan que esconde lo que decidio no hacer no se puede auditar.
    sin_tarea: list[str] = field(default_factory=list)

    @property
    def completas(self) -> list[Tarea]:
        return [t for t in self.tareas if aplicable(t)]

    @property
    def borradores(self) -> list[Tarea]:
        return [t for t in self.tareas if not aplicable(t)]

    def por_estrategia(self) -> dict[str, int]:
        cuenta = {k: 0 for k in ESTRATEGIAS}
        for t in self.tareas:
            cuenta[t.estrategia] += 1
        cuenta["operar_hasta_falla"] = len(self.sin_tarea)
        return cuenta

    def a_dict(self) -> dict:
        return {"activo_codigo": self.activo_codigo,
                "tareas": [t.a_dict() for t in self.tareas],
                "sin_tarea": list(self.sin_tarea),
                "completas": len(self.completas),
                "borradores": len(self.borradores),
                "por_estrategia": self.por_estrategia()}


def generar(analisis: Analisis, decisiones) -> Plan:
    """El plan que sale de un analisis ya decidido.

    Solo genera para los modos que tienen decision. Un modo sin decidir no
    produce una tarea en blanco: produce nada, y eso lo denuncia la Q6 de
    `rcm.completitud`.
    """
    plan = Plan(activo_codigo=analisis.activo.codigo)
    n = 0
    for modo in analisis.modos:
        d = decisiones.get(modo.id) if hasattr(decisiones, "get") else None
        if d is None:
            continue
        n += 1
        tarea = desde_dictamen(modo, d, analisis.activo.codigo, n)
        if tarea is None:
            plan.sin_tarea.append(modo.id)
        else:
            plan.tareas.append(tarea)
    return plan


# ------------------------------------------- el camino de vuelta a TPM

@dataclass(frozen=True)
class BorradorPuntoTPM:
    """Un punto de pauta a medio hacer, con lo que falta enumerado.

    `criterio` sale vacio y es deliberado: el analisis RCM dice QUE hay que
    mirar; no dice que significa que este bien. Rellenarlo con algo plausible
    daria una pauta que se ve terminada y que cada operador interpreta
    distinto, que es el modo en que una ronda deja de medir nada.
    """

    clase: str
    punto: str
    criterio: str = ""
    codigo_catalogo: str = ""
    modo_falla_id: str = ""
    alcance_operador: bool = True
    desde_tarea: str = ""
    falta: tuple[str, ...] = ()

    def a_dict(self) -> dict:
        return {"clase": self.clase, "punto": self.punto,
                "criterio": self.criterio,
                "codigo_catalogo": self.codigo_catalogo,
                "modo_falla_id": self.modo_falla_id,
                "alcance_operador": self.alcance_operador,
                "desde_tarea": self.desde_tarea, "falta": list(self.falta)}


# Lo que el operador puede hacer sin instrumento. Si la verificacion de la
# tarea no esta aqui, pertenece a la ruta del tecnico.
SENSORIAL = frozenset({"vista", "oido", "tacto", "olfato"})


def punto_tpm(tarea: Tarea, modo: ModoFalla, verificacion: str = "",
              alcance_operador: bool = False) -> BorradorPuntoTPM | None:
    """Baja una tarea a la ronda autonoma, si de verdad puede bajar.

    Devuelve `None` salvo que se den las tres cosas:

    1. la estrategia es CBM (una restauracion o un descarte no son una ronda
       de treinta segundos, y una busqueda de fallas tampoco: probar una
       proteccion no es mirarla);
    2. la verificacion es SENSORIAL —vista, oido, tacto, olfato—; si hace
       falta un instrumento, es ruta del tecnico y mezclarlas hace que la
       ronda no se cumpla;
    3. esta declarado que cae dentro del alcance del operador.

    Los tres son decisiones de quien escribe el plan, no inferencias. Por eso
    `verificacion` y `alcance_operador` son argumentos y no se adivinan de la
    descripcion de la tarea.
    """
    if tarea.estrategia != "cbm":
        return None
    if verificacion.strip().lower() not in SENSORIAL:
        return None
    if not alcance_operador:
        return None

    clase = "inspeccionar"
    falta = ["criterio observable: que cuenta como OK",
             "segundos que cuesta el punto"]
    return BorradorPuntoTPM(
        clase=clase,
        punto=tarea.componente or modo.descripcion,
        criterio="",
        codigo_catalogo=modo.codigo_catalogo,
        modo_falla_id=modo.id,
        alcance_operador=True,
        desde_tarea=tarea.id,
        falta=tuple(falta),
    )
