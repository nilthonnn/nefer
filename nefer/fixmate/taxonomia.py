"""Los nueve niveles de ISO 14224, y que llena FixMate en cada uno.

Esto cierra la OBS-02 de la auditoria, que decia: «la jerarquia de activos
de FixMate son tres niveles; la de la norma, nueve». La observacion no se
cierra ampliando la jerarquia porque si —un nivel que nadie necesita se
rellena con cualquier cosa, que es el problema de «Otro» otra vez— sino
diciendo EXACTAMENTE que nivel llena que campo, cual no se modela y por que.
Lo que quedaba abierto no era la falta de niveles: era que nadie podia
responder «¿esto mapea a la norma?» sin abrir el codigo.

LOS NUEVE NIVELES. Los cinco primeros dicen donde esta el equipo y a que
operacion pertenece; los cuatro ultimos lo desarman:

    1  industria                     \\
    2  categoria de negocio           |  uso y localizacion
    3  instalacion                    |
    4  planta o unidad                |
    5  seccion o sistema             /
    6  UNIDAD DE EQUIPO              \\   nivel comun de reporte
    7  subunidad                      |  subdivision del equipo
    8  COMPONENTE / ITEM MANTENIBLE   |   donde cae el mantenimiento
    9  parte                         /

Dos de ellos tienen nombre propio en la norma y los dos coinciden con como
trabaja FixMate, lo cual no es casualidad sino la razon de que el mapeo
salga limpio:

- **El nivel 6 es el nivel comun de reporte.** Es donde la norma agrega y
  compara. En FixMate es el activo, que es donde se cuenta el MTBF.
- **El nivel 8 es donde cae el mantenimiento.** Es el item que se repara o
  se reemplaza. En FixMate es el componente del modo de falla, que es donde
  se decide la estrategia.

LO QUE NO SE MODELA, Y POR QUE. Decirlo es la mitad del valor:

- **Niveles 1 y 2** son constantes de la instalacion entera, no del activo.
  Los pone quien exporta, con `Contexto`: repetirlos en cada maquina seria
  guardar mil veces el mismo dato y que un dia uno de ellos no coincida.
- **Niveles 4 y 5** se colapsan en el 3 para una flota movil. Una excavadora
  que hoy esta en un frente y mañana en otro no tiene «planta» ni «seccion»
  estables, y anotar la de hoy como si fuera suya es anotar algo falso.
  En una planta fija esto no vale, y entonces hay que agregarlos.
- **Nivel 9, la parte.** RCM decide en el item mantenible: si algo no se
  reemplaza por separado, no es donde se toma una decision de mantenimiento.
  Bajar a parte seria modelar un detalle que ninguna tarea usa.

Y una diferencia de forma: FixMate tiene `subsistema` entre el sistema y el
componente. No es un nivel de la norma, es un refinamiento propio DENTRO del
nivel 7. En un intercambio conforme se concatena con la subunidad; aqui se
dice en vez de inventarle un numero.
"""

from __future__ import annotations

from dataclasses import dataclass

from .activos import Activo, Ubicacion

# El nivel donde la norma agrega y compara, y donde FixMate cuenta el MTBF.
NIVEL_DE_REPORTE = 6
# El nivel donde cae el trabajo, y donde RCM decide la estrategia.
NIVEL_DE_MANTENIMIENTO = 8


@dataclass(frozen=True)
class Nivel:
    """Un nivel de la taxonomia, y de donde sale su valor en FixMate."""

    numero: int
    nombre: str
    # Que campo de FixMate lo llena, o por que no se llena. Es lo que
    # convierte esta tabla en algo auditable y no en una lista de nombres.
    origen: str
    # True cuando FixMate puede dar un valor. False es una ausencia
    # declarada, no un olvido.
    modelado: bool

    def a_dict(self) -> dict:
        return {"numero": self.numero, "nombre": self.nombre,
                "origen": self.origen, "modelado": self.modelado}


NIVELES: tuple[Nivel, ...] = (
    Nivel(1, "industria", "constante de la instalacion: `Contexto.industria`", True),
    Nivel(2, "categoria de negocio",
          "constante de la instalacion: `Contexto.categoria_negocio`", True),
    Nivel(3, "instalacion", "`Activo.instalacion`", True),
    Nivel(4, "planta o unidad",
          "no se modela: una flota movil no tiene planta estable", False),
    Nivel(5, "seccion o sistema",
          "no se modela: el frente cambia de turno a turno", False),
    Nivel(6, "unidad de equipo", "`Activo.codigo` y `Activo.categoria`", True),
    Nivel(7, "subunidad",
          "`Ubicacion.sistema` (con `subsistema` como refinamiento propio)", True),
    Nivel(8, "componente / item mantenible", "`Ubicacion.componente`", True),
    Nivel(9, "parte",
          "no se modela: RCM decide en el item mantenible", False),
)

MODELADOS = tuple(n.numero for n in NIVELES if n.modelado)
NO_MODELADOS = tuple(n.numero for n in NIVELES if not n.modelado)

# Y de los modelados, cuales son del ACTIVO y cuales del MODO DE FALLA. Sin
# esta distincion, mirar un activo sin modo de falla delante contaba como
# «faltan» la subunidad y el componente, que no son suyos: son de donde
# esta la falla. Un informe que llama falta a algo que no corresponde
# declarar ahi enseña a rellenarlo con cualquier cosa.
NIVELES_DEL_ACTIVO = (1, 2, 3, 6)
NIVELES_DEL_MODO = (7, 8)


@dataclass(frozen=True)
class Contexto:
    """Lo que es igual para toda la instalacion, y por eso no va en el activo.

    Vacios por omision: declararlos es del que exporta, y una industria
    inventada por el programa seria un dato que nadie reviso.
    """

    industria: str = ""
    categoria_negocio: str = ""


def niveles(activo: Activo, ubicacion: Ubicacion | None = None,
            contexto: Contexto | None = None) -> dict[int, str]:
    """El valor de cada nivel para un activo y, si se da, un modo de falla.

    Cadena vacia es «no declarado», y en los niveles no modelados lo es
    siempre: ver el encabezado. Nunca se rellena con un parecido.
    """
    u = ubicacion or Ubicacion()
    c = contexto or Contexto()
    sub = " / ".join(p for p in (u.sistema, u.subsistema) if p)
    return {
        1: c.industria,
        2: c.categoria_negocio,
        3: getattr(activo, "instalacion", ""),
        4: "",
        5: "",
        6: activo.codigo,
        7: sub,
        8: u.componente,
        9: "",
    }


@dataclass(frozen=True)
class Cobertura:
    """Cuanto de la taxonomia se puede entregar, y que falta por declarar."""

    valores: dict[int, str]
    # Los niveles que tocaba declarar en esta mirada: los del activo, y
    # ademas los del modo de falla si se dio uno.
    aplicables: tuple[int, ...]
    # De esos, los que quedaron vacios. Se arreglan escribiendolos; los no
    # modelados, no.
    sin_declarar: tuple[int, ...]

    @property
    def declarados(self) -> int:
        return sum(1 for n in self.aplicables if self.valores[n])

    @property
    def completa(self) -> bool:
        """Si esta todo lo que FixMate puede dar en esta mirada. No dice
        «conforme con la norma»: los niveles no modelados siguen sin estar,
        a proposito."""
        return not self.sin_declarar

    def resumen(self) -> str:
        return (f"{self.declarados} de {len(self.aplicables)} niveles "
                f"aplicables declarados; {len(NO_MODELADOS)} no se modelan a "
                f"proposito (niveles {', '.join(str(n) for n in NO_MODELADOS)}).")

    def a_dict(self) -> dict:
        return {"valores": {str(k): v for k, v in self.valores.items()},
                "aplicables": list(self.aplicables),
                "sin_declarar": list(self.sin_declarar),
                "declarados": self.declarados, "completa": self.completa}


def cobertura(activo: Activo, ubicacion: Ubicacion | None = None,
              contexto: Contexto | None = None) -> Cobertura:
    """Cuanto de la taxonomia se puede entregar.

    Sin `ubicacion` se miran solo los niveles del activo: la subunidad y el
    componente son del modo de falla, y reclamarlos aqui seria pedir que se
    rellene algo que en el activo no existe.
    """
    valores = niveles(activo, ubicacion, contexto)
    aplicables = (NIVELES_DEL_ACTIVO if ubicacion is None
                  else tuple(sorted(NIVELES_DEL_ACTIVO + NIVELES_DEL_MODO)))
    faltan = tuple(n for n in aplicables if not valores[n])
    return Cobertura(valores, aplicables, faltan)


def filas(analisis, contexto: Contexto | None = None) -> list[dict]:
    """Una fila por modo de falla, con los nueve niveles.

    Es la forma que tiene un archivo de intercambio: cada registro trae su
    taxonomia entera. Los niveles que no se modelan van vacios y se ven.
    """
    salida = []
    for modo in analisis.modos:
        v = niveles(analisis.activo, modo.ubicacion, contexto)
        fila = {"modo_falla_id": modo.id, "modo_falla": modo.descripcion}
        for n in NIVELES:
            fila[f"n{n.numero}_{n.nombre.split()[0]}"] = v[n.numero]
        salida.append(fila)
    return salida
