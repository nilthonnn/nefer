"""El catalogo de causas: de lo que el tecnico escribio a un codigo estable.

Hoy la causa raiz es texto libre, y eso es el techo de todo lo demas.
«Filtro de aire colmatado», «filtro aire tapado» y «FILTRO DE AIRE
OBSTRUIDO» son tres causas distintas para el clasificador, tres intervalos
distintos para el MTBF y tres lineas distintas en la lista de repuestos. Lo
que hoy las junta es una heuristica de parecido de palabras, que acierta
seguido y falla en silencio.

ISO 14224 —la norma de recoleccion de datos de confiabilidad— resuelve esto
con una jerarquia de tres niveles, y la distincion importa porque
confundirla es el error de datos mas comun del rubro:

- **modo de falla**: lo que se observa        («fuga externa»)
- **mecanismo**: el proceso fisico que lo produjo  («desgaste»)
- **causa**: la condicion raiz que lo disparo      («sello vencido»)

Tres decisiones que este catalogo toma, y por que:

**No existe «Otro».** Es la recomendacion explicita de la norma y la razon
es empirica: «Otro» termina siendo el codigo mas usado de cualquier base mal
llevada, y una vez que pasa eso los datos no sirven para nada. Aqui, lo que
no casa con nada se queda **sin codificar**, y se cuenta. Ese numero es la
medida honesta de cuanto cubre el catalogo, y es lo que dice que hay que
agrandarlo.

**No se adivina.** Un texto entra en una entrada cuando trae sus palabras,
no cuando se le parece un poco. Codificar mal es peor que no codificar: un
codigo equivocado se agrega con los demas y ensucia la cuenta de toda la
flota, mientras que uno que falta se ve.

**El texto libre no se pierde.** Se guarda al lado. La norma dice
codificarlo; el taller escribio ahi lo que no cabe en ningun codigo —«con
una rebaba en el cromado»— y eso es justo lo que un manual OEM no trae.

El catalogo de fabrica cubre maquinaria pesada. Cada taller puede agregar
las suyas con `cargar()`: un catalogo que no se puede ampliar obliga a
elegir la entrada equivocada, que es volver al problema de «Otro» por otro
camino.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import texto as _texto

# Cuantas de sus palabras tiene que traer el texto para que una entrada
# cuente. Con una sola, «bomba» se lleva por delante la bomba hidraulica, la
# de inyeccion y la de agua.
MINIMO_PISTAS = 2

# Las pistas se escriben como raiz y casan por prefijo: «bateri» encuentra
# «bateria» y «baterias», «sulfatad» encuentra las cuatro terminaciones. El
# tokenizador no lematiza, y sin esto «Baterias sulfatadas» —asi, en plural
# y en femenino— no casaba con ninguna entrada. Se pide un minimo de letras
# para que una raiz corta no se lleve por delante media columna.
MINIMO_PARA_PREFIJO = 4

# Una pista de una sola palabra vale por dos cuando es inequivoca en el
# rubro: «sulfatado» no es otra cosa que un borne, «colmatado» no es otra
# cosa que un filtro.
INEQUIVOCAS = frozenset({
    "sulfatad", "colmatad", "cavitacion", "termostato", "turbo",
    "alternador", "inyector", "embrague", "radiador", "vastago",
    "acumulador",
})


# Un servicio planificado no es una falla. La norma separa lo correctivo de
# lo preventivo, y mezclarlos infla el MTBF y llena de cambios de aceite la
# lista de lo que le vuelve a pasar a la maquina. Ojo con la diferencia:
# «programado» es plan cumplido y no se codifica; «atrasado» o «vencido» si
# es un hallazgo, porque alguien no lo hizo a tiempo.
PLANIFICADO = ("programado", "programada", "preventivo", "preventiva",
               "rutina", "rutinario", "segun plan", "por horas",
               "mantenimiento de", "servicio de", "pm ")


@dataclass(frozen=True)
class Entrada:
    """Una causa del catalogo, con los tres niveles de la norma."""

    codigo: str
    sistema: str
    modo: str           # lo que se observa
    mecanismo: str      # el proceso fisico
    causa: str          # la condicion raiz
    pistas: tuple[str, ...]

    def a_dict(self) -> dict:
        return {"codigo": self.codigo, "sistema": self.sistema,
                "modo": self.modo, "mecanismo": self.mecanismo,
                "causa": self.causa}


def _casa(pista: str, palabras: set) -> bool:
    """Si el texto trae esa pista. Por prefijo cuando la raiz da para ello."""
    if pista in palabras:
        return True
    if len(pista) < MINIMO_PARA_PREFIJO:
        return False
    return any(p.startswith(pista) for p in palabras)


def _e(codigo, sistema, modo, mecanismo, causa, *pistas) -> Entrada:
    return Entrada(codigo, sistema, modo, mecanismo, causa, tuple(pistas))


# El catalogo de fabrica. Sale de lo que un taller de maquinaria pesada
# escribe de verdad en la columna de causa raiz, no de un catalogo de
# fabricante: los codigos tienen que reconocer lo que ya esta escrito.
DE_FABRICA: tuple[Entrada, ...] = (
    # ---------------------------------------------------- admision y escape
    _e("ADM.RESTRICCION.FILTRO", "admision", "Perdida de potencia",
       "Obstruccion", "Filtro de aire colmatado",
       "filtro", "aire", "colmatad", "tapad", "obstruid", "saturad",
       "restriccion", "admision", "sucio"),
    _e("ESC.FUGA.MULTIPLE", "escape", "Fuga de gases", "Fatiga termica",
       "Junta o multiple de escape fisurado",
       "escape", "multiple", "junta", "fisura", "fuga", "gases", "sopla"),
    _e("ADM.BAJA_PRESION.TURBO", "admision", "Perdida de potencia",
       "Desgaste", "Turbo con holgura o alabes dañados",
       "turbo", "turbocompresor", "holgura", "alabe", "sopla", "presion"),

    # ---------------------------------------------------------- combustible
    _e("COM.COMBUSTION.INYECTOR", "combustible", "Marcha inestable",
       "Desgaste", "Inyector con retorno excesivo o goteo",
       "inyector", "retorno", "gote", "pulveriza", "combustion", "excesiv"),
    _e("COM.RESTRICCION.FILTRO", "combustible", "Falta de potencia",
       "Obstruccion", "Filtro de combustible colmatado",
       "filtro", "combustible", "petroleo", "diesel", "colmatad", "tapad",
       "obstruid"),
    _e("COM.CONTAMINACION.AGUA", "combustible", "Marcha inestable",
       "Contaminacion", "Agua o particulas en el combustible",
       "agua", "combustible", "contaminad", "particula", "sedimento",
       "tanque", "condensacion"),
    _e("COM.BAJA_PRESION.BOMBA", "combustible", "No arranca",
       "Desgaste", "Bomba de inyeccion con baja presion",
       "bomba", "inyeccion", "presion", "combustible", "riel"),

    # ------------------------------------------------------------ hidraulico
    _e("HID.FUGA.SELLO", "hidraulico", "Fuga externa", "Desgaste",
       "Sello o reten de cilindro vencido",
       "sello", "reten", "vastago", "cilindro", "fuga", "gote", "aceite",
       "empaquetadura"),
    _e("HID.FUGA.MANGUERA", "hidraulico", "Fuga externa", "Abrasion",
       "Manguera picada o acople flojo",
       "manguera", "acople", "picad", "rozand", "fuga", "reventad",
       "conexion", "abrazadera"),
    _e("HID.BAJA_PRESION.BOMBA", "hidraulico", "Perdida de fuerza",
       "Desgaste", "Bomba hidraulica con baja presion",
       "bomba", "hidraulic", "presion", "caudal", "fuerza", "desgaste"),
    _e("HID.DERIVA.VALVULA", "hidraulico", "Movimiento involuntario",
       "Fuga interna", "Valvula de retencion o de mando con fuga interna",
       "valvula", "retencion", "deriva", "interna", "mando", "distribuidor"),
    _e("HID.CONTAMINACION.ACEITE", "hidraulico", "Desgaste acelerado",
       "Contaminacion", "Aceite hidraulico contaminado o vencido",
       "aceite", "hidraulic", "contaminad", "sucio", "particula", "analisis"),
    _e("HID.SOBRECALENTAMIENTO.ENFRIADOR", "hidraulico",
       "Temperatura alta de aceite", "Obstruccion",
       "Enfriador de aceite obstruido",
       "enfriador", "aceite", "obstruid", "temperatura", "hidraulic", "panal"),

    # -------------------------------------------------------------- electrico
    _e("ELE.NO_ARRANCA.BORNES", "electrico", "No arranca", "Corrosion",
       "Bornes de bateria sulfatados o flojos",
       "borne", "bateri", "sulfatad", "flojo", "corrosion", "terminal"),
    _e("ELE.NO_ARRANCA.BATERIA", "electrico", "No arranca", "Envejecimiento",
       "Bateria descargada o con vaso en corto",
       "bateri", "descargad", "vaso", "densidad", "corto", "arranca",
       "lento"),
    _e("ELE.NO_CARGA.ALTERNADOR", "electrico", "No carga", "Desgaste",
       "Alternador o regulador en falla",
       "alternador", "carga", "regulador", "carbon", "correa", "amperaje",
       "voltaje"),
    _e("ELE.NO_ARRANCA.MOTOR_ARRANQUE", "electrico", "No arranca",
       "Desgaste", "Motor de arranque o solenoide en falla",
       "arranque", "solenoide", "bendix", "carbon", "burro"),
    _e("ELE.FALSO_CONTACTO.ARNES", "electrico", "Falla intermitente",
       "Abrasion", "Arnes rozado o conector con falso contacto",
       "arnes", "conector", "cable", "falso", "contacto", "intermitente",
       "rozad", "empalme"),
    _e("ELE.LECTURA_ERRATICA.SENSOR", "electrico", "Lectura erratica",
       "Deriva", "Sensor descalibrado o en falla",
       "sensor", "lectura", "erratic", "descalibrad", "señal", "tablero",
       "testigo"),

    # -------------------------------------------------------------- termico
    _e("TER.SOBRECALENTAMIENTO.RADIADOR", "termico", "Sobrecalentamiento",
       "Obstruccion", "Radiador obstruido por tierra o incrustacion",
       "radiador", "obstruid", "panal", "tierra", "incrustacion",
       "sobrecalient", "calient", "temperatura"),
    _e("TER.SOBRECALENTAMIENTO.TERMOSTATO", "termico", "Temperatura anormal",
       "Atascamiento", "Termostato trabado",
       "termostato", "trabad", "abiert", "cerrad", "temperatura", "calient"),
    _e("TER.FUGA.REFRIGERANTE", "termico", "Fuga de refrigerante",
       "Desgaste", "Manguera, tapa o bomba de agua con fuga",
       "refrigerante", "fuga", "agua", "tapa", "manguera", "nivel"),
    _e("TER.SOBRECALENTAMIENTO.VENTILADOR", "termico", "Sobrecalentamiento",
       "Desgaste", "Ventilador, correa o embrague viscoso en falla",
       "ventilador", "correa", "viscos", "embrague", "tensor", "floj"),

    # ------------------------------------------------------------- neumatico
    _e("NEU.FUGA.AIRE", "neumatico", "Perdida de presion de aire", "Desgaste",
       "Fuga en circuito de aire comprimido",
       "aire", "comprimid", "fuga", "presion", "calderin", "purga",
       "neumatic"),
    _e("NEU.BAJA_PRESION.LLANTA", "neumatico", "Presion baja en llanta",
       "Perforacion", "Llanta con perforacion o valvula con fuga",
       "llanta", "neumatic", "perforacion", "clavo", "valvula", "presion"),

    # ------------------------------------------------- transmision y frenos
    _e("TRA.PATINA.EMBRAGUE", "transmision", "Patinamiento", "Desgaste",
       "Embrague o disco desgastado",
       "embrague", "disco", "patina", "desgastad", "clutch", "resbala"),
    _e("TRA.RUIDO.RODAMIENTO", "transmision", "Ruido anormal", "Fatiga",
       "Rodamiento picado o sin lubricacion",
       "rodamiento", "ruido", "picad", "cojinete", "balero", "zumbido"),
    _e("TRA.FUGA.RETEN", "transmision", "Fuga externa", "Desgaste",
       "Reten de transmision o mando final vencido",
       "reten", "transmision", "mando", "final", "fuga", "diferencial",
       "corona"),
    _e("FRE.BAJA_EFICACIA.PASTILLAS", "frenos", "Frenado deficiente",
       "Desgaste", "Pastillas, bandas o discos desgastados",
       "freno", "pastilla", "banda", "disco", "desgastad", "zapata", "frena"),

    # ------------------------------------------------- estructura y desgaste
    _e("EST.FISURA.SOLDADURA", "estructura", "Fisura", "Fatiga",
       "Fisura en soldadura o elemento estructural",
       "fisura", "grieta", "soldadura", "rajad", "estructura", "chasis",
       "quebrad", "trizad"),
    _e("EST.DESGASTE.TREN_RODAJE", "estructura", "Desgaste excesivo",
       "Abrasion", "Tren de rodaje o cadena fuera de tolerancia",
       "cadena", "rodaje", "zapata", "rodillo", "eslabon", "desgaste",
       "tension", "oruga"),
    _e("EST.DESGASTE.DIENTES", "estructura", "Desgaste excesivo", "Abrasion",
       "Dientes o cuchillas de cucharon gastados",
       "diente", "cuchilla", "cucharon", "gastad", "adaptador"),

    # ------------------------------------------------------ lubricacion y uso
    _e("LUB.FALTA.NIVEL", "lubricacion", "Nivel bajo", "Consumo o fuga",
       "Nivel de aceite bajo por consumo o fuga",
       "nivel", "aceite", "consumo", "rellenar", "lubricacion"),
    # Ojo: esto es el servicio que NO se hizo a tiempo, no el que se hizo.
    # «cambio», «aceite» y «mantenimiento» no son pistas: aparecen en toda
    # orden de servicio cumplida y la codificaban como si fuera una falla.
    _e("LUB.VENCIDO.INTERVALO", "lubricacion", "Aceite fuera de servicio",
       "Degradacion", "Aceite o filtro fuera de intervalo",
       "intervalo", "vencid", "atrasad", "sobrepasad", "excedid", "horas"),
    _e("OPE.DAÑO.OPERACION", "operacion", "Daño por uso", "Sobrecarga o mal uso",
       "Sobrecarga, golpe o maniobra indebida",
       "golpe", "sobrecarga", "operador", "maniobra", "choque", "impacto"),
)


class Catalogo:
    """El catalogo con el que se codifica. De fabrica, mas lo del taller."""

    def __init__(self, entradas=None):
        self.entradas: list[Entrada] = list(entradas if entradas is not None
                                            else DE_FABRICA)
        self._por_codigo = {e.codigo: e for e in self.entradas}
        self._preparadas = [(e, {_texto.normalizar(p) for p in e.pistas})
                            for e in self.entradas]

    def __len__(self) -> int:
        return len(self.entradas)

    def __contains__(self, codigo: str) -> bool:
        return codigo in self._por_codigo

    def get(self, codigo: str) -> Entrada | None:
        return self._por_codigo.get(codigo)

    def clasificar(self, texto: str) -> Entrada | None:
        """La entrada que le corresponde a un texto, o None. Nunca adivina.

        Gana la que mas pistas suyas encuentre. En empate, ninguna: dos
        entradas igual de defendibles quieren decir que el texto no alcanza
        para decidir, y elegir una a la suerte es peor que dejarlo sin
        codificar, porque el error se suma a la cuenta de la flota.
        """
        normal = _texto.normalizar(texto)
        if any(m in normal for m in PLANIFICADO):
            return None
        palabras = set(_texto.tokenizar(texto))
        if not palabras:
            return None

        marcador: list[tuple[int, Entrada]] = []
        for entrada, pistas in self._preparadas:
            puntos = 0
            for pista in pistas:
                if not _casa(pista, palabras):
                    continue
                puntos += 1
                # Una pista inequivoca en el rubro vale por dos.
                if pista in INEQUIVOCAS:
                    puntos += 1
            if puntos >= MINIMO_PISTAS:
                marcador.append((puntos, entrada))

        if not marcador:
            return None
        marcador.sort(key=lambda p: (-p[0], p[1].codigo))
        if len(marcador) > 1 and marcador[0][0] == marcador[1][0]:
            return None
        return marcador[0][1]

    def cobertura(self, causas) -> dict:
        """Cuanto del historial queda codificado, y que se quedo fuera.

        El numero que importa no es el de aciertos: es el de lo que no se
        pudo codificar, con los textos, porque eso es la lista de lo que
        hay que agregarle al catalogo.
        """
        codificadas: dict[str, int] = {}
        sin_codigo: dict[str, int] = {}
        for causa in causas:
            limpia = str(causa or "").strip()
            if not limpia:
                continue
            entrada = self.clasificar(limpia)
            if entrada is None:
                sin_codigo[limpia] = sin_codigo.get(limpia, 0) + 1
            else:
                codificadas[entrada.codigo] = codificadas.get(entrada.codigo, 0) + 1

        total = sum(codificadas.values()) + sum(sin_codigo.values())
        return {
            "total": total,
            "codificadas": sum(codificadas.values()),
            "sin_codigo": sum(sin_codigo.values()),
            "cobertura": round(sum(codificadas.values()) / total, 3) if total else 0.0,
            "por_codigo": dict(sorted(codificadas.items(),
                                      key=lambda p: (-p[1], p[0]))),
            # Lo mas repetido primero: es lo que mas rinde agregar.
            "faltantes": [t for t, _ in sorted(sin_codigo.items(),
                                               key=lambda p: (-p[1], p[0]))],
        }

    def agregar(self, entrada: Entrada) -> None:
        if entrada.codigo in self._por_codigo:
            raise ValueError(f"el codigo {entrada.codigo} ya esta en el catalogo")
        self.entradas.append(entrada)
        self._por_codigo[entrada.codigo] = entrada
        self._preparadas.append(
            (entrada, {_texto.normalizar(p) for p in entrada.pistas}))


def cargar(ruta: str | Path, base: Catalogo | None = None) -> Catalogo:
    """Suma al catalogo las causas propias del taller, desde un JSON.

    Un catalogo que no se puede ampliar obliga al tecnico a elegir la entrada
    equivocada, que es volver al problema de «Otro» por otro camino.

        [{"codigo": "HID.FUGA.CILINDRO_GIRO", "sistema": "hidraulico",
          "modo": "Fuga externa", "mecanismo": "Desgaste",
          "causa": "Sello del cilindro de giro", "pistas": ["giro", "sello"]}]
    """
    ruta = Path(ruta)
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{ruta.name}: no se pudo leer el catalogo ({exc}).") from exc
    if not isinstance(datos, list):
        raise ValueError(f"{ruta.name}: el catalogo es una lista de entradas.")

    catalogo = base or Catalogo()
    for n, cruda in enumerate(datos, 1):
        faltan = [c for c in ("codigo", "sistema", "modo", "mecanismo", "causa")
                  if not str(cruda.get(c, "")).strip()]
        if faltan:
            raise ValueError(
                f"{ruta.name}, entrada {n}: le falta {', '.join(faltan)}. "
                "Los tres niveles de la norma son obligatorios: sin el modo "
                "no se sabe que se observo, y sin la causa no se sabe que "
                "arreglar.")
        pistas = [str(p) for p in (cruda.get("pistas") or []) if str(p).strip()]
        if len(pistas) < MINIMO_PISTAS:
            raise ValueError(
                f"{ruta.name}, entrada {n} ({cruda['codigo']}): hacen falta "
                f"al menos {MINIMO_PISTAS} pistas. Con una sola, la entrada "
                "se lleva por delante todo lo que la mencione.")
        catalogo.agregar(Entrada(
            codigo=str(cruda["codigo"]).strip(), sistema=str(cruda["sistema"]).strip(),
            modo=str(cruda["modo"]).strip(), mecanismo=str(cruda["mecanismo"]).strip(),
            causa=str(cruda["causa"]).strip(), pistas=tuple(pistas)))
    return catalogo


# El de fabrica, armado una sola vez.
POR_DEFECTO = Catalogo()
