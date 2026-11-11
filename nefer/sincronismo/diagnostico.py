"""Guia de sintomas del paralelo de grupos electrogenos.

Esto es REFERENCIA, no antecedente. Ordena las causas posibles de un
sintoma de sincronismo en el orden en que conviene descartarlas (de la mas
barata de comprobar a la mas cara), con la medicion que confirma o descarta
cada una. No dice cual es la causa en un equipo concreto: eso lo dice el
tecnico con el multimetro, y lo que confirme se cierra en FixMate
(`nefer fixmate cerrar`) para que la flota lo aprenda.

`exportar_markdown()` escribe la guia como un manual que FixMate indexa
igual que un manual de fabricante, asi la busqueda del telefono tambien la
encuentra.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

ROTULO = "Guia de referencia — no es antecedente de la flota"


@dataclass
class Causa:
    causa: str
    comprobacion: str


@dataclass
class Sintoma:
    id: str
    titulo: str
    claves: tuple[str, ...]
    ansi: tuple[str, ...]
    causas: tuple[Causa, ...]

    def a_dict(self) -> dict:
        d = asdict(self)
        d["rotulo"] = ROTULO
        return d


GUIA: tuple[Sintoma, ...] = (
    Sintoma(
        "S1", "No sincroniza: el interruptor no recibe orden de cierre",
        ("no sincroniza", "no cierra", "no entra en paralelo", "tarda en sincronizar",
         "timeout sincronismo", "falla de sincronismo"),
        ("25",),
        (
            Causa("Ventanas del sincronoscopio mas estrechas de lo que el "
                  "gobernador puede sostener",
                  "Compare ±Δf/±ΔV/±Δφ del controlador con la estabilidad real de "
                  "frecuencia en vacio (oscilacion pico a pico en 30 s)."),
            Causa("Gobernador inestable (ganancias o actuador)",
                  "Registre la frecuencia en vacio: una oscilacion > 0.1 Hz no "
                  "deja que el angulo se quede en ventana. Revise varillaje y "
                  "ganancias P/I."),
            Causa("Consigna de tension del AVR distinta de la de barra",
                  "Mida V generador y V barra en el mismo instrumento; ΔV debe "
                  "quedar dentro de la ventana con margen."),
            Causa("Medicion de barra equivocada: fusible de TP abierto, fase "
                  "cruzada o relacion mal declarada",
                  "Con la barra energizada, mida las tres tensiones de TP en "
                  "bornera del controlador y compare con la barra."),
            Causa("Secuencia de fases invertida entre generador y barra",
                  "Secuencimetro en los dos lados del interruptor. Nunca se "
                  "corrige desde el controlador."),
            Causa("Circuito de cierre: bobina, resorte sin cargar, enclavamiento "
                  "o permisivo externo abierto",
                  "Verifique tension de mando en la bobina de cierre al momento "
                  "de la orden y el estado del motor de carga de resortes."),
        ),
    ),
    Sintoma(
        "S2", "Dispara por potencia inversa al cerrar o al bajar carga",
        ("potencia inversa", "reverse power", "32", "motoriza", "dispara al cerrar",
         "dispara al descargar"),
        ("32", "25"),
        (
            Causa("Cierre con deslizamiento negativo (generador mas lento)",
                  "Lea el deslizamiento en la orden de cierre: debe ser levemente "
                  "positivo (+0.05 a +0.2 Hz)."),
            Causa("Rampa de descarga que llega a 0 kW antes de abrir",
                  "Revise el umbral de apertura de la rampa: debe abrir antes de "
                  "cruzar a potencia negativa (tipico 5–10 % kW)."),
            Causa("Restriccion de combustible: filtros, aire en la linea, "
                  "bomba de transferencia",
                  "Tome carga en escalones; si cae la frecuencia y no recupera, "
                  "mida restriccion de filtros y presion de combustible."),
            Causa("Polaridad o relacion de TC equivocada en el controlador",
                  "Con carga resistiva conocida, compare los kW del controlador "
                  "con una pinza de potencia: signo y magnitud."),
            Causa("Ajuste de la 32 demasiado sensible o sin retardo",
                  "Revise pickup y retardo contra el estudio de coordinacion."),
        ),
    ),
    Sintoma(
        "S3", "Oscilacion de carga activa entre unidades (pendulea, hunting)",
        ("oscila", "pendulea", "hunting", "se pasan la carga", "fluctua kw",
         "inestable en paralelo"),
        ("32",),
        (
            Causa("Ganancias del gobernador altas para el paralelo",
                  "Baje la ganancia proporcional de a 10 % y observe la "
                  "amplitud de la oscilacion de kW."),
            Causa("Lineas de reparto de carga con ruido o sin malla aterrada en "
                  "un solo extremo",
                  "Revise el cable apantallado de las lineas de reparto: malla "
                  "a tierra solo del lado del controlador."),
            Causa("Mas de una unidad en isocrono sin reparto por lineas",
                  "Revise el modo de cada unidad: una sola en isocrono, o todas "
                  "con reparto isocrono por lineas o bus de comunicacion."),
            Causa("Juego en el varillaje o actuador gastado",
                  "Mueva el actuador a mano con el motor detenido y mida el "
                  "juego; compare la corriente del actuador con la del manual."),
        ),
    ),
    Sintoma(
        "S4", "Reparto de reactivos desigual o corriente circulante",
        ("kvar", "reactivo", "reactiva", "corriente circulante", "factor de potencia",
         "fp desigual", "una absorbe reactivos", "sobreexcitada"),
        ("40",),
        (
            Causa("Consignas de tension del AVR distintas entre unidades",
                  "Mida la tension en vacio de cada unidad con el mismo "
                  "instrumento; deben coincidir dentro de 0.5 %."),
            Causa("Estatismo de tension deshabilitado o distinto entre AVR",
                  "Revise el ajuste de droop de cada AVR (tipico 3–5 %) y que "
                  "sea igual en todas."),
            Causa("TC de compensacion de estatismo con polaridad invertida o en "
                  "la fase equivocada",
                  "El TC de droop va en la fase que el manual del AVR indica "
                  "(habitualmente B) y con su polaridad: con carga inductiva la "
                  "tension debe BAJAR al aumentar la corriente."),
            Causa("Control de factor de potencia o de kVAr del controlador "
                  "peleando con el AVR",
                  "Deje un solo lazo a cargo de los reactivos: el del "
                  "controlador o el estatismo del AVR."),
        ),
    ),
    Sintoma(
        "S5", "Disparo por perdida de excitacion",
        ("perdida de excitacion", "loss of excitation", "40", "subexcitada",
         "absorbe reactivos", "campo"),
        ("40",),
        (
            Causa("Fusible o alimentacion del AVR",
                  "Mida la alimentacion del AVR (PMG o shunt) y la corriente de "
                  "campo de la excitatriz bajo carga."),
            Causa("Diodos rotativos o varistor en falla",
                  "Con el equipo detenido, mida cada diodo del puente rotativo "
                  "en directo e inverso, desconectado."),
            Causa("Sensado de tension del AVR abierto o con fase faltante",
                  "Mida la tension de sensado en la bornera del AVR."),
            Causa("Unidad empujada a subexcitarse por otra con consigna alta",
                  "Ver sintoma S4: el reparto de kVAr desigual termina aqui."),
        ),
    ),
    Sintoma(
        "S6", "Golpe mecanico, ruido o pico de corriente al cerrar",
        ("golpe", "ruido al cerrar", "pico de corriente", "estruendo", "brinca",
         "cierre brusco", "cierre fuera de fase"),
        ("25",),
        (
            Causa("Angulo en el contacto mayor que el de la orden: tiempo de "
                  "cierre del interruptor no compensado",
                  "Mida el tiempo de cierre del interruptor y calcule el angulo "
                  "de adelanto (nefer sincronismo verificar)."),
            Causa("Deslizamiento alto en el momento de la orden",
                  "Baje la ventana de Δf o la consigna de deslizamiento."),
            Causa("Medicion de angulo desplazada: TP en otra fase o conexion "
                  "estrella/triangulo distinta entre lados",
                  "Sincronoscopio externo en paralelo con el del controlador: "
                  "los dos deben marcar cero en el mismo instante."),
        ),
    ),
    Sintoma(
        "S7", "Reparto de carga activa desigual en regimen",
        ("reparto desigual", "no reparte", "una toma toda la carga",
         "kw desigual", "load sharing", "reparto de carga"),
        (),
        (
            Causa("Consignas de velocidad en vacio distintas (unidades en droop)",
                  "Calcule el reparto esperado (nefer sincronismo estatismo) y "
                  "compare con lo medido; ajuste la consigna sugerida."),
            Causa("Estatismo distinto entre gobernadores",
                  "Revise que todas tengan el mismo estatismo en %."),
            Causa("Lineas de reparto abiertas o una unidad fuera del bus de "
                  "comunicacion",
                  "Revise la tension de la linea de reparto en cada controlador "
                  "y el estado del bus (CAN/intercontrolador)."),
            Causa("Unidad que no puede tomar carga: limite de combustible, "
                  "temperatura de escape o derrateo por altura",
                  "Revise si alguna unidad esta en limitacion o con derrateo "
                  "activo en el controlador."),
        ),
    ),
)


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip()


def buscar(descripcion: str, limite: int = 3) -> list[tuple[Sintoma, int]]:
    """Sintomas cuyas claves aparecen en la descripcion, por coincidencias."""
    q = _norm(descripcion)
    palabras = set(re.findall(r"[a-z0-9]+", q))
    puntajes = []
    for s in GUIA:
        p = 0
        for clave in s.claves:
            c = _norm(clave)
            if " " in c:
                p += 3 if c in q else 0
            elif c in palabras:
                p += 2
        for ansi in s.ansi:
            if ansi.lower() in palabras:
                p += 1
        if p:
            puntajes.append((s, p))
    puntajes.sort(key=lambda x: -x[1])
    return puntajes[:limite]


def exportar_markdown() -> str:
    """La guia como manual indexable por FixMate."""
    lineas = [
        "# Guia de sintomas del paralelo de grupos electrogenos",
        "",
        f"{ROTULO}. Generada por `nefer sincronismo guia`; no editar a mano.",
        "Ordena las causas de cada sintoma de la mas barata de descartar a la",
        "mas cara. No sustituye el manual del controlador ni del AVR.",
        "",
    ]
    for s in GUIA:
        lineas.append(f"## {s.id}. {s.titulo}")
        lineas.append("")
        if s.ansi:
            lineas.append(f"Funciones ANSI relacionadas: {', '.join(s.ansi)}.")
            lineas.append("")
        lineas.append(f"Tambien se describe como: {'; '.join(s.claves)}.")
        lineas.append("")
        for n, c in enumerate(s.causas, 1):
            lineas.append(f"{n}. **{c.causa}.** {c.comprobacion}")
        lineas.append("")
    return "\n".join(lineas)
