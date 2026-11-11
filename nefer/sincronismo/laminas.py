"""Laminas didacticas de conexion: TTA y sincronismo, por capas.

Una lamina es una pagina HTML de un solo archivo (abre sin red, en el
telefono o en la PC) con:

1. El esquema de UNA unidad con todo su cableado real: fusibles de TP,
   bornera seccionable del TC, reles interpuestos, bobinas de cierre y
   disparo, auxiliar 52a, parada de emergencia, J1939 al ECM, enlace entre
   modulos y polarizacion del AVR.
2. Botones por capa —potencia, medicion, mando, comunicacion— que dejan
   solo esa capa encendida. Asi se estudia, y asi se busca una falla: una
   capa a la vez.
3. Por cada capa: que hace, como se verifica con el multimetro y el error
   tipico que se encuentra en campo.
4. La secuencia de operacion paso a paso; cada paso enciende la capa que
   actua en ese momento.

Lo que se rotula es lo estandar y verificable: designaciones IEC/ANSI
(52G, KM1, YC, YO, 52a), señales L1-L2-L3-N, la terminacion de 120 ohm en
los extremos del bus CAN (ISO 11898 / SAE J1939). Los numeros de borne del
modulo no: se toman de la planta (`bornes`) o se remite al manual DSE.
Tiempos y umbrales quedan como «configurable»: dependen del ajuste de cada
tablero y una cifra tipica en una lamina se copia como si fuera la norma.
"""

from __future__ import annotations

import json
from xml.sax.saxutils import escape

from .diagramas import MANUAL

CAPAS = {
    "pot": ("Potencia", "#1f2937"),
    "med": ("Medicion", "#b45309"),
    "man": ("Mando", "#2563eb"),
    "com": ("Comunicacion", "#059669"),
}


# --- primitivas SVG ----------------------------------------------------------

def _t(x, y, s, cls="s", anchor="middle"):
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{escape(str(s))}</text>'


def _p(puntos, capa, extra=""):
    d = " ".join(f"{'M' if i == 0 else 'L'}{x},{y}" for i, (x, y) in enumerate(puntos))
    return f'<path d="{d}" class="l-{capa}" {extra}/>'


def _caja(x, y, w, h, cls="caja", rx=6):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{cls}"/>'


def _g(capa, *partes):
    return f'<g class="capa" data-capa="{capa}">' + "\n".join(partes) + "</g>"


def _fusible(x, y, rot):
    """Fusible horizontal centrado en (x, y)."""
    return (_caja(x - 12, y - 5, 24, 10, "fus", 2) + _t(x, y - 9, rot, "r"))


def _bobina(x, y, rot):
    return (f'<circle cx="{x}" cy="{y}" r="11" class="bob"/>' + _t(x, y + 4, rot, "r"))


def _contacto_na(x, y, rot):
    """Contacto normalmente abierto vertical entre y-14 y y+14."""
    return (f'<path d="M{x},{y - 14} L{x},{y - 6} M{x - 7},{y - 4} L{x + 3},{y + 6} '
            f'M{x},{y + 6} L{x},{y + 14}" class="l-man"/>' + _t(x + 10, y + 4, rot, "r", "start"))


def _contacto_nc(x, y, rot):
    return (f'<path d="M{x},{y - 14} L{x},{y - 6} M{x - 8},{y - 6} L{x + 6},{y + 6} '
            f'M{x},{y + 6} L{x},{y + 14} M{x - 8},{y - 6} L{x - 8},{y - 1}" class="l-man"/>'
            + _t(x + 10, y + 4, rot, "r", "start"))


def _na_h(x, y, rot=""):
    """Contacto NA sobre un peldaño horizontal, centrado en (x, y)."""
    return (f'<path d="M{x - 16},{y} L{x - 6},{y} M{x - 6},{y} L{x + 6},{y - 9} '
            f'M{x + 6},{y} L{x + 16},{y}" class="l-man"/>'
            f'<path d="M{x - 6},{y - 5} L{x - 6},{y + 5} M{x + 6},{y - 5} L{x + 6},{y + 5}" '
            f'class="l-man"/>' + (_t(x, y + 18, rot, "r") if rot else ""))


def _nc_h(x, y, rot=""):
    return (_na_h(x, y) + f'<path d="M{x - 9},{y + 6} L{x + 9},{y - 8}" class="l-man"/>'
            + (_t(x, y + 18, rot, "r") if rot else ""))


def _rele(x, y, rot, sub=""):
    return (_caja(x - 22, y - 12, 44, 24, "bob", 4) + _t(x, y + 4, rot, "p")
            + (_t(x, y + 24, sub, "r") if sub else ""))


def _interruptor(x, y, rot, capa="pot"):
    """Polo de potencia vertical de y a y+44."""
    return (f'<path d="M{x},{y} L{x},{y + 12} M{x},{y + 12} L{x + 14},{y + 32} '
            f'M{x},{y + 32} L{x},{y + 44}" class="l-{capa}"/>'
            f'<circle cx="{x}" cy="{y + 12}" r="3" class="punto"/>'
            f'<circle cx="{x}" cy="{y + 32}" r="3" class="punto"/>'
            + _t(x - 14, y + 27, rot, "t", "end"))


def _tc(x, y):
    return (f'<circle cx="{x - 7}" cy="{y}" r="7" class="anillo"/>'
            f'<circle cx="{x + 7}" cy="{y}" r="7" class="anillo"/>')


def _pin(x, y, rot, lado="izq"):
    """Borne del modulo: un cuadradito en el borde y su rotulo hacia adentro."""
    ancla, dx = ("start", 10) if lado == "izq" else ("end", -10)
    return (f'<rect x="{x - 4}" y="{y - 4}" width="8" height="8" class="pin"/>'
            + _t(x + dx, y + 4, rot, "p", ancla))


def _borne(bornes, clave, manual):
    v = (bornes or {}).get(clave)
    return f"borne {v}" if v else f"borne: ver {manual}"


# --- lamina de sincronismo ----------------------------------------------------

def _svg_sincronismo(planta: dict) -> str:
    u = (planta.get("unidades") or [{}])[0]
    ident = u.get("id", "GE-01")
    otras = [x.get("id") for x in (planta.get("unidades") or [])[1:]] or ["GE-02"]
    ctl = u.get("controlador") or {}
    mot = u.get("motor") or {}
    modelo = ctl.get("modelo") or "8610 MKII"
    nombre_mod = f"{ctl.get('marca') or 'DSE'} {modelo}"
    manual = MANUAL.get(("DSE" + modelo.replace(" ", "")).split("MK")[0], "manual del modulo")
    b = u.get("bornes", {})
    v = planta.get("v_nominal", 380)
    f = planta.get("f_nominal", 60)
    marca_motor = mot.get("marca") or "motor"

    X = 150           # columna de potencia
    MX, MY, MW, MH = 430, 140, 300, 300   # modulo
    out = []

    # Potencia
    out.append(_g("pot",
        f'<circle cx="{X}" cy="90" r="34" class="gen"/>', _t(X, 96, "G", "big"),
        _t(X - 44, 76, ident, "t", "end"),
        _t(X - 44, 92, f"{marca_motor} {mot.get('modelo') or ''}".strip(), "r", "end"),
        _t(X - 44, 106, f"{v:g} V {f:g} Hz 3F+N", "r", "end"),
        _p([(X, 124), (X, 290)], "pot"),
        _interruptor(X, 290, "52G"),
        _p([(X, 334), (X, 500)], "pot"),
        _p([(60, 500), (960, 500)], "pot", 'stroke-width="6"'),
        _t(64, 492, f"BARRA COMUN {v:g} V", "t", "start"),
        _t(956, 492, f"→ {', '.join(otras)} y carga", "r", "end"),
    ))

    # Medicion: TP de generador (antes del 52G), TC, TP de barra (despues)
    out.append(_g("med",
        _tc(X, 200), _t(X - 22, 204, "TC", "t", "end"),
        _p([(X, 150), (250, 150), (250, 175)], "med"), _fusible(250, 186, "F1-F3"),
        _p([(250, 197), (250, 200), (MX, 200)], "med"),
        _t(260, 146, "V gen: ANTES del 52G", "r", "start"),
        _p([(X + 14, 200), (X + 30, 200), (X + 30, 240), (300, 240)], "med"),
        _caja(300, 228, 54, 24, "bornera", 3), _t(327, 244, "X-TC", "r"),
        _t(327, 222, "bornera seccionable", "r"),
        _p([(354, 240), (MX, 240)], "med"),
        _p([(400, 500), (400, 410), (MX, 410)], "med"), _fusible(400, 470, "F4-F6"),
        _t(410, 492, "V barra: DESPUES del 52G", "r", "start"),
    ))

    # Mando: 52a, y cierre/apertura por reles interpuestos a las bobinas YC / YO
    out.append(_g("man",
        _rele(320, 275, "52a", ""),
        _p([(X + 10, 312), (X + 40, 312), (X + 40, 275), (298, 275)], "man",
           'stroke-dasharray="2 3"'),
        _t(X + 46, 268, "aux. del 52G", "r", "start"),
        _p([(342, 275), (MX, 275)], "man"),
        _rele(360, 310, "K1"), _p([(382, 310), (MX, 310)], "man"),
        _rele(360, 345, "K2"), _p([(382, 345), (MX, 345)], "man"),
        _bobina(270, 310, "YC"), _p([(281, 310), (338, 310)], "man"),
        _bobina(270, 345, "YO"), _p([(281, 345), (338, 345)], "man"),
        _p([(259, 310), (X + 22, 318)], "man", 'stroke-dasharray="2 3"'),
        _p([(259, 345), (X + 22, 322)], "man", 'stroke-dasharray="2 3"'),
        _t(250, 378, "YC cierra · YO dispara", "r"),
        _t(375, 378, "reles interpuestos", "r"),
        _caja(MX + MW + 70, 150, 120, 34, "caja"), _t(MX + MW + 130, 166, "Bateria 24 Vdc", "r"),
        _t(MX + MW + 130, 178, "+ fusible", "r"),
        _p([(MX + MW + 70, 167), (MX + MW, 167)], "man"),
        _contacto_nc(MX + MW + 40, 210, "PARO EMERG."),
        _p([(MX + MW + 40, 196), (MX + MW + 40, 184), (MX + MW + 70, 184)], "man"),
        _p([(MX + MW + 40, 224), (MX + MW + 40, 230), (MX + MW, 230)], "man"),
    ))

    # Comunicacion y polarizacion
    out.append(_g("com",
        _caja(MX + MW + 70, 255, 150, 40, "ecm"), _t(MX + MW + 145, 272, f"ECM {marca_motor}", "t"),
        _t(MX + MW + 145, 287, "control de velocidad", "r"),
        _p([(MX + MW, 275), (MX + MW + 70, 275)], "com"),
        _t(MX + MW + 35, 268, "J1939", "r"),
        _caja(MX + MW + 70, 315, 150, 40, "ecm"), _t(MX + MW + 145, 332, f"DSE de {otras[0]}", "t"),
        _t(MX + MW + 145, 347, "enlace MSC en cadena", "r"),
        _p([(MX + MW, 335), (MX + MW + 70, 335)], "com"),
        _caja(MX + MW + 70, 375, 150, 40, "ecm"), _t(MX + MW + 145, 392, "AVR", "t"),
        _t(MX + MW + 145, 407, "entrada de ajuste remoto", "r"),
        _p([(MX + MW, 395), (MX + MW + 70, 395)], "com"),
        _t(MX + MW + 35, 388, "bias V", "r"),
        _t(MX + MW + 145, 432, "120 Ω en cada extremo del CAN", "r"),
    ))

    # Modulo (siempre visible) con sus bornes
    modulo = [
        _caja(MX, MY, MW, MH, "mod", 8),
        _t(MX + 14, MY + 24, nombre_mod, "t", "start"),
        _t(MX + 14, MY + 40, f"controlador de {ident}", "r", "start"),
        _pin(MX, 200, "V GEN L1 L2 L3 N"),
        _pin(MX, 240, "I  L1 L2 L3 COM"),
        _pin(MX, 275, "ENTRADA 52G CERRADO"),
        _pin(MX, 310, "SALIDA CERRAR 52G"),
        _pin(MX, 345, "SALIDA ABRIR 52G"),
        _pin(MX, 410, "V BARRA L1 L2 L3 N"),
        _pin(MX + MW, 167, "+ / − ALIMENTACION", "der"),
        _pin(MX + MW, 230, "PARO DE EMERGENCIA", "der"),
        _pin(MX + MW, 275, "CAN ECU (J1939)", "der"),
        _pin(MX + MW, 335, "MSC", "der"),
        _pin(MX + MW, 395, "SALIDA ANALOG. AVR", "der"),
        _t(MX + MW / 2, MY + MH - 8, f"bornes: {_borne(b, 'modulo', manual).replace('borne: ', '')}", "r"),
    ]
    cuerpo = "\n".join(modulo + out)
    return _envolver_svg(1000, 540, cuerpo)


def _envolver_svg(w, h, cuerpo):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'role="img" class="esquema">{cuerpo}</svg>')


# --- lamina de TTA -----------------------------------------------------------

def _svg_tta(planta: dict) -> str:
    v = planta.get("v_nominal", 380)
    f = planta.get("f_nominal", 60)
    tta = planta.get("tta", {})
    modulo = tta.get("modulo", "DSE7320 MKII")
    polos = tta.get("polos", 4)
    u = (planta.get("unidades") or [{}])[0]
    ident = u.get("id", "GE-01")
    marca_motor = (u.get("motor") or {}).get("marca") or "motor"
    XR, XG, XC = 150, 520, 335
    MX, MY, MW, MH = 640, 120, 300, 260
    out = []

    out.append(_g("pot",
        _caja(XR - 55, 40, 110, 46, "red"), _t(XR, 60, "RED", "t"), _t(XR, 76, f"{v:g} V {f:g} Hz", "r"),
        _p([(XR, 86), (XR, 120)], "pot"), _interruptor(XR, 120, "Q1"),
        _t(XR + 18, 150, "int. general", "r", "start"),
        _p([(XR, 164), (XR, 200)], "pot"), _interruptor(XR, 200, "KM1"),
        f'<circle cx="{XG}" cy="72" r="32" class="gen"/>', _t(XG, 78, "G", "big"),
        _t(XG + 40, 66, ident, "t", "start"), _t(XG + 40, 82, marca_motor, "r", "start"),
        _p([(XG, 104), (XG, 120)], "pot"), _interruptor(XG, 120, "Q2"),
        _p([(XG, 164), (XG, 200)], "pot"), _interruptor(XG, 200, "KM2"),
        _p([(XR, 244), (XR, 290), (XG, 290), (XG, 244)], "pot"),
        _p([(XC, 290), (XC, 360)], "pot"),
        _caja(XC - 60, 360, 120, 36, "caja"), _t(XC, 383, "CARGA", "t"),
        _t(XR + 8, 282, f"{polos} polos: L1 L2 L3{' N' if polos == 4 else ''}", "r", "start"),
        _p([(XR + 30, 228), (XG - 30, 228)], "man", 'stroke-dasharray="3 3"'),
        _t(XC, 222, "enclavamiento mecanico", "r"),
    ))

    out.append(_g("med",
        _p([(XR, 100), (245, 100), (245, 130)], "med"), _fusible(245, 140, "F1-F3"),
        _p([(245, 150), (245, 175), (MX, 175)], "med"), _t(255, 96, "V red", "r", "start"),
        _p([(XG, 110), (590, 110), (590, 210), (MX, 210)], "med"), _fusible(590, 140, "F4-F6"),
        _t(600, 106, "V grupo", "r", "start"),
        _tc(XC, 335), _t(XC - 18, 339, "TC carga", "r", "end"),
        _p([(XC + 14, 335), (430, 335), (430, 245), (MX, 245)], "med"),
    ))

    # Mando en escalera bajo el modulo
    yb = 440
    r1, r2 = yb + 40, yb + 110
    out.append(_g("man",
        _t(40, yb - 12, "Circuito de mando (tension de mando segun tablero)", "t", "start"),
        _p([(60, yb), (60, yb + 150)], "man"), _p([(560, yb), (560, yb + 150)], "man"),
        _t(60, yb + 166, "L / +", "r"), _t(560, yb + 166, "N / −", "r"),
        _p([(60, r1), (124 - 16, r1)], "man"), _na_h(124, r1, "salida «cerrar red»"),
        _p([(140, r1), (214 - 16, r1)], "man"), _nc_h(214, r1, "KM2 aux. NC"),
        _p([(230, r1), (444, r1)], "man"), _bobina(455, r1, "KM1"),
        _p([(466, r1), (560, r1)], "man"),
        _p([(60, r2), (124 - 16, r2)], "man"), _na_h(124, r2, "salida «cerrar grupo»"),
        _p([(140, r2), (214 - 16, r2)], "man"), _nc_h(214, r2, "KM1 aux. NC"),
        _p([(230, r2), (444, r2)], "man"), _bobina(455, r2, "KM2"),
        _p([(466, r2), (560, r2)], "man"),
        _p([(MX, 300), (600, 300), (600, yb + 8), (124, yb + 8), (124, r1 - 10)], "man",
           'stroke-dasharray="2 3"'),
        _p([(MX, 340), (615, 340), (615, yb + 78), (124, yb + 78), (124, r2 - 10)], "man",
           'stroke-dasharray="2 3"'),
        _t(630, r1, "Contacto de salida del modulo", "r", "start"),
        _t(630, r1 + 14, "(o rele interpuesto K1 si la bobina", "r", "start"),
        _t(630, r1 + 28, "consume mas que la salida)", "r", "start"),
        _t(630, r2 + 4, "El NC de la otra bobina es el", "r", "start"),
        _t(630, r2 + 18, "enclavamiento electrico", "r", "start"),
    ))

    out.append(_g("com",
        _p([(MX + MW / 2, MY), (MX + MW / 2, 40), (XG + 32, 40), (XG + 32, 58)], "com"),
        _t((XG + MX + MW / 2) / 2 + 20, 32, f"arranque, combustible y J1939 al ECM {marca_motor}", "r"),
    ))

    modulo_svg = [
        _caja(MX, MY, MW, MH, "mod", 8),
        _t(MX + MW / 2, MY + 24, modulo, "t"),
        _t(MX + MW / 2, MY + 40, "AMF: arranque por falla de red + TTA", "r"),
        _pin(MX, 175, "V RED L1 L2 L3 N"),
        _pin(MX, 210, "V GRUPO L1 L2 L3 N"),
        _pin(MX, 245, "I CARGA L1 L2 L3 COM"),
        _pin(MX, 300, "SALIDA CERRAR RED"),
        _pin(MX, 340, "SALIDA CERRAR GRUPO"),
        _t(MX + MW / 2, MY + MH - 12, f"bornes: ver {MANUAL.get('DSE7320')}", "r"),
    ]
    return _envolver_svg(1000, 630, "\n".join(modulo_svg + out))


# --- contenido didactico -----------------------------------------------------

TEXTO = {
    "sincronismo": {
        "capas": {
            "pot": ("El generador entrega a la barra comun a traves de su interruptor 52G. "
                    "Todas las unidades cuelgan de la misma barra: por eso, antes de cerrar, "
                    "tension, frecuencia y angulo tienen que coincidir.",
                    "Con todo desenergizado y bloqueado: continuidad y secuencia de fases "
                    "L1-L2-L3 igual en el generador y en la barra (secuencimetro a los dos "
                    "lados del 52G).",
                    "Una fase cruzada entre el generador y la barra. Ningun ajuste del "
                    "modulo lo corrige; el primer cierre lo descubre de la peor manera."),
            "med": ("Tres señales llegan al modulo: tension del generador (tomada ANTES "
                    "del 52G), tension de barra (DESPUES del 52G) y corriente por el TC. "
                    "Con las dos tensiones el modulo calcula ΔV, Δf y angulo; con la "
                    "corriente, kW y kVAr para repartir.",
                    "Con el grupo en vacio y el 52G abierto: en los bornes del modulo, "
                    f"tension entre fases y fase-neutro igual a la nominal en V GEN; "
                    "con la barra energizada por otra unidad, lo mismo en V BARRA. "
                    "Con carga: kW positivos y parecidos a los de una pinza de potencia.",
                    "TP de barra conectado del lado del generador: el modulo ve siempre "
                    "las dos tensiones iguales y da permiso de cierre en cualquier angulo. "
                    "Y abrir el secundario del TC con carga: se induce alta tension. Para "
                    "eso esta la bornera seccionable, que primero cortocircuita."),
            "man": ("El modulo no mueve el interruptor directo: cierra y abre a traves de "
                    "reles interpuestos K1/K2 que energizan la bobina de cierre YC o la de "
                    "disparo YO. El contacto auxiliar 52a le confirma al modulo que el "
                    "interruptor realmente cerro. La parada de emergencia corta la "
                    "alimentacion en serie.",
                    "Con el interruptor en prueba (sin potencia): ordenar cerrar y abrir "
                    "desde el modulo, medir tension en YC/YO en el instante de la orden y "
                    "comprobar que la entrada «52G cerrado» cambia de estado.",
                    "Falta el 52a o esta invertido: el modulo ordena cerrar, no recibe "
                    "confirmacion y da alarma de falla de interruptor, o cree que cerro "
                    "cuando no."),
            "com": ("Por J1939 el modulo le pide velocidad al ECM del motor (asi ajusta la "
                    "frecuencia para sincronizar y reparte kW). Por el enlace MSC los "
                    "modulos se dicen cuanto carga lleva cada uno. La salida analogica "
                    "polariza al AVR para igualar tension y repartir kVAr.",
                    "Con todo apagado, medir resistencia entre CAN H y CAN L: unos 60 Ω "
                    "significa las dos terminaciones de 120 Ω en su lugar; 120 Ω, falta "
                    "una; muy bajo, sobra alguna. Lo mismo en el enlace MSC.",
                    "Malla del cable aterrada en los dos extremos o terminacion faltante: "
                    "errores intermitentes de comunicacion y reparto de carga que oscila."),
        },
        "secuencia": [
            ("Arranque: el modulo arranca el motor por el ECM y espera tension y "
             "frecuencia estables.", "com"),
            ("Barra muerta: si nadie la alimenta, la primera unidad cierra sin sincronizar; "
             "la logica impide que dos cierren a la vez.", "man"),
            ("Barra viva: el modulo compara V GEN con V BARRA (ΔV, Δf, angulo).", "med"),
            ("Ajuste: pide al ECM mas o menos velocidad y al AVR mas o menos tension "
             "hasta entrar en ventana.", "com"),
            ("Cierre: con el angulo en ventana —compensando el tiempo del interruptor— "
             "activa K1, la bobina YC cierra el 52G y el 52a lo confirma.", "man"),
            ("Toma de carga: rampa de kW hasta su parte; el reparto se coordina por el "
             "enlace MSC.", "com"),
            ("Descarga y apertura: rampa hacia abajo y K2/YO abre el 52G antes de cruzar "
             "a potencia inversa.", "man"),
        ],
    },
    "tta": {
        "capas": {
            "pot": ("La carga se alimenta de la red por KM1 o del grupo por KM2, nunca de "
                    "los dos a la vez. Q1 y Q2 protegen y aislan cada lado para "
                    "mantenimiento.",
                    "Con todo desenergizado: secuencia de fases de la red y del grupo "
                    "IGUAL en los bornes de entrada de KM1 y KM2. Si no, los motores de "
                    "la carga giran al reves al pasar al grupo.",
                    "Secuencia distinta entre red y grupo, o neutro sin conmutar cuando el "
                    "esquema de tierra lo exige."),
            "med": ("El modulo vigila la tension de la red (para detectar la falla y el "
                    "retorno) y la del grupo (para saber cuando puede tomar carga). El TC "
                    "de carga le da la corriente y la potencia.",
                    "En los bornes del modulo: tension de red y de grupo entre fases y "
                    "fase-neutro igual a la nominal; fusibles F1-F6 sanos.",
                    "Un fusible de medicion de red abierto: el modulo «ve» falla de red y "
                    "arranca el grupo con la red buena."),
            "man": ("Las salidas del modulo energizan K1 («cerrar red») y K2 («cerrar "
                    "grupo»). Cada bobina pasa por el contacto NC de la otra: "
                    "enclavamiento electrico. Ademas, enclavamiento mecanico entre KM1 y "
                    "KM2, porque un contacto soldado salta al electrico.",
                    "Con la potencia aislada: forzar KM1 cerrado a mano y ordenar cerrar "
                    "grupo; KM2 no debe cerrar. Y al reves.",
                    "Enclavamiento solo electrico, o puenteado «para probar» y olvidado: "
                    "red y grupo en paralelo sin sincronizar."),
            "com": ("El modulo arranca y para el motor (salidas de arranque y combustible) "
                    "y lee sus parametros por J1939 del ECM.",
                    "Resistencia entre CAN H y CAN L con todo apagado: unos 60 Ω.",
                    "Terminacion de 120 Ω faltante: el modulo pierde al ECM a ratos y "
                    "para el grupo por falla de comunicacion."),
        },
        "secuencia": [
            ("Falla de red: la tension sale de los limites; el modulo espera el tiempo "
             "de confirmacion (configurable) para no arrancar por un parpadeo.", "med"),
            ("Arranque: ordena arranque y combustible al motor y espera tension y "
             "frecuencia del grupo estables.", "com"),
            ("Transferencia: abre KM1 (suelta K1), espera el tiempo muerto configurado "
             "y cierra KM2 (activa K2).", "man"),
            ("La carga queda en el grupo, con KM1 enclavado abierto.", "pot"),
            ("Retorno de red: espera el tiempo de retorno (configurable) para confirmar "
             "que la red es estable.", "med"),
            ("Retransferencia: abre KM2, tiempo muerto, cierra KM1.", "man"),
            ("Enfriamiento: el motor sigue en vacio el tiempo configurado y para.", "com"),
        ],
    },
}


CSS = """
:root{--fondo:#f4f6f8;--panel:#ffffff;--tinta:#111827;--suave:#4b5563;--borde:#d1d5db;
--acento:#2563eb}
@media (prefers-color-scheme:dark){:root{--fondo:#0f172a;--panel:#1e293b;--tinta:#e5e7eb;
--suave:#9ca3af;--borde:#334155;--acento:#60a5fa}}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--tinta);
font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}
main{max-width:1060px;margin:0 auto;padding:16px}
h1{font-size:1.45rem;margin:.2rem 0}
h2{font-size:1.15rem;margin:1.6rem 0 .6rem}
.sub{color:var(--suave);margin:0 0 1rem}
.botones{display:flex;flex-wrap:wrap;gap:8px;margin:.6rem 0}
.botones button{border:2px solid var(--borde);background:var(--panel);color:var(--tinta);
border-radius:999px;padding:6px 14px;font:inherit;cursor:pointer}
.botones button[aria-pressed=true]{border-color:var(--c,var(--acento));
box-shadow:inset 0 0 0 1px var(--c,var(--acento));font-weight:600}
.lienzo{background:#fff;border:1px solid var(--borde);border-radius:10px;overflow-x:auto}
.esquema{display:block;width:100%;min-width:760px;height:auto}
.esquema text{font-family:Arial,Helvetica,sans-serif;fill:#111827}
.esquema .t{font-size:13px;font-weight:700}.esquema .big{font-size:20px;font-weight:700}
.esquema .r{font-size:10.5px;fill:#374151}.esquema .p{font-size:10px;font-weight:700;fill:#1e3a8a}
.esquema .s{font-size:11px}
.l-pot{stroke:#1f2937;stroke-width:3.2;fill:none}
.l-med{stroke:#b45309;stroke-width:1.8;fill:none}
.l-man{stroke:#2563eb;stroke-width:1.8;fill:none}
.l-com{stroke:#059669;stroke-width:2.2;fill:none;stroke-dasharray:7 4}
.caja{fill:#f8fafc;stroke:#475569;stroke-width:1.4}
.mod{fill:#eff6ff;stroke:#2563eb;stroke-width:2}
.gen{fill:#fef9c3;stroke:#854d0e;stroke-width:2.2}
.red{fill:#dcfce7;stroke:#166534;stroke-width:2}
.ecm{fill:#ecfdf5;stroke:#059669;stroke-width:1.6}
.fus{fill:#fff7ed;stroke:#b45309;stroke-width:1.4}
.bornera{fill:#fff7ed;stroke:#b45309;stroke-width:1.4}
.bob{fill:#fff;stroke:#2563eb;stroke-width:1.8}
.anillo{fill:none;stroke:#b45309;stroke-width:2}
.punto{fill:#1f2937}.pin{fill:#1e3a8a}
.capa{transition:opacity .2s}
.lienzo[data-ver]:not([data-ver=todo]) .capa{opacity:.1}
.lienzo[data-ver=pot] .capa[data-capa=pot],.lienzo[data-ver=med] .capa[data-capa=med],
.lienzo[data-ver=man] .capa[data-capa=man],.lienzo[data-ver=com] .capa[data-capa=com]{opacity:1}
.tarjetas{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.tarjeta{background:var(--panel);border:1px solid var(--borde);border-left:5px solid var(--c);
border-radius:10px;padding:12px 14px;cursor:pointer}
.tarjeta h3{margin:0 0 .4rem;font-size:1rem;color:var(--c)}
.tarjeta p{margin:.3rem 0;font-size:.92rem}
.tarjeta b{display:block;font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;
color:var(--suave);margin-top:.5rem}
ol.pasos{padding-left:1.4rem}
ol.pasos li{background:var(--panel);border:1px solid var(--borde);border-radius:8px;
padding:8px 12px;margin:6px 0;cursor:pointer}
ol.pasos li[aria-current=true]{border-color:var(--acento);box-shadow:0 0 0 2px var(--acento)}
.etq{display:inline-block;font-size:.75rem;border-radius:999px;padding:1px 8px;
margin-left:6px;color:#fff;background:var(--c)}
.nota{color:var(--suave);font-size:.85rem;margin-top:1.5rem}
"""

JS = """
const lienzo=document.querySelector('.lienzo');
const botones=[...document.querySelectorAll('.botones button')];
function ver(capa){lienzo.dataset.ver=capa;
botones.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.capa===capa)));}
botones.forEach(b=>b.addEventListener('click',()=>ver(b.dataset.capa)));
document.querySelectorAll('.tarjeta').forEach(t=>t.addEventListener('click',()=>{
ver(t.dataset.capa);lienzo.scrollIntoView({behavior:'smooth',block:'center'});}));
const pasos=[...document.querySelectorAll('ol.pasos li')];
pasos.forEach(p=>p.addEventListener('click',()=>{pasos.forEach(q=>q.removeAttribute('aria-current'));
p.setAttribute('aria-current','true');ver(p.dataset.capa);}));
ver('todo');
"""


def lamina_html(tipo: str, planta: dict | None = None) -> str:
    """Pagina HTML autocontenida con el esquema por capas y su explicacion."""
    if tipo not in TEXTO:
        raise ValueError("tipo debe ser 'sincronismo' o 'tta'")
    planta = planta or {}
    svg = _svg_sincronismo(planta) if tipo == "sincronismo" else _svg_tta(planta)
    txt = TEXTO[tipo]
    titulo = ("Sincronismo de grupos en paralelo" if tipo == "sincronismo"
              else "Transferencia automatica (TTA)")
    nombre = planta.get("planta", "")

    botones = ['<button data-capa="todo" style="--c:#6b7280">Todo</button>']
    botones += [f'<button data-capa="{k}" style="--c:{c}">{n}</button>'
                for k, (n, c) in CAPAS.items()]

    tarjetas = []
    for k, (que, verif, error) in txt["capas"].items():
        n, c = CAPAS[k]
        tarjetas.append(
            f'<article class="tarjeta" data-capa="{k}" style="--c:{c}"><h3>{n}</h3>'
            f'<p>{escape(que)}</p><b>Como se verifica</b><p>{escape(verif)}</p>'
            f'<b>Error tipico en campo</b><p>{escape(error)}</p></article>')

    pasos = []
    for texto, capa in txt["secuencia"]:
        n, c = CAPAS[capa]
        pasos.append(f'<li data-capa="{capa}">{escape(texto)}'
                     f'<span class="etq" style="--c:{c}">{n}</span></li>')

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(titulo)}</title><style>{CSS}</style></head>
<body><main>
<h1>{escape(titulo)}</h1>
<p class="sub">{escape(nombre)} · Toque una capa para estudiarla sola, o un paso de la secuencia para ver que actua.</p>
<div class="botones" role="group" aria-label="Capas">{''.join(botones)}</div>
<div class="lienzo" data-ver="todo">{svg}</div>
<h2>Las cuatro capas</h2>
<div class="tarjetas">{''.join(tarjetas)}</div>
<h2>Secuencia de operacion</h2>
<ol class="pasos">{''.join(pasos)}</ol>
<p class="nota">Generado por <code>nefer sincronismo lamina</code>. Designaciones IEC/ANSI y
terminacion CAN de 120 Ω segun ISO 11898 / SAE J1939. Los numeros de borne del modulo,
tiempos y umbrales dependen del modelo y del ajuste de cada tablero: se toman del manual
del fabricante ({escape(', '.join(f'{k} {v}' for k, v in MANUAL.items()))}) y del plano
del tablero antes de cablear.</p>
</main><script>{JS}</script>
<script type="application/json" id="planta">{escape(json.dumps({'planta': nombre}, ensure_ascii=False))}</script>
</body></html>
"""
