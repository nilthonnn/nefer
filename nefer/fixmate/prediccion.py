"""Diagnostico predictivo con lo que la flota ya registro.

No hay sensores en estas maquinas. Hay dos cosas: la fecha de cada falla y el
horometro que el tecnico anota en cada acta. Con eso se contestan las tres
preguntas que un jefe de taller hace de verdad, y no se contesta ninguna mas:

- **¿A que ritmo se usa este equipo?** Horas por dia, de la pendiente entre
  dos lecturas de horometro con fecha. De ahi sale cuando llega al proximo
  intervalo de mantenimiento, en dias y no en horas: «faltan 118 horas» no se
  puede poner en un calendario, «llega el 3 de octubre» si.
- **¿Que le vuelve a pasar?** Cada causa que aparecio dos veces o mas tiene un
  intervalo medio entre apariciones. Si desde la ultima paso mas tiempo que
  ese intervalo, la falla esta vencida y se dice.
- **¿Que repuestos hay que tener?** Los que consumieron las causas
  reincidentes de esa familia de equipos.

Todo lleva el numero de casos en que se apoya, y nada se calcula con uno solo:
con una sola aparicion no hay intervalo, hay una fecha. La diferencia importa
cuando alguien va a comprar un repuesto por lo que diga esto.
"""

from __future__ import annotations

import datetime as _dt
import re
import statistics
from dataclasses import asdict, dataclass, field

from . import texto as _texto

# Dos apariciones dan un intervalo; tres lo hacen algo mas que una resta.
MINIMO_PARA_INTERVALO = 2
MINIMO_PARA_RITMO = 2

# Intervalos de servicio habituales en maquinaria; el proximo se calcula
# sobre el que toque. Se pueden pasar otros a `pronostico()`.
INTERVALOS_SERVICIO = (250, 500, 1000, 2000)


@dataclass
class Evento:
    """Algo que le paso a un equipo en una fecha."""

    fecha: _dt.date
    equipo: str
    causa: str = ""
    referencia: str = ""
    horometro: float | None = None
    repuestos: list[str] = field(default_factory=list)


@dataclass
class Uso:
    """A que ritmo se usa el equipo, segun sus horometros con fecha."""

    lecturas: int
    horometro: float
    fecha: str
    ritmo_horas_dia: float
    dias_observados: int
    # Tramos en los que el horometro anotado bajo: dato para revisar.
    retrocesos: list[str] = field(default_factory=list)

    def a_dict(self) -> dict:
        return asdict(self)


@dataclass
class Reincidencia:
    """Una causa que ya volvio, con cada cuanto vuelve."""

    causa: str
    casos: int
    ultima: str
    dias_desde_la_ultima: int
    intervalo_medio_dias: int | None = None
    proxima_estimada: str | None = None
    vencida: bool = False
    repuestos: list[str] = field(default_factory=list)

    def a_dict(self) -> dict:
        return asdict(self)


@dataclass
class Servicio:
    """Cuando llega el equipo al proximo intervalo de mantenimiento."""

    proximo_intervalo_horas: int
    horas_faltantes: float
    dias_estimados: int
    fecha_estimada: str

    def a_dict(self) -> dict:
        return asdict(self)


@dataclass
class Pronostico:
    """Lo que se puede decir hoy de un equipo, y con cuanto respaldo."""

    equipo: str
    eventos: int
    uso: Uso | None = None
    servicio: Servicio | None = None
    reincidencias: list[Reincidencia] = field(default_factory=list)
    mtbf_dias: int | None = None
    repuestos_sugeridos: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def a_dict(self) -> dict:
        return {
            "equipo": self.equipo,
            "eventos": self.eventos,
            "uso": self.uso.a_dict() if self.uso else None,
            "servicio": self.servicio.a_dict() if self.servicio else None,
            "reincidencias": [r.a_dict() for r in self.reincidencias],
            "mtbf_dias": self.mtbf_dias,
            "repuestos_sugeridos": self.repuestos_sugeridos,
            "avisos": self.avisos,
        }


# ---------------------------------------------------------------- lectura

def _fecha(valor) -> _dt.date | None:
    """Acepta lo que traen las hojas de calculo: ISO, d/m/a y datetime."""
    if isinstance(valor, _dt.datetime):
        return valor.date()
    if isinstance(valor, _dt.date):
        return valor
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        return _dt.date.fromisoformat(texto[:10])
    except ValueError:
        pass
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", texto)
    if m:
        dia, mes, anio = (int(g) for g in m.groups())
        anio += 2000 if anio < 100 else 0
        try:
            return _dt.date(anio, mes, dia)
        except ValueError:
            return None
    return None


def _numero(valor) -> float | None:
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(valor))
    return float(m.group(0).replace(",", ".")) if m else None


def _causa_de(meta: dict) -> str:
    """Que cuenta como falla de este equipo, y que no.

    Una causa raiz confirmada siempre cuenta. Un componente observado o
    dañado en un acta tambien: es una averia, aunque nadie abriera una orden.
    Un consumible que no retorno, no: es una recuperacion que se factura, y
    contarla como falla hincha el MTBF y llena de extintores la lista de lo
    que le vuelve a pasar a la maquina.
    """
    causa = str(meta.get("causa_raiz") or "").strip()
    if causa:
        return causa
    item = str(meta.get("item") or "").strip()
    if item and meta.get("clase") == "componente":
        return f"Componente {str(meta.get('estado') or '').strip()}: {item}".strip()
    return ""


def eventos(indice, equipo: str | None = None) -> list[Evento]:
    """Los hechos fechados del indice, de un equipo o de toda la flota."""
    buscado = _texto.normalizar(equipo) if equipo else None
    encontrados = []
    for fragmento in getattr(indice, "fragmentos", []):
        meta = fragmento.metadatos
        codigo = str(meta.get("codigo_equipo") or "").strip()
        if buscado and _texto.normalizar(codigo) != buscado:
            continue
        fecha = _fecha(meta.get("fecha"))
        if fecha is None:
            continue
        encontrados.append(Evento(
            fecha=fecha,
            equipo=codigo,
            causa=_causa_de(meta),
            referencia=str(meta.get("codigo_ot") or meta.get("n_acta") or fragmento.id),
            horometro=_numero(meta.get("horometro")),
            repuestos=[str(r) for r in (meta.get("repuestos") or [])],
        ))
    encontrados.sort(key=lambda e: e.fecha)
    return encontrados


# ------------------------------------------------------------------ ritmo

def uso_de(eventos_equipo: list[Evento]) -> Uso | None:
    """Horas por dia entre la primera y la ultima lectura de horometro."""
    lecturas = [(e.fecha, e.horometro) for e in eventos_equipo
                if e.horometro is not None and e.horometro > 0]
    # Una misma fecha puede traer dos lecturas (despacho y recepcion); se
    # queda la mayor, que es la del final del dia.
    por_fecha: dict[_dt.date, float] = {}
    for fecha, horas in lecturas:
        por_fecha[fecha] = max(horas, por_fecha.get(fecha, 0.0))
    if len(por_fecha) < MINIMO_PARA_RITMO:
        return None

    # Un horometro no retrocede: si lo hace, alguien anoto mal. Se suman solo
    # los tramos que avanzan, en vez de restar la primera lectura de la ultima
    # y sacar un ritmo que no vivio ninguna maquina.
    fechas = sorted(por_fecha)
    avance = 0.0
    dias = 0
    retrocesos = []
    for antes, despues in zip(fechas, fechas[1:]):
        salto = por_fecha[despues] - por_fecha[antes]
        if salto < 0:
            retrocesos.append((antes.isoformat(), despues.isoformat()))
            continue
        avance += salto
        dias += (despues - antes).days
    if dias <= 0 or avance <= 0:
        return None
    # Se informa la lectura mas alta con la fecha en que se tomo: un
    # horometro no baja, asi que esa es la unica que puede seguir siendo
    # cierta si otra se anoto mal.
    mayor = max(fechas, key=lambda f: por_fecha[f])
    return Uso(
        lecturas=len(por_fecha),
        horometro=round(por_fecha[mayor], 1),
        fecha=mayor.isoformat(),
        ritmo_horas_dia=round(avance / dias, 2),
        dias_observados=dias,
        retrocesos=[f"{a} → {b}" for a, b in retrocesos],
    )


def servicio_de(uso: Uso | None, hoy: _dt.date | None = None,
                intervalos=INTERVALOS_SERVICIO) -> Servicio | None:
    """Cuando llega el equipo al siguiente intervalo de mantenimiento."""
    if uso is None or uso.ritmo_horas_dia <= 0:
        return None
    hoy = hoy or _dt.date.today()
    # Al horometro de la ultima lectura se le suma lo andado desde entonces.
    corridos = (hoy - _dt.date.fromisoformat(uso.fecha)).days
    horas_hoy = uso.horometro + max(corridos, 0) * uso.ritmo_horas_dia

    proximos = [i * (int(horas_hoy // i) + 1) for i in intervalos]
    objetivo = min(proximos)
    faltan = objetivo - horas_hoy
    dias = max(int(round(faltan / uso.ritmo_horas_dia)), 0)
    return Servicio(
        proximo_intervalo_horas=int(objetivo),
        horas_faltantes=round(faltan, 1),
        dias_estimados=dias,
        fecha_estimada=(hoy + _dt.timedelta(days=dias)).isoformat(),
    )


# ----------------------------------------------------------- reincidencia

def reincidencias(eventos_equipo: list[Evento],
                  hoy: _dt.date | None = None) -> list[Reincidencia]:
    """Causas que ya volvieron, con cada cuanto vuelven y si estan vencidas."""
    hoy = hoy or _dt.date.today()
    from .aprendizaje import agrupar_causas

    conocidas = [e for e in eventos_equipo if e.causa]
    mapa = agrupar_causas(e.causa for e in conocidas)

    por_causa: dict[str, list[Evento]] = {}
    for evento in conocidas:
        por_causa.setdefault(mapa[evento.causa], []).append(evento)

    salida = []
    for causa, sucesos in por_causa.items():
        fechas = sorted({e.fecha for e in sucesos})
        ultima = fechas[-1]
        desde = (hoy - ultima).days
        intervalo = None
        proxima = None
        vencida = False
        if len(fechas) >= MINIMO_PARA_INTERVALO:
            huecos = [(b - a).days for a, b in zip(fechas, fechas[1:]) if (b - a).days > 0]
            if huecos:
                intervalo = int(round(statistics.fmean(huecos)))
                proxima = (ultima + _dt.timedelta(days=intervalo)).isoformat()
                vencida = desde > intervalo
        repuestos = []
        for suceso in sucesos:
            for repuesto in suceso.repuestos:
                if repuesto not in repuestos:
                    repuestos.append(repuesto)
        salida.append(Reincidencia(
            causa=causa, casos=len(sucesos), ultima=ultima.isoformat(),
            dias_desde_la_ultima=desde, intervalo_medio_dias=intervalo,
            proxima_estimada=proxima, vencida=vencida, repuestos=repuestos))

    # Primero lo vencido, luego lo que mas se repite, luego lo mas reciente.
    salida.sort(key=lambda r: (not r.vencida, -r.casos, r.dias_desde_la_ultima))
    return salida


def mtbf(eventos_equipo: list[Evento]) -> int | None:
    """Dias medios entre fallas, empirico. None con menos de dos fechas."""
    fechas = sorted({e.fecha for e in eventos_equipo if e.causa})
    if len(fechas) < 2:
        return None
    return int(round((fechas[-1] - fechas[0]).days / (len(fechas) - 1)))


# ------------------------------------------------------------- pronostico

def pronostico(indice, equipo: str, hoy: _dt.date | None = None) -> Pronostico:
    """Todo lo que se puede decir de un equipo, con sus avisos."""
    hoy = hoy or _dt.date.today()
    propios = eventos(indice, equipo)
    parte = Pronostico(equipo=equipo, eventos=len(propios))
    if not propios:
        parte.avisos.append(
            f"No hay nada fechado de {equipo} en el indice. Sin fechas no hay "
            "prediccion; con una sola tampoco.")
        return parte

    parte.uso = uso_de(propios)
    parte.servicio = servicio_de(parte.uso, hoy)
    parte.reincidencias = reincidencias(propios, hoy)
    parte.mtbf_dias = mtbf(propios)

    for reincidencia in parte.reincidencias:
        if reincidencia.vencida or reincidencia.casos >= MINIMO_PARA_INTERVALO:
            for repuesto in reincidencia.repuestos:
                if repuesto not in parte.repuestos_sugeridos:
                    parte.repuestos_sugeridos.append(repuesto)

    if parte.uso is None:
        parte.avisos.append(
            "Sin dos lecturas de horometro con fecha distinta no se puede "
            "estimar el ritmo de uso ni el proximo servicio.")
    elif parte.uso.retrocesos:
        parte.avisos.append(
            "El horometro anotado baja entre "
            + "; ".join(parte.uso.retrocesos)
            + ". Una maquina no desanda horas: revise esas actas. El ritmo "
              "se calculo solo con los tramos que avanzan.")
    if not any(r.intervalo_medio_dias for r in parte.reincidencias):
        parte.avisos.append(
            "Ninguna causa se repitio todavia en este equipo: lo que hay son "
            "hechos sueltos, no un patron.")
    if len(propios) < 4:
        plural = "s" if len(propios) != 1 else ""
        parte.avisos.append(
            f"Solo {len(propios)} registro{plural} de este equipo. Tomelo como "
            "lo que es: una señal debil.")
    return parte


def flota(indice, hoy: _dt.date | None = None, limite: int = 5) -> dict:
    """Vista de toda la flota: que falla mas y que equipo da mas trabajo."""
    hoy = hoy or _dt.date.today()
    todos = eventos(indice)
    if not todos:
        return {"equipos": [], "causas": [], "eventos": 0,
                "avisos": ["No hay eventos fechados en el indice."]}

    por_equipo: dict[str, list[Evento]] = {}
    for evento in todos:
        if evento.equipo:
            por_equipo.setdefault(evento.equipo, []).append(evento)

    equipos = []
    for codigo, sucesos in por_equipo.items():
        equipos.append({"equipo": codigo, "eventos": len(sucesos),
                        "mtbf_dias": mtbf(sucesos),
                        "ultima": max(e.fecha for e in sucesos).isoformat()})
    equipos.sort(key=lambda e: (-e["eventos"], e["equipo"]))

    causas = [r.a_dict() for r in reincidencias(todos, hoy)]
    return {
        "eventos": len(todos),
        "equipos": equipos[:limite],
        "causas": causas[:limite],
        "avisos": ([] if len(todos) >= 8 else
                   [f"Solo {len(todos)} eventos fechados en toda la flota: "
                    "cualquier orden aqui es provisional."]),
    }
