"""El mismo indice, pero en PostgreSQL con pgvector.

Cuando el historial deja de caber en un archivo —una flota entera, varios
talleres escribiendo a la vez— el indice se muda a una base y la busqueda se
hace en SQL. La interfaz es la de `Indice`: `buscar()` devuelve
`Coincidencia`, y el motor no distingue cual de los dos tiene delante.

Nada de esto se configura en el codigo. La cadena de conexion se lee de
`FIXMATE_PG_DSN` (o de `PGHOST`/`PGUSER`/... como cualquier cliente de
PostgreSQL): una contraseña escrita en un archivo .py es una contraseña
publicada el dia que el repositorio se comparte.

Esquema minimo:

    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE TABLE fixmate_fragmentos (
        id         text PRIMARY KEY,
        texto      text NOT NULL,
        fuente     text DEFAULT '',
        tipo       text DEFAULT 'documento',
        metadatos  jsonb NOT NULL DEFAULT '{}'::jsonb,
        embedding  vector(256) NOT NULL
    );
    CREATE INDEX ON fixmate_fragmentos
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    CREATE INDEX ON fixmate_fragmentos USING gin (metadatos);

Quien ya tenga sus informes en sus propias tablas no necesita copiarlos: basta
una vista con ese nombre y esas columnas, con el JOIN que le corresponda.
"""

from __future__ import annotations

import json
import os

from . import embeddings
from .indice import Coincidencia, Fragmento

TABLA = os.getenv("FIXMATE_PG_TABLA", "fixmate_fragmentos")

DDL = """CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS fixmate_fragmentos (
    id         text PRIMARY KEY,
    texto      text NOT NULL,
    fuente     text DEFAULT '',
    tipo       text DEFAULT 'documento',
    metadatos  jsonb NOT NULL DEFAULT '{}'::jsonb,
    embedding  vector(256) NOT NULL
);
CREATE INDEX IF NOT EXISTS fixmate_fragmentos_embedding
    ON fixmate_fragmentos USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS fixmate_fragmentos_metadatos
    ON fixmate_fragmentos USING gin (metadatos);
"""

COLUMNAS = "id, texto, fuente, tipo, metadatos"


class ErrorAlmacen(RuntimeError):
    """No se pudo hablar con la base."""


def literal_vector(vector) -> str:
    """El vector como lo espera pgvector: '[0.1,0.2,...]', sin espacios."""
    return "[" + ",".join(f"{float(v):.6f}" for v in vector) + "]"


def sql_busqueda(filtros: dict | None = None, tabla: str = TABLA) -> tuple[str, list]:
    """Arma la consulta y sus parametros. Se prueba sin base delante.

    Los filtros viajan como parametros, nunca interpolados: un codigo de falla
    dictado por voz puede llegar con cualquier cosa dentro.
    """
    condiciones, parametros = [], []
    for clave, valor in (filtros or {}).items():
        if valor in (None, "", []):
            continue
        valores = valor if isinstance(valor, (list, tuple, set)) else [valor]
        # El metadato puede ser una lista ("codigos_dtc": [...]) o un escalar;
        # la primera mitad de cada OR cubre la lista y la segunda el escalar.
        partes = []
        for v in valores:
            partes.append("(metadatos -> %s @> %s::jsonb OR metadatos ->> %s = %s)")
            parametros.extend([clave, json.dumps([str(v)]), clave, str(v)])
        condiciones.append("(" + " OR ".join(partes) + ")")

    donde = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    sql = (
        f"SELECT {COLUMNAS}, 1 - (embedding <=> %s::vector) AS similitud\n"
        f"FROM {tabla}\n"
        f"{donde}\n"
        f"ORDER BY embedding <=> %s::vector\n"
        f"LIMIT %s"
    ).replace("\n\n", "\n")
    return sql, parametros


class AlmacenPgvector:
    """Busqueda vectorial contra PostgreSQL. Misma firma que `Indice.buscar`."""

    def __init__(self, embebedor: embeddings.Embebedor | None = None,
                 dsn: str | None = None, tabla: str = TABLA, conexion=None):
        self.embebedor = embebedor or embeddings.EmbebedorLocal()
        self.tabla = tabla
        self.dsn = dsn or os.getenv("FIXMATE_PG_DSN") or ""
        self._conexion = conexion

    def conectar(self):
        if self._conexion is not None:
            return self._conexion
        try:
            import psycopg2
        except ImportError as exc:  # pragma: no cover - depende del entorno
            raise ErrorAlmacen("el almacen PostgreSQL necesita 'psycopg2-binary': "
                               "pip install nefer[fixmate-pg]") from exc
        try:
            # Sin DSN se dejan hablar las variables PGHOST/PGUSER/PGPASSWORD,
            # que es como se configura cualquier otro cliente de PostgreSQL.
            self._conexion = psycopg2.connect(self.dsn) if self.dsn else psycopg2.connect()
        except Exception as exc:
            raise ErrorAlmacen(f"no se pudo conectar a PostgreSQL: {exc}") from exc
        return self._conexion

    def buscar(self, consulta: str, limite: int = 3, filtros: dict | None = None,
               umbral: float = 0.0, preferencias: dict | None = None) -> list[Coincidencia]:
        vector = literal_vector(self.embebedor.embeber([consulta])[0])
        sql, parametros = sql_busqueda(filtros, self.tabla)
        conexion = self.conectar()
        try:
            with conexion.cursor() as cur:
                cur.execute(sql, [vector, *parametros, vector, limite])
                filas = cur.fetchall()
        except Exception as exc:
            raise ErrorAlmacen(f"la busqueda en PostgreSQL fallo: {exc}") from exc

        coincidencias = []
        for fila in filas:
            id_, texto, fuente, tipo, metadatos, similitud = fila
            if isinstance(metadatos, str):
                metadatos = json.loads(metadatos)
            similitud = float(similitud)
            if similitud < umbral:
                continue
            fragmento = Fragmento(id=str(id_), texto=texto or "", fuente=fuente or "",
                                  tipo=tipo or "documento", metadatos=metadatos or {})
            # Aqui no hay BM25: la base ordena por vector, y el lexico se deja
            # en cero para no simular una precision que no se midio.
            coincidencias.append(Coincidencia(fragmento, round(similitud, 4), 0.0,
                                              round(max(similitud, 0.0), 4)))
        return coincidencias

    def guardar_fragmentos(self, fragmentos) -> int:
        """Inserta o actualiza fragmentos ya vectorizados."""
        pendientes = [f for f in fragmentos if f.vector is None]
        if pendientes:
            for fragmento, vector in zip(
                    pendientes, self.embebedor.embeber([f.texto for f in pendientes])):
                fragmento.vector = vector
        conexion = self.conectar()
        sql = (f"INSERT INTO {self.tabla} (id, texto, fuente, tipo, metadatos, embedding) "
               f"VALUES (%s, %s, %s, %s, %s::jsonb, %s::vector) "
               f"ON CONFLICT (id) DO UPDATE SET texto = EXCLUDED.texto, "
               f"fuente = EXCLUDED.fuente, tipo = EXCLUDED.tipo, "
               f"metadatos = EXCLUDED.metadatos, embedding = EXCLUDED.embedding")
        try:
            with conexion.cursor() as cur:
                for f in fragmentos:
                    cur.execute(sql, (f.id, f.texto, f.fuente, f.tipo,
                                      json.dumps(f.metadatos, ensure_ascii=False),
                                      literal_vector(f.vector)))
            conexion.commit()
        except Exception as exc:
            conexion.rollback()
            raise ErrorAlmacen(f"no se pudieron guardar los fragmentos: {exc}") from exc
        return len(list(fragmentos))
