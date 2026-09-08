"""Maestro de clientes y equipos.

El parque de maquinaria y la cartera de clientes son finitos y conocidos: no
hay nada que "reconocer". Un catalogo local llena el encabezado de forma
determinista, sin OCR y sin conexion.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

NOMBRE_ARCHIVO = "catalogo.json"

PLANTILLA = {
    "empresa": "",
    "logo": None,
    "codigo_formato": "",
    "version_formato": "",
    "fecha_formato": "",
    "clientes": [
        {
            "id": "ejemplo",
            "razon_social": "CONSTRUCTORA EJEMPLO S.A.C.",
            "obras": ["OBRA PRINCIPAL — CIUDAD"],
        }
    ],
    "equipos": [
        {
            "codigo": "GE110-01",
            "modelo": "GRUPO ELECTRÓGENO INSONORIZADO DE 110 KW (POT. CONTINUA)",
            "categoria": "grupo_electrogeno",
        }
    ],
}


class ErrorCatalogo(ValueError):
    """El catalogo no existe, no es legible, o no contiene lo buscado."""


def _clave(texto: str) -> str:
    limpio = unicodedata.normalize("NFD", str(texto).lower())
    limpio = "".join(c for c in limpio if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", limpio)


def rutas_probables(desde: Path | None = None) -> list[Path]:
    """Donde se busca el catalogo, en orden.

    Primero junto al acta si se indica, luego el directorio actual —que es
    donde queda al crearlo— y por ultimo el del usuario, para el catalogo
    compartido de toda la flota.
    """
    rutas = []
    if desde is not None:
        rutas.append(Path(desde) / NOMBRE_ARCHIVO)
    rutas.append(Path.cwd() / NOMBRE_ARCHIVO)
    rutas.append(Path.home() / ".nefer" / NOMBRE_ARCHIVO)
    vistas, unicas = set(), []
    for r in rutas:
        if r not in vistas:
            vistas.add(r); unicas.append(r)
    return unicas


def cargar(ruta: str | Path | None = None, desde: Path | None = None) -> dict:
    """Lee el catalogo. Sin `ruta`, lo busca en las ubicaciones habituales."""
    candidatas = [Path(ruta)] if ruta else rutas_probables(desde)
    for candidata in candidatas:
        if not candidata.exists():
            continue
        try:
            with candidata.open(encoding="utf-8") as fh:
                datos = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ErrorCatalogo(
                f"{candidata}: no es JSON valido.\n"
                f"  linea {exc.lineno}, columna {exc.colno}: {exc.msg}"
            ) from None
        datos["_ruta"] = str(candidata)
        return datos
    raise ErrorCatalogo(
        "No se encontro el catalogo. Se busco en:\n  "
        + "\n  ".join(str(c) for c in candidatas)
        + "\nCree uno con: nefer catalogo --crear"
    )


def _buscar(coleccion: list[dict], claves: tuple[str, ...], termino: str,
            que: str) -> dict:
    """Busca por coincidencia exacta y, si no, por prefijo o subcadena."""
    objetivo = _clave(termino)
    if not objetivo:
        raise ErrorCatalogo(f"Indique un {que}.")

    def valores(item):
        return [_clave(item.get(k, "")) for k in claves if item.get(k)]

    for item in coleccion:
        if objetivo in valores(item):
            return item

    parciales = [i for i in coleccion
                 if any(v.startswith(objetivo) or objetivo in v for v in valores(i))]
    if len(parciales) == 1:
        return parciales[0]
    if len(parciales) > 1:
        muestra = ", ".join(str(i.get(claves[0], "?")) for i in parciales[:6])
        raise ErrorCatalogo(
            f"{termino!r} coincide con varios {que}s: {muestra}. Sea mas preciso."
        )
    disponibles = ", ".join(str(i.get(claves[0], "?")) for i in coleccion[:8])
    raise ErrorCatalogo(
        f"No hay ningun {que} que coincida con {termino!r}.\n"
        f"  Disponibles: {disponibles}" + (" …" if len(coleccion) > 8 else "")
    )


def equipo(catalogo: dict, termino: str) -> dict:
    return _buscar(catalogo.get("equipos", []), ("codigo", "modelo"), termino, "equipo")


def cliente(catalogo: dict, termino: str) -> dict:
    return _buscar(catalogo.get("clientes", []), ("id", "razon_social"), termino, "cliente")


def encabezado(catalogo: dict, cod_equipo: str, id_cliente: str | None = None,
               tipo_documento: str = "DESPACHO", obra: str | None = None) -> dict:
    """Encabezado prellenado con todo lo que el catalogo sabe."""
    eq = equipo(catalogo, cod_equipo)
    enc = {
        "empresa": catalogo.get("empresa", ""),
        "tipo_documento": tipo_documento,
        "n_acta": "",
        "n_guia": "",
        "cliente": "",
        "obra": obra or "",
        "fecha": "",
        "horometro": 0.0,
        "codigo_equipo": eq.get("codigo", ""),
        "modelo_equipo": eq.get("modelo", ""),
        "categoria": eq.get("categoria", "generico"),
    }
    for campo in ("logo", "codigo_formato", "version_formato", "fecha_formato"):
        if catalogo.get(campo):
            enc[campo] = catalogo[campo]
    if id_cliente:
        cl = cliente(catalogo, id_cliente)
        enc["cliente"] = cl.get("razon_social", "")
        obras = cl.get("obras") or []
        if not enc["obra"] and len(obras) == 1:
            enc["obra"] = obras[0]
    return enc
