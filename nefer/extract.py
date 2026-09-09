"""Lee un reporte ya llenado y lo devuelve como manifiesto JSON.

Sirve para dos cosas: migrar el historico de actas hechas a mano y verificar
que el generador reproduce fielmente un reporte real.
"""

from __future__ import annotations

import datetime as _dt
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import openpyxl

from . import emf, layout, schema

_RE_RECUPERACION = re.compile(r"^\s*(RECUPERACI[OÓ]N|RECUPERACION|CONFORME)\b", re.I)
_RE_OBSERVACIONES = re.compile(r"^\s*OBSERVACI[OÓ]N", re.I)
_RE_CANTIDAD = re.compile(r"^\s*(\d{1,3})\s+(.*)$")


def _texto(ws, coordenada: str) -> str:
    valor = ws[coordenada].value
    if valor is None:
        return ""
    if isinstance(valor, _dt.datetime):
        return valor.date().isoformat()
    return str(valor).replace("\r", "").strip()


def _detectar_fin_fotos(ws) -> int:
    """Cuantos bloques fotograficos tiene la hoja antes de OBSERVACIONES."""
    for i in range(0, 40):
        fila = layout.fila_titulo_observaciones(i)
        if fila > ws.max_row:
            return i
        if _RE_OBSERVACIONES.match(_texto(ws, f"A{fila}")):
            return i
    return 0


def _horometro(ws):
    valor = ws[layout.CELDA_HOROMETRO].value
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = _texto(ws, layout.CELDA_HOROMETRO)
    if not texto:
        return schema.REVISION_MANUAL
    normalizado = texto.replace(",", ".")
    try:
        return float(re.sub(r"[^\d.]", "", normalizado))
    except ValueError:
        return schema.REVISION_MANUAL


def _fecha(ws) -> str:
    valor = ws[layout.CELDA_FECHA].value
    if isinstance(valor, _dt.datetime):
        return valor.date().isoformat()
    if isinstance(valor, _dt.date):
        return valor.isoformat()
    texto = _texto(ws, layout.CELDA_FECHA)
    for patron in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return _dt.datetime.strptime(texto, patron).date().isoformat()
        except ValueError:
            continue
    return texto


def _tipo_documento(ws) -> str:
    marca_despacho = _texto(ws, layout.CELDA_MARCA_DESPACHO).upper()
    return "DESPACHO" if marca_despacho == "X" else "RECEPCION"


def _categoria(modelo: str) -> str:
    m = modelo.upper()
    if "ELECTR" in m and "GRUPO" in m:
        return "grupo_electrogeno"
    if "TORRE" in m and "ILUMINA" in m:
        return "torre_iluminacion"
    if "PLATAFORMA" in m or "TIJERA" in m or "ELEVACI" in m:
        return "plataforma_elevacion"
    if "COMPRESOR" in m:
        return "compresor"
    if any(p in m for p in ("EXCAVADORA", "CARGADOR", "RETROEXCAVADORA",
                            "MINICARGADOR", "TRACTOR", "MOTONIVELADORA",
                            "RODILLO", "MONTACARGA")):
        return "maquinaria_amarilla"
    return "generico"


EXT_FOTO = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
# Las actas hechas a mano pegan las fotos desde Word y quedan como metarchivos.
EXT_METARCHIVO = {".emf", ".wmf"}
EXT_ANCLABLE = EXT_FOTO | EXT_METARCHIVO
NS_RELACIONES = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CLASES_ANCLA = {"twoCellAnchor", "oneCellAnchor", "absoluteAnchor"}


def _local(etiqueta: str) -> str:
    """Nombre de la etiqueta sin su namespace."""
    return etiqueta.rsplit("}", 1)[-1]


def _anclas_de_imagen(z: zipfile.ZipFile) -> list[tuple[int, int, str]]:
    """(columna, fila, archivo_media) de cada imagen anclada, en orden de lectura.

    Se lee el XML de dibujo en vez de confiar en el orden de `xl/media/`: ese
    orden no tiene relacion con la posicion de la foto en la hoja.

    El XML se recorre por nombre local de etiqueta, sin exigir el prefijo
    `xdr:`: Excel lo escribe, openpyxl declara el mismo namespace por defecto
    y lo omite. Atarse al prefijo dejaria de leer las actas que genera este
    mismo paquete.
    """
    anclas = []
    for nombre in z.namelist():
        if not re.fullmatch(r"xl/drawings/drawing\d+\.xml", nombre):
            continue
        rels_nombre = nombre.replace("drawings/", "drawings/_rels/") + ".rels"
        try:
            rels_xml = z.read(rels_nombre)
        except KeyError:
            continue
        rels = {r.get("Id"): r.get("Target", "")
                for r in ET.fromstring(rels_xml)}

        for ancla in ET.fromstring(z.read(nombre)):
            if _local(ancla.tag) not in CLASES_ANCLA:
                continue
            columna = fila = None
            for hijo in ancla:
                if _local(hijo.tag) != "from":
                    continue
                for campo in hijo:
                    if _local(campo.tag) == "col":
                        columna = int(campo.text or 0)
                    elif _local(campo.tag) == "row":
                        fila = int(campo.text or 0)
            embed = next((el.get(f"{{{NS_RELACIONES}}}embed") for el in ancla.iter()
                          if _local(el.tag) == "blip"), None)
            if columna is None or fila is None or not embed:
                continue
            archivo = rels.get(embed, "").split("/")[-1]
            if _sufijo(archivo) in EXT_ANCLABLE:
                anclas.append((columna, fila, archivo))
    anclas.sort(key=lambda a: (a[1], a[0]))
    return anclas


def _sufijo(nombre: str) -> str:
    return Path(nombre).suffix.lower()


def _fotos_por_slot(xlsx: Path, n_bloques_foto: int) -> dict:
    """Mapa de posicion -> archivo de imagen.

    Claves: ("foto", bloque, panel) para la rejilla y ("cons", fila_encabezado,
    panel) para los bloques de consumibles. panel 0 = izquierda, 1 = derecha.
    """
    fila_observaciones = layout.fila_titulo_observaciones(n_bloques_foto)
    slots: dict = {}
    with zipfile.ZipFile(xlsx) as z:
        for col, fila_0, archivo in _anclas_de_imagen(z):
            fila = fila_0 + 1
            if fila < layout.FILA_INICIO_FOTOS:
                continue  # cabecera: es el logo del formato
            panel = 0 if col < 12 else 1
            if fila < fila_observaciones:
                bloque = (fila - layout.FILA_INICIO_FOTOS) // layout.ALTO_BLOQUE_FOTO
                slots.setdefault(("foto", bloque, panel), archivo)
            else:
                slots.setdefault(("cons", fila, panel), archivo)
    return slots


def _foto_consumible(slots: dict, fila_encabezado: int, panel: int) -> str | None:
    """Imagen anclada dentro del bloque de consumible que arranca en esa fila."""
    inicio = fila_encabezado + 1
    fin = fila_encabezado + layout.FILAS_IMAGEN
    for (clase, fila, p), archivo in slots.items():
        if clase == "cons" and p == panel and inicio - 1 <= fila <= fin:
            return archivo
    return None


def _extraer_medios(xlsx: Path, destino: Path, solo: set[str]) -> dict[str, str]:
    """Vuelca las imagenes pedidas a `destino`.

    Los metarchivos EMF/WMF se convierten a PNG. Devuelve el mapa
    nombre_original -> nombre_final (distintos cuando hubo conversion).
    """
    destino.mkdir(parents=True, exist_ok=True)
    finales: dict[str, str] = {}
    with zipfile.ZipFile(xlsx) as z:
        for nombre in z.namelist():
            if not nombre.startswith("xl/media/"):
                continue
            archivo = Path(nombre).name
            if archivo not in solo:
                continue
            sufijo = Path(archivo).suffix.lower()
            ruta = destino / archivo
            ruta.write_bytes(z.read(nombre))
            if sufijo in EXT_METARCHIVO:
                png = ruta.with_suffix(".png")
                if emf.extraer_imagen(ruta, png):
                    finales[archivo] = png.name
                ruta.unlink()
            else:
                finales[archivo] = archivo
    return finales


def _filas_encabezado_consumible(ws, n_bloques_foto: int) -> list[int]:
    """Filas donde arranca un bloque de consumible.

    Se localizan por su par de rotulos DESPACHO/RECEPCION en vez de asumir un
    paso fijo de 17 filas: las actas llenadas a mano suelen traer filas
    insertadas que corren la rejilla hacia abajo.
    """
    inicio = layout.fila_titulo_observaciones(n_bloques_foto) + 1
    # Las secciones pareadas de una recepcion usan los mismos rotulos DESPACHO /
    # RECEPCION, asi que el barrido se detiene en su titulo: si no, cada bloque
    # comparativo se leeria como un consumible mas.
    finales = {layout.TITULO_COMPARATIVO.upper(), layout.TITULO_DANOS.upper()}
    filas = []
    for fila in range(inicio, ws.max_row + 1):
        izq = _texto(ws, f"{layout.PANEL_IZQ[0]}{fila}").upper()
        if izq in finales:
            break
        der = _texto(ws, f"{layout.PANEL_DER[0]}{fila}").upper()
        if izq == "DESPACHO" and der.startswith("RECEPCI"):
            filas.append(fila)
    return filas


def extraer(xlsx: str | Path, dir_fotos: str | Path | None = None) -> dict:
    """Convierte un reporte llenado en manifiesto. Si `dir_fotos`, vuelca las imagenes."""
    xlsx = Path(xlsx)
    wb = openpyxl.load_workbook(xlsx)
    ws = wb["REPORTE"] if "REPORTE" in wb.sheetnames else wb.worksheets[0]

    modelo = _texto(ws, layout.CELDA_EQUIPO)
    n_bloques = _detectar_fin_fotos(ws)

    fotos = []
    for pos in range(n_bloques * 2):
        bloque = layout.bloque_foto(pos // 2)
        columna = layout.PANEL_IZQ[0] if pos % 2 == 0 else layout.PANEL_DER[0]
        descripcion = _texto(ws, f"{columna}{bloque['fila_rotulo']}")
        if not descripcion:
            continue
        fotos.append({
            "foto_id": len(fotos) + 1,
            "descripcion": descripcion,
            "celda_excel_destino": f"{columna}{bloque['fila_imagen_inicio']}",
        })

    consumibles = []
    filas_consumible = []
    for fila_encabezado in _filas_encabezado_consumible(ws, n_bloques):
        fila_rotulo = fila_encabezado + layout.FILAS_IMAGEN + 1
        fila_recuperacion = fila_rotulo + 1
        texto_despacho = _texto(ws, f"{layout.PANEL_IZQ[0]}{fila_rotulo}")
        texto_recepcion = _texto(ws, f"{layout.PANEL_DER[0]}{fila_rotulo}")
        recuperacion = _texto(ws, f"A{fila_recuperacion}")
        if not _RE_RECUPERACION.match(recuperacion):
            recuperacion = ""
        if not (texto_despacho or texto_recepcion):
            continue
        descripcion = texto_despacho
        cantidad = 1
        limpio = re.sub(r"\s+(EN\s+)?DESPACHAD[OA]\s*$", "", descripcion, flags=re.I)
        limpio = re.sub(r"\s+EN\s+DESPACHO\s*$", "", limpio, flags=re.I).strip()
        m = _RE_CANTIDAD.match(limpio)
        if m:
            cantidad, limpio = int(m.group(1)), m.group(2).strip()
        estado = None
        if re.search(r"RETORN[OÓ]\s+SIN", texto_recepcion, re.I):
            estado = "NO_RETORNA"
        elif re.search(r"DA[ÑN]AD", texto_recepcion, re.I):
            estado = "D"
        elif texto_recepcion:
            estado = "OK"
        filas_consumible.append(fila_encabezado)
        consumibles.append({
            "descripcion": limpio or descripcion,
            "cantidad": cantidad,
            "estado_recepcion": estado,
            "texto_despacho": texto_despacho or None,
            "texto_recepcion": texto_recepcion or None,
            "recuperacion": recuperacion or None,
        })

    manifiesto = {
        "encabezado": {
            "empresa": "",
            "tipo_documento": _tipo_documento(ws),
            "n_acta": _texto(ws, layout.CELDA_ACTA),
            "n_guia": _texto(ws, layout.CELDA_GUIA),
            "cliente": _texto(ws, layout.CELDA_CLIENTE),
            "obra": "",
            "fecha": _fecha(ws),
            "horometro": _horometro(ws),
            "codigo_equipo": _texto(ws, layout.CELDA_CODIGO),
            "modelo_equipo": modelo,
            "categoria": _categoria(modelo),
        },
        "inspeccion_componentes": [],
        "registro_fotografico": fotos,
        "consumibles": consumibles,
        "control_consumibles": [],
        "resumen_ejecutivo": "",
    }

    if dir_fotos is not None:
        dir_fotos = Path(dir_fotos)
        slots = _fotos_por_slot(xlsx, n_bloques)
        base = dir_fotos.name
        pendientes: list[tuple[dict, str, str]] = []
        for pos, foto in enumerate(manifiesto["registro_fotografico"]):
            archivo = slots.get(("foto", pos // 2, pos % 2))
            if archivo:
                pendientes.append((foto, "archivo", archivo))
        for cons, fila in zip(consumibles, filas_consumible):
            for panel, clave in ((0, "foto_despacho"), (1, "foto_recepcion")):
                archivo = _foto_consumible(slots, fila, panel)
                if archivo:
                    pendientes.append((cons, clave, archivo))

        finales = _extraer_medios(xlsx, dir_fotos, {a for _, _, a in pendientes})
        for destino, clave, archivo in pendientes:
            final = finales.get(archivo)
            if final:
                destino[clave] = f"{base}/{final}"

    return manifiesto
