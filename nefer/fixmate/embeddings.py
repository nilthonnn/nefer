"""Vectores de texto: uno local que no pide red y otro que llama a un servicio.

El local es el que se usa por defecto, y no por comodidad: el tecnico consulta
desde el patio o desde un socavon, donde no hay señal. Un motor que solo
responde con internet no responde cuando hace falta.

Los dos cumplen la misma interfaz, asi que el indice no sabe cual tiene
delante; lo unico que no se puede es mezclarlos, y por eso el indice guarda el
nombre del que lo construyo y se niega a buscar con otro.
"""

from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol, Sequence

from . import texto as _texto

DIMENSION_LOCAL = 256

# Cuanto pesa un trozo de palabra frente a la palabra entera.
PESO_NGRAMA = 0.35


class Embebedor(Protocol):
    """Convierte texto en vectores comparables por coseno."""

    nombre: str
    dimension: int

    def embeber(self, textos: Sequence[str]) -> list[list[float]]:
        ...


class ErrorEmbebedor(RuntimeError):
    """No se pudo obtener el vector de un texto."""


def _l2(vector: list[float]) -> list[float]:
    norma = math.sqrt(sum(v * v for v in vector))
    if norma == 0.0:
        return vector
    return [v / norma for v in vector]


class EmbebedorLocal:
    """Vectores por hashing, sin modelo ni red.

    Cada palabra y cada trozo de cuatro caracteres de la palabra cae en una
    posicion del vector con un signo fijo, derivados de su hash. No entiende
    lenguaje —eso lo pone el LLM cuando lo hay— pero si empareja 'inyector'
    con 'inyectores' y 'fuga hidraulica' con 'fugas hidraulicas', que es
    justamente lo que la busqueda por palabras exactas del BM25 no hace.
    """

    def __init__(self, dimension: int = DIMENSION_LOCAL, semilla: str = "fixmate"):
        if dimension < 16:
            raise ValueError("la dimension del vector local no baja de 16.")
        self.dimension = dimension
        self.semilla = semilla
        self.nombre = f"local-hash-{dimension}"

    def _posicion(self, rasgo: str) -> tuple[int, float]:
        digest = hashlib.blake2b(
            f"{self.semilla}:{rasgo}".encode("utf-8"), digest_size=8).digest()
        entero = int.from_bytes(digest, "big")
        return entero % self.dimension, 1.0 if (entero >> 63) & 1 else -1.0

    def embeber(self, textos: Sequence[str]) -> list[list[float]]:
        return [self._uno(t) for t in textos]

    def _uno(self, cadena: str) -> list[float]:
        vector = [0.0] * self.dimension
        cuenta: dict[str, int] = {}
        peso: dict[str, float] = {}
        for token in _texto.tokenizar(cadena):
            # La palabra entera pesa mas que sus trozos: 'inyector' y
            # 'inyectores' se parecen, pero no son la misma palabra.
            cuenta[token] = cuenta.get(token, 0) + 1
            peso[token] = 1.0
            for trozo in _texto.ngramas(token):
                cuenta[trozo] = cuenta.get(trozo, 0) + 1
                peso[trozo] = PESO_NGRAMA
        for rasgo, veces in cuenta.items():
            # Frecuencia sublineal: la decima mencion de 'motor' no vale diez
            # veces la primera.
            i, signo = self._posicion(rasgo)
            vector[i] += signo * peso[rasgo] * (1.0 + math.log(veces))
        return _l2(vector)


class EmbebedorOpenAI:
    """Vectores de la API de OpenAI, para quien tenga el indice en un servidor.

    La clave se lee del entorno y no tiene valor por defecto: una clave de
    ejemplo escrita en el codigo es una clave que termina en el repositorio.
    """

    def __init__(self, modelo: str = "text-embedding-3-small",
                 clave: str | None = None, dimension: int = 1536,
                 cliente=None):
        self.modelo = modelo
        self.dimension = dimension
        self.nombre = f"openai-{modelo}"
        self._cliente = cliente
        self._clave = clave or os.getenv("OPENAI_API_KEY")

    def _obtener_cliente(self):
        if self._cliente is not None:
            return self._cliente
        if not self._clave:
            raise ErrorEmbebedor(
                "falta OPENAI_API_KEY. Use el embebedor local (--embebedor local) "
                "si no quiere depender de un servicio.")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise ErrorEmbebedor(
                "el embebedor de OpenAI necesita el paquete 'openai': "
                "pip install nefer[fixmate-openai]") from exc
        self._cliente = OpenAI(api_key=self._clave)
        return self._cliente

    def embeber(self, textos: Sequence[str]) -> list[list[float]]:
        if not textos:
            return []
        cliente = self._obtener_cliente()
        vectores: list[list[float]] = []
        # En lotes: un manual entero en una sola llamada la rechaza el servicio.
        for inicio in range(0, len(textos), 64):
            lote = [t.replace("\n", " ") or " " for t in textos[inicio:inicio + 64]]
            try:
                respuesta = cliente.embeddings.create(model=self.modelo, input=lote)
            except Exception as exc:  # pragma: no cover - depende de la red
                raise ErrorEmbebedor(f"el servicio de embeddings fallo: {exc}") from exc
            vectores.extend(list(dato.embedding) for dato in respuesta.data)
        if vectores:
            self.dimension = len(vectores[0])
        return [_l2(v) for v in vectores]


def obtener(nombre: str = "local", **kw) -> Embebedor:
    """Embebedor por nombre: 'local', 'openai' o 'auto'.

    'auto' usa OpenAI solo si hay clave en el entorno; si no, el local. Nunca
    falla por no tener red: un motor de campo que no arranca sin servicio no
    sirve en campo.
    """
    if nombre == "auto":
        nombre = "openai" if os.getenv("OPENAI_API_KEY") else "local"
    if nombre in ("local", "local-hash"):
        return EmbebedorLocal(**{k: v for k, v in kw.items()
                                 if k in ("dimension", "semilla")})
    if nombre == "openai":
        return EmbebedorOpenAI(**{k: v for k, v in kw.items()
                                  if k in ("modelo", "clave", "dimension", "cliente")})
    if nombre.startswith("local-hash-"):
        return EmbebedorLocal(dimension=int(nombre.rsplit("-", 1)[1]))
    if nombre.startswith("openai-"):
        return EmbebedorOpenAI(modelo=nombre.split("-", 1)[1])
    raise ValueError(f"embebedor desconocido: {nombre!r}. Use 'local' u 'openai'.")
