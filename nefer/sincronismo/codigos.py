"""Codigos de evento SPN/FMI (PowerWizard y controladores J1939) y perfiles de controlador.

El PowerWizard de FG Wilson (1.0, 1.1, 1.1+, 2.0, 2.1) informa sus eventos
como SPN/FMI: el SPN dice QUE parametro, el FMI dice QUE le paso. Los dos
vienen de SAE J1939 (SPN de J1939-71, FMI de J1939-73), que es tambien lo que
hablan los ECM de los motores CAT y Cummins. Por eso un mismo decodificador
sirve para el tablero y para el motor.

Lo que este modulo sabe y lo que no:

- La tabla de FMI es la de J1939-73, completa.
- Los SPN son los de motor mas comunes de J1939-71. Un SPN que no esta aqui no
  se adivina: se remite al Apendice A del manual tecnico del PowerWizard,
  donde estan los propios del tablero (por ejemplo, los eventos de entradas
  configurables, SPN 701-711 con FMI 31).
- La lectura de FMI como «parada» o «alarma» sigue la convencion del manual
  del PowerWizard (FMI 0 = parada por alto, FMI 1 = parada por bajo); FMI 15 y
  17 son los niveles «menos severos» de J1939 y el tablero los usa como
  alarma.
- Cada SPN apunta a los modos de falla del analisis RCM de la planta que lo
  pueden producir, para que el codigo lleve directo al plan de accion.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

FUENTE_FMI = "SAE J1939-73 (FMI)"
FUENTE_SPN = "SAE J1939-71 (SPN)"
MANUAL_PW = ("FG Wilson PowerWizard 1.1, 1.1+ & 2.1 Technical Manual, Apendice A "
             "(lista de eventos SPN/FMI)")

FMI = {
    0: "Dato valido pero por encima del rango normal — nivel mas severo",
    1: "Dato valido pero por debajo del rango normal — nivel mas severo",
    2: "Dato erratico, intermitente o incorrecto",
    3: "Tension por encima de lo normal o cortocircuito a positivo",
    4: "Tension por debajo de lo normal o cortocircuito a negativo",
    5: "Corriente por debajo de lo normal o circuito abierto",
    6: "Corriente por encima de lo normal o circuito a masa",
    7: "El sistema mecanico no responde o esta desajustado",
    8: "Frecuencia, ancho de pulso o periodo anormal",
    9: "Frecuencia de actualizacion anormal",
    10: "Velocidad de cambio anormal",
    11: "Causa raiz no conocida",
    12: "Dispositivo o componente inteligente defectuoso",
    13: "Fuera de calibracion",
    14: "Instrucciones especiales",
    15: "Dato valido pero por encima del rango normal — nivel menos severo",
    16: "Dato valido pero por encima del rango normal — nivel moderado",
    17: "Dato valido pero por debajo del rango normal — nivel menos severo",
    18: "Dato valido pero por debajo del rango normal — nivel moderado",
    19: "Dato recibido de la red con error",
    31: "La condicion existe",
}
# 20 a 30 son reservados en J1939-73.

# Como lo trata el PowerWizard.
ACCION_PW = {0: "parada (alto)", 1: "parada (bajo)", 15: "alarma (alto)",
             17: "alarma (bajo)", 31: "evento (entrada o condicion)"}

# SPN de motor de J1939-71 -> (nombre, codigos de modo de falla de la planta)
SPN = {
    38: ("Nivel de combustible del tanque externo", ("COM.AIRE.INYECTOR",)),
    82: ("Presion de aire de arranque", ()),
    94: ("Presion de entrega de combustible", ("COM.CONTAMINACION.AGUA", "COM.AIRE.INYECTOR")),
    97: ("Agua en el combustible", ("COM.CONTAMINACION.AGUA",)),
    98: ("Nivel de aceite del motor", ()),
    100: ("Presion de aceite del motor", ()),
    101: ("Presion del carter", ("MOT.PRESION_CARTER.RESPIRADERO",)),
    102: ("Presion del multiple de admision (sobrealimentacion)", ("MOT.DERRATEO.ALTURA",)),
    105: ("Temperatura del multiple de admision", ("MOT.DERRATEO.ALTURA",)),
    107: ("Presion diferencial del filtro de aire", ()),
    108: ("Presion barometrica", ("MOT.DERRATEO.ALTURA",)),
    110: ("Temperatura del refrigerante", ("TER.FUGA.REFRIGERANTE",)),
    111: ("Nivel del refrigerante", ("TER.FUGA.REFRIGERANTE",)),
    157: ("Presion del riel de inyeccion", ("COM.AIRE.INYECTOR",)),
    158: ("Tension de bateria en el interruptor de llave", ("ELE.NO_ARRANCA.BATERIA",)),
    168: ("Tension de bateria", ("ELE.NO_ARRANCA.BATERIA", "ELE.NO_ARRANCA.CARGADOR")),
    171: ("Temperatura del aire ambiente", ("MOT.DERRATEO.ALTURA",)),
    172: ("Temperatura del aire de admision", ("MOT.DERRATEO.ALTURA",)),
    173: ("Temperatura de los gases de escape", ("MOT.DERRATEO.ALTURA",
                                               "ESC.CARBONIZACION.BAJA_CARGA")),
    174: ("Temperatura del combustible", ()),
    175: ("Temperatura del aceite del motor", ()),
    190: ("Velocidad del motor", ("SIN.NO_SINCRONIZA.GOBERNADOR",)),
    247: ("Horas totales de operacion", ()),
    629: ("Controlador #1 (ECM)", ()),
    636: ("Sensor de posicion del motor", ()),
    637: ("Sensor de sincronizacion del motor", ()),
    639: ("Red J1939 #1", ()),
}

# Primeras comprobaciones por FMI, para el tecnico.
COMPROBAR = {
    0: "Confirmar con un instrumento independiente que el valor es real antes de buscar la causa.",
    1: "Confirmar con un instrumento independiente que el valor es real antes de buscar la causa.",
    2: "Revisar conectores y malla: un dato erratico suele ser conexion, no sensor.",
    3: "Medir el cableado del sensor: corto a positivo o sensor abierto con pull-up.",
    4: "Medir el cableado del sensor: corto a masa o falta de alimentacion.",
    5: "Medir continuidad del circuito: cable o conector abierto.",
    6: "Medir aislamiento a masa del circuito.",
    7: "Revisar el actuador o mecanismo: la orden sale y no hay respuesta.",
    8: "Revisar el sensor de frecuencia/pulso y su entrehierro.",
    9: "Revisar la red: terminacion de 120 ohm en los extremos y malla.",
    12: "Diagnosticar el modulo electronico con la herramienta del fabricante.",
    13: "Recalibrar segun el manual.",
    15: "Valor alto en nivel de alarma: atender antes de que llegue a parada.",
    17: "Valor bajo en nivel de alarma: atender antes de que llegue a parada.",
    19: "Revisar la red J1939: otro modulo envia el dato con error.",
    31: "Ver que entrada o condicion configurada esta activa.",
}


@dataclass
class Lectura:
    spn: int
    fmi: int
    parametro: str
    fmi_texto: str
    accion_tablero: str
    comprobar: str
    codigos_planta: tuple[str, ...]
    fuente: str
    conocido: bool

    def a_dict(self) -> dict:
        return asdict(self)


def decodificar(spn: int, fmi: int) -> Lectura:
    if not 0 <= fmi <= 31:
        raise ValueError(f"FMI {fmi} fuera de rango (0-31)")
    if 20 <= fmi <= 30:
        fmi_texto = "Reservado en J1939-73: consulte el manual del controlador"
    else:
        fmi_texto = FMI[fmi]
    if spn in SPN:
        nombre, codigos = SPN[spn]
        fuente, conocido = f"{FUENTE_SPN}; {FUENTE_FMI}", True
    elif 701 <= spn <= 711 and fmi == 31:
        nombre, codigos = "Entrada configurable del tablero (evento personalizado)", ()
        fuente, conocido = MANUAL_PW, True
    else:
        nombre, codigos = (f"SPN {spn}: no esta en la tabla de este modulo; buscarlo en el "
                           f"{MANUAL_PW}", ())
        fuente, conocido = MANUAL_PW, False
    return Lectura(spn, fmi, nombre, fmi_texto, ACCION_PW.get(fmi, "segun configuracion"),
                   COMPROBAR.get(fmi, "Ver el manual del controlador."), codigos, fuente,
                   conocido)


# --- perfiles de controlador -------------------------------------------------

@dataclass(frozen=True)
class Perfil:
    familia: str
    paralelo: bool | None      # None = no confirmado
    nota: str
    fuente: str


PERFILES = {
    "powerwizard": Perfil(
        "FG Wilson PowerWizard 1.0 / 1.1 / 1.1+ / 2.0 / 2.1", False,
        "Controlador de un solo grupo. Para paralelo, FG Wilson usa otros controladores "
        "(por ejemplo Woodward easYgen). La 2.1 agrega Modbus y medicion de potencia.",
        "Catalogos y manuales publicos de FG Wilson (confirmar con el distribuidor)"),
    "dse8610": Perfil("DSE8610 MKII", True,
                      "Sincronismo y reparto de kW/kVAr por enlace MSC.", "Hoja tecnica DSE"),
    "dse7320": Perfil("DSE7320 MKII", False,
                      "Control de un grupo con transferencia automatica (AMF).", "Hoja tecnica DSE"),
    "emcp4.4": Perfil("Caterpillar EMCP 4.4", True,
                      "Sincronismo y reparto hasta 16 grupos; modo de emergencia en estatismo "
                      "si cae el enlace.", "Paginas de producto y white paper de Caterpillar"),
    "pcc3300": Perfil("Cummins PowerCommand 3.3", True,
                      "Control con funciones de paralelo.", "Paginas de producto de Cummins"),
    "easygen": Perfil("Woodward easYgen", True,
                      "Controlador de paralelo usado en tableros de sincronismo.",
                      "Documentos de FG Wilson que lo nombran para paralelo"),
}


def perfil(marca: str | None, modelo: str | None) -> Perfil | None:
    t = f"{marca or ''} {modelo or ''}".lower().replace(" ", "")
    if "powerwizard" in t or "wizard" in t:
        return PERFILES["powerwizard"]
    if "8610" in t:
        return PERFILES["dse8610"]
    if "7320" in t:
        return PERFILES["dse7320"]
    if "emcp4.4" in t or "emcp44" in t:
        return PERFILES["emcp4.4"]
    if "3300" in t or "pcc3.3" in t:
        return PERFILES["pcc3300"]
    if "easygen" in t:
        return PERFILES["easygen"]
    return None


def revisar_controladores(planta: dict) -> list[dict]:
    """Que el controlador de cada unidad pueda hacer lo que la planta le pide."""
    obs = []
    unidades = planta.get("unidades") or []
    for u in unidades:
        ctl = u.get("controlador") or {}
        p = perfil(ctl.get("marca"), ctl.get("modelo"))
        if p is None:
            obs.append({"severidad": "oportunidad", "unidad": u.get("id", "?"),
                        "texto": f"Controlador «{ctl.get('marca') or ''} {ctl.get('modelo') or ''}» "
                                 "sin perfil: no se puede revisar si admite paralelo."})
            continue
        en_paralelo = len(unidades) > 1 and u.get("modo", "droop") != "solo"
        if en_paralelo and p.paralelo is False:
            obs.append({"severidad": "detiene", "unidad": u.get("id", "?"),
                        "texto": f"{p.familia} es de un solo grupo ({p.fuente}). Para ponerlo en "
                                 "paralelo hace falta un controlador de paralelo o un tablero de "
                                 "sincronismo aparte; si la unidad trabaja sola, declare "
                                 "\"modo\": \"solo\"."})
    return obs
