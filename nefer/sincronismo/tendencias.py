"""Lo predictivo del sincronismo: derivas que avisan antes del disparo.

Un gobernador que se gasta no deja de sincronizar de un dia para otro:
tarda cada vez mas. Un AVR que pierde su estatismo no dispara la primera
semana: el desbalance de kVAr crece de a poco. Esas derivas estan en el
registro del controlador (o en la hoja que se llena en cada ronda), y una
recta sobre ellas dice CUANDO cruzan el limite, en fecha.

El registro es un CSV de cuatro columnas, lo mas facil de llenar a mano o de
exportar de cualquier controlador:

    fecha,equipo,variable,valor
    2026-09-01,GE-01,tiempo_sincronizacion_s,12.5
    2026-09-03,GE-02,alarma,32 potencia inversa

Las variables numericas se proyectan contra su limite; `alarma` cuenta
reincidencias. Reglas:

- Menos de MINIMO_PUNTOS lecturas no se proyectan: se dice cuantas hay.
- Una recta que explica poco (R² bajo) no se proyecta: se dice que hay
  dispersion, no tendencia. Proyectar ruido es inventar una fecha.
- Una alarma vista una sola vez es una fecha, no una reincidencia.
"""

from __future__ import annotations

import csv
import datetime as _dt
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

MINIMO_PUNTOS = 4
R2_MINIMO = 0.5
VENTANA_ALARMAS_DIAS = 90

# Limites por defecto: criterio de taller, se sobreescriben desde la planta.
LIMITES_POR_DEFECTO = {
    "tiempo_sincronizacion_s": 30.0,
    "intentos_sincronizacion": 3.0,
    "desbalance_kw_pct": 5.0,
    "desbalance_kvar_pct": 10.0,
    "angulo_cierre_grados": 10.0,
}


@dataclass
class Registro:
    fecha: _dt.date
    equipo: str
    variable: str
    valor: str


def leer_csv(ruta: str | Path) -> list[Registro]:
    filas = []
    with open(ruta, newline="", encoding="utf-8-sig") as fh:
        for n, fila in enumerate(csv.DictReader(fh), start=2):
            try:
                fecha = _dt.date.fromisoformat(fila["fecha"].strip())
            except (KeyError, ValueError, AttributeError):
                raise ValueError(f"{ruta}:{n}: fecha ilegible ({fila.get('fecha')!r}); "
                                 "use AAAA-MM-DD") from None
            filas.append(Registro(fecha, fila["equipo"].strip(),
                                  fila["variable"].strip(), fila["valor"].strip()))
    return filas


@dataclass
class Tendencia:
    equipo: str
    variable: str
    puntos: int
    ultimo: float | None
    limite: float | None
    pendiente_por_dia: float | None
    r2: float | None
    cruza_el: str | None          # fecha ISO
    dias_restantes: int | None
    severidad: str | None
    texto: str

    def a_dict(self) -> dict:
        return asdict(self)


def _recta(xs, ys):
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return 0.0, my, 0.0
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    m = sxy / sxx
    b = my - m * mx
    sst = sum((y - my) ** 2 for y in ys)
    sse = sum((y - (m * x + b)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 if sst == 0 else 1 - sse / sst
    return m, b, r2


def _severidad(dias: int) -> str:
    if dias <= 7:
        return "detiene"
    if dias <= 30:
        return "programable"
    return "oportunidad"


def proyectar(registros: list[Registro], limites: dict | None = None,
              hoy: _dt.date | None = None) -> list[Tendencia]:
    """Una tendencia por (equipo, variable numerica)."""
    limites = {**LIMITES_POR_DEFECTO, **(limites or {})}
    hoy = hoy or _dt.date.today()
    series: dict[tuple, list] = defaultdict(list)
    for r in registros:
        if r.variable == "alarma":
            continue
        try:
            series[(r.equipo, r.variable)].append((r.fecha, float(r.valor)))
        except ValueError:
            continue

    salida = []
    for (equipo, variable), pts in sorted(series.items()):
        pts.sort()
        limite = limites.get(variable)
        ultimo = pts[-1][1]
        base = dict(equipo=equipo, variable=variable, puntos=len(pts),
                    ultimo=ultimo, limite=limite)
        if limite is not None and ultimo >= limite:
            salida.append(Tendencia(**base, pendiente_por_dia=None, r2=None,
                                    cruza_el=pts[-1][0].isoformat(),
                                    dias_restantes=0, severidad="detiene",
                                    texto=f"Ya esta en {ultimo:g}, sobre el limite "
                                          f"de {limite:g}."))
            continue
        if len(pts) < MINIMO_PUNTOS:
            salida.append(Tendencia(**base, pendiente_por_dia=None, r2=None,
                                    cruza_el=None, dias_restantes=None,
                                    severidad=None,
                                    texto=f"{len(pts)} lecturas; hacen falta "
                                          f"{MINIMO_PUNTOS} para proyectar."))
            continue
        origen = pts[0][0]
        xs = [(f - origen).days for f, _ in pts]
        ys = [v for _, v in pts]
        m, b, r2 = _recta(xs, ys)
        comun = dict(**base, pendiente_por_dia=round(m, 4), r2=round(r2, 3))
        if limite is None:
            salida.append(Tendencia(**comun, cruza_el=None, dias_restantes=None,
                                    severidad=None,
                                    texto="Sin limite declarado para esta variable."))
        elif r2 < R2_MINIMO:
            salida.append(Tendencia(**comun, cruza_el=None, dias_restantes=None,
                                    severidad=None,
                                    texto=f"Dispersion sin tendencia (R² {r2:.2f}); "
                                          "no se proyecta."))
        elif m <= 0:
            salida.append(Tendencia(**comun, cruza_el=None, dias_restantes=None,
                                    severidad=None,
                                    texto="Estable o mejorando."))
        else:
            dia_cruce = (limite - b) / m
            fecha = origen + _dt.timedelta(days=round(dia_cruce))
            dias = max(0, (fecha - hoy).days)
            salida.append(Tendencia(
                **comun, cruza_el=fecha.isoformat(), dias_restantes=dias,
                severidad=_severidad(dias),
                texto=f"Sube {m*30:.2g} por mes; cruza {limite:g} el "
                      f"{fecha.isoformat()} (en {dias} dias, {len(pts)} lecturas, "
                      f"R² {r2:.2f})."))
    return salida


@dataclass
class Reincidencia:
    equipo: str
    alarma: str
    veces: int
    ultima: str
    intervalo_medio_dias: float | None
    vencida: bool
    severidad: str
    texto: str

    def a_dict(self) -> dict:
        return asdict(self)


def reincidencias(registros: list[Registro], hoy: _dt.date | None = None,
                  ventana_dias: int = VENTANA_ALARMAS_DIAS) -> list[Reincidencia]:
    """Alarmas que se repiten en la ventana, con su intervalo medio."""
    hoy = hoy or _dt.date.today()
    desde = hoy - _dt.timedelta(days=ventana_dias)
    grupos: dict[tuple, list] = defaultdict(list)
    for r in registros:
        if r.variable == "alarma" and r.fecha >= desde:
            grupos[(r.equipo, r.valor)].append(r.fecha)

    salida = []
    for (equipo, alarma), fechas in sorted(grupos.items()):
        if len(fechas) < 2:
            continue
        fechas.sort()
        gaps = [(b - a).days for a, b in zip(fechas, fechas[1:])]
        medio = statistics.fmean(gaps) if gaps else None
        desde_ultima = (hoy - fechas[-1]).days
        vencida = medio is not None and desde_ultima >= medio
        sev = "detiene" if len(fechas) >= 3 else "programable"
        texto = (f"{len(fechas)} veces en {ventana_dias} dias, cada "
                 f"{medio:.0f} dias en promedio.")
        if vencida:
            texto += f" Ya pasaron {desde_ultima}: la proxima esta vencida."
        salida.append(Reincidencia(equipo, alarma, len(fechas),
                                   fechas[-1].isoformat(),
                                   None if medio is None else round(medio, 1),
                                   vencida, sev, texto))
    return salida
