"""Contabilidad de la cuota diaria de la YouTube Data API v3.

La cuota se reinicia a medianoche hora del Pacífico. Subir un video cuesta
``SF_YOUTUBE_COSTO_SUBIDA`` unidades (1600 en la tabla clásica de Google;
ajústalo si tu proyecto tiene otra tarifa). Se RESERVA antes de subir: si
no alcanza, no se intenta (un 403 quotaExceeded a mitad de subida desperdicia
el render). Repartir la carga entre varios proyectos para esquivar la cuota
está prohibido por los términos de la API: si necesitas más, se pide una
ampliación oficial a Google.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ..errors import ErrorCuota

PACIFICO = ZoneInfo("America/Los_Angeles")


class Cuota:
    def __init__(self, dir_estado: Path, limite: int) -> None:
        self.ruta = dir_estado / "cuota.json"
        self.limite = limite

    @staticmethod
    def hoy(ahora: datetime | None = None) -> str:
        return (ahora or datetime.now(PACIFICO)).astimezone(PACIFICO).date().isoformat()

    def _leer(self) -> dict[str, int]:
        try:
            return json.loads(self.ruta.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def usadas(self, ahora: datetime | None = None) -> int:
        return self._leer().get(self.hoy(ahora), 0)

    def reservar(self, unidades: int, ahora: datetime | None = None) -> None:
        datos = self._leer()
        dia = self.hoy(ahora)
        if datos.get(dia, 0) + unidades > self.limite:
            raise ErrorCuota(f"Cuota de YouTube insuficiente hoy ({datos.get(dia, 0)}/{self.limite}, se necesitan {unidades})")
        datos = {d: u for d, u in datos.items() if d >= dia[:8]}  # conserva solo el mes en curso
        datos[dia] = datos.get(dia, 0) + unidades
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(datos, indent=2), encoding="utf-8")
        os.replace(tmp, self.ruta)
