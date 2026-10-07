"""Leer analisis RCM y pautas TPM desde JSON, con errores que se entienden.

El formato es JSON y no una base porque es lo que FixMate ya usa para el
historial: un archivo que se edita, se versiona en git, se manda por correo
y se copia al telefono. Un analisis RCM es exactamente la clase de documento
que un cliente quiere poder leer sin la herramienta delante.

El valor de este modulo no es el parseo: es lo que dicen los errores. Un
«KeyError: 'estandar'» obliga a abrir el codigo; «la funcion 2 del activo
EX-220 no declara estandar de desempeño» se arregla sin preguntarle a nadie.
"""

from __future__ import annotations

import json
from pathlib import Path

from .activos import Activo, Ubicacion
from .anomalia import Anomalia
from .criticidad import EJEMPLOS, Metodo
from .decision import Decisiones, Respuestas
from .rcm import (Analisis, Consecuencia, Efecto, ErrorRCM, Referencia)
from .tpm import Checklist, Ejecucion, ErrorTPM


class ErrorCargador(ValueError):
    """El documento no se puede leer como lo que dice ser."""


def _dict(ruta: str | Path) -> dict:
    ruta = Path(ruta)
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ErrorCargador(f"{ruta}: no existe.") from exc
    except json.JSONDecodeError as exc:
        raise ErrorCargador(f"{ruta}: no es JSON legible ({exc}).") from exc
    if not isinstance(datos, dict):
        raise ErrorCargador(f"{ruta}: se esperaba un objeto JSON.")
    return datos


def _lista(datos: dict, clave: str, donde: str) -> list:
    valor = datos.get(clave) or []
    if not isinstance(valor, list):
        raise ErrorCargador(f"{donde}: «{clave}» tiene que ser una lista.")
    return valor


def analisis_de_dict(datos: dict, donde: str = "el analisis") -> Analisis:
    """Un analisis RCM completo desde su JSON.

    Las llaves entre funcion, falla y modo se reconstruyen por POSICION
    cuando no vienen declaradas: en un JSON escrito a mano, anidar los modos
    dentro de su falla es mas facil de no equivocar que repetir ids.
    """
    if not isinstance(datos.get("activo"), dict):
        raise ErrorCargador(f"{donde}: falta el objeto «activo».")
    try:
        activo = Activo.de_dict(datos["activo"])
    except Exception as exc:
        raise ErrorCargador(f"{donde}: activo invalido ({exc}).") from exc

    metodo = _metodo(datos.get("metodo_criticidad"), donde)
    a = Analisis(activo, contexto=str(datos.get("contexto") or ""),
                 facilitador=str(datos.get("facilitador") or ""),
                 participantes=tuple(datos.get("participantes") or ()),
                 fecha=str(datos.get("fecha") or ""),
                 metodo_criticidad=metodo)

    for i, fd in enumerate(_lista(datos, "funciones", donde), 1):
        donde_f = f"{donde}, funcion {i}"
        if not isinstance(fd, dict):
            raise ErrorCargador(f"{donde_f}: se esperaba un objeto.")
        try:
            funcion = a.agregar_funcion(
                str(fd.get("descripcion") or ""), str(fd.get("estandar") or ""),
                tipo=str(fd.get("tipo") or "principal"),
                condicion=str(fd.get("condicion") or ""))
        except ErrorRCM as exc:
            raise ErrorCargador(f"{donde_f}: {exc}") from exc

        for j, ffd in enumerate(_lista(fd, "fallas", donde_f), 1):
            donde_ff = f"{donde_f}, falla funcional {j}"
            if not isinstance(ffd, dict):
                raise ErrorCargador(f"{donde_ff}: se esperaba un objeto.")
            try:
                falla = a.agregar_falla(funcion.id,
                                        str(ffd.get("descripcion") or ""))
            except ErrorRCM as exc:
                raise ErrorCargador(f"{donde_ff}: {exc}") from exc

            for k, md in enumerate(_lista(ffd, "modos", donde_ff), 1):
                _modo(a, falla.id, md, f"{donde_ff}, modo {k}", metodo)
    return a


def _metodo(valor, donde: str) -> Metodo | None:
    """El metodo de criticidad: un nombre de los de ejemplo, o nada.

    Un metodo propio se construye en codigo y se pasa a `Analisis`: definir
    una matriz de criticidad entera en JSON invita a escribirla a medias, y
    una tabla con huecos decide por omision.
    """
    if not valor:
        return None
    if isinstance(valor, Metodo):
        return valor
    nombre = str(valor)
    if nombre in EJEMPLOS:
        return EJEMPLOS[nombre]
    raise ErrorCargador(
        f"{donde}: metodo de criticidad «{nombre}» desconocido. Los de ejemplo "
        f"son: {', '.join(EJEMPLOS)}. Un metodo propio se pasa en codigo.")


def _modo(a: Analisis, falla_id: str, md: dict, donde: str, metodo) -> None:
    if not isinstance(md, dict):
        raise ErrorCargador(f"{donde}: se esperaba un objeto.")
    u = md.get("ubicacion") or {}
    consecuencias = []
    for c in md.get("consecuencias") or []:
        clase = c if isinstance(c, str) else str(c.get("clase") or "")
        desc = "" if isinstance(c, str) else str(c.get("descripcion") or "")
        try:
            consecuencias.append(Consecuencia(clase, desc))
        except ErrorRCM as exc:
            raise ErrorCargador(f"{donde}: {exc}") from exc

    referencias = []
    for r in md.get("evidencia") or []:
        try:
            referencias.append(Referencia(
                str(r.get("fuente") or ""), str(r.get("referencia") or ""),
                str(r.get("nota") or "")))
        except ErrorRCM as exc:
            raise ErrorCargador(f"{donde}: {exc}") from exc

    try:
        modo = a.agregar_modo(
            falla_id, str(md.get("descripcion") or ""),
            ubicacion=Ubicacion(str(u.get("sistema") or ""),
                                str(u.get("subsistema") or ""),
                                str(u.get("componente") or "")),
            codigo_catalogo=str(md.get("codigo_catalogo") or ""),
            causa=str(md.get("causa") or ""),
            mecanismo=str(md.get("mecanismo") or ""),
            evidente=bool(md.get("evidente", True)),
            efecto=Efecto(**{k: str(v) for k, v in (md.get("efecto") or {}).items()
                             if k in Efecto.__dataclass_fields__}),
            consecuencias=tuple(consecuencias),
            evidencia=tuple(referencias),
            estado=str(md.get("estado") or "propuesto"))
    except (ErrorRCM, TypeError) as exc:
        raise ErrorCargador(f"{donde}: {exc}") from exc

    if md.get("criticidad"):
        try:
            modo.evaluar_criticidad(metodo, dict(md["criticidad"]))
        except Exception as exc:
            raise ErrorCargador(f"{donde}: criticidad ({exc}).") from exc


def analisis(ruta: str | Path) -> Analisis:
    return analisis_de_dict(_dict(ruta), str(ruta))


# Los campos del arbol de decision, tal como los nombra `decision.Respuestas`.
CAMPOS_DECISION = tuple(Respuestas.__dataclass_fields__)


def decisiones_de_dict(datos: dict, a: Analisis,
                       donde: str = "el analisis") -> Decisiones:
    """Las respuestas del arbol que vengan en el JSON, por modo de falla.

    Van dentro de cada modo, en un objeto «decision», y en el MISMO orden en
    que se cargaron los modos. Un modo sin «decision» simplemente no se
    decide: no se le inventa una respuesta conservadora para que el analisis
    parezca completo, porque la Q6 existe justamente para denunciar eso.

    Las claves que falten quedan en `None`, que en el arbol significa «nadie
    se lo pregunto» y no «la respuesta es no».
    """
    d = Decisiones()
    modos = list(a.modos)
    i = 0
    for fd in _lista(datos, "funciones", donde):
        for ffd in _lista(fd, "fallas", f"{donde}, funcion"):
            for md in _lista(ffd, "modos", f"{donde}, falla"):
                if i >= len(modos):
                    break
                modo = modos[i]
                i += 1
                decision = md.get("decision")
                if not isinstance(decision, dict):
                    continue
                desconocidas = set(decision) - set(CAMPOS_DECISION)
                if desconocidas:
                    raise ErrorCargador(
                        f"{donde}, modo {modo.id}: «{', '.join(sorted(desconocidas))}» "
                        f"no es una pregunta del arbol. Las que hay: "
                        f"{', '.join(CAMPOS_DECISION)}.")
                d.registrar(modo, Respuestas(**{
                    k: (None if v is None else bool(v))
                    for k, v in decision.items()}))
    return d


def analisis_y_decisiones(ruta: str | Path):
    """El analisis y las decisiones que su JSON declare, de una sola lectura."""
    datos = _dict(ruta)
    a = analisis_de_dict(datos, str(ruta))
    return a, decisiones_de_dict(datos, a, str(ruta))


def checklist_de_dict(datos: dict, donde: str = "la pauta") -> Checklist:
    try:
        c = Checklist(id=str(datos.get("id") or ""),
                      activo_codigo=str(datos.get("activo_codigo")
                                        or datos.get("codigo_equipo") or ""),
                      nombre=str(datos.get("nombre") or ""),
                      frecuencia=str(datos.get("frecuencia") or "diaria"),
                      origen=str(datos.get("origen") or ""))
    except ErrorTPM as exc:
        raise ErrorCargador(f"{donde}: {exc}") from exc
    if not c.id or not c.activo_codigo:
        raise ErrorCargador(f"{donde}: la pauta necesita «id» y «activo_codigo».")

    for i, p in enumerate(_lista(datos, "puntos", donde), 1):
        try:
            c.agregar(str(p.get("clase") or ""), str(p.get("punto") or ""),
                      str(p.get("criterio") or ""),
                      alcance_operador=bool(p.get("alcance_operador", True)),
                      segundos=int(p.get("segundos") or 0),
                      codigo_catalogo=str(p.get("codigo_catalogo") or ""),
                      modo_falla_id=str(p.get("modo_falla_id") or ""))
        except (ErrorTPM, TypeError, ValueError) as exc:
            raise ErrorCargador(f"{donde}, punto {i}: {exc}") from exc
    return c


def checklist(ruta: str | Path) -> Checklist:
    return checklist_de_dict(_dict(ruta), str(ruta))


def ejecucion_de_dict(datos: dict, donde: str = "la ejecucion") -> Ejecucion:
    try:
        e = Ejecucion(id=str(datos.get("id") or ""),
                      checklist_id=str(datos.get("checklist_id") or ""),
                      activo_codigo=str(datos.get("activo_codigo") or ""),
                      operador=str(datos.get("operador") or ""),
                      fecha=str(datos.get("fecha") or ""))
    except ErrorTPM as exc:
        raise ErrorCargador(f"{donde}: {exc}") from exc
    if not e.id or not e.checklist_id:
        raise ErrorCargador(f"{donde}: necesita «id» y «checklist_id».")

    for i, it in enumerate(_lista(datos, "items", donde), 1):
        try:
            e.registrar(str(it.get("punto_id") or ""),
                        str(it.get("resultado") or ""),
                        str(it.get("observacion") or ""),
                        int(it.get("segundos") or 0))
        except (ErrorTPM, TypeError, ValueError) as exc:
            raise ErrorCargador(f"{donde}, item {i}: {exc}") from exc
    return e


def ejecucion(ruta: str | Path) -> Ejecucion:
    return ejecucion_de_dict(_dict(ruta), str(ruta))


def anomalia_de_dict(datos: dict, donde: str = "la anomalia") -> Anomalia:
    campos = {k: v for k, v in datos.items()
              if k in Anomalia.__dataclass_fields__}
    campos.setdefault("id", "")
    if "evidencia" in campos:
        campos["evidencia"] = tuple(campos["evidencia"] or ())
    try:
        return Anomalia(**campos)
    except Exception as exc:
        raise ErrorCargador(f"{donde}: {exc}") from exc
