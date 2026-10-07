"""Los indicadores de RCM, TPM y confiabilidad. Nada se calcula sin dato.

La regla que gobierna este modulo entero: **`None` no es cero.** Un tablero
que muestra 0 % de cumplimiento cuando todavia no hay ninguna ronda esta
diciendo «lo hicieron mal» cuando lo que pasa es que no hay dato, y esa es
la forma mas rapida de que un tablero deje de mirarse.

Asi que cada indicador que no se puede calcular devuelve `None`, y
`a_dict()` lo conserva como `null` en vez de rellenarlo. Quien pinte la
pantalla tiene que distinguir las dos cosas.

Lo de confiabilidad —MTBF, disponibilidad, recurrencia— no se recalcula
aqui: sale de `prediccion`, que ya lo hace sobre el mismo historial y ya
declara sus minimos (con una sola aparicion no hay intervalo, hay una
fecha). Duplicarlo con otra formula daria dos numeros distintos para la
misma pregunta, que es peor que no tener ninguno.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import prediccion as _prediccion
from .criticidad import NO_EVALUADA
from .decision import ESTRATEGIAS, PROACTIVAS


def _fraccion(parte: int, total: int) -> float | None:
    return (parte / total) if total else None


@dataclass
class TableroRCM:
    """Lo que un jefe de confiabilidad mira del analisis."""

    activos_analizados: int = 0
    funciones: int = 0
    fallas_funcionales: int = 0
    modos: int = 0
    modos_graves: int = 0
    modos_ocultos: int = 0
    modos_validados: int = 0
    modos_sin_criticidad: int = 0
    modos_recurrentes: int = 0
    por_estrategia: dict[str, int] = field(default_factory=dict)
    analisis_completos: int = 0
    # Fraccion de analisis que contestan las siete preguntas. `None` sin
    # ningun analisis cargado.
    completitud: float | None = None

    def a_dict(self) -> dict:
        return {
            "activos_analizados": self.activos_analizados,
            "funciones": self.funciones,
            "fallas_funcionales": self.fallas_funcionales,
            "modos": self.modos, "modos_graves": self.modos_graves,
            "modos_ocultos": self.modos_ocultos,
            "modos_validados": self.modos_validados,
            "modos_sin_criticidad": self.modos_sin_criticidad,
            "modos_recurrentes": self.modos_recurrentes,
            "por_estrategia": dict(self.por_estrategia),
            "analisis_completos": self.analisis_completos,
            "completitud": self.completitud,
        }


def rcm(analisis_lista, decisiones_por_activo=None) -> TableroRCM:
    """El tablero RCM sobre uno o varios analisis.

    `decisiones_por_activo` es `{codigo_activo: Decisiones}`. Sin el, el
    reparto por estrategia queda en cero y la completitud no puede dar
    «completo», que es correcto: sin decisiones faltan las Q6 y Q7.
    """
    from .rcm import completitud as _completitud

    analisis_lista = list(analisis_lista)
    decisiones_por_activo = decisiones_por_activo or {}
    t = TableroRCM(por_estrategia={k: 0 for k in ESTRATEGIAS})
    completos = 0

    for a in analisis_lista:
        t.activos_analizados += 1
        t.funciones += len(a.funciones)
        t.fallas_funcionales += len(a.fallas)
        t.modos += len(a.modos)
        t.modos_graves += len(a.modos_graves())
        t.modos_ocultos += len(a.modos_ocultos())
        t.modos_validados += sum(1 for m in a.modos if m.estado == "validado")
        t.modos_sin_criticidad += sum(
            1 for m in a.modos if m.criticidad.etiqueta == NO_EVALUADA)
        # Recurrente = contrastado contra el historial y visto mas de una vez.
        # Los que nadie contrasto no cuentan como «no recurrentes»: no se
        # saben, y `frecuencia_historica is None` lo dice.
        t.modos_recurrentes += sum(
            1 for m in a.modos
            if m.frecuencia_historica is not None and m.frecuencia_historica > 1)

        d = decisiones_por_activo.get(a.activo.codigo)
        if d is not None:
            for clave, n in d.reparto().items():
                t.por_estrategia[clave] += n
        if _completitud(a, getattr(d, "por_modo", {}) if d else {}).completo:
            completos += 1

    t.analisis_completos = completos
    t.completitud = _fraccion(completos, len(analisis_lista))
    return t


@dataclass
class TableroTPM:
    """Lo que un supervisor de produccion mira del pilar 1."""

    checklists: int = 0
    ejecuciones: int = 0
    ejecuciones_completas: int = 0
    ejecuciones_sospechosas: int = 0
    cumplimiento: float | None = None
    por_clase: dict[str, int] = field(default_factory=dict)
    puntos_nunca_vistos: int = 0
    anomalias: int = 0
    anomalias_abiertas: int = 0
    anomalias_cerradas: int = 0
    anomalias_sin_enlazar: int = 0
    dias_medios_de_cierre: float | None = None
    reincidentes: int = 0

    def a_dict(self) -> dict:
        return {
            "checklists": self.checklists, "ejecuciones": self.ejecuciones,
            "ejecuciones_completas": self.ejecuciones_completas,
            "ejecuciones_sospechosas": self.ejecuciones_sospechosas,
            "cumplimiento": self.cumplimiento,
            "por_clase": dict(self.por_clase),
            "puntos_nunca_vistos": self.puntos_nunca_vistos,
            "anomalias": self.anomalias,
            "anomalias_abiertas": self.anomalias_abiertas,
            "anomalias_cerradas": self.anomalias_cerradas,
            "anomalias_sin_enlazar": self.anomalias_sin_enlazar,
            "dias_medios_de_cierre": self.dias_medios_de_cierre,
            "reincidentes": self.reincidentes,
        }


def tpm(checklists, ejecuciones, anomalias=(), hoy=None) -> TableroTPM:
    """El tablero del mantenimiento autonomo.

    El cumplimiento se calcula por pauta y se agrega: una planta con una
    pauta de cinco puntos y otra de veinte no puede promediar rondas como si
    fueran la misma cosa, pero si puede contar cuantas se completaron.
    """
    from . import tpm as _tpm
    from .anomalia import salud as _salud

    checklists = list(checklists)
    ejecuciones = list(ejecuciones)
    por_id = {c.id: c for c in checklists}

    t = TableroTPM(checklists=len(checklists), ejecuciones=len(ejecuciones),
                   por_clase={c: 0 for c in _tpm.CLASES})
    nunca = 0
    for c in checklists:
        suyas = [e for e in ejecuciones if e.checklist_id == c.id]
        r = _tpm.cumplimiento(suyas, c)
        t.ejecuciones_completas += r.completas
        t.ejecuciones_sospechosas += r.sospechosas
        for clave, n in r.por_clase.items():
            t.por_clase[clave] += n
        nunca += len(r.nunca_vistos)
    # Las ejecuciones cuya pauta no esta cargada no se cuentan como
    # incompletas: no se pueden evaluar, y restarlas del denominador es mas
    # honesto que darlas por fallidas.
    evaluables = sum(1 for e in ejecuciones if e.checklist_id in por_id)
    t.puntos_nunca_vistos = nunca
    t.cumplimiento = _fraccion(t.ejecuciones_completas, evaluables)

    s = _salud(anomalias, hoy)
    t.anomalias = s.total
    t.anomalias_abiertas = s.abiertas
    t.anomalias_cerradas = s.cerradas
    t.anomalias_sin_enlazar = s.sin_enlazar
    t.dias_medios_de_cierre = s.dias_medios_de_cierre
    t.reincidentes = len(s.reincidentes)
    return t


@dataclass
class TableroConfiabilidad:
    """MTBF, recurrencia y reparaciones. Todo sale de `prediccion` y `ot`."""

    equipos: int = 0
    # equipo -> MTBF en dias. Solo los que tienen suficientes fallas.
    mtbf_dias: dict[str, int] = field(default_factory=dict)
    mttr_horas: float | None = None
    disponibilidad: float | None = None
    fallas: int = 0
    reincidencias_vencidas: int = 0

    def a_dict(self) -> dict:
        return {"equipos": self.equipos, "mtbf_dias": dict(self.mtbf_dias),
                "mttr_horas": self.mttr_horas,
                "disponibilidad": self.disponibilidad, "fallas": self.fallas,
                "reincidencias_vencidas": self.reincidencias_vencidas}


def confiabilidad(indice, equipos=None, hoy=None) -> TableroConfiabilidad:
    """Lo que el historial dice de la flota.

    No recalcula nada: llama a `prediccion`, que ya declara sus minimos. Con
    menos de dos apariciones no hay intervalo, y eso se respeta aqui tambien
    —el equipo simplemente no aparece en `mtbf_dias`—.

    `mttr_horas` y `disponibilidad` quedan en `None` a proposito: FixMate
    registra cuando ocurrio una falla, no cuanto duro la reparacion ni
    cuantas horas estuvo detenida la maquina. Calcularlas exigiria inventar
    la duracion, y un MTTR inventado se usa para dimensionar un taller.
    """
    t = TableroConfiabilidad()
    equipos = list(equipos) if equipos is not None else sorted(
        {str(f.metadatos.get("codigo_equipo") or "")
         for f in (getattr(indice, "fragmentos", []) or [])
         if f.metadatos.get("codigo_equipo")})

    for codigo in equipos:
        eventos = _prediccion.eventos(indice, codigo)
        if not eventos:
            continue
        t.equipos += 1
        t.fallas += len(eventos)
        m = _prediccion.mtbf(eventos)
        if m is not None:
            t.mtbf_dias[codigo] = m
        t.reincidencias_vencidas += sum(
            1 for r in _prediccion.reincidencias(eventos, hoy) if r.vencida)
    return t


def completo(analisis_lista=(), decisiones=None, checklists=(), ejecuciones=(),
             anomalias=(), indice=None, hoy=None) -> dict:
    """Los tres tableros juntos, como los pide el §16."""
    salida = {
        "rcm": rcm(analisis_lista, decisiones).a_dict(),
        "tpm": tpm(checklists, ejecuciones, anomalias, hoy).a_dict(),
    }
    salida["confiabilidad"] = (confiabilidad(indice, hoy=hoy).a_dict()
                               if indice is not None else None)
    return salida
