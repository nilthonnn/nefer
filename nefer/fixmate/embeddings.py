"""Vectores de texto: uno local que no pide red y otro que llama a un servicio.

El local es el que se usa por defecto, y no por comodidad: el tecnico consulta
desde el patio o desde un socavon, donde no hay señal. Un motor que solo
responde con internet no responde cuando hace falta.

Y el mismo vector se tiene que poder calcular en el telefono. El indice es un
archivo que se copia a la app de campo, pero ahi la consulta se escribe en el
propio telefono: si el navegador calculara su vector con otra cuenta que la
de aqui, no casaria con nada. Por eso el hash es FNV-1a, que son dos
operaciones enteras y sale identico en Python y en JavaScript, en vez de una
funcion criptografica que el navegador no trae.

Los dos cumplen la misma interfaz, asi que el indice no sabe cual tiene
delante; lo unico que no se puede es mezclarlos, y por eso el indice guarda el
nombre del que lo construyo y se niega a buscar con otro.
"""

from __future__ import annotations

import math
import os
from typing import Protocol, Sequence

from . import texto as _texto

DIMENSION_LOCAL = 256

# Cuanto pesa un trozo de palabra frente a la palabra entera.
PESO_NGRAMA = 0.35

# FNV-1a de 64 bits. Las dos constantes son las del algoritmo, y la mascara
# es lo unico que hay que recordar al portarlo: Python no desborda solo.
FNV_INICIO = 0xCBF29CE484222325
FNV_PRIMO = 0x100000001B3
MASCARA_64 = 0xFFFFFFFFFFFFFFFF


def fnv1a(datos: bytes) -> int:
    """FNV-1a de 64 bits. En JavaScript, lo mismo con BigInt:

        let h = 0xcbf29ce484222325n;
        for (const b of bytes) {
          h = BigInt.asUintN(64, (h ^ BigInt(b)) * 0x100000001b3n);
        }
    """
    huella = FNV_INICIO
    for byte in datos:
        huella = ((huella ^ byte) * FNV_PRIMO) & MASCARA_64
    return huella


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
        self.nombre = f"local-fnv-{dimension}"

    def _posicion(self, rasgo: str) -> tuple[int, float]:
        """En que posicion del vector cae un rasgo, y con que signo.

        El signo sale del bit mas alto del mismo hash. Sirve para que dos
        rasgos distintos que caen en la misma posicion —pasa, con 256
        posiciones— tiendan a cancelarse en vez de sumarse siempre.
        """
        huella = fnv1a(f"{self.semilla}:{rasgo}".encode("utf-8"))
        return huella % self.dimension, 1.0 if (huella >> 63) & 1 else -1.0

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


def obtener(nombre: str = "local", **kw) -> Embebedor:
    """Embebedor por nombre. Hay uno, y corre en esta maquina.

    Hubo un embebedor que llamaba a un servicio, y un modo 'auto' que lo
    elegia solo si habia clave en el entorno. Se quitaron los dos. Dos
    razones, y cualquiera de ellas basta: el indice que producia tiene 1536
    dimensiones y la app de campo solo sabe leer `local-fnv-256`, asi que el
    telefono lo rechazaba despues de haber indexado todo; y la variable de
    entorno decidia, sin que nadie lo pidiera, que el historial de fallas de
    la flota entera saliera a un tercero mientras se indexaba.
    """
    if nombre in ("local", "local-hash"):
        return EmbebedorLocal(**{k: v for k, v in kw.items()
                                 if k in ("dimension", "semilla")})
    # 'local-hash-N' es como se llamaba antes de FNV-1a. Se resuelve igual,
    # para que el indice viejo falle con el mensaje que dice que hay que
    # reindexar y no con un 'embebedor desconocido' que no ayuda a nadie.
    if nombre.startswith(("local-fnv-", "local-hash-")):
        return EmbebedorLocal(dimension=int(nombre.rsplit("-", 1)[1]))
    if nombre.startswith("openai"):
        raise ValueError(
            f"el embebedor {nombre!r} ya no existe: producia un indice que la "
            "app de campo no puede leer. Reindexe con 'local'.")
    raise ValueError(f"embebedor desconocido: {nombre!r}. Use 'local'.")
