"""Cerrar el circulo: lo que se resolvio hoy es el antecedente de mañana.

Un asistente que solo lee es un asistente que envejece. Cada falla que el
tecnico resuelve en campo —sobre todo la que resolvio *sin* que el indice la
tuviera— es exactamente el dato que le faltaba al proximo. Si registrarla
cuesta abrir un Excel en la oficina tres dias despues, no se registra.

Aqui se registra en el acto, desde la misma herramienta con la que se
consulto: el informe se añade al historial en disco y al indice que ya esta
cargado, de modo que la siguiente consulta —la del compañero que esta a
cuarenta kilometros -- ya lo encuentra.

Lo que no se acepta:

- un informe sin causa ni solucion, que no es un antecedente sino una queja;
- una orden de trabajo repetida, que duplicaria la evidencia y haria contar
  dos veces lo que paso una.

Y lo que se cierra en el telefono llega despues: en faena no hay senal, asi
que la app guarda lo resuelto y lo manda cuando la hay, en un archivo que
`recibir()` mete en el historial. Un archivo por WhatsApp es sincronizacion
suficiente para un taller, y no obliga a montar un servidor que alguien
tendria que mantener.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from . import ingesta
from .indice import Fragmento, Indice, firma_de

CAMPOS_MINIMOS = ("causa_raiz", "solucion_aplicada")


class ErrorCierre(ValueError):
    """El informe no se puede registrar tal como viene."""


def _historial(ruta: Path) -> dict:
    if not ruta.exists():
        return {"informes": []}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ErrorCierre(f"{ruta}: el historial no es JSON legible ({exc}).") from exc
    if isinstance(datos, list):
        return {"informes": datos}
    if not isinstance(datos, dict) or not isinstance(datos.get("informes"), list):
        raise ErrorCierre(f"{ruta}: no es un historial (falta la lista 'informes').")
    return datos


def siguiente_ot(historial: dict, hoy: _dt.date | None = None) -> str:
    """Un codigo correlativo del año, mirando los que ya estan."""
    hoy = hoy or _dt.date.today()
    prefijo = f"OT-{hoy.year}-"
    usados = []
    for informe in historial.get("informes", []):
        codigo = str(informe.get("codigo_ot") or "")
        if codigo.startswith(prefijo) and codigo[len(prefijo):].isdigit():
            usados.append(int(codigo[len(prefijo):]))
    return f"{prefijo}{max(usados, default=0) + 1:04d}"


def registrar(informe: dict, historial: str | Path,
              indice: Indice | None = None,
              hoy: _dt.date | None = None) -> dict:
    """Añade un informe al historial y, si se pasa, al indice ya cargado.

    Devuelve el informe tal como quedo guardado, con su codigo de orden y su
    fecha puestos si no venian.
    """
    if not isinstance(informe, dict):
        raise ErrorCierre("el informe tiene que ser un objeto.")
    faltan = [c for c in CAMPOS_MINIMOS if not str(informe.get(c) or "").strip()]
    if faltan:
        raise ErrorCierre(
            f"falta {' y '.join(faltan)}. Un informe sin causa ni solucion no "
            "le sirve al proximo tecnico: es una queja, no un antecedente.")
    if not str(informe.get("resumen_falla") or "").strip():
        raise ErrorCierre(
            "falta resumen_falla: sin la falla como se describio en campo, "
            "nadie va a encontrar este informe buscando por su sintoma.")

    ruta = Path(historial)
    datos = _historial(ruta)
    hoy = hoy or _dt.date.today()

    guardado = dict(informe)
    guardado.setdefault("fecha", hoy.isoformat())
    if not str(guardado.get("codigo_ot") or "").strip():
        guardado["codigo_ot"] = siguiente_ot(datos, hoy)
    elif any(str(i.get("codigo_ot") or "") == str(guardado["codigo_ot"])
             for i in datos["informes"]):
        raise ErrorCierre(
            f"la orden {guardado['codigo_ot']} ya esta en {ruta.name}. Use otro "
            "codigo, o deje que se genere solo.")

    datos["informes"].append(guardado)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")

    if indice is not None:
        fragmento = ingesta.de_informe(guardado, ruta.name,
                                       len(datos["informes"]) - 1)
        fragmento.metadatos["_origen"] = str(ruta)
        indice.agregar([fragmento])
        # El historial en disco cambio: se anota su firma nueva para que la
        # proxima reindexacion no lo relea entero por este informe.
        indice.anotar_fuente(str(ruta), firma_de(ruta))
    return guardado


def desde_diagnostico(consulta, diagnostico, solucion: str,
                      causa: str | None = None, **extra) -> dict:
    """Arma el informe a partir de lo que ya se consulto, para no reescribirlo."""
    informe = {
        "resumen_falla": getattr(consulta, "texto", str(consulta)),
        "causa_raiz": causa or getattr(diagnostico, "causa_raiz_mas_probable", ""),
        "solucion_aplicada": solucion,
    }
    for campo in ("codigo_equipo", "categoria"):
        valor = getattr(consulta, campo, None)
        if valor:
            informe[campo] = valor
    dtc = getattr(consulta, "codigo_dtc", None)
    if dtc:
        informe["codigos_dtc"] = [dtc]
    informe.update({k: v for k, v in extra.items() if v})
    return informe


def fragmento_de(informe: dict, origen: str = "") -> Fragmento:
    """El fragmento que representaria a ese informe, sin guardar nada."""
    fragmento = ingesta.de_informe(informe, origen)
    if origen:
        fragmento.metadatos["_origen"] = origen
    return fragmento


# ------------------------------------------------- lo que llega del campo

class Recepcion:
    """Que entro, que ya estaba y que se rechazo de un envio del telefono."""

    def __init__(self):
        self.nuevos: list[dict] = []
        self.repetidos: list[str] = []
        self.rechazados: list[tuple[str, str]] = []

    @property
    def hubo_cambios(self) -> bool:
        return bool(self.nuevos)

    def resumen(self) -> str:
        return (f"{len(self.nuevos)} nuevos, {len(self.repetidos)} ya estaban, "
                f"{len(self.rechazados)} rechazados")


def _informes_de(datos) -> list[dict]:
    if isinstance(datos, list):
        return datos
    if isinstance(datos, dict):
        for clave in ("informes", "pendientes"):
            if isinstance(datos.get(clave), list):
                return datos[clave]
    raise ErrorCierre("el envio no trae una lista de informes.")


def recibir(envio: str | Path | dict | list, historial: str | Path,
            indice: Indice | None = None,
            hoy: _dt.date | None = None) -> Recepcion:
    """Mete en el historial los informes que el telefono cerro en faena.

    Reenviar el mismo archivo no duplica nada: una orden que ya esta se cuenta
    como repetida y se deja pasar. Es lo que va a ocurrir —el tecnico manda el
    archivo, no sabe si llego, lo manda otra vez— y tratarlo como error
    obligaria a alguien a decidir cual de los dos envios era el bueno.
    """
    if isinstance(envio, (str, Path)):
        ruta = Path(envio)
        if not ruta.is_file():
            raise ErrorCierre(f"no existe el envio {ruta}")
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ErrorCierre(f"{ruta}: no es JSON legible ({exc}).") from exc
    else:
        datos = envio

    entrantes = _informes_de(datos)
    destino = Path(historial)
    ya_estan = {str(i.get("codigo_ot") or "")
                for i in _historial(destino).get("informes", [])}

    parte = Recepcion()
    for informe in entrantes:
        if not isinstance(informe, dict):
            parte.rechazados.append(("(no es un objeto)", "el informe no es un objeto"))
            continue
        codigo = str(informe.get("codigo_ot") or "").strip()
        if codigo and codigo in ya_estan:
            parte.repetidos.append(codigo)
            continue
        try:
            guardado = registrar(informe, destino, indice, hoy)
        except ErrorCierre as exc:
            parte.rechazados.append((codigo or "(sin OT)", str(exc)))
            continue
        ya_estan.add(str(guardado.get("codigo_ot") or ""))
        parte.nuevos.append(guardado)
    return parte
