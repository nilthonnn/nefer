"""Logging estructurado: consola legible y JSONL por run (auditoría)."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

RAIZ_LOG = "shortsfactory"


class _JSON(logging.Formatter):
    def format(self, r: logging.LogRecord) -> str:
        datos = {
            "t": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(r.created)) + "Z",
            "nivel": r.levelname,
            "modulo": r.name.removeprefix(RAIZ_LOG + "."),
            "msg": r.getMessage(),
        }
        for clave in ("run", "estado"):
            if hasattr(r, clave):
                datos[clave] = getattr(r, clave)
        if r.exc_info:
            datos["excepcion"] = self.formatException(r.exc_info)
        return json.dumps(datos, ensure_ascii=False)


def configurar(nivel: str | None = None) -> None:
    log = logging.getLogger(RAIZ_LOG)
    if getattr(log, "_listo", False):
        return
    log.setLevel(logging.DEBUG)
    consola = logging.StreamHandler(sys.stderr)
    consola.setLevel((nivel or os.environ.get("SF_LOG") or "INFO").upper())
    consola.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", "%H:%M:%S"))
    log.addHandler(consola)
    log.propagate = False
    log._listo = True  # type: ignore[attr-defined]


def a_archivo(ruta: Path) -> logging.Handler:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    h = logging.FileHandler(ruta, encoding="utf-8")
    h.setLevel(logging.DEBUG)
    h.setFormatter(_JSON())
    logging.getLogger(RAIZ_LOG).addHandler(h)
    return h


def quitar(h: logging.Handler) -> None:
    logging.getLogger(RAIZ_LOG).removeHandler(h)
    h.close()


def obtener(nombre: str) -> logging.Logger:
    return logging.getLogger(f"{RAIZ_LOG}.{nombre}")
