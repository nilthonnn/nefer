"""Recupera el bitmap incrustado en un EMF.

Las actas antiguas se llenaban pegando las fotos desde Word, lo que deja la
imagen dentro de un metarchivo EMF que Excel dibuja pero que las librerias de
Python no leen. Casi siempre el EMF contiene un unico registro
EMR_STRETCHDIBITS con un DIB sin comprimir; reenvolviendolo en una cabecera BMP
se recupera la fotografia original sin perdida.
"""

from __future__ import annotations

import struct
from pathlib import Path

EMR_STRETCHDIBITS = 81
EMR_SETDIBITSTODEVICE = 79
_CON_DIB = {EMR_STRETCHDIBITS, EMR_SETDIBITSTODEVICE}

# Desplazamientos de offBmiSrc dentro del registro, por tipo.
_OFFSET_CAMPOS = {EMR_STRETCHDIBITS: 48, EMR_SETDIBITSTODEVICE: 48}


def _dibs(datos: bytes):
    """Itera los bloques (cabecera BITMAPINFO, bits) que contiene el EMF."""
    pos = 0
    total = len(datos)
    while pos + 8 <= total:
        tipo, tam = struct.unpack_from("<II", datos, pos)
        if tam < 8 or pos + tam > total:
            break
        if tipo in _CON_DIB:
            base = _OFFSET_CAMPOS[tipo]
            if pos + base + 16 <= total:
                off_bmi, cb_bmi, off_bits, cb_bits = struct.unpack_from(
                    "<IIII", datos, pos + base)
                if cb_bmi and cb_bits and pos + off_bits + cb_bits <= total:
                    yield (datos[pos + off_bmi: pos + off_bmi + cb_bmi],
                           datos[pos + off_bits: pos + off_bits + cb_bits])
        pos += tam


def _a_bmp(bmi: bytes, bits: bytes) -> bytes:
    offset_datos = 14 + len(bmi)
    cabecera = struct.pack("<2sIHHI", b"BM", offset_datos + len(bits), 0, 0, offset_datos)
    return cabecera + bmi + bits


def extraer_imagen(ruta_emf: str | Path, destino_png: str | Path) -> bool:
    """Convierte el EMF a PNG. Devuelve False si no contiene un bitmap legible."""
    try:
        from PIL import Image
    except ImportError:
        return False

    import io

    datos = Path(ruta_emf).read_bytes()
    mejor = None
    for bmi, bits in _dibs(datos):
        try:
            imagen = Image.open(io.BytesIO(_a_bmp(bmi, bits)))
            imagen.load()
        except Exception:
            continue
        if mejor is None or imagen.size[0] * imagen.size[1] > mejor.size[0] * mejor.size[1]:
            mejor = imagen
    if mejor is None:
        return False

    destino_png = Path(destino_png)
    destino_png.parent.mkdir(parents=True, exist_ok=True)
    mejor.convert("RGB").save(destino_png, "PNG")
    return True
