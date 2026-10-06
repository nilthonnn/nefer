"""La matriz FMEA/FMECA, y lo que aprende del historial real.

Dos cosas distintas viven aqui, y la segunda es la que vale.

**Exportar** la matriz es mecanico: el analisis ya tiene la cadena completa
—activo, sistema, funcion, falla funcional, modo, causa, efecto,
consecuencia, criticidad, tarea, responsable, evidencia, fuente, estado— y
esto la aplana en filas. La estructura ya existia; esto solo la saca.

**Medir** el analisis contra el historial es lo otro. Un FMECA se escribe en
una sala con gente que opina, y despues la maquina falla como le parece. La
frecuencia historica de cada modo no se declara: se cuenta. `contrastar()`
recorre el historial que FixMate ya tiene y le pone a cada modo cuantas
veces aparecio de verdad, con que codigo del catalogo, y senala las dos
asimetrias que importan:

- **modos analizados que nunca ocurrieron**: puede ser prevencion que
  funciona, o puede ser una fila que alguien copio de otra maquina. El
  analisis no distingue; el dato lo pone a la vista para que alguien mire.
- **causas del historial sin modo que las cubra**: esas si son un hueco del
  analisis, y son la lista de trabajo para la proxima revision.

Nada de esto corrige el analisis solo. Un modo que no ocurrio no se borra ni
se marca invalido: se cuenta. La decision de quitarlo es de un humano con
contexto, y automatizarla seria borrar tareas de seguridad por falta de
evidencia, que es justo lo que la guarda de `decision.py` impide.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from . import aprendizaje as _aprendizaje
from . import catalogo as _catalogo
from .criticidad import NO_EVALUADA

# El orden de las columnas es el de la cadena de razonamiento, para que la
# matriz se pueda leer de izquierda a derecha como se construyo.
COLUMNAS = (
    "activo", "sistema", "subsistema", "componente",
    "funcion", "estandar", "falla_funcional",
    "modo_falla_id", "modo_falla", "codigo_catalogo", "causa", "mecanismo",
    "efecto_local", "observa_operador", "parametro", "alarma",
    "evidente", "consecuencias", "criticidad", "metodo_criticidad",
    "frecuencia_historica",
    "estrategia", "motivo_estrategia",
    "tarea", "disparador", "intervalo", "responsable",
    "evidencia", "fuente", "estado",
)


def _texto_evidencia(modo) -> tuple[str, str]:
    """Las referencias del modo, separadas en «que dice» y «de donde»."""
    if not modo.evidencia:
        return "", ""
    notas = "; ".join(r.nota or r.referencia for r in modo.evidencia if r.nota or r.referencia)
    fuentes = "; ".join(f"{r.fuente}:{r.referencia}" if r.referencia else r.fuente
                        for r in modo.evidencia)
    return notas, fuentes


def filas(analisis, decisiones=None, plan=None) -> list[dict]:
    """La matriz como lista de filas. Una fila por modo de falla."""
    get_d = getattr(decisiones, "get", lambda _: None) if decisiones else (lambda _: None)
    tareas = {t.modo_falla_id: t for t in (plan.tareas if plan else [])}

    salida: list[dict] = []
    for modo in analisis.modos:
        falla = next((f for f in analisis.fallas
                      if f.id == modo.falla_funcional_id), None)
        funcion = next((f for f in analisis.funciones
                        if falla and f.id == falla.funcion_id), None)
        d = get_d(modo.id)
        t = tareas.get(modo.id)

        notas, fuentes = _texto_evidencia(modo)
        intervalo = ""
        if t is not None:
            if t.intervalo_dias:
                intervalo = f"{t.intervalo_dias} d"
            elif t.intervalo_horas:
                intervalo = f"{t.intervalo_horas} h"
            elif t.disparador == "condicion" and t.limite:
                intervalo = f"{t.parametro} {t.limite}".strip()

        salida.append({
            "activo": analisis.activo.codigo,
            "sistema": modo.ubicacion.sistema,
            "subsistema": modo.ubicacion.subsistema,
            "componente": modo.ubicacion.componente,
            "funcion": funcion.descripcion if funcion else "",
            "estandar": funcion.estandar if funcion else "",
            "falla_funcional": falla.descripcion if falla else "",
            "modo_falla_id": modo.id,
            "modo_falla": modo.descripcion,
            "codigo_catalogo": modo.codigo_catalogo,
            "causa": modo.causa,
            "mecanismo": modo.mecanismo,
            "efecto_local": modo.efecto.local,
            "observa_operador": modo.efecto.observa_operador,
            "parametro": modo.efecto.parametro,
            "alarma": modo.efecto.alarma,
            # «oculta» va aqui como texto porque en una matriz impresa es
            # donde el lector la busca, aunque en el modelo sea un booleano.
            "evidente": "si" if modo.evidente else "no (oculta)",
            "consecuencias": ", ".join(c.clase for c in modo.consecuencias),
            "criticidad": modo.criticidad.etiqueta,
            "metodo_criticidad": modo.criticidad.metodo,
            # Vacio, no cero: cero diria «se conto y no ocurrio», y lo que
            # pasa mientras no se contraste es que nadie conto.
            "frecuencia_historica": ("" if modo.frecuencia_historica is None
                                     else modo.frecuencia_historica),
            "estrategia": d.rotulo if d else "",
            "motivo_estrategia": d.motivo if d else "",
            "tarea": t.descripcion if t else "",
            "disparador": t.disparador if t else "",
            "intervalo": intervalo,
            "responsable": t.responsable if t else "",
            "evidencia": notas,
            "fuente": fuentes,
            "estado": modo.estado,
        })
    return salida


def a_csv(analisis, decisiones=None, plan=None, delimitador: str = ";") -> str:
    """La matriz en CSV. Punto y coma por defecto: en es-ES y es-PE, Excel
    espera punto y coma, y con coma abre todo en una sola columna."""
    buffer = io.StringIO()
    w = csv.DictWriter(buffer, fieldnames=list(COLUMNAS), delimiter=delimitador,
                       lineterminator="\n")
    w.writeheader()
    for fila in filas(analisis, decisiones, plan):
        w.writerow(fila)
    return buffer.getvalue()


# ------------------------------------- contrastar contra el historial

@dataclass
class Contraste:
    """Lo que el historial dice del analisis. No lo corrige: lo mide."""

    modos: int
    # modo_falla_id -> cuantas veces aparecio en el historial
    frecuencias: dict[str, int] = field(default_factory=dict)
    # Analizados y nunca vistos. Puede ser prevencion que funciona, o una
    # fila copiada de otra maquina. El dato no distingue; lo pone a la vista.
    nunca_ocurrieron: tuple[str, ...] = ()
    # Causas del historial que ningun modo del analisis cubre. Estas si son
    # un hueco, y son la lista de trabajo de la proxima revision.
    sin_cubrir: tuple[tuple[str, int], ...] = ()
    # Informes cuya causa el catalogo no pudo codificar. Es la medida honesta
    # de cuanto alcanza el catalogo, y lo que dice que hay que agrandarlo.
    sin_codificar: int = 0

    @property
    def cobertura(self) -> float | None:
        """Fraccion de informes codificados que algun modo del analisis cubre."""
        total = sum(self.frecuencias.values()) + sum(n for _, n in self.sin_cubrir)
        return (sum(self.frecuencias.values()) / total) if total else None

    def a_dict(self) -> dict:
        return {"modos": self.modos, "frecuencias": dict(self.frecuencias),
                "nunca_ocurrieron": list(self.nunca_ocurrieron),
                "sin_cubrir": [list(x) for x in self.sin_cubrir],
                "sin_codificar": self.sin_codificar,
                "cobertura": self.cobertura}


def contrastar(analisis, indice, cat=None, aplicar: bool = False) -> Contraste:
    """Cuenta en el historial cuantas veces ocurrio de verdad cada modo.

    El cruce se hace por codigo del catalogo, que es la unica llave estable:
    cruzar por texto libre juntaria «filtro de aire colmatado» con «filtro
    aire tapado» a veces si y a veces no.

    `aplicar=True` escribe `frecuencia_historica` en los modos. Por defecto
    NO toca el analisis: medir y modificar son dos permisos distintos.
    """
    cat = cat or _catalogo.Catalogo()
    codigo_activo = analisis.activo.codigo

    # Lo que el historial trae de este activo, codificado.
    conteo: dict[str, int] = {}
    sin_codificar = 0
    for fragmento in getattr(indice, "fragmentos", []) or []:
        meta = getattr(fragmento, "metadatos", {}) or {}
        if fragmento.tipo != "informe":
            continue
        if str(meta.get("codigo_equipo") or "") != codigo_activo:
            continue
        causa = str(meta.get("causa_raiz") or "").strip()
        if not causa:
            continue
        # Si el informe ya trae el codigo, se respeta: alguien lo decidio.
        codigo = str(meta.get("codigo_catalogo") or "").strip()
        if not codigo:
            entrada = cat.clasificar(causa)
            codigo = entrada.codigo if entrada else ""
        if codigo:
            conteo[codigo] = conteo.get(codigo, 0) + 1
        else:
            sin_codificar += 1

    frecuencias: dict[str, int] = {}
    cubiertos: set[str] = set()
    for modo in analisis.modos:
        n = conteo.get(modo.codigo_catalogo, 0) if modo.codigo_catalogo else 0
        frecuencias[modo.id] = n
        if modo.codigo_catalogo:
            cubiertos.add(modo.codigo_catalogo)
        if aplicar:
            modo.frecuencia_historica = n

    return Contraste(
        modos=len(analisis.modos),
        frecuencias=frecuencias,
        nunca_ocurrieron=tuple(mid for mid, n in frecuencias.items() if n == 0),
        sin_cubrir=tuple(sorted(((c, n) for c, n in conteo.items()
                                 if c not in cubiertos), key=lambda x: -x[1])),
        sin_codificar=sin_codificar,
    )
