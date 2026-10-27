"""Logging: legible en consola y en JSON por líneas en el archivo del trabajo.

El archivo ``render.log.jsonl`` de cada video guarda todo (incluido DEBUG con
cada comando de ffmpeg), así un fallo nocturno se puede reconstruir sin repetir
el render.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

NOMBRE = "documental"


class _FormatoJSON(logging.Formatter):
    def format(self, registro: logging.LogRecord) -> str:
        datos = {
            "t": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(registro.created)),
            "nivel": registro.levelname,
            "modulo": registro.name,
            "msg": registro.getMessage(),
        }
        escena = getattr(registro, "escena", None)
        if escena:
            datos["escena"] = escena
        if registro.exc_info:
            datos["excepcion"] = self.formatException(registro.exc_info)
        return json.dumps(datos, ensure_ascii=False)


class _FormatoConsola(logging.Formatter):
    def format(self, registro: logging.LogRecord) -> str:
        escena = getattr(registro, "escena", None)
        prefijo = f"[{escena}] " if escena else ""
        base = f"{time.strftime('%H:%M:%S')} {registro.levelname:<7} {prefijo}{registro.getMessage()}"
        if registro.exc_info and registro.levelno >= logging.ERROR:
            base += "\n" + self.formatException(registro.exc_info)
        return base


def configurar(nivel: str | None = None) -> logging.Logger:
    """Prepara el logger raíz del paquete (idempotente)."""
    log = logging.getLogger(NOMBRE)
    if getattr(log, "_configurado", False):
        return log
    log.setLevel(logging.DEBUG)
    consola = logging.StreamHandler(sys.stderr)
    consola.setLevel((nivel or os.environ.get("DOCUMENTAL_LOG") or "INFO").upper())
    consola.setFormatter(_FormatoConsola())
    log.addHandler(consola)
    log.propagate = False
    log._configurado = True  # type: ignore[attr-defined]
    return log


def a_archivo(ruta: Path) -> logging.Handler:
    """Añade un archivo JSONL con todo el detalle. Devuelve el handler para quitarlo al terminar."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    manejador = logging.FileHandler(ruta, encoding="utf-8")
    manejador.setLevel(logging.DEBUG)
    manejador.setFormatter(_FormatoJSON())
    logging.getLogger(NOMBRE).addHandler(manejador)
    return manejador


def quitar(manejador: logging.Handler) -> None:
    logging.getLogger(NOMBRE).removeHandler(manejador)
    manejador.close()


def obtener(modulo: str) -> logging.Logger:
    return logging.getLogger(f"{NOMBRE}.{modulo}")


def de_escena(log: logging.Logger, escena: str) -> logging.LoggerAdapter:
    """Logger que etiqueta cada línea con la escena en curso."""
    return logging.LoggerAdapter(log, {"escena": escena})
