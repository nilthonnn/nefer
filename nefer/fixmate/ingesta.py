"""De lo que hay en la oficina a fragmentos indexables.

Tres insumos, que son los tres que existen de verdad en un taller:

- el **historial de fallas** en JSON, una orden de trabajo por entrada: que
  fallo, cual resulto ser la causa y que se hizo;
- los **manuales** del fabricante en Markdown o texto plano, troceados por
  seccion para que un procedimiento no se recupere partido a la mitad;
- las **actas** de despacho y recepcion que ya genera nefer —el manifiesto
  JSON o el propio Excel llenado—, de donde salen los componentes observados
  o dañados con su observacion escrita.

Lo ultimo es lo que hace que esto no sea un buscador de manuales mas: el
historial de la flota propia, con la observacion que el tecnico escribio a
mano, es la fuente que ningun manual OEM trae.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import texto as _texto
from .indice import Fragmento

EXTENSIONES_MANUAL = {".md", ".txt", ".markdown"}
EXTENSIONES = EXTENSIONES_MANUAL | {".json", ".xlsx"}

CAMPOS_INFORME = ("codigo_ot", "fecha", "codigo_equipo", "modelo_equipo",
                  "categoria", "resumen_falla", "causa_raiz", "solucion_aplicada",
                  "horas_hombre")


class ErrorIngesta(ValueError):
    """El documento no se puede convertir en fragmentos."""


# ------------------------------------------------------------- historial

def de_informe(informe: dict, fuente: str = "", n: int = 0) -> Fragmento:
    """Una orden de trabajo cerrada -> un fragmento."""
    if not isinstance(informe, dict):
        raise ErrorIngesta(f"{fuente}: cada informe debe ser un objeto JSON.")
    ot = str(informe.get("codigo_ot") or f"SIN-OT-{n + 1}").strip()

    pasos = [str(p).strip() for p in informe.get("pasos") or [] if str(p).strip()]
    herramientas = [str(h).strip() for h in informe.get("herramientas") or [] if str(h).strip()]
    repuestos = [str(r).strip() for r in informe.get("repuestos") or [] if str(r).strip()]

    lineas = [f"ORDEN DE TRABAJO {ot}"]
    for etiqueta, clave in (("Equipo", "codigo_equipo"), ("Modelo", "modelo_equipo"),
                            ("Fecha", "fecha"), ("Falla reportada", "resumen_falla"),
                            ("Causa raiz confirmada", "causa_raiz"),
                            ("Solucion aplicada", "solucion_aplicada")):
        valor = str(informe.get(clave) or "").strip()
        if valor:
            lineas.append(f"{etiqueta}: {valor}")
    if pasos:
        lineas.append("Procedimiento: " + " ".join(f"{i}. {p}" for i, p in enumerate(pasos, 1)))
    if herramientas:
        lineas.append("Herramientas: " + ", ".join(herramientas))
    if repuestos:
        lineas.append("Repuestos: " + ", ".join(repuestos))
    cuerpo = "\n".join(lineas)

    declarados = informe.get("codigos_dtc") or informe.get("codigo_dtc") or []
    if isinstance(declarados, str):
        declarados = [declarados]
    codigos = [_texto.normalizar_dtc(c) for c in declarados if str(c).strip()]
    for codigo in _texto.codigos_dtc(cuerpo):
        if codigo not in codigos:
            codigos.append(codigo)

    metadatos = {clave: informe[clave] for clave in CAMPOS_INFORME if informe.get(clave)}
    metadatos.update({
        "codigo_ot": ot,
        "codigos_dtc": codigos,
        "pasos": pasos,
        "herramientas": herramientas,
        "repuestos": repuestos,
        "torques": _texto.torques(cuerpo),
    })
    return Fragmento(id=f"ot:{ot}", texto=cuerpo, fuente=fuente or ot,
                     tipo="informe", metadatos=metadatos)


def de_historial(datos, fuente: str = "") -> list[Fragmento]:
    """Lista de ordenes de trabajo -> fragmentos."""
    informes = datos.get("informes", []) if isinstance(datos, dict) else datos
    if not isinstance(informes, list):
        raise ErrorIngesta(f"{fuente}: se esperaba una lista de informes.")
    return [de_informe(informe, fuente, n) for n, informe in enumerate(informes)]


# ----------------------------------------------------------------- actas

def de_manifiesto(manifiesto: dict, fuente: str = "") -> list[Fragmento]:
    """Un acta de nefer -> un fragmento por acta y uno por hallazgo."""
    enc = manifiesto.get("encabezado") or {}
    equipo = str(enc.get("codigo_equipo") or "").strip()
    acta = str(enc.get("n_acta") or "").strip()
    base = acta or equipo or Path(fuente).stem or "acta"
    tipo_doc = str(enc.get("tipo_documento") or "").strip()

    comun = {
        "codigo_equipo": equipo,
        "modelo_equipo": str(enc.get("modelo_equipo") or ""),
        "categoria": str(enc.get("categoria") or ""),
        "fecha": str(enc.get("fecha") or ""),
        "cliente": str(enc.get("cliente") or ""),
        "obra": str(enc.get("obra") or ""),
        "n_acta": acta,
        "tipo_documento": tipo_doc,
    }
    comun = {k: v for k, v in comun.items() if v}

    cabecera = (f"ACTA DE {tipo_doc or 'MOVIMIENTO'} {acta}".strip()
                + f"\nEquipo: {equipo} {comun.get('modelo_equipo', '')}".rstrip())
    if enc.get("horometro") not in (None, ""):
        cabecera += f"\nHorometro: {enc['horometro']}"
    if manifiesto.get("resumen_ejecutivo"):
        cabecera += f"\nResumen: {manifiesto['resumen_ejecutivo']}"

    hallazgos = [c for c in manifiesto.get("inspeccion_componentes") or []
                 if isinstance(c, dict) and c.get("estado") in ("OBS", "D")]
    if hallazgos:
        cabecera += "\nHallazgos: " + "; ".join(
            f"{c.get('item', '')} ({c.get('estado')}): {c.get('observacion', '')}".strip()
            for c in hallazgos)

    fragmentos = [Fragmento(
        id=f"acta:{base}", texto=cabecera, fuente=fuente or base, tipo="acta",
        metadatos={**comun, "codigos_dtc": _texto.codigos_dtc(cabecera),
                   "hallazgos": len(hallazgos)})]

    # Un consumible que no retorno, o que retorno mal, es un hecho registrado
    # del equipo igual que un componente dañado. Ademas es lo unico que
    # sobrevive al pasar por el Excel: la hoja de inspeccion no se relee.
    faltantes = [c for c in manifiesto.get("consumibles") or []
                 if isinstance(c, dict)
                 and str(c.get("estado_recepcion") or "OK").upper() not in ("OK", "")]
    for n, consumible in enumerate(faltantes, 1):
        descripcion = str(consumible.get("descripcion") or "").strip()
        estado = str(consumible.get("estado_recepcion") or "").strip()
        detalle = " ".join(str(consumible.get(clave) or "").strip()
                           for clave in ("texto_recepcion", "recuperacion")).strip()
        cuerpo = (f"CONSUMIBLE {descripcion}\nEstado en recepcion: {estado}\n"
                  f"{detalle}\nEquipo: {equipo} {comun.get('modelo_equipo', '')}").rstrip()
        fragmentos.append(Fragmento(
            id=f"acta:{base}:c{n}", texto=cuerpo, fuente=fuente or base, tipo="acta",
            metadatos={**comun, "item": descripcion, "estado": estado,
                       "codigos_dtc": _texto.codigos_dtc(cuerpo)}))

    # Cada componente observado o dañado es un antecedente por si mismo: la
    # observacion que el tecnico escribio en campo es el dato que se busca.
    for n, componente in enumerate(hallazgos, 1):
        item = str(componente.get("item") or "").strip()
        observacion = str(componente.get("observacion") or "").strip()
        cuerpo = (f"COMPONENTE {item}\nEstado: {componente.get('estado')}\n"
                  f"Observacion: {observacion}\n"
                  f"Equipo: {equipo} {comun.get('modelo_equipo', '')}".rstrip())
        fragmentos.append(Fragmento(
            id=f"acta:{base}:{n}", texto=cuerpo, fuente=fuente or base, tipo="acta",
            metadatos={**comun, "item": item, "estado": componente.get("estado"),
                       "codigos_dtc": _texto.codigos_dtc(cuerpo)}))
    return fragmentos


def de_acta_xlsx(ruta: str | Path) -> list[Fragmento]:
    """Un Excel de acta ya llenado -> fragmentos, pasando por el extractor."""
    from .. import extract

    ruta = Path(ruta)
    try:
        manifiesto = extract.extraer(ruta)
    except Exception as exc:
        raise ErrorIngesta(f"{ruta}: no se pudo leer como acta ({exc}).") from exc
    return de_manifiesto(manifiesto, fuente=ruta.name)


# -------------------------------------------------------------- manuales

_RE_TITULO = re.compile(r"^(#{1,6})\s*(.+?)\s*#*$")
_RE_HERRAMIENTAS = re.compile(r"^\s*(?:herramientas?|herramental)\s*:\s*(.+)$", re.I)


def de_manual(contenido: str, fuente: str = "", equipo: str = "",
              categoria: str = "") -> list[Fragmento]:
    """Un manual en Markdown o texto plano -> un fragmento por seccion.

    Se corta por titulo, no por numero de caracteres: un torque recuperado sin
    el paso que lo pide no le sirve a nadie en campo.
    """
    fragmentos: list[Fragmento] = []
    for seccion, cuerpo in _secciones(contenido):
        for n, trozo in enumerate(_texto.trocear(cuerpo), 1):
            encabezado = f"{seccion}\n" if seccion else ""
            cuerpo_trozo = f"{encabezado}{trozo}"
            herramientas = []
            for linea in trozo.splitlines():
                m = _RE_HERRAMIENTAS.match(linea)
                if m:
                    herramientas.extend(
                        h.strip(" .-") for h in re.split(r"[,;]", m.group(1)) if h.strip(" .-"))
            fragmentos.append(Fragmento(
                id=f"man:{Path(fuente).stem or 'manual'}:{len(fragmentos) + 1}",
                texto=cuerpo_trozo,
                fuente=fuente,
                tipo="manual",
                metadatos={
                    "seccion": seccion,
                    "codigo_equipo": equipo,
                    "categoria": categoria,
                    "codigos_dtc": _texto.codigos_dtc(cuerpo_trozo),
                    "torques": _texto.torques(cuerpo_trozo),
                    "herramientas": herramientas,
                    "parte": n,
                },
            ))
    return fragmentos


def _secciones(contenido: str) -> list[tuple[str, str]]:
    """Parte el documento por titulos Markdown; sin titulos, es una sola seccion."""
    secciones: list[tuple[str, list[str]]] = []
    actual = ("", [])
    for linea in str(contenido).splitlines():
        m = _RE_TITULO.match(linea)
        if m:
            if actual[1]:
                secciones.append(actual)
            actual = (m.group(2).strip(), [])
        else:
            actual[1].append(linea)
    if actual[1]:
        secciones.append(actual)
    return [(titulo, "\n".join(lineas).strip())
            for titulo, lineas in secciones if "\n".join(lineas).strip()]


# ------------------------------------------------------------- recorrido

def de_archivo(ruta: str | Path) -> list[Fragmento]:
    """Fragmentos de un archivo, deduciendo que es por su forma."""
    ruta = Path(ruta)
    sufijo = ruta.suffix.lower()
    if sufijo == ".xlsx":
        return de_acta_xlsx(ruta)
    if sufijo in EXTENSIONES_MANUAL:
        return de_manual(ruta.read_text(encoding="utf-8"), fuente=ruta.name)
    if sufijo == ".json":
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ErrorIngesta(f"{ruta}: JSON ilegible ({exc}).") from exc
        if isinstance(datos, dict) and "encabezado" in datos:
            return de_manifiesto(datos, fuente=ruta.name)
        if isinstance(datos, list) or "informes" in datos:
            return de_historial(datos, fuente=ruta.name)
        raise ErrorIngesta(
            f"{ruta}: no parece ni un acta (falta 'encabezado') ni un historial "
            "(falta 'informes').")
    raise ErrorIngesta(f"{ruta}: extension no soportada ({sufijo or 'sin extension'}).")


def recorrer(rutas) -> list[Path]:
    """Archivos indexables de una lista de rutas, entrando en las carpetas."""
    encontrados: list[Path] = []
    for ruta in rutas:
        ruta = Path(ruta)
        if ruta.is_dir():
            encontrados.extend(sorted(
                a for a in ruta.rglob("*")
                if a.is_file() and a.suffix.lower() in EXTENSIONES
                and not a.name.startswith(".")))
        elif ruta.is_file():
            encontrados.append(ruta)
        else:
            raise ErrorIngesta(f"no existe: {ruta}")
    return encontrados
