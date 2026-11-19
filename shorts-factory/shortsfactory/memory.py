"""Memoria del canal: lo ya producido, para no repetirse.

YouTube desmonetiza el contenido "repetitivo" o "producido en masa". La
memoria guarda, por cada Short, el tema, la narración, el indicador usado y
la firma de diseño, y la consultan:
- el selector de tendencias y la etapa TENDENCIA (no repetir tema ni ángulo),
- el validador de guiones (no repetir texto),
- el sorteo de diseño (no repetir combinación visual),
- la rotación de indicadores (no anclar siempre en el mismo dato).

Es un JSONL append-only en ``SF_DIR_ESTADO``. En CI se persiste en la rama
huérfana ``estado-produccion`` (``estado_git.py``) y, como complemento, en
la caché de Actions. Dos copias que divergieron se FUSIONAN por ``run_id``:
nunca se pierde una fila por sobrescribir.
"""

from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ARCHIVO = "historial.jsonl"

# Palabras que no distinguen un tema de otro (es + en: las tendencias llegan en ambos).
_VACIAS = frozenset("""
a al algo ante como con contra cual cuando de del desde donde el ella ellos en entre es esa ese esta este esto
fue ha hay la las le les lo los mas me mi muy no nos o otra otro para pero por porque que quien se ser si sin sobre
son su sus tambien te tiene todo tras tu un una uno unos y ya ahora asi cada
lanza lanzo nuevo nueva nuevos nuevas vuelve vuelven sube suben subir baja bajan bajar pierde supera dispara
anuncia presenta llega llegan record hoy ano anos mundo primer primera puede pueden hace dice segun
the of to in on for and or a an is are was be by with from at as its it this that how why what new vs
launches launch says now first more than after over
""".split())


def _bigramas(texto: str) -> set[tuple[str, str]]:
    p = re.findall(r"\w+", texto.lower())
    return set(zip(p, p[1:]))


def similitud(a: str, b: str) -> float:
    """Jaccard de bigramas de palabras: 0 = nada en común, 1 = idénticos."""
    x, y = _bigramas(a), _bigramas(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def _raices(texto: str) -> list[str]:
    """Palabras con contenido, reducidas a una raíz corta.

    Cortar a 6 letras es un lematizador burdo pero eficaz en español:
    «semiconductores»/«semiconductor», «inflación»/«inflacionaria» y
    «aranceles»/«arancel» caen en la misma raíz.
    """
    return [p[:6] for p in re.findall(r"[a-z0-9]+", _sin_acentos(texto)) if p not in _VACIAS and len(p) > 1]


def _trigramas(texto: str) -> Counter[str]:
    t = f"  {' '.join(_raices(texto))}  "
    return Counter(t[i:i + 3] for i in range(len(t) - 2))


def _coseno(x: Counter[str], y: Counter[str]) -> float:
    comun = sum(x[k] * y[k] for k in x.keys() & y.keys())
    norma = math.sqrt(sum(v * v for v in x.values())) * math.sqrt(sum(v * v for v in y.values()))
    return comun / norma if norma else 0.0


def similitud_tema(a: str, b: str) -> float:
    """Parecido de dos temas (0–1), robusto a orden, plurales, acentos y relleno.

    Combina el solapamiento de raíces (qué conceptos aparecen) con el coseno de
    trigramas de caracteres (variantes de una misma palabra). Toma el mayor:
    basta con que una de las dos señales vea el mismo tema.
    """
    ra, rb = set(_raices(a)), set(_raices(b))
    if not ra or not rb:
        return 0.0
    solape = len(ra & rb) / min(len(ra), len(rb))
    # Un solo concepto en común entre títulos largos no es el mismo tema.
    if len(ra & rb) == 1 and min(len(ra), len(rb)) > 2:
        solape *= 0.5
    return max(solape, _coseno(_trigramas(a), _trigramas(b)))


def _clave(fila: dict) -> str:
    return str(fila.get("run_id") or json.dumps(fila, sort_keys=True, ensure_ascii=False))


def fusionar(*listas: list[dict]) -> list[dict]:
    """Une historiales sin duplicar (clave: ``run_id``), en orden de fecha."""
    vistas: dict[str, dict] = {}
    for filas in listas:
        for f in filas:
            vistas.setdefault(_clave(f), f)
    return sorted(vistas.values(), key=lambda f: (str(f.get("fecha", "")), _clave(f)))


def leer_jsonl(ruta: Path) -> list[dict]:
    if not ruta.is_file():
        return []
    filas = []
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        try:
            fila = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if isinstance(fila, dict):
            filas.append(fila)
    return filas


def escribir_jsonl(ruta: Path, filas: list[dict]) -> None:
    """Escritura atómica: un corte a mitad nunca deja el historial truncado."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(f, ensure_ascii=False) + "\n" for f in filas), encoding="utf-8")
    os.replace(tmp, ruta)


class Memoria:
    def __init__(self, dir_estado: Path) -> None:
        self.ruta = dir_estado / ARCHIVO

    def entradas(self, ultimas: int | None = None) -> list[dict]:
        filas = leer_jsonl(self.ruta)
        return filas[-ultimas:] if ultimas else filas

    def registrar(self, **datos) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        datos.setdefault("fecha", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        with self.ruta.open("a", encoding="utf-8") as f:
            f.write(json.dumps(datos, ensure_ascii=False) + "\n")

    def fusionar_con(self, otras: list[dict]) -> int:
        """Incorpora filas de otra copia del historial. Devuelve cuántas eran nuevas."""
        propias = self.entradas()
        unidas = fusionar(propias, otras)
        if len(unidas) != len(propias):
            escribir_jsonl(self.ruta, unidas)
        return len(unidas) - len(propias)

    def mas_parecido(self, texto: str, campo: str = "narracion") -> tuple[float, dict | None]:
        mejor, fila = 0.0, None
        for e in self.entradas():
            s = similitud(texto, e.get(campo, ""))
            if s > mejor:
                mejor, fila = s, e
        return mejor, fila

    def tema_mas_parecido(self, tema: str, ultimas: int = 50) -> tuple[float, dict | None]:
        """El registro de los últimos ``ultimas`` cuyo tema o título más se parece a ``tema``."""
        mejor, fila = 0.0, None
        for e in self.entradas(ultimas):
            s = max(similitud_tema(tema, e.get("tema", "")), similitud_tema(tema, e.get("titulo", "")))
            if s > mejor:
                mejor, fila = s, e
        return mejor, fila

    def angulo_repetido(self, tema: str, indicador: str, ultimas: int = 50, umbral: float = 0.4) -> dict | None:
        """Mismo dato con un tema parecido: el mismo ángulo aunque el titular cambie."""
        for e in reversed(self.entradas(ultimas)):
            if e.get("indicador") == indicador and similitud_tema(tema, e.get("tema", "")) >= umbral:
                return e
        return None

    def firmas_recientes(self, n: int = 12) -> list[dict[str, str]]:
        return [e["variacion"] for e in self.entradas(n) if isinstance(e.get("variacion"), dict)]

    def indicadores_recientes(self, n: int = 10) -> list[str]:
        return [e.get("indicador", "") for e in self.entradas(n)]
