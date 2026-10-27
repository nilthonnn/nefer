"""Cola de trabajos en disco: una carpeta por estado, un JSON por trabajo.

    trabajos/pendiente → en_curso → hecho
                                  ↘ fallido (con el error y la traza)

El paso de un estado a otro es un ``rename`` (atómico en el mismo disco), así
dos procesos que lean la misma cola nunca toman el mismo trabajo. No hace
falta Redis ni una base de datos para producir unos pocos videos al día.
"""

from __future__ import annotations

import json
import os
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable

from .errores import ErrorTransitorio
from .registro import obtener

log = obtener("cola")
ESTADOS = ("pendiente", "en_curso", "hecho", "fallido")
REENCOLADOS_MAX = 2


class Cola:
    def __init__(self, raiz: Path) -> None:
        self.raiz = raiz
        for estado in ESTADOS:
            (raiz / estado).mkdir(parents=True, exist_ok=True)

    def agregar(self, guion: Path) -> str:
        # Microsegundos al frente: el orden alfabético es el orden de llegada.
        id_ = datetime.now().strftime("%Y%m%d-%H%M%S-%f-") + uuid.uuid4().hex[:4]
        datos = {"id": id_, "guion": str(guion.resolve()), "creado": datetime.now().isoformat(timespec="seconds"), "reencolados": 0}
        self._escribir("pendiente", id_, datos)
        log.info("trabajo %s en cola: %s", id_, guion)
        return id_

    def estado(self) -> dict[str, list[dict]]:
        return {e: [self._leer(p) for p in sorted((self.raiz / e).glob("*.json"))] for e in ESTADOS}

    def tomar(self) -> dict | None:
        """Reclama el trabajo pendiente más antiguo (o None si no hay)."""
        for ruta in sorted((self.raiz / "pendiente").glob("*.json")):
            destino = self.raiz / "en_curso" / ruta.name
            try:
                os.rename(ruta, destino)
            except FileNotFoundError:
                continue  # otro proceso lo tomó primero
            return self._leer(destino)
        return None

    def terminar(self, trabajo: dict, resultado: dict) -> None:
        trabajo.update(resultado=resultado, terminado=datetime.now().isoformat(timespec="seconds"))
        self._mover(trabajo, "hecho")

    def fallar(self, trabajo: dict, error: BaseException) -> None:
        trabajo["error"] = f"{type(error).__name__}: {error}"
        trabajo["traza"] = traceback.format_exception(error)
        if isinstance(error, ErrorTransitorio) and trabajo.get("reencolados", 0) < REENCOLADOS_MAX:
            trabajo["reencolados"] = trabajo.get("reencolados", 0) + 1
            log.warning("trabajo %s: fallo transitorio, vuelve a la cola (%d/%d)", trabajo["id"], trabajo["reencolados"], REENCOLADOS_MAX)
            self._mover(trabajo, "pendiente")
        else:
            log.error("trabajo %s fallido: %s", trabajo["id"], trabajo["error"])
            self._mover(trabajo, "fallido")

    def reintentar_fallidos(self) -> int:
        n = 0
        for ruta in (self.raiz / "fallido").glob("*.json"):
            datos = self._leer(ruta)
            datos.pop("error", None)
            datos.pop("traza", None)
            datos["reencolados"] = 0
            self._escribir("pendiente", datos["id"], datos)
            ruta.unlink()
            n += 1
        return n

    def procesar(self, ejecutar: Callable[[Path], dict], maximo: int | None = None) -> int:
        """Procesa trabajos hasta vaciar la cola (o ``maximo``). Devuelve cuántos terminó bien."""
        hechos = 0
        atendidos = 0
        while maximo is None or atendidos < maximo:
            trabajo = self.tomar()
            if trabajo is None:
                break
            atendidos += 1
            log.info("trabajo %s: %s", trabajo["id"], trabajo["guion"])
            try:
                self.terminar(trabajo, ejecutar(Path(trabajo["guion"])))
                hechos += 1
            except KeyboardInterrupt:
                self._mover(trabajo, "pendiente")
                raise
            except Exception as e:  # un trabajo roto no debe detener la cola
                self.fallar(trabajo, e)
        return hechos

    # --- internos
    def _escribir(self, estado: str, id_: str, datos: dict) -> None:
        temporal = self.raiz / estado / f".{id_}.tmp"
        temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporal, self.raiz / estado / f"{id_}.json")

    def _leer(self, ruta: Path) -> dict:
        return json.loads(ruta.read_text(encoding="utf-8"))

    def _mover(self, trabajo: dict, estado: str) -> None:
        self._escribir(estado, trabajo["id"], trabajo)
        (self.raiz / "en_curso" / f"{trabajo['id']}.json").unlink(missing_ok=True)
