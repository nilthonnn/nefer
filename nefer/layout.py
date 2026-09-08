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

# Rotulos por defecto de la rejilla fotografica, por familia de equipo.
VISTAS_POR_CATEGORIA = {
    "grupo_electrogeno": [
        "VISTA FRONTAL", "VISTA POSTERIOR",
        "VISTA LATERAL IZQUIERDA", "VISTA LATERAL DERECHA",
        "HORÓMETRO", "PANEL DE CONTROL",
        "VISTA FRONTAL DE MOTOR", "VISTA POSTERIOR DE MOTOR",
        "BATERÍAS", "TANQUE DE COMBUSTIBLE",
    ],
    "torre_iluminacion": [
        "VISTA FRONTAL", "VISTA POSTERIOR",
        "VISTA LATERAL IZQUIERDA", "VISTA LATERAL DERECHA",
        "HORÓMETRO", "PANEL DE CONTROL",
        "MÁSTIL Y WINCHE", "FOCOS",
        "ESTABILIZADORES", "BATERÍAS",
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

# Equipos que llevan hoja de consumibles (equipos moviles / autopropulsados).
CATEGORIAS_MOVILES = {"plataforma_elevacion", "maquinaria_amarilla", "torre_iluminacion"}


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


def ultima_fila(n_bloques_foto: int, n_consumibles: int) -> int:
    if n_consumibles:
        return bloque_consumible(n_consumibles - 1, n_bloques_foto)["fila_recuperacion"]
    return fila_titulo_observaciones(n_bloques_foto)


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
