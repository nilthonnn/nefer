"""Geometria del formato "Reporte fotografico de despacho y recepcion".

Todas las medidas se derivaron de reportes reales llenados a mano, uno de un
grupo electrogeno y otro de una plataforma de elevacion. El formato es una
rejilla regular:

    filas 1-3    cabecera (logo | titulo | codigo/version/fecha)
    filas 4-9    datos del acta (acta, guia, fecha, cliente, equipo, codigo, horometro)
    fila  10     separador
    fila  11+    rejilla fotografica: bloques de 15 filas
                 (14 filas de foto + 1 fila de rotulo), dos columnas por bloque
    fila  X      titulo "OBSERVACIONES"
    fila  X+1+   bloques de consumibles: 17 filas
                 (rotulo despacho/recepcion + 14 filas de foto + rotulo + recuperacion)

Las columnas se agrupan en dos paneles: A:L (izquierda) y M:Z (derecha).
"""

from __future__ import annotations

import re
import unicodedata

# --- Paneles de columnas -----------------------------------------------------
PANEL_IZQ = ("A", "L")
PANEL_DER = ("M", "Z")
COL_PRIMERA, COL_ULTIMA = "A", "Z"

# Anchos de columna medidos en los reportes originales (unidades Excel).
ANCHOS_COLUMNA = {
    "A": 5.00, "B": 4.29, "C": 3.71, "D": 2.29, "E": 4.00, "F": 1.71,
    "G": 4.00, "H": 8.43, "I": 8.43, "J": 2.86, "K": 2.43, "L": 11.71,
    "M": 1.43, "N": 2.71, "O": 1.57, "P": 1.14, "Q": 3.71, "R": 4.86,
    "S": 4.00, "T": 7.57, "U": 4.00, "V": 2.14, "W": 4.00, "X": 3.14,
    "Y": 0.43, "Z": 11.43,
}

# --- Cabecera ----------------------------------------------------------------
FILA_TITULO = 1              # A1:F3 logo, G1:R3 titulo, S1/S2/S3 codigo-version-fecha
FILA_ACTA = 4
FILA_GUIA = 5
FILA_FECHA = 6               # comparte fila con las casillas DESPACHO / RECEPCION
FILA_CLIENTE = 7
FILA_EQUIPO = 8
FILA_CODIGO = 9              # comparte fila con HOROMETRO
FILA_SEPARADOR = 10

CELDA_ACTA = "G4"
CELDA_GUIA = "G5"
CELDA_FECHA = "G6"
CELDA_CLIENTE = "G7"
CELDA_EQUIPO = "G8"
CELDA_CODIGO = "G9"
CELDA_HOROMETRO = "S9"
CELDA_MARCA_DESPACHO = "S6"   # la "X" del tipo de documento
CELDA_MARCA_RECEPCION = "Z6"

# --- Rejilla fotografica -----------------------------------------------------
FILA_INICIO_FOTOS = 11
ALTO_BLOQUE_FOTO = 15         # 14 filas de imagen + 1 fila de rotulo
FILAS_IMAGEN = 14

# --- Bloques de consumibles / observaciones ----------------------------------
ALTO_BLOQUE_CONSUMIBLE = 17   # rotulos + 14 filas de imagen + rotulos + recuperacion

# --- Estilo ------------------------------------------------------------------
FUENTE = "Cambria"
PT_ETIQUETA = 10
PT_VALOR = 11
PT_ROTULO = 8
PT_TITULO = 10
GRIS_CABECERA = "FFD9D9D9"    # tema 0 con tinte -0.15 en los originales
AMARILLO_RECUPERACION = "FFFFFF00"
BLANCO = "FFFFFFFF"

ALTO_FILA_ESTANDAR = 15.0
ALTO_FILA_SEPARADOR = 10.5
ALTO_FILA_ROTULO = 16.5

# Bloque de control documental. Cada organizacion pone el suyo desde el
# manifiesto: encabezado.codigo_formato, version_formato y fecha_formato.
CODIGO_FORMATO = "FO-DR-001"
VERSION_FORMATO = "00"
FECHA_FORMATO = ""
TITULO_FORMATO = " REPORTE FOTOGRÁFICO \nDE DESPACHO Y RECEPCIÓN"
TITULO_COMPARATIVO = "COMPARATIVO DESPACHO / RECEPCIÓN"
TITULO_DANOS = "DAÑOS Y OBSERVACIONES"

# Rotulos por defecto de la rejilla fotografica, por familia de equipo.
VISTAS_POR_CATEGORIA = {
    "grupo_electrogeno": [
        "VISTA FRONTAL", "VISTA POSTERIOR",
        "VISTA LATERAL IZQUIERDA", "VISTA LATERAL DERECHA",
        "HORÓMETRO", "PANEL DE CONTROL",
        "VISTA FRONTAL DE MOTOR", "VISTA POSTERIOR DE MOTOR",
        "BATERÍAS", "TANQUE DE COMBUSTIBLE",
    ],
    # Tomadas de un acta real de torre LED: la rejilla del formato termina en
    # las dos vistas de motor, no en mastil ni estabilizadores.
    "torre_iluminacion": [
        "VISTA FRONTAL", "VISTA POSTERIOR",
        "VISTA LATERAL IZQUIERDA", "VISTA LATERAL DERECHA",
        "HORÓMETRO", "PANEL DE CONTROL",
        "LUMINARIAS", "BATERÍA",
        "VISTA FRONTAL DE MOTOR", "VISTA POSTERIOR DE MOTOR",
    ],
    # Compresor transportable: el motor se fotografia por sus dos costados.
    "compresor": [
        "VISTA FRONTAL", "VISTA POSTERIOR",
        "VISTA LATERAL IZQUIERDA", "VISTA LATERAL DERECHA",
        "HORÓMETRO", "PANEL DE CONTROL",
        "BATERÍA",
        "VISTA LATERAL IZQUIERDA DE MOTOR", "VISTA LATERAL DERECHA DE MOTOR",
    ],
    "plataforma_elevacion": [
        "VISTA FRONTAL", "VISTA POSTERIOR",
        "VISTA LATERAL IZQUIERDA", "VISTA LATERAL DERECHA",
        "HORÓMETRO", "PANEL DE CONTROL",
        "MANDO DE CONTROL", "PISO DE PLATAFORMA",
        "LLAVE DE CONTACTO", "BATERÍAS",
        "TACOS",
    ],
    "maquinaria_amarilla": [
        "VISTA FRONTAL", "VISTA POSTERIOR",
        "VISTA LATERAL IZQUIERDA", "VISTA LATERAL DERECHA",
        "HORÓMETRO", "CABINA",
        "CUCHARÓN / HOJA", "SISTEMA HIDRÁULICO",
        "TREN DE RODAJE / LLANTAS", "MOTOR",
    ],
    "generico": [
        "VISTA FRONTAL", "VISTA POSTERIOR",
        "VISTA LATERAL IZQUIERDA", "VISTA LATERAL DERECHA",
        "HORÓMETRO", "PANEL DE CONTROL",
    ],
}

# Palabras del nombre de archivo que delatan la vista. El orden importa: una
# entrada mas especifica ("lateral izquierda") debe evaluarse antes que la
# generica que la contiene. La herramienta web usa esta misma tabla.
PISTAS_NOMBRE = [
    ("VISTA LATERAL IZQUIERDA", ("latizq", "lateralizquierda", "izquierda", "izq", "left")),
    ("VISTA LATERAL DERECHA", ("latder", "lateralderecha", "derecha", "der", "right")),
    ("VISTA FRONTAL DE MOTOR", ("motorfrente", "motorfrontal", "frentemotor", "enginefront")),
    ("VISTA POSTERIOR DE MOTOR", ("motoratras", "motorposterior", "atrasmotor", "engineback")),
    ("VISTA FRONTAL", ("frontal", "frente", "delante", "front")),
    ("VISTA POSTERIOR", ("posterior", "atras", "trasera", "back", "rear")),
    ("HORÓMETRO", ("horometro", "horimetro", "horas", "hourmeter", "hour")),
    ("PANEL DE CONTROL", ("panel", "tablero", "controlpanel")),
    ("MANDO DE CONTROL", ("mando", "joystick", "botonera")),
    ("TANQUE DE COMBUSTIBLE", ("tanque", "combustible", "diesel", "fuel")),
    ("BATERÍAS", ("bateria", "baterias", "battery")),
    ("VISTA LATERAL IZQUIERDA DE MOTOR", ("motorlatizq", "motorizquierda")),
    ("VISTA LATERAL DERECHA DE MOTOR", ("motorlatder", "motorderecha")),
    ("LUMINARIAS", ("luminaria", "luminarias", "foco", "focos", "luces", "lampara")),
    ("MÁSTIL Y WINCHE", ("mastil", "winche")),
    ("ESTABILIZADORES", ("estabilizador", "outrigger")),
    ("PISO DE PLATAFORMA", ("piso", "plataforma", "canastilla")),
    ("LLAVE DE CONTACTO", ("llave", "contacto", "ignicion")),
    ("TACOS", ("taco", "tacos", "cuna")),
    ("CABINA", ("cabina",)),
    ("CUCHARÓN / HOJA", ("cucharon", "cuchara", "hoja", "balde", "bucket")),
    ("SISTEMA HIDRÁULICO", ("hidraulico", "hidraulica", "manguera", "hydraulic")),
    ("TREN DE RODAJE / LLANTAS", ("rodaje", "llanta", "oruga", "neumatico", "track")),
    ("MOTOR", ("motor", "engine")),
]


def vista_sugerida(nombre: str) -> str | None:
    """Vista que delata el nombre de archivo, o None si no dice nada."""
    limpio = unicodedata.normalize("NFD", nombre.lower())
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    limpio = re.sub(r"[^a-z0-9]", "", limpio)
    for vista, claves in PISTAS_NOMBRE:
        if any(clave in limpio for clave in claves):
            return vista
    return None


# Equipos que llevan hoja de consumibles (equipos moviles / autopropulsados).
CATEGORIAS_MOVILES = {"plataforma_elevacion", "maquinaria_amarilla",
                      "torre_iluminacion", "compresor"}


def bloque_foto(indice: int) -> dict:
    """Filas que ocupa el bloque fotografico `indice` (0-based, de arriba abajo)."""
    tope = FILA_INICIO_FOTOS + ALTO_BLOQUE_FOTO * indice
    return {
        "fila_imagen_inicio": tope,
        "fila_imagen_fin": tope + FILAS_IMAGEN - 1,
        "fila_rotulo": tope + FILAS_IMAGEN,
    }


def fila_titulo_observaciones(n_bloques_foto: int) -> int:
    return FILA_INICIO_FOTOS + ALTO_BLOQUE_FOTO * n_bloques_foto


def bloque_consumible(indice: int, n_bloques_foto: int) -> dict:
    """Filas del bloque de consumible `indice` (0-based)."""
    base = fila_titulo_observaciones(n_bloques_foto) + 1 + ALTO_BLOQUE_CONSUMIBLE * indice
    return {
        "fila_encabezado": base,
        "fila_imagen_inicio": base + 1,
        "fila_imagen_fin": base + FILAS_IMAGEN,
        "fila_rotulo": base + FILAS_IMAGEN + 1,
        "fila_recuperacion": base + FILAS_IMAGEN + 2,
    }


def fin_consumibles(n_bloques_foto: int, n_consumibles: int) -> int:
    """Ultima fila ocupada por la seccion OBSERVACIONES."""
    if n_consumibles:
        return bloque_consumible(n_consumibles - 1, n_bloques_foto)["fila_recuperacion"]
    return fila_titulo_observaciones(n_bloques_foto)


# --- Secciones pareadas: solo en actas de recepcion ---------------------------
# Comparten la forma del bloque de consumible (encabezado + imagenes + rotulos +
# pie), porque es la misma idea: lo que salio a la izquierda, lo que volvio a la
# derecha.
ALTO_BLOQUE_PAREADO = ALTO_BLOQUE_CONSUMIBLE


def bloque_pareado(indice: int, fila_titulo: int) -> dict:
    """Filas del bloque pareado `indice` bajo el titulo de su seccion."""
    base = fila_titulo + 1 + ALTO_BLOQUE_PAREADO * indice
    return {
        "fila_encabezado": base,
        "fila_imagen_inicio": base + 1,
        "fila_imagen_fin": base + FILAS_IMAGEN,
        "fila_rotulo": base + FILAS_IMAGEN + 1,
        "fila_pie": base + FILAS_IMAGEN + 2,
    }


def fin_seccion_pareada(fila_titulo: int, n_bloques: int) -> int:
    if not n_bloques:
        return fila_titulo
    return bloque_pareado(n_bloques - 1, fila_titulo)["fila_pie"]


def plan_secciones(n_bloques_foto: int, n_consumibles: int,
                   n_comparativo: int = 0, n_danos: int = 0) -> dict:
    """Fila donde arranca cada seccion y donde termina el acta.

    Las secciones se encadenan en el orden en que se imprimen: rejilla,
    observaciones, comparativo despacho/recepcion y, al final, danos.
    """
    fila = fin_consumibles(n_bloques_foto, n_consumibles)

    titulo_comparativo = fila + 1 if n_comparativo else None
    if n_comparativo:
        fila = fin_seccion_pareada(titulo_comparativo, n_comparativo)

    titulo_danos = fila + 1 if n_danos else None
    if n_danos:
        fila = fin_seccion_pareada(titulo_danos, n_danos)

    return {
        "fila_observaciones": fila_titulo_observaciones(n_bloques_foto) if n_consumibles else None,
        "fila_comparativo": titulo_comparativo,
        "fila_danos": titulo_danos,
        "ultima_fila": fila,
    }


def ultima_fila(n_bloques_foto: int, n_consumibles: int,
                n_comparativo: int = 0, n_danos: int = 0) -> int:
    return plan_secciones(n_bloques_foto, n_consumibles,
                          n_comparativo, n_danos)["ultima_fila"]


def _ancho_px(col: str) -> int:
    """Ancho de columna en pixeles (conversion estandar de Excel para Calibri 11)."""
    return round(ANCHOS_COLUMNA.get(col, 8.43) * 7) + 5


def _cols(desde: str, hasta: str):
    return [chr(c) for c in range(ord(desde), ord(hasta) + 1)]


def ancho_panel_px(panel) -> int:
    return sum(_ancho_px(c) for c in _cols(*panel))


def alto_bloque_px(filas: int = FILAS_IMAGEN) -> int:
    """Alto en pixeles de un bloque de imagen de `filas` filas estandar."""
    return round(filas * ALTO_FILA_ESTANDAR * 96 / 72)
