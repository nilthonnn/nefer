"""Elige el proveedor de cada escena y cae a un respaldo si el principal falla.

Orden de preferencia:
  stock        → MoneyPrinterTurbo  → tarjeta "frase" (la idea clave en grande)
  infografías  → Remotion           → tarjeta Pillow equivalente
  imagen       → Ken Burns sobre la imagen

Un respaldo nunca es silencioso: queda en el log y en ``respaldos`` para que
la auditoría lo muestre antes de publicar.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..errores import DocumentalError, ErrorConfiguracion
from ..modelos import ClipEscena, Escena
from ..registro import de_escena, obtener
from .mpt import VisualStockMPT
from .remotion import VisualRemotion
from .tarjetas import VisualTarjetas

log = obtener("visual")


class Selector:
    def __init__(self, config: Config, cache: Path, usar_remotion: bool = True, usar_stock: bool = True) -> None:
        self.tarjetas = VisualTarjetas(config)
        self.remotion: VisualRemotion | None = None
        self.stock: VisualStockMPT | None = None
        self.respaldos: dict[str, str] = {}  # escena → motivo
        if usar_remotion:
            try:
                self.remotion = VisualRemotion(config)
            except ErrorConfiguracion as e:
                log.warning("Remotion no disponible, uso tarjetas Pillow: %s", e)
        if usar_stock:
            try:
                self.stock = VisualStockMPT(config, cache)
            except ErrorConfiguracion as e:
                log.warning("Stock (MoneyPrinterTurbo) no disponible, uso tarjetas: %s", e)

    def generar(self, escena: Escena, duracion: float, destino: Path) -> ClipEscena:
        slog = de_escena(log, escena.id)
        principal = None
        if escena.visual.tipo == "stock":
            principal = self.stock
        elif self.remotion is not None and self.remotion.puede(escena):
            principal = self.remotion

        if principal is not None:
            try:
                return principal.generar(escena, duracion, destino)
            except DocumentalError as e:
                slog.warning("%s falló, uso respaldo: %s", principal.nombre, e)
                self.respaldos[escena.id] = f"{principal.nombre}: {str(e).splitlines()[0]}"
        elif escena.visual.tipo == "stock":
            self.respaldos[escena.id] = "stock no configurado"

        tipo = "frase" if escena.visual.tipo == "stock" else escena.visual.tipo
        clip = self.tarjetas.generar(escena, duracion, destino, tipo=tipo)
        return clip
