"""Modelo de datos del guion y de los resultados intermedios.

Un guion es: título + capítulos; cada capítulo, escenas; cada escena, una
narración (lo que dice la voz) y un visual (lo que se ve mientras tanto).
La duración de cada escena NO se escribe a mano: la decide la voz.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

# Visuales generados por nosotros (aportan originalidad ante YouTube) frente a
# material de stock (útil, pero por sí solo cuenta como contenido reutilizado).
TIPOS_PROPIOS = ("titular", "cifra", "linea_tiempo", "comparativa", "final")
TIPOS_VISUAL = ("stock", "imagen", *TIPOS_PROPIOS)
TipoVisual = Literal["stock", "imagen", "titular", "cifra", "linea_tiempo", "comparativa", "final"]


@dataclass
class Visual:
    tipo: TipoVisual
    # stock: términos de búsqueda (en inglés rinden mucho más en Pexels/Pixabay)
    busqueda: list[str] = field(default_factory=list)
    # titular/cifra/linea_tiempo/comparativa/final: props de la composición
    datos: dict[str, Any] = field(default_factory=dict)
    # imagen: ruta local (relativa al guion) de una foto o ilustración propia
    ruta: str = ""

    @property
    def es_propio(self) -> bool:
        return self.tipo in TIPOS_PROPIOS or self.tipo == "imagen"


@dataclass
class Escena:
    id: str
    narracion: str
    visual: Visual
    # silencio extra tras la frase, para dejar respirar un dato fuerte
    pausa: float = 0.0


@dataclass
class Capitulo:
    titulo: str
    escenas: list[Escena]


@dataclass
class Guion:
    titulo: str
    slug: str
    capitulos: list[Capitulo]
    descripcion: str = ""
    etiquetas: list[str] = field(default_factory=list)
    fuentes: list[str] = field(default_factory=list)
    miniatura: str = ""  # 2–5 palabras para la miniatura
    idioma: str = "es-419"
    origen: Path | None = None  # archivo de donde se leyó (para rutas relativas)

    @property
    def escenas(self) -> list[Escena]:
        return [e for c in self.capitulos for e in c.escenas]


@dataclass
class Palabra:
    texto: str
    inicio: float
    fin: float


@dataclass
class Locucion:
    """Audio de una escena con los tiempos de cada palabra (relativos a la escena)."""

    audio: Path
    duracion: float
    palabras: list[Palabra]


@dataclass
class Atribucion:
    """Crédito de un material de terceros, para la descripción del video."""

    proveedor: str
    autor: str = ""
    url: str = ""
    licencia: str = ""
    escena: str = ""


@dataclass
class ClipEscena:
    ruta: Path
    propio: bool
    atribuciones: list[Atribucion] = field(default_factory=list)
    # identificador del material de stock (para detectar repeticiones)
    ids_stock: list[str] = field(default_factory=list)


@dataclass
class Tramo:
    """Una escena ya ubicada en la línea de tiempo final."""

    escena: Escena
    capitulo: str
    inicio: float
    duracion: float
    locucion: Locucion
    clip: ClipEscena | None = None
