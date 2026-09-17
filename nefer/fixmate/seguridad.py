"""Lo que hay que hacer antes de tocar la maquina, y de donde sale.

Un diagnostico que termina en «desmontar el inyector 3» esta diciendole a
alguien que meta las manos en una maquina. Entre esa frase y el tecnico no
habia nada. Esto es lo que va en medio.

La regla de la casa es que nada se inventa y todo se cita, y una precaucion
tambien tiene que decir de donde viene. Por eso hay dos clases, y se rotulan
distinto:

- **Lo que dice el manual indexado.** Si entre lo recuperado hay una seccion
  de manual con una advertencia, se copia literal y se cita, igual que un par
  de apriete. Es evidencia.
- **La regla de la herramienta.** Una precaucion fija, siempre la misma, que
  no afirma nada sobre *esta* maquina: dice que hay que verificar antes de
  intervenir. No es evidencia y no se presenta como tal; va rotulada como lo
  que es. Callarla porque el historial no la menciona seria confundir «no
  esta escrito» con «no aplica», y eso en una excavadora lo paga alguien.

Que precaucion toca no se adivina: sale de los sistemas que el propio
procedimiento nombra. Si los pasos hablan de un cilindro, hay energia
hidraulica almacenada; si hablan del arranque, hay energia electrica; si
hablan de un inyector, hay combustible a presion. Un procedimiento que no
nombra ningun sistema reconocido igual lleva la precaucion de base, porque
toda intervencion en maquinaria pesada empieza igual.

Nada de esto reemplaza al manual OEM ni al procedimiento de bloqueo del
taller, y el texto lo dice en voz alta.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import texto as _texto

# Cada sistema: como se lo reconoce en el texto, y que hay que asegurar antes.
# Las palabras son las que usa un taller, no las de un catalogo.
SISTEMAS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("hidraulico",
     ("cilindro", "hidraulic", "manguera", "vastago", "sello", "bomba",
      "valvula", "acumulador", "presion", "pluma", "brazo", "cucharon",
      "aguilon", "estabilizador", "mastil"),
     "Descargue la presion hidraulica y apoye en el suelo lo que este "
     "levantado. El circuito queda con presion y la carga baja sola con la "
     "maquina apagada."),
    ("electrico",
     ("bateria", "borne", "arranque", "alternador", "fusible", "arnes",
      "electric", "motor de arranque", "alternador", "cable", "sensor",
      "ecm", "tablero"),
     "Desconecte el borne negativo de la bateria y espere. Un arranque que "
     "gira con alguien dentro del compartimiento no avisa."),
    ("combustible",
     ("inyector", "riel", "common rail", "combustible", "bomba de inyeccion",
      "caneria de alta", "petroleo", "diesel"),
     "El riel de inyeccion queda a presion despues de parar. Purgue segun el "
     "manual y no afloje una caneria de alta con el motor caliente: el "
     "chorro atraviesa un guante."),
    ("termico",
     ("refrigerante", "radiador", "termostato", "sobrecalent", "temperatura",
      "recalent", "tapa del radiador", "ventilador"),
     "Deje enfriar antes de abrir. Un radiador caliente esta presurizado y "
     "el ventilador puede arrancar solo."),
    ("neumatico",
     ("neumatic", "aire comprimido", "compresor", "calderin", "llanta",
      "aro", "neumatico"),
     "Purgue el aire comprimido antes de desarmar. Un aro con presion es "
     "una granada."),
)

# La que va siempre, nombre el procedimiento lo que nombre.
BASE = ("Bloquee y senalice la maquina antes de intervenir: motor detenido, "
        "llave fuera, tarjeta puesta. Si el procedimiento no le consta, "
        "pare y consulte el manual OEM.")

CIERRE = ("Esto no reemplaza al manual OEM ni al procedimiento de bloqueo "
          "del taller.")

# Como se rotula cada clase, para que se vea de donde sale sin leer el codigo.
DE_LA_HERRAMIENTA = "regla de la herramienta"
DEL_MANUAL = "manual"


@dataclass
class Precaucion:
    """Una precaucion y su procedencia. La procedencia no es decorativa."""

    texto: str
    origen: str                     # DE_LA_HERRAMIENTA o DEL_MANUAL
    referencia: str = ""            # de donde se copio, si es del manual
    sistema: str = ""

    def a_dict(self) -> dict:
        d = {"texto": self.texto, "origen": self.origen}
        if self.referencia:
            d["referencia"] = self.referencia
        if self.sistema:
            d["sistema"] = self.sistema
        return d


# Una linea de manual es advertencia si empieza avisando. Se copia literal.
AVISOS = ("peligro", "advertencia", "precaucion", "atencion", "cuidado",
          "aviso", "riesgo", "nunca ", "no opere", "antes de intervenir",
          "antes de desmontar", "bloquee", "despresurice", "desconecte la bateria")


def sistemas_de(*textos: str) -> list[str]:
    """Que sistemas nombra lo que se va a ejecutar. Sin adivinar: por palabra."""
    junto = _texto.normalizar(" ".join(t for t in textos if t))
    encontrados = []
    for nombre, palabras, _ in SISTEMAS:
        if any(p in junto for p in palabras):
            encontrados.append(nombre)
    return encontrados


def del_manual(coincidencias) -> list[Precaucion]:
    """Las advertencias que el manual indexado trae, copiadas y citadas.

    Solo de fragmentos de manual: una observacion escrita en una orden de
    trabajo es lo que le paso a una maquina, no una regla de seguridad.
    """
    salida: list[Precaucion] = []
    for c in coincidencias:
        fragmento = getattr(c, "fragmento", c)
        if getattr(fragmento, "tipo", "") != "manual":
            continue
        referencia = (fragmento.metadatos.get("seccion")
                      or fragmento.fuente or fragmento.id)
        for linea in str(fragmento.texto or "").splitlines():
            limpia = linea.strip(" -*\t")
            if not limpia or len(limpia) < 12:
                continue
            if any(_texto.normalizar(limpia).startswith(a) for a in AVISOS):
                salida.append(Precaucion(texto=limpia, origen=DEL_MANUAL,
                                         referencia=str(referencia)))
    return salida


def precauciones(pasos, coincidencias=None, causa: str = "") -> list[Precaucion]:
    """Lo que va antes de los pasos. Si hay pasos, esto nunca viene vacio.

    El orden es el del taller: primero bloquear, despues cada energia que el
    trabajo vaya a tocar, y al final lo que diga el manual —que es lo unico
    especifico de esta maquina y por eso cierra—.
    """
    if not pasos:
        return []

    salida = [Precaucion(texto=BASE, origen=DE_LA_HERRAMIENTA)]
    nombrados = sistemas_de(" ".join(pasos), causa)
    for nombre, _, aviso in SISTEMAS:
        if nombre in nombrados:
            salida.append(Precaucion(texto=aviso, origen=DE_LA_HERRAMIENTA,
                                     sistema=nombre))

    vistas = {p.texto for p in salida}
    for p in del_manual(coincidencias or []):
        if p.texto not in vistas:
            salida.append(p)
            vistas.add(p.texto)
    return salida
