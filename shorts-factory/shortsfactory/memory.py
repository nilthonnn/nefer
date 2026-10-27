"""Memoria del canal: lo ya producido, para no repetirse.

YouTube desmonetiza el contenido "repetitivo" o "producido en masa". La
memoria guarda, por cada Short, el tema, la narración, el indicador usado y
la firma de diseño, y la consultan:
- el selector de tendencias (no repetir tema),
- el validador de guiones (no repetir texto),
- el sorteo de diseño (no repetir combinación visual),
- la rotación de indicadores (no anclar siempre en el mismo dato).

Es un JSONL append-only en ``SF_DIR_ESTADO`` (en CI se persiste con caché).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ARCHIVO = "historial.jsonl"


def _bigramas(texto: str) -> set[tuple[str, str]]:
    p = re.findall(r"\w+", texto.lower())
    return set(zip(p, p[1:]))


def similitud(a: str, b: str) -> float:
    """Jaccard de bigramas de palabras: 0 = nada en común, 1 = idénticos."""
    x, y = _bigramas(a), _bigramas(b)
    return len(x & y) / len(x | y) if x and y else 0.0


class Memoria:
    def __init__(self, dir_estado: Path) -> None:
        self.ruta = dir_estado / ARCHIVO

    def entradas(self, ultimas: int | None = None) -> list[dict]:
        if not self.ruta.is_file():
            return []
        filas = []
        for linea in self.ruta.read_text(encoding="utf-8").splitlines():
            try:
                filas.append(json.loads(linea))
            except json.JSONDecodeError:
                continue
        return filas[-ultimas:] if ultimas else filas

    def registrar(self, **datos) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        datos.setdefault("fecha", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        with self.ruta.open("a", encoding="utf-8") as f:
            f.write(json.dumps(datos, ensure_ascii=False) + "\n")

    def mas_parecido(self, texto: str, campo: str = "narracion") -> tuple[float, dict | None]:
        mejor, fila = 0.0, None
        for e in self.entradas():
            s = similitud(texto, e.get(campo, ""))
            if s > mejor:
                mejor, fila = s, e
        return mejor, fila

    def firmas_recientes(self, n: int = 12) -> list[dict[str, str]]:
        return [e["variacion"] for e in self.entradas(n) if isinstance(e.get("variacion"), dict)]

    def indicadores_recientes(self, n: int = 10) -> list[str]:
        return [e.get("indicador", "") for e in self.entradas(n)]
