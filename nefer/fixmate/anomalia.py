"""La anomalia TPM, y el puente automatico hacia el modo de falla RCM.

Una anomalia es lo que el operador encontro y no pudo o no debio resolver en
el acto. Es la unidad de trabajo que el mantenimiento autonomo le entrega al
resto del sistema, y por eso tiene que poder viajar hasta el final: anomalia
-> caso de diagnostico -> modo de falla -> tarea -> cierre -> aprendizaje.

----------------------------------------------------------------------------
COMO SE ENGANCHA CON RCM, Y CUANDO NO SE ENGANCHA

El encargo pide que la conexion sea automatica «cuando exista suficiente
informacion». La frase importante es la ultima, y aqui define el diseño.

El enganche usa lo que FixMate ya sabe hacer: el texto de la anomalia pasa
por `catalogo.clasificar()`, que devuelve un codigo ISO 14224 o nada. Si
devuelve codigo y algun modo de falla del analisis RCM declara ese mismo
codigo, se enlazan. Si el catalogo no alcanza, o si ningun modo declara ese
codigo, la anomalia queda SIN ENLAZAR y eso se ve.

Lo que no se hace, en ningun caso: elegir el modo de falla «mas parecido».
Una anomalia enlazada al modo equivocado contamina el MTBF por modo, la
frecuencia historica del analisis y la decision de estrategia que sale de
ahi. Un enlace que falta se ve; uno equivocado se suma con los demas.

El catalogo ya se niega a adivinar por su cuenta —no tiene categoria «Otro»
y en empate no elige—, asi que heredar su criterio es gratis y es correcto.
----------------------------------------------------------------------------

Y la severidad: la pone el operador entre tres valores que se distinguen por
lo que OBLIGAN a hacer, no por cuanto preocupan. Una escala de cinco obliga
a decidir entre «alta» y «muy alta», que es una decision que nadie puede
defender y que termina resolviendose por costumbre.

Sobre la fotografia: `evidencia` guarda referencias a archivos para que la
arquitectura este lista. FixMate NO diagnostica por imagen y nada de esto lo
acerca a hacerlo; la foto es un adjunto para que un humano la mire.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from . import catalogo as _catalogo

# Tres, y se distinguen por lo que obligan a hacer.
SEVERIDADES = {
    "detiene": "Se detiene la maquina ahora",
    "programable": "Se atiende en la proxima ventana",
    "oportunidad": "Cuando se abra una ocasion",
}

ESTADOS = ("abierta", "en_proceso", "cerrada", "descartada")


class ErrorAnomalia(ValueError):
    """La anomalia no se puede registrar tal como viene."""


@dataclass
class Anomalia:
    """Lo que el operador encontro. El texto libre no se normaliza nunca."""

    id: str
    activo_codigo: str
    descripcion: str
    severidad: str = "programable"
    # De donde vino.
    ejecucion_id: str = ""
    punto_id: str = ""
    componente: str = ""
    condicion_observada: str = ""
    detectada_por: str = ""
    fecha: str = ""
    # Los dos enlaces hacia RCM. Vacios mientras no haya con que llenarlos.
    codigo_catalogo: str = ""
    modo_falla_id: str = ""
    # Rutas o ids de adjuntos. No hay diagnostico por imagen: ver encabezado.
    evidencia: tuple[str, ...] = ()
    estado: str = "abierta"
    responsable: str = ""
    accion: str = ""
    fecha_cierre: str = ""
    # El caso de FixMate que se abrio desde esta anomalia, si se abrio.
    codigo_ot: str = ""

    def __post_init__(self):
        if not str(self.descripcion).strip():
            raise ErrorAnomalia(
                "la anomalia necesita descripcion: es lo unico que el proximo "
                "va a leer.")
        if self.severidad not in SEVERIDADES:
            raise ErrorAnomalia(
                f"severidad «{self.severidad}» desconocida: "
                f"use {', '.join(SEVERIDADES)}.")
        if self.estado not in ESTADOS:
            raise ErrorAnomalia(f"estado «{self.estado}» desconocido.")
        self.fecha = self.fecha or _dt.date.today().isoformat()

    @property
    def abierta(self) -> bool:
        return self.estado in ("abierta", "en_proceso")

    @property
    def enlazada(self) -> bool:
        """Si llego hasta un modo de falla concreto del analisis RCM."""
        return bool(self.modo_falla_id)

    def dias_abierta(self, hoy: _dt.date | None = None) -> int | None:
        hoy = hoy or _dt.date.today()
        try:
            desde = _dt.date.fromisoformat(self.fecha)
        except ValueError:
            return None
        hasta = hoy
        if self.fecha_cierre:
            try:
                hasta = _dt.date.fromisoformat(self.fecha_cierre)
            except ValueError:
                pass
        return (hasta - desde).days

    def cerrar(self, accion: str, responsable: str = "",
               hoy: _dt.date | None = None) -> "Anomalia":
        if not str(accion).strip():
            raise ErrorAnomalia(
                "no se cierra una anomalia sin decir que se hizo. Una anomalia "
                "cerrada en blanco es una anomalia borrada.")
        self.estado = "cerrada"
        self.accion = accion
        self.responsable = responsable or self.responsable
        self.fecha_cierre = (hoy or _dt.date.today()).isoformat()
        return self

    def a_dict(self) -> dict:
        return {
            "id": self.id, "activo_codigo": self.activo_codigo,
            "descripcion": self.descripcion, "severidad": self.severidad,
            "ejecucion_id": self.ejecucion_id, "punto_id": self.punto_id,
            "componente": self.componente,
            "condicion_observada": self.condicion_observada,
            "detectada_por": self.detectada_por, "fecha": self.fecha,
            "codigo_catalogo": self.codigo_catalogo,
            "modo_falla_id": self.modo_falla_id,
            "evidencia": list(self.evidencia), "estado": self.estado,
            "responsable": self.responsable, "accion": self.accion,
            "fecha_cierre": self.fecha_cierre, "codigo_ot": self.codigo_ot,
        }


# ---------------------------------------------------- de la ronda al dato

def desde_item(ejecucion, item, checklist, cat=None,
               hoy: _dt.date | None = None) -> Anomalia | None:
    """La anomalia que sale de un punto NOK. `None` para cualquier otro caso.

    Un `sin_acceso` NO genera anomalia: no se encontro un defecto, se
    encontro que no se pudo mirar. Eso es un problema de la pauta o de la
    maquina, y sale por el cumplimiento, no por una anomalia colgada de un
    punto que nadie vio.
    """
    if item.resultado != "nok":
        return None
    punto = checklist.punto(item.punto_id)
    if punto is None:
        raise ErrorAnomalia(
            f"el punto {item.punto_id} no esta en la pauta {checklist.id}.")

    a = Anomalia(
        id=f"{ejecucion.id}.{item.punto_id}",
        activo_codigo=ejecucion.activo_codigo,
        descripcion=item.observacion.strip() or punto.punto,
        # Fuera del alcance del operador significa que hace falta el tecnico:
        # se decidio en frio al escribir la pauta, no en campo.
        severidad="programable" if punto.alcance_operador else "detiene",
        ejecucion_id=ejecucion.id,
        punto_id=punto.id,
        componente=punto.punto,
        condicion_observada=punto.criterio,
        detectada_por=ejecucion.operador,
        fecha=(hoy or _dt.date.today()).isoformat(),
        # Si la pauta ya declara el codigo, se hereda: es el mismo dato.
        codigo_catalogo=punto.codigo_catalogo,
        modo_falla_id=punto.modo_falla_id,
    )
    if not a.codigo_catalogo:
        clasificar(a, cat)
    return a


def clasificar(a: Anomalia, cat=None) -> Anomalia:
    """Codifica el texto con el catalogo. Si no alcanza, lo deja vacio.

    Hereda el criterio del catalogo, que no adivina: sin suficientes pistas o
    con empate, devuelve `None` y la anomalia se queda sin codigo. Un codigo
    equivocado ensucia la cuenta de toda la flota; uno que falta se ve.
    """
    cat = cat or _catalogo.Catalogo()
    texto = " ".join(x for x in (a.descripcion, a.componente) if x)
    entrada = cat.clasificar(texto)
    if entrada is not None:
        a.codigo_catalogo = entrada.codigo
    return a


def enlazar(a: Anomalia, analisis) -> Anomalia:
    """Une la anomalia con el modo de falla RCM que declara su mismo codigo.

    Exige coincidencia EXACTA de codigo y de activo. No busca el modo «mas
    parecido»: una anomalia enlazada al modo equivocado contamina el MTBF por
    modo y la decision de estrategia que sale de ahi.

    Si dos modos del mismo analisis declaran el mismo codigo, no se elige:
    el analisis tiene una ambiguedad que hay que resolver en el analisis, no
    aqui a la suerte.
    """
    if not a.codigo_catalogo or a.modo_falla_id:
        return a
    if analisis is None or analisis.activo.codigo != a.activo_codigo:
        return a
    candidatos = [m for m in analisis.modos
                  if m.codigo_catalogo == a.codigo_catalogo]
    if len(candidatos) == 1:
        a.modo_falla_id = candidatos[0].id
    return a


def desde_ejecucion(ejecucion, checklist, analisis=None, cat=None,
                    hoy: _dt.date | None = None) -> list[Anomalia]:
    """Todas las anomalias de una ronda, ya codificadas y enlazadas si se pudo."""
    salida = []
    for item in ejecucion.items:
        a = desde_item(ejecucion, item, checklist, cat, hoy)
        if a is None:
            continue
        enlazar(a, analisis)
        salida.append(a)
        if a.id not in ejecucion.anomalias:
            ejecucion.anomalias.append(a.id)
    return salida


# ------------------------------------------------------------ indicadores

@dataclass(frozen=True)
class SaludAnomalias:
    """Lo que mide si el pilar 1 funciona: no cuantas se abrieron, cuantas se cerraron."""

    total: int
    abiertas: int
    cerradas: int
    sin_enlazar: int
    dias_medios_de_cierre: float | None
    # Componentes con mas de una anomalia: la reincidencia es la señal de que
    # se cerro el sintoma y no la causa.
    reincidentes: tuple[tuple[str, int], ...] = ()

    def a_dict(self) -> dict:
        return {"total": self.total, "abiertas": self.abiertas,
                "cerradas": self.cerradas, "sin_enlazar": self.sin_enlazar,
                "dias_medios_de_cierre": self.dias_medios_de_cierre,
                "reincidentes": [list(r) for r in self.reincidentes]}


def salud(anomalias, hoy: _dt.date | None = None) -> SaludAnomalias:
    """Contar las colocadas mide entusiasmo del primer mes. Esto mide otra cosa."""
    anomalias = list(anomalias)
    cerradas = [a for a in anomalias if a.estado == "cerrada"]
    dias = [d for d in (a.dias_abierta(hoy) for a in cerradas) if d is not None]

    cuenta: dict[str, int] = {}
    for a in anomalias:
        clave = a.codigo_catalogo or a.componente
        if clave:
            cuenta[clave] = cuenta.get(clave, 0) + 1

    return SaludAnomalias(
        total=len(anomalias),
        abiertas=sum(1 for a in anomalias if a.abierta),
        cerradas=len(cerradas),
        sin_enlazar=sum(1 for a in anomalias if not a.enlazada),
        dias_medios_de_cierre=(sum(dias) / len(dias)) if dias else None,
        reincidentes=tuple(sorted(((k, n) for k, n in cuenta.items() if n > 1),
                                  key=lambda kv: -kv[1])),
    )
