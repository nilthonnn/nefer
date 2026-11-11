"""Reparto de carga activa y reactiva entre unidades en paralelo.

Dos preguntas distintas, y las dos se hacen en campo:

1. **¿Como estan repartiendo ahora?** De las lecturas de kW y kVAr de cada
   unidad sale su carga en por unidad de su propia potencia, y la
   desviacion respecto del promedio de la planta. Un reparto bueno no es
   «todas con los mismos kW», es «todas al mismo porcentaje de su placa».

2. **¿Como van a repartir si cambio la carga o un ajuste?** Con estatismo
   (droop) el reparto no depende del controlador sino de la recta de cada
   gobernador o AVR, y se puede calcular antes de tocar la planta:

       P_i = (f_vacio_i - f) / (estatismo_i * f_nominal) * P_nominal_i

   La suma de las P_i es la carga; de ahi sale la frecuencia de la barra, y
   de la frecuencia, lo que toma cada unidad. La misma recta vale para kVAr
   con la tension y el estatismo de tension del AVR.

Los limites de aceptacion por defecto (±5 % en kW, ±10 % en kVAr, sobre la
potencia de cada unidad) son criterio de puesta en marcha de taller, no de
una norma: se rotulan asi y se pueden cambiar.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

LIMITE_KW_PCT = 5.0
LIMITE_KVAR_PCT = 10.0
FUENTE_LIMITES = "criterio de puesta en marcha de taller (configurable)"
FP_NOMINAL = 0.8


@dataclass
class Unidad:
    id: str
    kw_nominal: float
    kva_nominal: float | None = None
    kw: float | None = None
    kvar: float | None = None
    # Estatismo: solo para predecir.
    modo: str = "droop"                 # "droop" o "isocrono"
    f_vacio: float | None = None        # consigna de frecuencia en vacio, Hz
    estatismo_pct: float | None = None  # estatismo de velocidad, %
    v_vacio: float | None = None        # consigna de tension en vacio, V
    estatismo_v_pct: float | None = None

    @property
    def kvar_nominal(self) -> float:
        kva = self.kva_nominal or self.kw_nominal / FP_NOMINAL
        return kva * math.sqrt(1 - FP_NOMINAL ** 2)

    @classmethod
    def desde_dict(cls, d: dict) -> "Unidad":
        conocidos = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**conocidos)


@dataclass
class FilaReparto:
    id: str
    kw: float
    kvar: float | None
    pu_kw: float
    pu_kvar: float | None
    desvio_kw_pct: float
    desvio_kvar_pct: float | None


@dataclass
class Reparto:
    filas: list[FilaReparto]
    pu_kw_planta: float
    pu_kvar_planta: float | None
    limite_kw_pct: float
    limite_kvar_pct: float
    fuente_limites: str
    hallazgos: list[dict] = field(default_factory=list)

    def a_dict(self) -> dict:
        return asdict(self)


def _hallazgo(severidad: str, unidad: str, texto: str) -> dict:
    return {"severidad": severidad, "unidad": unidad, "texto": texto}


def analizar_reparto(unidades: list[Unidad], limite_kw_pct: float = LIMITE_KW_PCT,
                     limite_kvar_pct: float = LIMITE_KVAR_PCT) -> Reparto:
    """Reparto actual a partir de las lecturas de kW (y kVAr si estan)."""
    en_linea = [u for u in unidades if u.kw is not None]
    if len(en_linea) < 2:
        raise ValueError("hacen falta al menos dos unidades con lectura de kW "
                         "para hablar de reparto")

    total_kw = sum(u.kw for u in en_linea)
    total_nom = sum(u.kw_nominal for u in en_linea)
    pu_planta = total_kw / total_nom

    con_kvar = all(u.kvar is not None for u in en_linea)
    pu_kvar_planta = None
    if con_kvar:
        pu_kvar_planta = (sum(u.kvar for u in en_linea)
                          / sum(u.kvar_nominal for u in en_linea))

    filas, hallazgos = [], []
    for u in en_linea:
        pu = u.kw / u.kw_nominal
        desvio = (pu - pu_planta) * 100
        pu_q = desvio_q = None
        if con_kvar:
            pu_q = u.kvar / u.kvar_nominal
            desvio_q = (pu_q - pu_kvar_planta) * 100
        filas.append(FilaReparto(u.id, u.kw, u.kvar, round(pu, 4),
                                 None if pu_q is None else round(pu_q, 4),
                                 round(desvio, 2),
                                 None if desvio_q is None else round(desvio_q, 2)))

        if u.kw < 0:
            hallazgos.append(_hallazgo(
                "detiene", u.id,
                f"Absorbe {abs(u.kw):.0f} kW: esta motorizando. La 32 deberia "
                "dispararla; si no lo hizo, revise su ajuste y su polaridad de TC."))
        elif pu > 1.0:
            hallazgos.append(_hallazgo(
                "detiene", u.id, f"Sobrecargada al {pu*100:.0f} % de su placa."))
        elif abs(desvio) > limite_kw_pct:
            hallazgos.append(_hallazgo(
                "programable", u.id,
                f"Reparto de kW desviado {desvio:+.1f} % de su placa respecto "
                f"del promedio (limite ±{limite_kw_pct:g} %). Revise consigna "
                "de velocidad en vacio, estatismo y lineas de reparto."))
        if con_kvar and abs(desvio_q) > limite_kvar_pct:
            hallazgos.append(_hallazgo(
                "programable", u.id,
                f"Reparto de kVAr desviado {desvio_q:+.1f} % (limite "
                f"±{limite_kvar_pct:g} %). Revise consigna y estatismo del AVR "
                "y la polaridad del TC de compensacion."))

    if con_kvar:
        exporta = [u.id for u in en_linea if u.kvar > 0]
        importa = [u.id for u in en_linea if u.kvar < 0]
        if exporta and importa:
            hallazgos.append(_hallazgo(
                "programable", ",".join(importa),
                f"Corriente reactiva circulante: {', '.join(importa)} absorbe "
                f"kVAr que entrega {', '.join(exporta)}. Calienta los dos "
                "devanados sin servir a la carga."))

    return Reparto(filas, round(pu_planta, 4),
                   None if pu_kvar_planta is None else round(pu_kvar_planta, 4),
                   limite_kw_pct, limite_kvar_pct, FUENTE_LIMITES, hallazgos)


@dataclass
class Prediccion:
    magnitud: str               # "kW" o "kVAr"
    carga: float
    referencia: float           # f o V de barra resultante
    nominal: float
    toma: dict[str, float]      # carga de cada unidad
    pu: dict[str, float]
    consigna_sugerida: dict[str, float]
    hallazgos: list[dict] = field(default_factory=list)

    def a_dict(self) -> dict:
        return asdict(self)


def _resolver(unidades, carga, nominal, vacio_de, estatismo_de, potencia_de,
              isocronas, magnitud):
    """Resuelve la recta de estatismo comun a kW (f) y kVAr (V)."""
    hallazgos = []
    toma: dict[str, float] = {}

    if len(isocronas) > 1:
        hallazgos.append(_hallazgo(
            "detiene", ",".join(u.id for u in isocronas),
            f"{len(isocronas)} unidades en isocrono: sin lineas de reparto "
            "entre ellas no hay punto de equilibrio y se disputan la carga. "
            "Deje una sola en isocrono o reparta por lineas (load sharing)."))

    ids_iso = {u.id for u in isocronas}
    rectas = []
    for u in unidades:
        if u.id in ids_iso:
            continue
        vacio, est = vacio_de(u), estatismo_de(u)
        if vacio is None or not est:
            raise ValueError(f"{u.id}: falta la consigna en vacio o el estatismo "
                             f"para predecir el reparto de {magnitud}")
        pendiente = potencia_de(u) / (est / 100.0 * nominal)   # kW por Hz
        rectas.append((u, vacio, pendiente))

    if isocronas:
        # La isocrona fija la referencia en su nominal y toma el resto.
        ref = nominal
        for u, vacio, k in rectas:
            toma[u.id] = (vacio - ref) * k
        resto = carga - sum(toma.values())
        for u in isocronas:
            toma[u.id] = resto / len(isocronas)
    else:
        suma_k = sum(k for _, _, k in rectas)
        ref = (sum(k * v for _, v, k in rectas) - carga) / suma_k
        for u, vacio, k in rectas:
            toma[u.id] = (vacio - ref) * k

    pu = {u.id: toma[u.id] / potencia_de(u) for u in unidades}
    pu_obj = carga / sum(potencia_de(u) for u in unidades)

    # Consigna en vacio que deja la barra en su nominal a plena carga: con
    # todas asi, cada unidad toma el mismo % de su placa a cualquier carga.
    sugerida = {}
    for u, vacio, k in rectas:
        sugerida[u.id] = round(nominal * (1 + estatismo_de(u) / 100.0), 3)

    for u in unidades:
        p = pu[u.id]
        if p < 0:
            hallazgos.append(_hallazgo(
                "detiene", u.id, f"Quedaria absorbiendo {magnitud} "
                f"({toma[u.id]:.0f}): motorizada o subexcitada."))
        elif p > 1.0:
            hallazgos.append(_hallazgo(
                "detiene", u.id, f"Quedaria al {p*100:.0f} % de su {magnitud} nominal."))
        elif abs(p - pu_obj) * 100 > (LIMITE_KW_PCT if magnitud == "kW"
                                       else LIMITE_KVAR_PCT):
            hallazgos.append(_hallazgo(
                "programable", u.id,
                f"Tomaria {p*100:.0f} % contra {pu_obj*100:.0f} % de la planta. "
                f"Consigna en vacio sugerida: {sugerida.get(u.id, '—')}."))

    desvio_ref = (ref - nominal) / nominal * 100
    if abs(desvio_ref) > 1.0 and not isocronas:
        hallazgos.append(_hallazgo(
            "oportunidad", "barra",
            f"La barra quedaria en {ref:.2f} ({desvio_ref:+.1f} % del nominal). "
            "Es propio del estatismo sin control secundario; si la carga lo "
            "exige, deje una unidad en isocrono o use reparto isocrono."))

    return Prediccion(magnitud, carga, round(ref, 3), nominal,
                      {k: round(v, 1) for k, v in toma.items()},
                      {k: round(v, 4) for k, v in pu.items()},
                      sugerida, hallazgos)


def predecir_estatismo(unidades: list[Unidad], carga_kw: float,
                       f_nominal: float = 60.0) -> Prediccion:
    """Frecuencia de barra y kW que toma cada unidad, para una carga dada."""
    iso = [u for u in unidades if u.modo == "isocrono"]
    return _resolver(unidades, carga_kw, f_nominal,
                     lambda u: u.f_vacio, lambda u: u.estatismo_pct,
                     lambda u: u.kw_nominal, iso, "kW")


def predecir_estatismo_reactivo(unidades: list[Unidad], carga_kvar: float,
                                v_nominal: float) -> Prediccion:
    """Tension de barra y kVAr de cada unidad con estatismo de tension."""
    return _resolver(unidades, carga_kvar, v_nominal,
                     lambda u: u.v_vacio, lambda u: u.estatismo_v_pct,
                     lambda u: u.kvar_nominal, [], "kVAr")
