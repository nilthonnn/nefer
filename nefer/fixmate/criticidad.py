"""Criticidad: la escala es de la empresa, no de la herramienta.

Aqui no hay numeros universales, y la ausencia es deliberada. Una matriz de
criticidad codifica cuanto tolera una organizacion: lo que para una faena
minera es «severidad 4» para un taller de ciudad es cerrar la puerta. Una
herramienta que trae la escala puesta esta decidiendo el apetito de riesgo de
un cliente que no conoce, y despues ese numero se usa para priorizar quien
entra primero al taller.

Por eso `evaluar()` EXIGE un metodo. No hay escala por defecto y no hay
fallback silencioso: sin metodo configurado, la criticidad es «no evaluada»,
que es un estado legitimo y visible.

----------------------------------------------------------------------------
SOBRE EL RPN, PORQUE VA A SER LO PRIMERO QUE ALGUIEN PIDA

El RPN clasico —severidad x ocurrencia x deteccion— se sigue usando mucho y
tiene un defecto conocido: multiplica escalas ORDINALES. Un 8 de severidad no
es «el doble» de un 4; es el escalon siguiente de una lista. Multiplicar
posiciones de una lista produce un numero que parece medir y no mide.

La consecuencia practica se ve con dos casos:

    severidad 2 x ocurrencia 3 x deteccion 8 = 48
    severidad 8 x ocurrencia 3 x deteccion 2 = 48

El mismo RPN, y no son el mismo riesgo ni de lejos: el segundo mata gente. Un
umbral del tipo «actuar si RPN > 100» trata los dos igual.

Por eso el manual conjunto AIAG-VDA de 2019 ELIMINO el RPN y lo reemplazo por
una tabla de Prioridad de Accion (Alta / Media / Baja) que pondera primero
severidad, despues ocurrencia y por ultimo deteccion, sin multiplicarlas.

Este modulo soporta las dos combinaciones. `RPN_EJEMPLO` existe porque hay
plantas que lo tienen en su procedimiento y cambiarlo no es decision de la
herramienta — pero esta rotulado como ejemplo, lleva la advertencia encima y
no es el valor por defecto de nada.
----------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Lo que se guarda cuando no hay escala configurada. No es cero ni «baja»:
# son cosas distintas y confundirlas prioriza mal.
NO_EVALUADA = "no evaluada"

ADVERTENCIA_RPN = (
    "El RPN multiplica escalas ordinales, que es estadisticamente indefendible: "
    "dos combinaciones muy distintas de severidad dan el mismo numero. AIAG-VDA "
    "lo reemplazo en 2019 por una tabla de prioridad. Uselo solo si su "
    "procedimiento lo exige, y no compare RPN entre equipos distintos.")


@dataclass(frozen=True)
class Nivel:
    """Un escalon de un factor. El texto importa tanto como el numero."""

    valor: int
    etiqueta: str
    descripcion: str = ""

    def a_dict(self) -> dict:
        return {"valor": self.valor, "etiqueta": self.etiqueta,
                "descripcion": self.descripcion}


@dataclass(frozen=True)
class Factor:
    """Una dimension de la evaluacion: frecuencia, severidad, deteccion...

    `niveles` no se valida contra ninguna escala cannonica porque no hay una:
    una planta usa 1-5, otra 1-10, otra A-E con valores 1-5 detras.
    """

    clave: str
    etiqueta: str
    niveles: tuple[Nivel, ...]

    def nivel(self, valor: int) -> Nivel | None:
        return next((n for n in self.niveles if n.valor == valor), None)

    def a_dict(self) -> dict:
        return {"clave": self.clave, "etiqueta": self.etiqueta,
                "niveles": [n.a_dict() for n in self.niveles]}


class ErrorCriticidad(ValueError):
    """La evaluacion no se puede hacer tal como viene."""


@dataclass(frozen=True)
class Metodo:
    """Como ESTA empresa calcula criticidad. Se guarda con cada evaluacion.

    Guardar el metodo junto al resultado no es burocracia: la escala cambia
    —se reencuadra la matriz, se agrega un factor, se mueve un umbral— y sin
    el metodo anotado no hay forma de saber si un 12 de hace dos años es
    comparable con un 12 de hoy. Lo normal es que no lo sea.
    """

    nombre: str
    version: str
    factores: tuple[Factor, ...]
    # «producto» replica el RPN clasico; «maximo» y «suma» son alternativas
    # defendibles sobre ordinales; «matriz» usa `tabla` y no combina numeros.
    combinacion: str = "matriz"
    # De mayor a menor: el primer umbral que el valor alcanza da la etiqueta.
    umbrales: tuple[tuple[int, str], ...] = ()
    # Solo para `combinacion="matriz"`: clave = tupla de valores, en el orden
    # de `factores`; valor = etiqueta. Es lo que recomienda AIAG-VDA.
    tabla: dict[tuple[int, ...], str] = field(default_factory=dict)
    # Si el metodo tiene letra chica, va aqui y viaja con cada evaluacion.
    advertencia: str = ""
    fuente: str = ""

    def factor(self, clave: str) -> Factor | None:
        return next((f for f in self.factores if f.clave == clave), None)

    def a_dict(self) -> dict:
        return {"nombre": self.nombre, "version": self.version,
                "combinacion": self.combinacion,
                "factores": [f.a_dict() for f in self.factores],
                "umbrales": [list(u) for u in self.umbrales],
                "advertencia": self.advertencia, "fuente": self.fuente}


@dataclass(frozen=True)
class Criticidad:
    """El resultado, con todo lo necesario para rehacerlo y discutirlo."""

    etiqueta: str
    valor: int | None
    # Lo que se respondio en cada factor, por clave.
    valores: dict[str, int] = field(default_factory=dict)
    metodo: str = ""
    version: str = ""
    advertencia: str = ""

    @property
    def evaluada(self) -> bool:
        return self.etiqueta != NO_EVALUADA

    def a_dict(self) -> dict:
        return {"etiqueta": self.etiqueta, "valor": self.valor,
                "valores": dict(self.valores), "metodo": self.metodo,
                "version": self.version, "advertencia": self.advertencia}


SIN_EVALUAR = Criticidad(etiqueta=NO_EVALUADA, valor=None)


def evaluar(metodo: Metodo | None, valores: dict[str, int]) -> Criticidad:
    """Aplica el metodo de la empresa. Sin metodo, «no evaluada».

    Devolver `SIN_EVALUAR` en vez de levantar una excepcion cuando no hay
    metodo es a proposito: un taller que todavia no configuro su matriz tiene
    que poder cargar modos de falla igual. Lo que no puede es creer que estan
    priorizados.
    """
    if metodo is None:
        return SIN_EVALUAR

    faltan = [f.clave for f in metodo.factores if f.clave not in valores]
    if faltan:
        raise ErrorCriticidad(
            f"falta responder {', '.join(faltan)}. Un metodo a medio responder "
            "da un numero que parece una evaluacion y no lo es.")

    limpios: dict[str, int] = {}
    for f in metodo.factores:
        v = valores[f.clave]
        if f.nivel(v) is None:
            permitidos = ", ".join(str(n.valor) for n in f.niveles)
            raise ErrorCriticidad(
                f"{f.clave}={v} no es un nivel de «{f.etiqueta}» "
                f"(permitidos: {permitidos}).")
        limpios[f.clave] = v

    if metodo.combinacion == "matriz":
        clave = tuple(limpios[f.clave] for f in metodo.factores)
        etiqueta = metodo.tabla.get(clave)
        if etiqueta is None:
            raise ErrorCriticidad(
                f"la combinacion {clave} no esta en la tabla del metodo "
                f"«{metodo.nombre}». Una tabla con huecos decide por omision.")
        valor = None
    else:
        numeros = [limpios[f.clave] for f in metodo.factores]
        if metodo.combinacion == "producto":
            valor = 1
            for n in numeros:
                valor *= n
        elif metodo.combinacion == "suma":
            valor = sum(numeros)
        elif metodo.combinacion == "maximo":
            valor = max(numeros)
        else:
            raise ErrorCriticidad(
                f"combinacion «{metodo.combinacion}» desconocida: use "
                "matriz, producto, suma o maximo.")
        etiqueta = _etiqueta_por_umbral(valor, metodo.umbrales)

    return Criticidad(etiqueta=etiqueta, valor=valor, valores=limpios,
                      metodo=metodo.nombre, version=metodo.version,
                      advertencia=metodo.advertencia)


def _etiqueta_por_umbral(valor: int, umbrales) -> str:
    """El primer umbral que el valor alcanza, de mayor a menor."""
    if not umbrales:
        return str(valor)
    for minimo, etiqueta in sorted(umbrales, key=lambda u: -u[0]):
        if valor >= minimo:
            return etiqueta
    return umbrales[-1][1] if umbrales else str(valor)


# --------------------------------------------------- escalas de ejemplo
#
# Van rotuladas como EJEMPLO en el nombre, y ninguna es el valor por defecto
# de nada. Estan para que un taller tenga de donde partir, no para que las
# use tal cual: los descriptores de cada nivel hay que reescribirlos con lo
# que significa en SU faena.

def _niveles(*pares) -> tuple[Nivel, ...]:
    return tuple(Nivel(v, e, d) for v, e, d in pares)


SEVERIDAD_EJEMPLO = Factor("severidad", "Severidad", _niveles(
    (1, "Insignificante", "Sin efecto perceptible en la funcion."),
    (2, "Menor", "Molestia; la maquina sigue cumpliendo su funcion."),
    (3, "Moderada", "Perdida parcial de funcion o parada corta."),
    (4, "Mayor", "Parada prolongada o daño a un componente mayor."),
    (5, "Critica", "Lesion a una persona, daño ambiental o perdida total."),
))

FRECUENCIA_EJEMPLO = Factor("frecuencia", "Frecuencia", _niveles(
    (1, "Remota", "No ha ocurrido en la flota."),
    (2, "Baja", "Una vez cada varios años."),
    (3, "Media", "Una vez al año, aproximadamente."),
    (4, "Alta", "Varias veces al año."),
    (5, "Muy alta", "Mensual o mas seguido."),
))

DETECCION_EJEMPLO = Factor("deteccion", "Deteccion", _niveles(
    (1, "Evidente", "El operador lo nota de inmediato, sin instrumento."),
    (2, "Facil", "Se detecta en la ronda o inspeccion de rutina."),
    (3, "Media", "Requiere instrumento o tecnica a condicion."),
    (4, "Dificil", "Solo se detecta desarmando."),
    (5, "Oculta", "No se detecta hasta que falla."),
))


def _tabla_prioridad() -> dict[tuple[int, ...], str]:
    """Prioridad de accion al estilo AIAG-VDA: severidad manda, sin multiplicar.

    Orden de los factores: (severidad, frecuencia, deteccion).
    """
    tabla: dict[tuple[int, ...], str] = {}
    for s in range(1, 6):
        for f in range(1, 6):
            for d in range(1, 6):
                if s >= 5:
                    # Severidad critica: alta salvo que sea remota Y evidente.
                    etiqueta = "baja" if (f <= 1 and d <= 1) else "alta"
                elif s == 4:
                    etiqueta = "alta" if f >= 3 or d >= 4 else "media"
                elif s == 3:
                    etiqueta = "alta" if f >= 4 and d >= 4 else (
                        "media" if f >= 3 or d >= 3 else "baja")
                else:
                    etiqueta = "media" if f >= 5 and d >= 4 else "baja"
                tabla[(s, f, d)] = etiqueta
    return tabla


PRIORIDAD_EJEMPLO = Metodo(
    nombre="Prioridad de accion (EJEMPLO)",
    version="1",
    factores=(SEVERIDAD_EJEMPLO, FRECUENCIA_EJEMPLO, DETECCION_EJEMPLO),
    combinacion="matriz",
    tabla=_tabla_prioridad(),
    advertencia=("Escala de EJEMPLO. Reescriba los descriptores de cada nivel "
                 "con lo que significan en su faena antes de usarla para "
                 "priorizar trabajo."),
    fuente="Estructura al estilo AIAG-VDA 2019 (prioridad de accion).",
)

RPN_EJEMPLO = Metodo(
    nombre="RPN clasico (EJEMPLO)",
    version="1",
    factores=(SEVERIDAD_EJEMPLO, FRECUENCIA_EJEMPLO, DETECCION_EJEMPLO),
    combinacion="producto",
    umbrales=((60, "alta"), (25, "media"), (1, "baja")),
    advertencia=ADVERTENCIA_RPN,
    fuente="RPN clasico, conservado por compatibilidad con procedimientos que lo exigen.",
)

EJEMPLOS = {m.nombre: m for m in (PRIORIDAD_EJEMPLO, RPN_EJEMPLO)}
