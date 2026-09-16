"""Indice de fragmentos: busqueda hibrida, filtros y persistencia en un archivo.

Hibrida quiere decir dos busquedas sumadas. BM25 encuentra lo que se llama
igual —un codigo de falla, un numero de parte, el nombre de un componente— y
el coseno de los vectores encuentra lo que se dice parecido. Por separado cada
una falla donde la otra acierta: 'P0300' no se parece a nada, y 'humo negro'
casi nunca esta escrito con esas dos palabras en el informe que lo resolvio.

El indice vive en un solo archivo JSON que se copia al telefono. No hay
servidor que levantar ni base que migrar; en `almacen_pg.py` esta la version
con PostgreSQL para quien ya tenga una flota entera cargada.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from . import embeddings, texto as _texto

VERSION_FORMATO = 1

# Reparto entre las dos busquedas. Medido contra el corpus de ejemplo: por
# debajo de 0.5 el codigo de falla exacto se pierde entre sinonimos, por
# encima de 0.7 una consulta dictada en voz alta deja de encontrar su informe.
PESO_VECTOR = 0.6
PESO_LEXICO = 0.4

# Lo que suma cada metadato preferido que coincide (el equipo, la familia).
# Suma en vez de filtrar: un manual no dice de que equipo de la flota habla, y
# descartarlo por eso deja al tecnico sin el procedimiento.
BONO_PREFERENCIA = 0.08

K1 = 1.5   # saturacion de frecuencia del BM25
B = 0.75   # cuanto penaliza la longitud del fragmento


@dataclass
class Fragmento:
    """Un trozo indexable: un informe, una seccion de manual o un acta."""

    id: str
    texto: str
    fuente: str = ""
    tipo: str = "documento"          # informe | manual | acta
    metadatos: dict = field(default_factory=dict)
    vector: list[float] | None = None

    def a_dict(self) -> dict:
        d = asdict(self)
        if self.vector is not None:
            d["vector"] = [round(v, 6) for v in self.vector]
        return d

    @classmethod
    def de_dict(cls, d: dict) -> "Fragmento":
        return cls(
            id=str(d["id"]),
            texto=d.get("texto", ""),
            fuente=d.get("fuente", ""),
            tipo=d.get("tipo", "documento"),
            metadatos=dict(d.get("metadatos") or {}),
            vector=list(d["vector"]) if d.get("vector") else None,
        )


@dataclass
class Coincidencia:
    """Un fragmento recuperado, con el desglose de por que salio."""

    fragmento: Fragmento
    similitud: float        # coseno del vector, [-1, 1]
    lexico: float           # BM25 ya normalizado a [0, 1]
    puntaje: float          # la mezcla de los dos, [0, 1]


class ErrorIndice(ValueError):
    """El indice no se puede usar tal como esta."""


def _coseno(a: Sequence[float], b: Sequence[float]) -> float:
    """Los vectores se guardan normalizados, asi que basta el producto punto."""
    return sum(x * y for x, y in zip(a, b))


class Indice:
    def __init__(self, embebedor: embeddings.Embebedor | None = None):
        self.embebedor = embebedor or embeddings.EmbebedorLocal()
        self.fragmentos: list[Fragmento] = []
        # Las cuentas del BM25 van juntas en un solo objeto y se cambian de
        # una sola vez: mientras se reindexa puede haber una consulta en
        # curso —la API atiende `POST /informes` y una busqueda a la vez— y
        # con las listas cambiandose una a una la busqueda leia una nueva
        # contra otra vieja y reventaba con IndexError.
        self._lexico: dict = {"tokens": [], "frecuencias": [],
                              "documentos": {}, "largo_medio": 0.0}
        # De que archivo salio cada cosa y como estaba ese archivo cuando se
        # leyo: es lo que permite reindexar solo lo que cambio.
        self.fuentes: dict[str, str] = {}
        # Lo que se midio del clasificador cuando se construyo el indice. Se
        # guarda porque el telefono no puede recalcularlo —dejar uno fuera es
        # cuadratico— y un porcentaje sin su medicion al lado no vale nada.
        self.medicion: dict | None = None
        self._tokens: list[list[str]] = []
        self._frecuencias: list[dict[str, int]] = []
        self._documentos_por_token: dict[str, int] = {}
        self._largo_medio = 0.0

    # ---------------------------------------------------------------- carga

    def agregar(self, fragmentos: Iterable[Fragmento]) -> int:
        """Añade fragmentos y calcula de una sola vez los que no traen vector.

        Un id que ya estaba se reemplaza en su sitio. Indexar dos veces la
        misma carpeta —o una carpeta y un archivo de dentro— es lo normal, y
        el resultado tiene que ser el mismo informe una vez, no dos veces el
        mismo antecedente ocupando los tres primeros lugares.
        """
        nuevos = list(fragmentos)
        if not nuevos:
            return 0
        pendientes = [f for f in nuevos if f.vector is None]
        if pendientes:
            vectores = self.embebedor.embeber([f.texto for f in pendientes])
            for fragmento, vector in zip(pendientes, vectores):
                fragmento.vector = vector

        posicion = {f.id: i for i, f in enumerate(self.fragmentos)}
        agregados = 0
        for fragmento in nuevos:
            if fragmento.id in posicion:
                self.fragmentos[posicion[fragmento.id]] = fragmento
            else:
                posicion[fragmento.id] = len(self.fragmentos)
                self.fragmentos.append(fragmento)
                agregados += 1
        self._reindexar()
        return agregados

    def olvidar(self, origen: str) -> int:
        """Quita todo lo que vino de un archivo. Devuelve cuantos fragmentos eran."""
        quedan = [f for f in self.fragmentos if f.metadatos.get("_origen") != origen]
        quitados = len(self.fragmentos) - len(quedan)
        self.fragmentos = quedan
        self.fuentes.pop(origen, None)
        if quitados:
            self._reindexar()
        return quitados

    def anotar_fuente(self, origen: str, firma: str) -> None:
        """Deja constancia de como estaba el archivo cuando se indexo."""
        self.fuentes[str(origen)] = firma

    def sin_cambios(self, origen: str, firma: str) -> bool:
        return self.fuentes.get(str(origen)) == firma

    def _reindexar(self) -> None:
        tokens_por_fragmento = [
            _texto.tokenizar(f"{f.texto} {self._texto_metadatos(f)}")
            for f in self.fragmentos]
        frecuencias: list[dict[str, int]] = []
        documentos: dict[str, int] = {}
        for tokens in tokens_por_fragmento:
            frecuencia: dict[str, int] = {}
            for token in tokens:
                frecuencia[token] = frecuencia.get(token, 0) + 1
            frecuencias.append(frecuencia)
            for token in frecuencia:
                documentos[token] = documentos.get(token, 0) + 1
        largo_medio = (sum(len(t) for t in tokens_por_fragmento)
                       / len(tokens_por_fragmento)) if tokens_por_fragmento else 0.0
        # Un solo cambio, al final: el que este buscando ve las cuentas
        # viejas enteras o las nuevas enteras, nunca media mezcla.
        self._lexico = {"tokens": tokens_por_fragmento, "frecuencias": frecuencias,
                        "documentos": documentos, "largo_medio": largo_medio}

    @staticmethod
    def _texto_metadatos(fragmento: Fragmento) -> str:
        """Los metadatos tambien se buscan: la OT y el codigo de falla se dictan."""
        partes = []
        for clave, valor in fragmento.metadatos.items():
            if clave.startswith("_"):
                continue
            if isinstance(valor, (list, tuple)):
                partes.extend(_numero(v) for v in valor)
            elif isinstance(valor, (str, int, float)):
                partes.append(_numero(valor))
        return " ".join(partes)

    # ------------------------------------------------------------ busqueda

    def buscar(self, consulta: str, limite: int = 3,
               filtros: dict | None = None, umbral: float = 0.0,
               preferencias: dict | None = None, acepta=None) -> list[Coincidencia]:
        """Los `limite` fragmentos mas parecidos a la consulta, mejor primero.

        `filtros` descarta lo que no case; `preferencias` no descarta nada, solo
        empuja hacia arriba lo que ademas coincide; `acepta` es un filtro
        escrito en Python, para lo que no se puede expresar comparando
        metadatos —por ejemplo, «la misma causa raiz, escrita como sea».
        """
        if not self.fragmentos:
            return []
        if limite < 1:
            raise ValueError("el limite de resultados no baja de 1.")

        candidatos = [i for i in range(len(self.fragmentos))
                      if _pasa_filtros(self.fragmentos[i], filtros)
                      and (acepta is None or acepta(self.fragmentos[i]))]
        if not candidatos:
            return []

        vector_consulta = self.embebedor.embeber([consulta])[0]
        lexico = self._lexico            # una sola lectura, coherente
        lexicos = self._bm25(consulta, candidatos, lexico)
        # BM25 no tiene tope: se lleva al [0, 1] del coseno con el mayor del
        # propio lote, que es lo unico comparable dentro de una consulta.
        mayor = max(lexicos.values()) if lexicos else 0.0

        resultados = []
        for i in candidatos:
            fragmento = self.fragmentos[i]
            similitud = _coseno(vector_consulta, fragmento.vector or [])
            lexico = (lexicos.get(i, 0.0) / mayor) if mayor > 0 else 0.0
            puntaje = PESO_VECTOR * max(similitud, 0.0) + PESO_LEXICO * lexico
            puntaje = min(1.0, puntaje + BONO_PREFERENCIA * _preferencias_que_casan(
                fragmento, preferencias))
            if puntaje >= umbral:
                resultados.append(Coincidencia(fragmento, round(similitud, 4),
                                               round(lexico, 4), round(puntaje, 4)))
        # A igualdad de puntaje gana el id, para que dos corridas del mismo
        # indice devuelvan el mismo orden.
        resultados.sort(key=lambda c: (-c.puntaje, c.fragmento.id))
        return resultados[:limite]

    def _bm25(self, consulta: str, candidatos: list[int],
              lexico: dict | None = None) -> dict[int, float]:
        lexico = lexico or self._lexico
        frecuencias, largos = lexico["frecuencias"], lexico["tokens"]
        largo_medio = lexico["largo_medio"]
        tokens = _texto.tokenizar(consulta)
        if not tokens or not largo_medio:
            return {}
        total = len(frecuencias)
        puntajes: dict[int, float] = {}
        for token in set(tokens):
            documentos = lexico["documentos"].get(token, 0)
            if not documentos:
                continue
            idf = math.log(1 + (total - documentos + 0.5) / (documentos + 0.5))
            for i in candidatos:
                if i >= total:
                    continue        # fragmento recien anadido: entra al reindexar
                frecuencia = frecuencias[i].get(token, 0)
                if not frecuencia:
                    continue
                largo = len(largos[i])
                denominador = frecuencia + K1 * (1 - B + B * largo / largo_medio)
                puntajes[i] = puntajes.get(i, 0.0) + idf * frecuencia * (K1 + 1) / denominador
        return puntajes

    # --------------------------------------------------------- persistencia

    def guardar(self, ruta: str | Path) -> Path:
        destino = Path(ruta)
        destino.parent.mkdir(parents=True, exist_ok=True)
        datos = {
            "version": VERSION_FORMATO,
            "embebedor": self.embebedor.nombre,
            "dimension": self.embebedor.dimension,
            "fuentes": self.fuentes,
            "medicion": self.medicion,
            "fragmentos": [f.a_dict() for f in self.fragmentos],
        }
        destino.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")
        return destino

    @classmethod
    def cargar(cls, ruta: str | Path,
               embebedor: embeddings.Embebedor | None = None) -> "Indice":
        origen = Path(ruta)
        if not origen.is_file():
            raise ErrorIndice(
                f"no existe el indice {origen}. Constrúyalo con: nefer fixmate indexar")
        try:
            datos = json.loads(origen.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ErrorIndice(f"{origen}: no es un indice legible ({exc}).") from exc
        if datos.get("version") != VERSION_FORMATO:
            raise ErrorIndice(
                f"{origen}: indice en formato v{datos.get('version')}, "
                f"este nefer lee v{VERSION_FORMATO}. Vuelva a indexar.")

        nombre = datos.get("embebedor", "local")
        embebedor = embebedor or embeddings.obtener(nombre)
        # Buscar con un embebedor distinto del que construyo el indice no da
        # error en ningun lado: da resultados sin sentido, que es peor.
        if embebedor.nombre != nombre:
            raise ErrorIndice(
                f"{origen}: se indexo con '{nombre}' y se esta buscando con "
                f"'{embebedor.nombre}'. Vuelva a indexar o use el mismo embebedor.")

        indice = cls(embebedor)
        indice.fuentes = {str(k): str(v) for k, v in (datos.get("fuentes") or {}).items()}
        indice.medicion = datos.get("medicion") or None
        indice.fragmentos = [Fragmento.de_dict(d) for d in datos.get("fragmentos", [])]
        sin_vector = [f.id for f in indice.fragmentos if not f.vector]
        if sin_vector:
            raise ErrorIndice(
                f"{origen}: {len(sin_vector)} fragmentos sin vector "
                f"(el primero, {sin_vector[0]}). Vuelva a indexar.")
        indice._reindexar()
        return indice

    def __len__(self) -> int:
        return len(self.fragmentos)


def _preferencias_que_casan(fragmento: Fragmento, preferencias: dict | None) -> int:
    """Cuantas preferencias cumple el fragmento. Ninguna es obligatoria."""
    if not preferencias:
        return 0
    return sum(1 for clave, valor in preferencias.items()
               if valor not in (None, "", [])
               and _pasa_filtros(fragmento, {clave: valor}))


def _numero(valor) -> str:
    """Un valor de metadato como texto, igual aqui que en el telefono.

    Python escribe `str(2050.0)` como «2050.0» y JavaScript como «2050»: el
    mismo horometro daria dos palabras distintas y el BM25 de cada lado
    contaria cosas distintas. Se escribe siempre la forma corta, que es la que
    los dos saben producir.
    """
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return str(valor)
    numero = float(valor)
    return str(int(numero)) if numero.is_integer() else repr(numero)


def firma_de(ruta) -> str:
    """Como esta un archivo ahora mismo: tamaño y huella de su contenido.

    Por contenido y no por fecha: copiar la carpeta compartida a otra maquina
    cambia todas las fechas sin cambiar una coma, y reindexar un manual de
    cuatrocientas paginas por eso cuesta tiempo y, con embeddings de pago,
    dinero.
    """
    ruta = Path(ruta)
    huella = hashlib.blake2b(digest_size=16)
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            huella.update(bloque)
    return f"{ruta.stat().st_size}:{huella.hexdigest()}"


def _pasa_filtros(fragmento: Fragmento, filtros: dict | None) -> bool:
    """Un filtro vacio no filtra; uno con valor exige coincidencia exacta.

    Los valores de lista casan por pertenencia: un informe con
    `codigos_dtc: ['P0300', 'SPN157']` pasa el filtro `codigo_dtc='P0300'`.
    """
    if not filtros:
        return True
    for clave, esperado in filtros.items():
        if esperado in (None, "", []):
            continue
        real = fragmento.metadatos.get(clave)
        if real is None and clave.endswith("s"):
            real = fragmento.metadatos.get(clave[:-1])
        if real is None and not clave.endswith("s"):
            real = fragmento.metadatos.get(clave + "s")
        if real is None:
            return False
        reales = real if isinstance(real, (list, tuple, set)) else [real]
        esperados = esperado if isinstance(esperado, (list, tuple, set)) else [esperado]
        normal = {_texto.normalizar(str(v)) for v in reales}
        if not any(_texto.normalizar(str(e)) in normal for e in esperados):
            return False
    return True
