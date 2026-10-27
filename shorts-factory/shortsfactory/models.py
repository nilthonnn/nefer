"""Modelos de datos del pipeline (Pydantic): lo que fluye entre etapas.

Todos se serializan a JSON en el directorio del run, de modo que cualquier
etapa puede reanudarse leyendo el resultado de la anterior.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

TipoVisual = Literal["broll", "grafico", "cifra", "texto"]


class Tendencia(BaseModel):
    titulo: str
    url: str = ""
    fuente: str = "manual"  # hackernews | gdelt | manual
    puntaje: float = 0.0


class Punto(BaseModel):
    anio: int
    valor: float


class Serie(BaseModel):
    """Serie de datos reales (Banco Mundial) en la que se ancla el Short."""

    indicador_id: str
    indicador: str  # nombre legible en español
    unidad: str  # "%", "USD", "por 100 personas"...
    pais: str  # código ISO
    pais_nombre: str
    puntos: list[Punto] = Field(min_length=2)
    fuente: str = "Banco Mundial"
    url: str = ""

    @property
    def ultimo(self) -> Punto:
        return self.puntos[-1]

    def valores_citables(self) -> set[float]:
        """Números que el guion puede decir: valores (redondeados) y variaciones."""
        citables: set[float] = set()
        for p in self.puntos:
            for dec in (0, 1):
                citables.add(round(p.valor, dec))
            citables.add(float(p.anio))
        primero, ultimo = self.puntos[0], self.puntos[-1]
        if primero.valor:
            cambio = (ultimo.valor - primero.valor) / abs(primero.valor) * 100
            citables.update({round(cambio), round(abs(cambio)), round(cambio, 1), round(abs(cambio), 1)})
            veces = ultimo.valor / primero.valor
            citables.update({round(veces), round(veces, 1)})
        citables.add(float(ultimo.anio - primero.anio))
        citables.add(round(ultimo.valor - primero.valor, 1))
        citables.add(round(abs(ultimo.valor - primero.valor), 1))
        return citables


class Frase(BaseModel):
    texto: str = Field(min_length=2)
    visual: TipoVisual
    broll_busqueda: str = ""  # en inglés, filmable (Pexels)
    enfasis: list[str] = Field(default_factory=list)  # palabras a resaltar en los subtítulos
    pausa_despues: float = Field(0.0, ge=0, le=0.8)


class Guion(BaseModel):
    titulo: str = Field(min_length=5, max_length=70)
    frases: list[Frase] = Field(min_length=3, max_length=8)
    hashtags: list[str] = Field(default_factory=list, max_length=5)
    descripcion: str = ""
    generador: str = "llm"  # "llm" | "plantilla" (la plantilla nunca se publica)

    @field_validator("hashtags")
    @classmethod
    def _limpiar_hashtags(cls, v: list[str]) -> list[str]:
        return ["#" + "".join(ch for ch in h.lstrip("#") if ch.isalnum()) for h in v if h.strip("# ")]

    @property
    def texto(self) -> str:
        return " ".join(f.texto for f in self.frases)

    @property
    def palabras(self) -> int:
        return len(self.texto.split())


class PalabraT(BaseModel):
    texto: str
    inicio: float
    fin: float
    enfasis: bool = False


class Narracion(BaseModel):
    audio: Path
    duracion: float
    palabras: list[PalabraT]
    frases: list[tuple[float, float]]  # (inicio, fin) de cada frase en el audio final
    motor: str
    exacta: bool  # True si los tiempos vienen del motor (no estimados)


class Variacion(BaseModel):
    """Diseño de ESTE video. Se sortea en cada run y se evita repetir los recientes."""

    paleta: str
    colores: dict[str, str]
    fuente: str
    estilo_subtitulos: Literal["caja", "pop", "subrayado"]
    palabras_por_pagina: int = Field(ge=1, le=3)
    mayusculas: bool
    posicion_subtitulos: float = Field(ge=0.45, le=0.8)  # fracción de alto
    fondo: Literal["degradado", "reticula", "orbitas"]
    estilo_grafico: Literal["linea", "barras"]
    transicion: Literal["deslizar", "zoom", "barrido"]
    intensidad_movimiento: float = Field(ge=0.03, le=0.12)
    velocidad_voz: float = Field(ge=0.92, le=1.12)
    pausa_gancho: float = Field(ge=0.1, le=0.4)
    semilla: int

    def firma(self) -> dict[str, str]:
        """Rasgos visibles que, repetidos, hacen que dos videos parezcan clones."""
        return {
            "paleta": self.paleta, "fuente": self.fuente, "estilo_subtitulos": self.estilo_subtitulos,
            "fondo": self.fondo, "estilo_grafico": self.estilo_grafico, "transicion": self.transicion,
            "palabras_por_pagina": str(self.palabras_por_pagina), "mayusculas": str(self.mayusculas),
        }


class Segmento(BaseModel):
    inicio: float
    fin: float
    tipo: TipoVisual
    texto: str = ""
    archivo: str = ""  # b-roll ya normalizado (ruta relativa a public/ de Remotion)


class ResultadoSubida(BaseModel):
    video_id: str
    url: str
    privacidad: str
    titulo: str
    unidades_cuota: int
