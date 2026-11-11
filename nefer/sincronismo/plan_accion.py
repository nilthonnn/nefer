"""AMEF completa y plan de accion: de la falla a la solucion, y la solucion medida.

El analisis RCM dice QUE estrategia corresponde a cada modo de falla. La AMEF
completa (IEC 60812:2018; AIAG-VDA 2019, paso 6 «optimizacion») agrega lo que
falta para que eso se convierta en trabajo:

- controles actuales: que previene y que detecta HOY la falla;
- acciones con responsable, plazo, intervalo y criterio de verificacion;
- la re-evaluacion: severidad, ocurrencia y deteccion DESPUES de las
  acciones, con su NPR y su prioridad de accion residuales.

Y las reglas que hacen que el plan sea defendible, cada una con su origen:

R1  Prioridad de accion alta -> al menos una accion.           (AIAG-VDA)
R2  Toda accion tiene responsable, plazo y verificacion.       (IEC 60812, AIAG-VDA)
R3  La severidad no baja sin rediseño: una inspeccion detecta
    antes, no hace que la falla duela menos.                   (AIAG-VDA, IEC 60812)
R4  Ocurrencia y deteccion residuales no empeoran, y alguna
    mejora si hay acciones.                                    (consistencia)
R5  Falla oculta -> una prueba con intervalo.                  (SAE JA1011: busqueda de fallas)
R6  La accion es coherente con la estrategia del arbol:
    CBM -> deteccion; busqueda de fallas -> prueba con intervalo;
    restauracion o descarte -> prevencion con intervalo;
    rediseño -> accion de rediseño.                            (SAE JA1011 / JA1012)
R7  Severidad critica con prioridad residual alta -> escalar.  (criterio de riesgo residual)
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..fixmate import cargador
from ..fixmate.criticidad import PRIORIDAD_EJEMPLO, RPN_EJEMPLO, evaluar

TIPOS_ACCION = ("prevencion", "deteccion", "rediseno")
ORDEN_AP = {"alta": 0, "media": 1, "baja": 2, "no evaluada": 3}


@dataclass
class Observacion:
    regla: str
    severidad: str        # detiene / programable / oportunidad
    modo_id: str
    texto: str


@dataclass
class FilaAMEF:
    modo_id: str
    sistema: str
    componente: str
    funcion: str
    falla_funcional: str
    efecto: str
    severidad: int
    modo_falla: str
    causa: str
    prevencion_actual: str
    ocurrencia: int
    deteccion_actual: str
    deteccion: int
    npr: int
    ap: str
    estrategia: str
    acciones: list[dict]
    severidad_r: int | None
    ocurrencia_r: int | None
    deteccion_r: int | None
    npr_r: int | None
    ap_r: str
    reduccion_npr_pct: float | None
    codigo_catalogo: str
    observaciones: list[Observacion] = field(default_factory=list)

    def a_dict(self) -> dict:
        return asdict(self)


def _modos_crudos(datos: dict) -> list[dict]:
    return [md for fd in datos["funciones"] for ffd in fd["fallas"] for md in ffd["modos"]]


def revisar_modo(fila: FilaAMEF, evidente: bool, estrategia_clave: str | None) -> list[Observacion]:
    obs: list[Observacion] = []
    mid = fila.modo_id

    def add(regla, sev, texto):
        obs.append(Observacion(regla, sev, mid, texto))

    acciones = fila.acciones
    if fila.ap == "alta" and not acciones:
        add("R1", "detiene", "Prioridad alta sin ninguna accion.")
    for i, a in enumerate(acciones, 1):
        faltan = [k for k in ("accion", "responsable", "plazo_dias", "verificacion") if not a.get(k)]
        if faltan:
            add("R2", "programable", f"Accion {i}: falta {', '.join(faltan)}.")
        if a.get("tipo") not in TIPOS_ACCION:
            add("R2", "programable", f"Accion {i}: tipo «{a.get('tipo')}» no es "
                                     f"{', '.join(TIPOS_ACCION)}.")
    if fila.severidad_r is not None:
        rediseno = any(a.get("tipo") == "rediseno" for a in acciones)
        if fila.severidad_r < fila.severidad and not rediseno:
            add("R3", "detiene", f"La severidad baja de {fila.severidad} a {fila.severidad_r} "
                                 "sin una accion de rediseño.")
        if fila.ocurrencia_r > fila.ocurrencia or fila.deteccion_r > fila.deteccion:
            add("R4", "programable", "La re-evaluacion empeora la ocurrencia o la deteccion.")
        # Con «operar hasta la falla» las acciones mitigan la consecuencia
        # (repuesto en stock), no la ocurrencia ni la deteccion: no cambiar
        # S, O, D es lo correcto ahi.
        if acciones and estrategia_clave != "operar_hasta_falla" and (
                fila.ocurrencia_r, fila.deteccion_r, fila.severidad_r) == (
                fila.ocurrencia, fila.deteccion, fila.severidad):
            add("R4", "oportunidad", "Hay acciones, pero la re-evaluacion no cambia nada: "
                                     "o las acciones no sirven o falta re-evaluar.")
    elif acciones:
        add("R4", "programable", "Hay acciones pero falta la re-evaluacion (S, O, D despues).")

    con_intervalo = [a for a in acciones if a.get("intervalo")]
    if not evidente and not any(a.get("tipo") == "deteccion" and a.get("intervalo")
                                for a in acciones):
        add("R5", "detiene", "Falla oculta sin prueba periodica con intervalo.")
    tipos = {a.get("tipo") for a in acciones}
    if estrategia_clave == "cbm" and "deteccion" not in tipos:
        add("R6", "programable", "Estrategia segun condicion sin accion de deteccion.")
    if estrategia_clave == "busqueda_fallas" and not con_intervalo:
        add("R6", "programable", "Busqueda de fallas sin intervalo de prueba.")
    if estrategia_clave in ("restauracion", "descarte") and not any(
            a.get("tipo") == "prevencion" and a.get("intervalo") for a in acciones):
        add("R6", "programable", "Restauracion o descarte sin accion preventiva con intervalo.")
    if estrategia_clave == "rediseno" and "rediseno" not in tipos:
        add("R6", "detiene", "El arbol exige rediseño y el plan no lo trae.")
    if fila.severidad >= 5 and fila.ap_r == "alta":
        add("R7", "detiene", "Severidad critica con prioridad residual alta: escalar a la "
                             "gerencia o rediseñar.")
    return obs


def amef(ruta: str | Path) -> list[FilaAMEF]:
    """La AMEF completa, una fila por modo, con su revision."""
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    analisis, decisiones = cargador.analisis_y_decisiones(ruta)
    filas = []
    for modo, md in zip(analisis.modos, _modos_crudos(datos)):
        falla = next(f for f in analisis.fallas if f.id == modo.falla_funcional_id)
        funcion = next(f for f in analisis.funciones if f.id == falla.funcion_id)
        v = dict(modo.criticidad.valores) or dict(md.get("criticidad") or {})
        if not v:
            continue
        npr, ap = evaluar(RPN_EJEMPLO, v), evaluar(PRIORIDAD_EJEMPLO, v)
        obj = md.get("criticidad_objetivo")
        npr_r = ap_r = None
        if obj:
            npr_r, ap_r = evaluar(RPN_EJEMPLO, obj), evaluar(PRIORIDAD_EJEMPLO, obj)
        d = decisiones.get(modo.id)
        ctl = md.get("controles_actuales") or {}
        fila = FilaAMEF(
            modo_id=modo.id, sistema=modo.ubicacion.sistema,
            componente=modo.ubicacion.componente, funcion=funcion.descripcion,
            falla_funcional=falla.descripcion,
            efecto=f"{modo.efecto.local}. {modo.efecto.observa_operador}".strip(". "),
            severidad=v["severidad"], modo_falla=modo.descripcion, causa=modo.causa,
            prevencion_actual=ctl.get("prevencion", ""), ocurrencia=v["frecuencia"],
            deteccion_actual=ctl.get("deteccion", ""), deteccion=v["deteccion"],
            npr=npr.valor, ap=ap.etiqueta,
            estrategia=d.rotulo if d else "Sin decidir",
            acciones=list(md.get("plan_accion") or []),
            severidad_r=obj["severidad"] if obj else None,
            ocurrencia_r=obj["frecuencia"] if obj else None,
            deteccion_r=obj["deteccion"] if obj else None,
            npr_r=npr_r.valor if npr_r else None,
            ap_r=ap_r.etiqueta if ap_r else "no evaluada",
            reduccion_npr_pct=(round((1 - npr_r.valor / npr.valor) * 100, 1)
                               if npr_r else None),
            codigo_catalogo=modo.codigo_catalogo or md.get("codigo_planta", ""),
        )
        fila.observaciones = revisar_modo(fila, modo.evidente, d.estrategia if d else None)
        filas.append(fila)
    return filas


def plan(filas: list[FilaAMEF], fecha_base: str) -> list[dict]:
    """Las acciones de todos los modos, en orden de urgencia.

    Orden: prioridad de accion inicial, luego severidad, luego NPR. Primero
    lo que puede herir; el NPR solo desempata.
    """
    base = _dt.date.fromisoformat(fecha_base)
    salida = []
    for f in sorted(filas, key=lambda f: (ORDEN_AP.get(f.ap, 9), -f.severidad, -f.npr)):
        for a in f.acciones:
            plazo = int(a.get("plazo_dias") or 0)
            salida.append({
                "prioridad": f.ap, "severidad": f.severidad, "npr": f.npr,
                "npr_objetivo": f.npr_r, "modo_id": f.modo_id, "modo_falla": f.modo_falla,
                "sistema": f.sistema, "estrategia": f.estrategia,
                "accion": a.get("accion", ""), "tipo": a.get("tipo", ""),
                "responsable": a.get("responsable", ""),
                "fecha_objetivo": (base + _dt.timedelta(days=plazo)).isoformat() if plazo else "",
                "intervalo": a.get("intervalo", ""),
                "verificacion": a.get("verificacion", ""), "estado": "abierta",
            })
    return salida


def resumen(filas: list[FilaAMEF]) -> dict:
    total_i = sum(f.npr for f in filas)
    total_r = sum(f.npr_r for f in filas if f.npr_r is not None)
    obs = [o for f in filas for o in f.observaciones]
    return {
        "modos": len(filas),
        "npr_total_inicial": total_i,
        "npr_total_residual": total_r,
        "reduccion_pct": round((1 - total_r / total_i) * 100, 1) if total_i else None,
        "ap_inicial": {k: sum(1 for f in filas if f.ap == k) for k in ("alta", "media", "baja")},
        "ap_residual": {k: sum(1 for f in filas if f.ap_r == k) for k in ("alta", "media", "baja")},
        "acciones": sum(len(f.acciones) for f in filas),
        "observaciones": {k: sum(1 for o in obs if o.severidad == k)
                          for k in ("detiene", "programable", "oportunidad")},
    }


COLUMNAS_AMEF = (
    ("sistema", "Sistema"), ("componente", "Componente"), ("funcion", "Funcion"),
    ("falla_funcional", "Falla funcional"), ("efecto", "Efecto"), ("severidad", "S"),
    ("modo_falla", "Modo de falla"), ("causa", "Causa"),
    ("prevencion_actual", "Control de prevencion actual"), ("ocurrencia", "O"),
    ("deteccion_actual", "Control de deteccion actual"), ("deteccion", "D"),
    ("npr", "NPR"), ("ap", "Prioridad de accion"), ("estrategia", "Estrategia RCM"),
    ("acciones_txt", "Acciones recomendadas"), ("responsables", "Responsable"),
    ("severidad_r", "S'"), ("ocurrencia_r", "O'"), ("deteccion_r", "D'"),
    ("npr_r", "NPR'"), ("ap_r", "Prioridad residual"), ("codigo_catalogo", "Codigo"),
)


def a_csv_amef(filas: list[FilaAMEF], delimitador: str = ";") -> str:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=delimitador)
    w.writerow([t for _, t in COLUMNAS_AMEF])
    for f in filas:
        d = f.a_dict()
        d["acciones_txt"] = " | ".join(a.get("accion", "") for a in f.acciones)
        d["responsables"] = " | ".join(a.get("responsable", "") for a in f.acciones)
        w.writerow(["" if d[k] is None else d[k] for k, _ in COLUMNAS_AMEF])
    return buf.getvalue()


def a_csv_plan(acciones: list[dict], delimitador: str = ";") -> str:
    buf = io.StringIO()
    if not acciones:
        return ""
    w = csv.DictWriter(buf, fieldnames=list(acciones[0]), delimiter=delimitador)
    w.writeheader()
    w.writerows(acciones)
    return buf.getvalue()
