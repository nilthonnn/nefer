"""Diagramas de conexion: TTA (transferencia automatica) y sincronismo.

Salen en SVG, un archivo que abre cualquier navegador o telefono, se imprime
y se pega en el tablero.

Lo que dibujan y lo que NO:

- Dibujan la arquitectura de conexion: que va con que, por que señal y en
  que lado del interruptor se mide. Es lo que se revisa primero en una falla
  de sincronismo (TP de barra en el lado equivocado, TC sin referencia,
  enlace MSC abierto) y lo que un diagrama de fabricante no muestra para la
  planta concreta.
- NO inventan numeros de borne. Cambian por modelo y version del modulo DSE;
  si la planta los declara (`"bornes": {"sensado_gen": "35-38", ...}`) se
  rotulan, y si no se rotula «ver manual» con la publicacion que los trae.

Publicaciones DSE de referencia: DSE8610 MKII manual del operador 057-254
(instalacion 053-182); DSE7320 MKII manual del operador 057-253 (instalacion
053-181).
"""

from __future__ import annotations

from xml.sax.saxutils import escape

MANUAL = {
    "DSE8610": "DSE 057-254",
    "DSE7320": "DSE 057-253",
}

ESTILO = """
  <style>
    .fondo { fill: #ffffff; }
    .pot { stroke: #1f2937; stroke-width: 3; fill: none; }
    .ctl { stroke: #2563eb; stroke-width: 1.6; fill: none; stroke-dasharray: 6 4; }
    .com { stroke: #059669; stroke-width: 2; fill: none; stroke-dasharray: 2 3; }
    .med { stroke: #b45309; stroke-width: 1.6; fill: none; }
    .caja { fill: #f8fafc; stroke: #334155; stroke-width: 1.5; }
    .mod { fill: #eff6ff; stroke: #2563eb; stroke-width: 1.8; }
    .gen { fill: #fefce8; stroke: #854d0e; stroke-width: 2; }
    .red { fill: #f0fdf4; stroke: #166534; stroke-width: 2; }
    text { font-family: Arial, Helvetica, sans-serif; fill: #111827; }
    .t { font-size: 13px; font-weight: bold; }
    .s { font-size: 10.5px; }
    .r { font-size: 9.5px; fill: #475569; }
    .titulo { font-size: 18px; font-weight: bold; }
  </style>
"""


def _t(x, y, texto, clase="s", ancla="middle"):
    return (f'<text x="{x}" y="{y}" class="{clase}" text-anchor="{ancla}">'
            f'{escape(str(texto))}</text>')


def _linea(x1, y1, x2, y2, clase="pot"):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{clase}"/>'


def _ruta(puntos, clase):
    d = " ".join(f"{'M' if i == 0 else 'L'}{x},{y}" for i, (x, y) in enumerate(puntos))
    return f'<path d="{d}" class="{clase}"/>'


def _caja(x, y, w, h, clase="caja", rx=6):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" class="{clase}"/>'


def _generador(cx, cy, rotulo, sub=""):
    return "\n".join([
        f'<circle cx="{cx}" cy="{cy}" r="30" class="gen"/>',
        _t(cx, cy + 5, "G", "t"),
        _t(cx, cy + 48, rotulo, "t"),
        _t(cx, cy + 62, sub, "r") if sub else "",
    ])


def _interruptor(cx, y, rotulo, abierto=True, lado="izq"):
    """Interruptor/contactor sobre una linea vertical que llega en y y sale en y+40."""
    partes = [
        _linea(cx, y, cx, y + 10),
        f'<circle cx="{cx}" cy="{y + 10}" r="2.5" fill="#1f2937"/>',
        _linea(cx, y + 10, cx + (12 if abierto else 0), y + 30),
        f'<circle cx="{cx}" cy="{y + 30}" r="2.5" fill="#1f2937"/>',
        _linea(cx, y + 30, cx, y + 40),
        (_t(cx - 18, y + 25, rotulo, "s", "end") if lado == "izq"
         else _t(cx + 20, y + 25, rotulo, "s", "start")),
    ]
    return "\n".join(partes)


def _tc(cx, y, rotulo="TC"):
    return "\n".join([
        f'<circle cx="{cx - 6}" cy="{y}" r="6" class="med"/>',
        f'<circle cx="{cx + 6}" cy="{y}" r="6" class="med"/>',
        _t(cx + 18, y + 4, rotulo, "r", "start"),
    ])


def _borne(bornes: dict, clave: str, manual: str) -> str:
    valor = (bornes or {}).get(clave)
    return f"borne {valor}" if valor else f"borne: {manual.replace('DSE ', '')}"


def _svg(ancho, alto, titulo, cuerpo, leyenda_y):
    leyenda = "\n".join([
        _linea(20, leyenda_y, 60, leyenda_y, "pot"), _t(66, leyenda_y + 4, "Potencia 3F+N", "r", "start"),
        _linea(170, leyenda_y, 210, leyenda_y, "med"), _t(216, leyenda_y + 4, "Medicion (TP/TC)", "r", "start"),
        _linea(330, leyenda_y, 370, leyenda_y, "ctl"), _t(376, leyenda_y + 4, "Mando / señal", "r", "start"),
        _linea(470, leyenda_y, 510, leyenda_y, "com"), _t(516, leyenda_y + 4, "Comunicacion", "r", "start"),
    ])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" '
            f'width="{ancho}" height="{alto}" font-family="Arial">\n'
            f'<title>{escape(titulo)}</title>\n{ESTILO}\n'
            f'<rect width="100%" height="100%" class="fondo"/>\n'
            f'{_t(20, 32, titulo, "titulo", "start")}\n{cuerpo}\n{leyenda}\n'
            f'{_t(20, alto - 12, "Diagrama de arquitectura generado por nefer sincronismo. Los bornes y calibres se verifican contra el manual del modulo y el plano del tablero antes de cablear.", "r", "start")}\n'
            f'</svg>\n')


# --------------------------------------------------------------------------
# TTA: red / grupo con enclavamiento

def diagrama_tta(planta: dict | None = None) -> str:
    planta = planta or {}
    v = planta.get("v_nominal", 380)
    f = planta.get("f_nominal", 60)
    tta = planta.get("tta", {})
    modulo = tta.get("modulo", "DSE7320")
    manual = MANUAL.get(modulo.replace(" ", "").split("MK")[0], "manual del modulo")
    bornes = tta.get("bornes", {})
    polos = tta.get("polos", 4)
    u = (planta.get("unidades") or [{}])[0]
    ge = u.get("id", "GE-01")
    motor = (u.get("motor") or {}).get("marca") or "motor"

    xr, xg, xc = 200, 640, 420
    c = []
    # Red
    c += [f'<rect x="{xr - 50}" y="60" width="100" height="44" rx="6" class="red"/>',
          _t(xr, 80, "RED", "t"), _t(xr, 96, f"{v:g} V {f:g} Hz", "r"),
          _linea(xr, 104, xr, 150)]
    # Generador
    c += [_generador(xg, 90, ge, f"{motor}"), _linea(xg, 120, xg, 150)]
    # Contactores
    c += [_interruptor(xr, 150, "KM1 red", lado="der"),
          _interruptor(xg, 150, "KM2 grupo", lado="izq")]
    c += [_t(xc, 200, f"enclavamiento mecanico + electrico ({polos} polos)", "r")]
    c += [_ruta([(xr + 25, 206), (xg - 25, 206)], "ctl")]
    # Barra de carga
    c += [_ruta([(xr, 190), (xr, 240), (xg, 240), (xg, 190)], "pot"),
          _linea(xc, 240, xc, 290), _tc(xc, 262, ""),
          _t(xc - 18, 266, "TC carga", "r", "end"),
          _caja(xc - 60, 290, 120, 36), _t(xc, 312, "CARGA", "t")]
    # Modulo
    mx, my, mw, mh = xc - 140, 380, 280, 120
    c += [_caja(mx, my, mw, mh, "mod"), _t(xc, my + 22, f"{modulo} (AMF / TTA)", "t"),
          _t(xc, my + 40, "control del grupo + transferencia", "r")]
    # Senales al modulo
    c += [_ruta([(xr, 135), (xr - 80, 135), (xr - 80, my + 30), (mx, my + 30)], "med"),
          _t(xr - 76, 300, "Sensado red L1-L2-L3-N", "r", "start"),
          _t(xr - 76, 312, _borne(bornes, "sensado_red", manual), "r", "start"),
          _ruta([(xg, 135), (xg + 80, 135), (xg + 80, my + 30), (mx + mw, my + 30)], "med"),
          _t(xg + 76, 300, "Sensado grupo L1-L2-L3-N", "r", "end"),
          _t(xg + 76, 312, _borne(bornes, "sensado_gen", manual), "r", "end"),
          _ruta([(xc + 18, 262), (xc + 110, 262), (xc + 110, my)], "med"),
          _t(xc + 114, 350, _borne(bornes, "tc", manual), "r", "start")]
    # Mandos a contactores
    c += [_ruta([(mx + 30, my + mh), (mx + 30, my + mh + 40), (xr - 40, my + mh + 40), (xr - 40, 170), (xr - 2, 170)], "ctl"),
          _t(xr - 36, my + mh + 34, "Salida «cerrar red» -> rele interpuesto -> bobina KM1", "r", "start"),
          _t(xr - 36, my + mh + 56, _borne(bornes, "cerrar_red", manual), "r", "start"),
          _ruta([(mx + mw - 30, my + mh), (mx + mw - 30, my + mh + 40), (xg + 40, my + mh + 40), (xg + 40, 170), (xg + 2, 170)], "ctl"),
          _t(xg + 36, my + mh + 34, "Salida «cerrar grupo» -> bobina KM2", "r", "end"),
          _t(xg + 36, my + mh + 56, _borne(bornes, "cerrar_grupo", manual), "r", "end")]
    # Motor
    c += [_ruta([(xc, my + mh), (xc, my + mh + 90), (xg + 120, my + mh + 90), (xg + 120, 90), (xg + 32, 90)], "com"),
          _t(xc + 6, my + mh + 84, f"Arranque / combustible y J1939 al ECM {motor}", "r", "start")]
    # Logica del circuito de mando (texto)
    lx, ly = 40, my + mh + 120
    c += [_caja(lx, ly, 760, 110), _t(lx + 10, ly + 20, "Circuito de mando — reglas que el cableado debe cumplir", "t", "start")]
    reglas = [
        "1. Bobina KM1 en serie con contacto NC auxiliar de KM2, y bobina KM2 en serie con NC de KM1 (enclavamiento electrico).",
        "2. Enclavamiento mecanico entre KM1 y KM2: el electrico solo no basta (soldadura de contactos).",
        "3. Tiempo muerto de transferencia configurado en el modulo: ninguna conexion red-grupo en paralelo, ni un instante.",
        f"4. {polos} polos: {'el neutro se conmuta (cargas con neutro aterrado en el grupo)' if polos == 4 else 'neutro solido comun'}; revisar el esquema de tierra.",
        "5. Mando de bobinas por rele interpuesto si su corriente supera la de la salida del modulo.",
    ]
    for i, r in enumerate(reglas):
        c.append(_t(lx + 10, ly + 40 + i * 14, r, "r", "start"))
    alto = ly + 160
    return _svg(840, alto, f"Transferencia automatica (TTA) — {planta.get('planta', 'planta')}",
                "\n".join(c), alto - 36)


# --------------------------------------------------------------------------
# Sincronismo: N grupos a barra comun, un DSE8610 por grupo

def diagrama_sincronismo(planta: dict) -> str:
    unidades = planta.get("unidades") or []
    if not unidades:
        raise ValueError("la planta no declara unidades")
    v = planta.get("v_nominal", 380)
    f = planta.get("f_nominal", 60)
    paso = 320
    x0 = 200
    ancho = max(840, x0 + paso * len(unidades) + 40)
    yb = 300             # barra comun
    c = []
    xs = [x0 + i * paso for i in range(len(unidades))]

    # Barra comun y salida a carga
    xc = xs[-1] + 170
    c += [_linea(xs[0] - 60, yb, xc, yb),
          _t(xs[0] - 60, yb - 8, f"BARRA COMUN {v:g} V {f:g} Hz", "t", "start"),
          _linea(xc, yb, xc, yb + 40),
          _caja(xc - 50, yb + 40, 100, 32), _t(xc, yb + 61, "CARGA", "t")]

    for i, (u, x) in enumerate(zip(unidades, xs)):
        ident = u.get("id", f"GE-{i + 1:02d}")
        ctl = u.get("controlador") or {}
        mot = u.get("motor") or {}
        modelo = ctl.get("modelo") or "8610 MKII"
        nombre_mod = f"{ctl.get('marca') or 'DSE'} {modelo}"
        clave = ("DSE" + modelo.replace(" ", "")).split("MK")[0]
        manual = MANUAL.get(clave, "manual del modulo")
        bornes = u.get("bornes", {})
        placa = u.get("kw_nominal")
        sub = " · ".join(s for s in (f"{mot.get('marca') or ''} {mot.get('modelo') or ''}".strip(),
                                      f"{placa:g} kW" if placa else "") if s)

        c += [_generador(x, 100, ident, sub), _linea(x, 130, x, 200),
              _tc(x, 168, "TC"), _interruptor(x, 200, f"52G-{i + 1}"),
              _linea(x, 240, x, yb)]
        # Modulo de la unidad
        mx, my, mw, mh = x - 95, 420, 190, 112
        c += [_caja(mx, my, mw, mh, "mod"), _t(x, my + 20, nombre_mod, "t"),
              _t(x, my + 36, ident, "r")]
        # Sensado de generador (antes del interruptor) y de barra (despues)
        c += [_ruta([(x, 150), (x - 70, 150), (x - 70, my)], "med"),
              _t(x - 74, 372, "V gen", "r", "end"),
              _t(x - 74, 384, _borne(bornes, "sensado_gen", manual), "r", "end"),
              _ruta([(x + 18, yb), (x + 18, 340), (x + 70, 340), (x + 70, my)], "med"),
              _t(x + 74, 372, "V barra", "r", "start"),
              _t(x + 74, 384, _borne(bornes, "sensado_barra", manual), "r", "start"),
              _ruta([(x + 12, 168), (x + 45, 168), (x + 45, my)], "med")]
        # Mando del interruptor y realimentacion
        c += [_ruta([(mx + 20, my + mh), (mx + 20, my + mh + 26), (x - 110, my + mh + 26), (x - 110, 220), (x - 4, 220)], "ctl"),
              _t(x, my + 56, "cerrar / abrir 52G  ·  aux 52a", "r"),
              _t(x, my + 70, _borne(bornes, "interruptor", manual), "r")]
        # Polarizacion al motor y AVR
        c += [_t(x, my + 88, f"J1939 -> ECM {mot.get('marca') or ''} (bias velocidad)", "r"),
              _t(x, my + 102, "salida analogica -> AVR (bias tension)", "r")]
        c += [_ruta([(mx + mw, my + 90), (x + 115, my + 90), (x + 115, 70), (x + 30, 70), (x + 30, 85)], "com")]

    # Enlace MSC encadenado
    ym = 420 + 112 + 50
    c += [_ruta([(xs[0], 532), (xs[0], ym)] + [(x, ym) for x in xs[1:]], "com")]
    for x in xs[1:]:
        c.append(_linea(x, 532, x, ym, "com"))
    c += [_t(xs[0] - 60, ym + 18,
             "Enlace MSC (reparto de kW/kVAr entre modulos): en cadena, malla aterrada en un extremo, "
             "terminacion en los dos extremos segun el manual.", "r", "start")]

    # Reglas de verificacion
    ly = ym + 40
    reglas = [
        "1. V barra se toma DESPUES del interruptor (lado barra); V gen ANTES. Invertirlos permite cerrar fuera de fase.",
        "2. Misma fase de referencia en V gen y V barra de todas las unidades; verificar con sincronoscopio externo en el primer cierre.",
        "3. TC en el lado generador del interruptor, con la relacion y polaridad declaradas en el modulo (kW negativos = polaridad).",
        "4. Contacto auxiliar 52a de cada interruptor al modulo: sin el, el modulo no sabe que cerro.",
        "5. Interruptor que abre por falta de tension de mando (bobina de minima o logica equivalente).",
    ]
    c += [_caja(20, ly, ancho - 40, 30 + 14 * len(reglas)),
          _t(30, ly + 20, "Verificaciones de cableado antes del primer cierre", "t", "start")]
    for i, r in enumerate(reglas):
        c.append(_t(30, ly + 40 + 14 * i, r, "r", "start"))
    alto = ly + 30 + 14 * len(reglas) + 60
    return _svg(ancho, alto, f"Sincronismo — {planta.get('planta', 'planta')}",
                "\n".join(c), alto - 36)
