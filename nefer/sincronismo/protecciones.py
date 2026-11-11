"""Revision de los ajustes de proteccion que el paralelo exige.

Un grupo que trabaja solo puede vivir sin la 32 o la 40. En paralelo no:
la unidad que pierde combustible se motoriza tirando de las demas, y la que
pierde excitacion se lleva los reactivos de la barra. Por eso lo primero que
se revisa es que la funcion EXISTA; despues, que su ajuste caiga en un rango
razonable.

Los rangos son referencia de taller para motores diesel, no el resultado de
un estudio de coordinacion. Un ajuste fuera de rango se rotula para
revisarlo, no se declara equivocado: el estudio de la planta manda.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

FUENTE = ("referencia de taller para grupos diesel; no sustituye el estudio "
          "de coordinacion de la planta")

# Funcion ANSI -> (nombre, obligatoria en paralelo, {parametro: (min, max)})
FUNCIONES = {
    "25": ("Verificacion de sincronismo", True, {}),
    "32": ("Potencia inversa", True,
           {"pickup_pct": (5.0, 15.0), "retardo_s": (1.0, 10.0)}),
    "40": ("Perdida de excitacion", True, {"retardo_s": (0.2, 5.0)}),
    "27": ("Subtension", True, {"pickup_pct": (80.0, 95.0)}),
    "59": ("Sobretension", True, {"pickup_pct": (105.0, 120.0)}),
    "81U": ("Subfrecuencia", True, {"pickup_pct": (90.0, 99.0)}),
    "81O": ("Sobrefrecuencia", True, {"pickup_pct": (101.0, 110.0)}),
    "46": ("Secuencia negativa (desbalance)", False, {}),
    "51V": ("Sobrecorriente con restriccion de tension", False, {}),
    "87G": ("Diferencial de generador", False, {}),
}


@dataclass
class Observacion:
    unidad: str
    funcion: str
    severidad: str
    texto: str

    def a_dict(self) -> dict:
        return asdict(self)


def revisar(unidad: str, ajustes: dict) -> list[Observacion]:
    """Compara los ajustes declarados de una unidad con la referencia."""
    obs: list[Observacion] = []
    declaradas = {str(k).upper(): v for k, v in (ajustes or {}).items()}

    for codigo, (nombre, obligatoria, rangos) in FUNCIONES.items():
        ajuste = declaradas.get(codigo)
        if ajuste is None or ajuste is False or (
                isinstance(ajuste, dict) and ajuste.get("habilitada") is False):
            if obligatoria:
                obs.append(Observacion(unidad, codigo, "detiene",
                                       f"{codigo} {nombre}: no declarada o "
                                       "deshabilitada. En paralelo es obligatoria."))
            continue
        if not isinstance(ajuste, dict):
            continue
        for parametro, (lo, hi) in rangos.items():
            valor = ajuste.get(parametro)
            if valor is None:
                obs.append(Observacion(unidad, codigo, "oportunidad",
                                       f"{codigo} {nombre}: falta anotar "
                                       f"{parametro}."))
            elif not lo <= float(valor) <= hi:
                obs.append(Observacion(unidad, codigo, "programable",
                                       f"{codigo} {nombre}: {parametro} = {valor} "
                                       f"fuera de la referencia {lo:g}–{hi:g}. "
                                       "Confirme contra el estudio de coordinacion."))
    return obs
