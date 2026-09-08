"""Esquema del manifiesto JSON que alimenta el reporte de despacho y recepcion.

El manifiesto es la unica fuente de verdad: de el salen el Excel, el PDF y la
hoja de consumibles. `validar()` devuelve una lista de errores legibles en
espanol, sin dependencias externas.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path

from . import layout

ESTADOS = {"OK", "OBS", "D"}
TIPOS_DOCUMENTO = {"DESPACHO", "RECEPCION"}
CATEGORIAS = set(layout.VISTAS_POR_CATEGORIA)
REVISION_MANUAL = "REVISIÓN MANUAL REQUERIDA"

PLANTILLA_MANIFIESTO = {
    "encabezado": {
        "empresa": "",
        "tipo_documento": "DESPACHO",
        "n_acta": "",
        "n_guia": "",
        "cliente": "",
        "obra": "",
        "fecha": "",
        "horometro": 0.0,
        "codigo_equipo": "",
        "modelo_equipo": "",
        "categoria": "generico",
    },
    "inspeccion_componentes": [],
    "registro_fotografico": [],
    "consumibles": [],
    "control_consumibles": [],
    "resumen_ejecutivo": "",
}


class ErrorManifiesto(ValueError):
    """El manifiesto no cumple el esquema."""


def _es_texto(v) -> bool:
    return isinstance(v, str) and v.strip() != ""


def _validar_encabezado(enc, errores, raiz=None):
    if not isinstance(enc, dict):
        errores.append("encabezado: debe ser un objeto.")
        return
    for campo in ("cliente", "codigo_equipo", "modelo_equipo"):
        if not _es_texto(enc.get(campo)):
            errores.append(f"encabezado.{campo}: obligatorio y no puede estar vacio.")

    tipo = enc.get("tipo_documento")
    if tipo not in TIPOS_DOCUMENTO:
        errores.append(
            f"encabezado.tipo_documento: debe ser uno de {sorted(TIPOS_DOCUMENTO)}, no {tipo!r}."
        )

    fecha = enc.get("fecha")
    if not _es_texto(fecha):
        errores.append("encabezado.fecha: obligatoria en formato YYYY-MM-DD.")
    elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        errores.append(f"encabezado.fecha: formato YYYY-MM-DD esperado, se recibio {fecha!r}.")
    else:
        try:
            _dt.date.fromisoformat(fecha)
        except ValueError:
            errores.append(f"encabezado.fecha: {fecha!r} no es una fecha valida.")

    horometro = enc.get("horometro")
    if horometro == REVISION_MANUAL:
        pass  # horometro ilegible: se imprime la leyenda y se firma a mano.
    elif not isinstance(horometro, (int, float)) or isinstance(horometro, bool):
        errores.append(
            "encabezado.horometro: numero de horas, o la cadena "
            f"{REVISION_MANUAL!r} si es ilegible."
        )
    elif horometro < 0:
        errores.append("encabezado.horometro: no puede ser negativo.")

    categoria = enc.get("categoria", "generico")
    if categoria not in CATEGORIAS:
        errores.append(
            f"encabezado.categoria: debe ser una de {sorted(CATEGORIAS)}, no {categoria!r}."
        )

    logo = enc.get("logo")
    if logo is not None:
        if not _es_texto(logo):
            errores.append("encabezado.logo: debe ser una ruta de imagen, o omitirse.")
        elif raiz is not None and not (raiz / logo).exists():
            # Sin esto el acta saldria sin logo y sin decir por que.
            errores.append(f"encabezado.logo: no existe {raiz / logo}.")


def _validar_inspeccion(items, errores):
    if not isinstance(items, list):
        errores.append("inspeccion_componentes: debe ser una lista.")
        return
    for i, it in enumerate(items):
        ruta = f"inspeccion_componentes[{i}]"
        if not isinstance(it, dict):
            errores.append(f"{ruta}: debe ser un objeto.")
            continue
        if not _es_texto(it.get("item")):
            errores.append(f"{ruta}.item: obligatorio.")
        if it.get("estado") not in ESTADOS:
            errores.append(
                f"{ruta}.estado: debe ser uno de {sorted(ESTADOS)}, no {it.get('estado')!r}."
            )
        if it.get("estado") in {"OBS", "D"} and not _es_texto(it.get("observacion")):
            errores.append(
                f"{ruta}.observacion: obligatoria cuando el estado es OBS o D."
            )


def _validar_fotos(fotos, errores, raiz: Path | None):
    if not isinstance(fotos, list):
        errores.append("registro_fotografico: debe ser una lista.")
        return
    if not fotos:
        errores.append("registro_fotografico: se requiere al menos una fotografia.")
    vistos = set()
    for i, f in enumerate(fotos):
        ruta = f"registro_fotografico[{i}]"
        if not isinstance(f, dict):
            errores.append(f"{ruta}: debe ser un objeto.")
            continue
        fid = f.get("foto_id")
        if not isinstance(fid, int) or isinstance(fid, bool) or fid < 1:
            errores.append(f"{ruta}.foto_id: entero positivo obligatorio.")
        elif fid in vistos:
            errores.append(f"{ruta}.foto_id: {fid} esta duplicado.")
        else:
            vistos.add(fid)
        if not _es_texto(f.get("descripcion")):
            errores.append(f"{ruta}.descripcion: obligatoria (es el rotulo bajo la foto).")
        archivo = f.get("archivo")
        if archivo is None:
            continue
        if not _es_texto(archivo):
            errores.append(f"{ruta}.archivo: debe ser una ruta de imagen.")
        elif raiz is not None and not (raiz / archivo).exists():
            errores.append(f"{ruta}.archivo: no existe {raiz / archivo}.")


def _validar_consumibles(consumibles, errores, raiz: Path | None,
                         tipo_documento: str | None = None):
    if not isinstance(consumibles, list):
        errores.append("consumibles: debe ser una lista.")
        return
    for i, c in enumerate(consumibles):
        ruta = f"consumibles[{i}]"
        if not isinstance(c, dict):
            errores.append(f"{ruta}: debe ser un objeto.")
            continue
        if not _es_texto(c.get("descripcion")):
            errores.append(f"{ruta}.descripcion: obligatoria.")
        cantidad = c.get("cantidad", 1)
        if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad < 1:
            errores.append(f"{ruta}.cantidad: entero positivo.")
        estado = c.get("estado_recepcion")
        if estado is not None and estado not in ESTADOS | {"NO_RETORNA"}:
            errores.append(
                f"{ruta}.estado_recepcion: uno de "
                f"{sorted(ESTADOS | {'NO_RETORNA'})}, no {estado!r}."
            )
        if tipo_documento == "DESPACHO":
            # En un despacho el equipo aun no ha vuelto: cualquier dato de
            # retorno es una contradiccion, no un descuido que se pueda ignorar.
            for clave in ("estado_recepcion", "texto_recepcion", "foto_recepcion"):
                if c.get(clave) is not None:
                    errores.append(
                        f"{ruta}.{clave}: un acta de DESPACHO no puede declarar "
                        "datos de recepcion; el equipo todavia no ha retornado."
                    )
        for clave in ("foto_despacho", "foto_recepcion"):
            archivo = c.get(clave)
            if archivo is None:
                continue
            if not _es_texto(archivo):
                errores.append(f"{ruta}.{clave}: debe ser una ruta de imagen.")
            elif raiz is not None and not (raiz / archivo).exists():
                errores.append(f"{ruta}.{clave}: no existe {raiz / archivo}.")


def _validar_control_consumibles(control, errores):
    if not isinstance(control, list):
        errores.append("control_consumibles: debe ser una lista.")
        return
    for i, c in enumerate(control):
        ruta = f"control_consumibles[{i}]"
        if not isinstance(c, dict):
            errores.append(f"{ruta}: debe ser un objeto.")
            continue
        if not _es_texto(c.get("consumible")):
            errores.append(f"{ruta}.consumible: obligatorio.")
        for clave in ("despacho", "recepcion", "consumo"):
            valor = c.get(clave)
            if valor is None or _es_texto(valor):
                continue
            if not isinstance(valor, (int, float)) or isinstance(valor, bool):
                errores.append(f"{ruta}.{clave}: numero, texto o null.")


def validar(manifiesto, raiz: Path | None = None) -> list[str]:
    """Devuelve la lista de errores del manifiesto. Vacia = valido."""
    errores: list[str] = []
    if not isinstance(manifiesto, dict):
        return ["El manifiesto debe ser un objeto JSON."]

    encabezado = manifiesto.get("encabezado")
    _validar_encabezado(encabezado, errores, raiz)
    _validar_inspeccion(manifiesto.get("inspeccion_componentes", []), errores)
    _validar_fotos(manifiesto.get("registro_fotografico", []), errores, raiz)
    tipo = encabezado.get("tipo_documento") if isinstance(encabezado, dict) else None
    _validar_consumibles(manifiesto.get("consumibles", []), errores, raiz, tipo)
    _validar_control_consumibles(manifiesto.get("control_consumibles", []), errores)

    resumen = manifiesto.get("resumen_ejecutivo", "")
    if not _es_texto(resumen):
        errores.append("resumen_ejecutivo: obligatorio (lo firma el cliente).")
    elif len(resumen.split()) > 20:
        errores.append(
            f"resumen_ejecutivo: maximo 20 palabras, tiene {len(resumen.split())}."
        )
    return errores


def cargar(ruta: str | Path, validar_rutas: bool = True) -> dict:
    """Lee y valida un manifiesto. Las rutas de imagen son relativas al JSON."""
    ruta = Path(ruta)
    try:
        with ruta.open(encoding="utf-8") as fh:
            manifiesto = json.load(fh)
    except FileNotFoundError:
        raise ErrorManifiesto(f"No existe el manifiesto {ruta}") from None
    except json.JSONDecodeError as exc:
        raise ErrorManifiesto(
            f"{ruta}: el archivo no es JSON valido.\n"
            f"  linea {exc.lineno}, columna {exc.colno}: {exc.msg}"
        ) from None
    errores = validar(manifiesto, ruta.parent if validar_rutas else None)
    if errores:
        raise ErrorManifiesto(
            f"{ruta}: {len(errores)} error(es)\n  - " + "\n  - ".join(errores)
        )
    return manifiesto


def celdas_destino(manifiesto: dict) -> dict[int, str]:
    """Celda de Excel donde aterriza cada `foto_id`, segun la rejilla del formato."""
    destino: dict[int, str] = {}
    for pos, foto in enumerate(manifiesto.get("registro_fotografico", [])):
        bloque = layout.bloque_foto(pos // 2)
        columna = layout.PANEL_IZQ[0] if pos % 2 == 0 else layout.PANEL_DER[0]
        destino[foto.get("foto_id", pos + 1)] = f"{columna}{bloque['fila_imagen_inicio']}"
    return destino
