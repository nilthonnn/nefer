"""Permisivo de cierre en paralelo (funcion ANSI 25, verificacion de sincronismo).

El error mas comun no esta en las ventanas sino en el instante en que se
miden. El controlador da la orden de cierre con un angulo; el interruptor
tarda su tiempo de cierre en juntar los contactos, y en ese tiempo el
deslizamiento sigue girando el fasor. Lo que golpea al eje y al devanado es
el angulo en el contacto:

    angulo_contacto = angulo_orden + 360 * deslizamiento_Hz * t_cierre_s

Con 0.2 Hz de deslizamiento y un interruptor de 100 ms, son 7.2° que se
suman. Por eso aqui el angulo se juzga en el contacto y se informa el
angulo de adelanto que el controlador deberia compensar.

Las ventanas por defecto son las de IEEE 1547-2018, tabla 5, por potencia
agregada de la unidad. Son las de interconexion con la red; en un barraje
aislado el fabricante del controlador suele pedir menos, y se pasan otras.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

# (kVA maximo, delta f Hz, delta V %, delta angulo °). IEEE 1547-2018, tabla 5.
LIMITES_IEEE1547 = (
    (500.0, 0.3, 10.0, 20.0),
    (1500.0, 0.2, 5.0, 15.0),
    (float("inf"), 0.1, 3.0, 10.0),
)

FUENTE_IEEE1547 = "IEEE 1547-2018, tabla 5"


@dataclass
class Ventana:
    delta_f_hz: float
    delta_v_pct: float
    delta_angulo_grados: float
    fuente: str


def ventana_por_potencia(kva: float) -> Ventana:
    """La ventana de IEEE 1547 que corresponde a la potencia de la unidad."""
    if kva <= 0:
        raise ValueError("la potencia de la unidad debe ser positiva")
    for tope, df, dv, da in LIMITES_IEEE1547:
        if kva <= tope:
            return Ventana(df, dv, da, f"{FUENTE_IEEE1547} ({kva:g} kVA)")
    raise AssertionError("inalcanzable")


@dataclass
class Lectura:
    """Lo que se lee en el modulo de sincronismo justo antes de cerrar.

    `angulo_grados` es el del generador respecto del barraje: positivo si el
    generador adelanta. `t_cierre_s` es el tiempo de cierre propio del
    interruptor (placa o prueba de tiempos), no el retardo del controlador.
    """

    v_barra: float
    f_barra: float
    v_gen: float
    f_gen: float
    angulo_grados: float
    t_cierre_s: float = 0.1
    secuencia_barra: str = "ABC"
    secuencia_gen: str = "ABC"
    barra_muerta: bool = False


@dataclass
class Veredicto:
    permitido: bool
    delta_v_pct: float
    deslizamiento_hz: float
    angulo_orden: float
    angulo_contacto: float
    angulo_adelanto: float
    espera_s: float | None
    ventana: Ventana
    bloqueos: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def a_dict(self) -> dict:
        return asdict(self)


def _envolver(grados: float) -> float:
    """Lleva un angulo a (-180, 180]."""
    a = (grados + 180.0) % 360.0 - 180.0
    return 180.0 if a == -180.0 else a


def _espera_hasta_ventana(angulo_contacto: float, desliz: float, ventana: float):
    """Segundos hasta que el angulo en el contacto entre en ±ventana.

    0 si ya esta dentro; None si no hay deslizamiento que lo mueva.
    """
    if abs(angulo_contacto) <= ventana:
        return 0.0
    if desliz == 0:
        return None
    if desliz > 0:        # el fasor avanza: entra por -ventana tras dar la vuelta
        distancia = (-ventana - angulo_contacto) % 360.0
    else:
        distancia = (angulo_contacto - ventana) % 360.0
    return distancia / (360.0 * abs(desliz))


def verificar(lectura: Lectura, ventana: Ventana) -> Veredicto:
    """Decide si se puede cerrar, y si no, por que y cuanto falta."""
    if lectura.v_barra <= 0 and not lectura.barra_muerta:
        raise ValueError("tension de barra nula: declare barra_muerta=True")

    bloqueos: list[str] = []
    avisos: list[str] = []

    if lectura.barra_muerta:
        # Cierre en barra muerta: no hay nada con que sincronizar, pero un
        # cierre simultaneo de dos unidades sobre la misma barra muerta es
        # exactamente el accidente que la logica de barra muerta evita.
        avisos.append("Cierre en barra muerta: confirme que la logica impide "
                      "que otra unidad cierre a la vez (enclavamiento de barra "
                      "muerta).")
        return Veredicto(True, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ventana, [], avisos)

    seq_b = lectura.secuencia_barra.strip().upper()
    seq_g = lectura.secuencia_gen.strip().upper()
    if seq_b != seq_g:
        bloqueos.append(f"Secuencia de fases distinta (barra {seq_b}, generador "
                        f"{seq_g}). No se cierra con ningun angulo: corrija el "
                        "cableado de potencia o de los TP antes de seguir.")

    # Redondeo a la resolucion de cualquier instrumento: 60.2 - 60 no debe
    # dar 0.2000000000003 y bloquear un cierre que esta justo en el limite.
    delta_v = round((lectura.v_gen - lectura.v_barra) / lectura.v_barra * 100.0, 6)
    desliz = round(lectura.f_gen - lectura.f_barra, 6)
    adelanto = 360.0 * desliz * lectura.t_cierre_s
    a_orden = _envolver(lectura.angulo_grados)
    a_contacto = _envolver(a_orden + adelanto)

    if abs(delta_v) > ventana.delta_v_pct:
        bloqueos.append(f"Diferencia de tension {delta_v:+.1f} % fuera de "
                        f"±{ventana.delta_v_pct:g} %: ajuste la consigna del AVR.")
    if abs(desliz) > ventana.delta_f_hz:
        bloqueos.append(f"Deslizamiento {desliz:+.3f} Hz fuera de "
                        f"±{ventana.delta_f_hz:g} Hz: ajuste el gobernador.")
    otros_bloqueos = len(bloqueos)
    if abs(a_contacto) > ventana.delta_angulo_grados:
        bloqueos.append(f"Angulo en el contacto {a_contacto:+.1f}° fuera de "
                        f"±{ventana.delta_angulo_grados:g}° "
                        f"(orden a {a_orden:+.1f}°, adelanto {adelanto:+.1f}°).")

    if desliz < 0:
        avisos.append("El generador gira mas lento que la barra: al cerrar "
                      "entrara absorbiendo potencia (riesgo de disparo 32). "
                      "Lo sano es un deslizamiento levemente positivo.")
    if delta_v < 0:
        avisos.append("La tension del generador es menor que la de la barra: "
                      "al cerrar absorbera reactivos.")
    if abs(adelanto) > ventana.delta_angulo_grados / 2:
        avisos.append(f"El tiempo de cierre del interruptor consume "
                      f"{abs(adelanto):.1f}° de la ventana: compense el angulo de "
                      "adelanto en el controlador o baje el deslizamiento.")

    espera = None
    if otros_bloqueos == 0:
        espera = _espera_hasta_ventana(a_contacto, desliz,
                                       ventana.delta_angulo_grados)
        if espera is None:
            avisos.append("Deslizamiento nulo con el angulo fuera de ventana: "
                          "el fasor no se movera solo. De un leve exceso de "
                          "velocidad al generador.")

    return Veredicto(
        permitido=not bloqueos,
        delta_v_pct=round(delta_v, 3),
        deslizamiento_hz=round(desliz, 4),
        angulo_orden=round(a_orden, 2),
        angulo_contacto=round(a_contacto, 2),
        angulo_adelanto=round(adelanto, 2),
        espera_s=None if espera is None else round(espera, 2),
        ventana=ventana,
        bloqueos=bloqueos,
        avisos=avisos,
    )
