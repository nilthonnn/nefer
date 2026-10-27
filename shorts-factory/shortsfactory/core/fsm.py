"""Máquina de estados finita (FSM) persistente para cada Short.

    INICIADO → TENDENCIA → DATOS → GUION → VOZ → VISUALES → RENDER → QA → PUBLICACION → COMPLETADO
         └─────────────────────────── cualquier etapa ──────────────────────────────→ FALLIDO

- El estado se guarda en ``runs/<run_id>/estado.json`` tras CADA transición
  (escritura atómica). Si el proceso muere, ``reanudar`` continúa en la
  etapa donde quedó, con los artefactos de las anteriores.
- Cada etapa tiene su política de reintentos. Solo se reintentan los
  ``ErrorTransitorio`` (red, 5xx, navegador caído); el resto falla al
  momento con el error guardado.
- Las transiciones válidas están en una tabla: un manejador no puede saltar
  etapas ni volver atrás por error.
"""

from __future__ import annotations

import json
import os
import random
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from ..errors import ErrorTransitorio, ShortsError
from ..logs import obtener

log = obtener("fsm")


class Estado(StrEnum):
    INICIADO = "INICIADO"
    TENDENCIA = "TENDENCIA"
    DATOS = "DATOS"
    GUION = "GUION"
    VOZ = "VOZ"
    VISUALES = "VISUALES"
    RENDER = "RENDER"
    QA = "QA"
    PUBLICACION = "PUBLICACION"
    COMPLETADO = "COMPLETADO"
    FALLIDO = "FALLIDO"


ORDEN: list[Estado] = [
    Estado.INICIADO, Estado.TENDENCIA, Estado.DATOS, Estado.GUION, Estado.VOZ,
    Estado.VISUALES, Estado.RENDER, Estado.QA, Estado.PUBLICACION, Estado.COMPLETADO,
]
TERMINALES = {Estado.COMPLETADO, Estado.FALLIDO}
TRANSICIONES: dict[Estado, set[Estado]] = {
    e: {ORDEN[i + 1], Estado.FALLIDO} for i, e in enumerate(ORDEN[:-1])
}
TRANSICIONES[Estado.FALLIDO] = set(ORDEN[:-1])  # reanudar vuelve a la etapa que falló
TRANSICIONES[Estado.COMPLETADO] = set()


@dataclass(frozen=True)
class Politica:
    intentos: int = 3
    espera_inicial: float = 2.0
    espera_maxima: float = 60.0

    def espera(self, intento: int) -> float:
        base = min(self.espera_maxima, self.espera_inicial * 2 ** (intento - 1))
        return base + random.uniform(0, base * 0.25)


class Paso(BaseModel):
    estado: Estado
    inicio: str
    fin: str = ""
    resultado: str = ""  # ok | reintento | fallo
    error: str = ""


class Registro(BaseModel):
    run_id: str
    estado: Estado = Estado.INICIADO
    estado_fallido: Estado | None = None
    intentos: dict[str, int] = Field(default_factory=dict)
    artefactos: dict[str, Any] = Field(default_factory=dict)
    opciones: dict[str, Any] = Field(default_factory=dict)
    pasos: list[Paso] = Field(default_factory=list)
    error: str = ""
    traza: str = ""
    creado: str = Field(default_factory=lambda: _ahora())
    actualizado: str = Field(default_factory=lambda: _ahora())


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


Manejador = Callable[[Registro], dict[str, Any]]


class TransicionInvalida(ShortsError):
    pass


class MaquinaEstados:
    def __init__(
        self,
        ruta: Path,
        manejadores: dict[Estado, Manejador],
        politicas: dict[Estado, Politica] | None = None,
        dormir: Callable[[float], None] = time.sleep,
    ) -> None:
        self.ruta = ruta
        self.manejadores = manejadores
        self.politicas = politicas or {}
        self.dormir = dormir

    # --- persistencia -----------------------------------------------------------
    @staticmethod
    def cargar(ruta: Path) -> Registro:
        return Registro.model_validate_json(ruta.read_text(encoding="utf-8"))

    def guardar(self, r: Registro) -> None:
        r.actualizado = _ahora()
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ruta.with_suffix(".tmp")
        tmp.write_text(r.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp, self.ruta)

    # --- transiciones -----------------------------------------------------------
    def _mover(self, r: Registro, destino: Estado) -> None:
        if destino not in TRANSICIONES[r.estado]:
            raise TransicionInvalida(f"{r.estado} → {destino} no está permitido")
        log.debug("%s: %s → %s", r.run_id, r.estado, destino)
        r.estado = destino
        self.guardar(r)

    def reanudar(self, r: Registro) -> Registro:
        """Vuelve un run FALLIDO a la etapa que falló, con los intentos a cero."""
        if r.estado != Estado.FALLIDO or r.estado_fallido is None:
            return r
        etapa = r.estado_fallido
        r.intentos.pop(etapa.value, None)
        r.error = r.traza = ""
        r.estado_fallido = None
        self._mover(r, etapa)
        return r

    def ejecutar(self, r: Registro) -> Registro:
        self.guardar(r)
        while r.estado not in TERMINALES:
            estado = r.estado
            manejador = self.manejadores.get(estado)
            politica = self.politicas.get(estado, Politica())
            paso = Paso(estado=estado, inicio=_ahora())
            r.pasos.append(paso)
            try:
                if manejador is not None:
                    artefactos = manejador(r) or {}
                    r.artefactos.update(artefactos)
                paso.resultado, paso.fin = "ok", _ahora()
                self._mover(r, ORDEN[ORDEN.index(estado) + 1])
            except ErrorTransitorio as e:
                n = r.intentos.get(estado.value, 0) + 1
                r.intentos[estado.value] = n
                paso.fin, paso.error = _ahora(), f"{type(e).__name__}: {e}"
                if n < politica.intentos:
                    espera = politica.espera(n)
                    paso.resultado = "reintento"
                    log.warning("%s en %s (intento %d/%d), reintento en %.1f s: %s",
                                r.run_id, estado, n, politica.intentos, espera, e)
                    self.guardar(r)
                    self.dormir(espera)
                    continue
                self._fallar(r, estado, e, paso)
            except Exception as e:  # cualquier otro error es definitivo para esta ejecución
                paso.fin, paso.error = _ahora(), f"{type(e).__name__}: {e}"
                self._fallar(r, estado, e, paso)
        return r

    def _fallar(self, r: Registro, estado: Estado, e: BaseException, paso: Paso) -> None:
        paso.resultado = "fallo"
        r.estado_fallido = estado
        r.error = f"{type(e).__name__}: {e}"
        r.traza = "".join(traceback.format_exception(e))
        log.error("%s: FALLIDO en %s: %s", r.run_id, estado, r.error)
        self._mover(r, Estado.FALLIDO)


def leer_json(ruta: Path) -> Any:
    return json.loads(ruta.read_text(encoding="utf-8"))
