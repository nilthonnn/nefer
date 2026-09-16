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
    CREATE INDEX ON fixmate_fragmentos USING gin (metadatos);
    CREATE INDEX ON fixmate_fragmentos USING gin (to_tsvector('spanish', texto));

Quien ya tenga sus informes en sus propias tablas no necesita copiarlos: basta
una vista con ese nombre y esas columnas, con el JOIN que le corresponda.

No hay indice vectorial, y es a proposito. La busqueda hibrida ordena por una
mezcla de dos puntajes, y por esa expresion no hay indice que valga: PostgreSQL
recorre la tabla igual. Un indice aproximado solo lo usaria la busqueda sin la
mitad lexica, y ahi hace daño: `ivfflat` reparte las filas en listas cuando se
crea, asi que creado sobre la tabla vacia —que es lo que hace `crear_esquema()`
antes de la primera carga— queda con listas que no corresponden a nada y la
consulta devuelve cero filas. Cero, no menos: el tecnico pregunta y no sale
nada, sin error que lo delate.

Con el historial de un taller —miles de filas— el recorrido completo cuesta
milisegundos y acierta siempre. Si algun dia la tabla crece hasta que no
alcance, el indice se agrega sobre la tabla ya cargada y se mide:

    CREATE INDEX ON fixmate_fragmentos
        USING hnsw (embedding vector_cosine_ops);

`hnsw` se construye fila por fila y no depende de que la tabla este llena,
pero sigue siendo aproximado: antes de dejarlo puesto hay que comparar lo que
devuelve contra el recorrido exacto, porque lo que se pierde no se ve.

La busqueda es hibrida igual que en el archivo: el vector lo pone pgvector y
las palabras exactas las pone la busqueda de texto del propio PostgreSQL
(`ts_rank_cd` con diccionario español). No es el mismo BM25 que el motor
local —son dos implementaciones distintas de la misma idea— y por eso los
puntajes no se comparan entre los dos caminos; el orden de lo recuperado si
es equivalente, y eso es lo que se mide.
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
CREATE INDEX IF NOT EXISTS fixmate_fragmentos_metadatos
    ON fixmate_fragmentos USING gin (metadatos);
-- La mitad léxica de la búsqueda: sin este índice funciona igual, pero
-- recorriendo la tabla entera en cada consulta.
CREATE INDEX IF NOT EXISTS fixmate_fragmentos_texto
    ON fixmate_fragmentos USING gin (to_tsvector('spanish', texto));
"""

COLUMNAS = "id, texto, fuente, tipo, metadatos"

# «gotea aceite cilindro» como «gotea O aceite O cilindro». El texto viene de
# un tsquery ya saneado por PostgreSQL, no del parametro en crudo.
CONSULTA_O = ("replace(plainto_tsquery('spanish', %s)::text, ' & ', ' | ')::tsquery")

# El mismo reparto que en el motor local, para que las dos mitades pesen lo
# mismo vengan de donde vengan.
PESO_VECTOR = 0.6
PESO_LEXICO = 0.4


class ErrorAlmacen(RuntimeError):
    """No se pudo hablar con la base."""


def literal_vector(vector) -> str:
    """El vector como lo espera pgvector: '[0.1,0.2,...]', sin espacios."""
    return "[" + ",".join(f"{float(v):.6f}" for v in vector) + "]"


def sql_busqueda(filtros: dict | None = None, tabla: str = TABLA,
                 lexico: bool = True) -> tuple[str, list]:
    """Arma la consulta hibrida y sus parametros. Se prueba sin base delante.

    Un solo recorrido: el vector y el texto se puntuan a la vez y se ordena
    por la mezcla. Recorre la tabla entera, que con el historial de un taller
    —miles de filas, no millones— cuesta milisegundos; afinar eso con una
    busqueda aproximada en dos pasos es un problema que todavia no existe, y
    resolverlo antes de tiempo costaria que el resultado dependiera de que la
    fila buena estuviera en el primer lote.

    Los filtros viajan como parametros, nunca interpolados: un codigo de
    falla dictado por voz puede llegar con cualquier cosa dentro.

    La consulta de texto se pasa a «o» entre palabras. `plainto_tsquery` las
    une con «y», y asi la mitad lexica queda muerta: el tecnico describe la
    falla con sus palabras y casi nunca acierta todas las del informe —«gotea
    aceite por el cilindro» contra «fuga de aceite en el cilindro» exige
    «gotea», que no esta, y el ranking entero da cero—. Con «o», cada palabra
    que si coincide suma.

    El orden de los parametros es: vector, consulta, filtros y limite.
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

    if not lexico:
        # Sin la mitad lexica: para una base sin diccionario español, o para
        # medir cuanto aporta cada mitad.
        return (
            f"SELECT {COLUMNAS}, 1 - (embedding <=> %s::vector) AS similitud,"
            f" 0.0 AS lexico\n"
            f"FROM {tabla}\n"
            f"{donde}\n"
            f"ORDER BY embedding <=> %s::vector\n"
            f"LIMIT %s"
        ), parametros

    return (
        f"WITH puntuado AS (\n"
        f"  SELECT {COLUMNAS},\n"
        f"         1 - (embedding <=> %s::vector) AS similitud,\n"
        f"         ts_rank_cd(to_tsvector('spanish', texto), {CONSULTA_O}) AS crudo\n"
        f"  FROM {tabla}\n"
        f"  {donde}\n"
        f"), normalizado AS (\n"
        f"  SELECT {COLUMNAS}, similitud,\n"
        f"         CASE WHEN max(crudo) OVER () > 0\n"
        f"              THEN crudo / max(crudo) OVER () ELSE 0 END AS lexico\n"
        f"  FROM puntuado\n"
        f")\n"
        f"SELECT {COLUMNAS}, similitud, lexico\n"
        f"FROM normalizado\n"
        f"ORDER BY {PESO_VECTOR} * greatest(similitud, 0) + {PESO_LEXICO} * lexico DESC,\n"
        f"         id\n"
        f"LIMIT %s"
    ), parametros


class AlmacenPgvector:
    """Busqueda vectorial contra PostgreSQL. Misma firma que `Indice.buscar`."""

    def __init__(self, embebedor: embeddings.Embebedor | None = None,
                 dsn: str | None = None, tabla: str = TABLA, conexion=None,
                 lexico: bool = True):
        self.embebedor = embebedor or embeddings.EmbebedorLocal()
        self.tabla = tabla
        self.dsn = dsn or os.getenv("FIXMATE_PG_DSN") or ""
        self.lexico = lexico
        self._conexion = conexion
        self._fragmentos: list[Fragmento] | None = None
        # Para que el motor la trate igual que a un indice de archivo.
        self.fuentes: dict[str, str] = {}
        self.medicion: dict | None = None

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
            self._conexion = (psycopg2.connect(self.dsn) if self.dsn
                              else psycopg2.connect())
            # Leer tambien abre transaccion, y una que nadie cierra deja la
            # sesion «idle in transaction»: mantiene cerrojos sobre la tabla
            # —un ALTER o un DROP se quedan esperando para siempre— y congela
            # la instantanea, asi que el servidor no puede limpiar lo viejo.
            # Con esto, cada lectura empieza y termina sola; las escrituras
            # abren su transaccion a mano.
            self._conexion.autocommit = True
        except Exception as exc:
            raise ErrorAlmacen(f"no se pudo conectar a PostgreSQL: {exc}") from exc
        return self._conexion

    def buscar(self, consulta: str, limite: int = 3, filtros: dict | None = None,
               umbral: float = 0.0, preferencias: dict | None = None,
               acepta=None) -> list[Coincidencia]:
        """Los `limite` fragmentos mas parecidos, mejor primero.

        Misma firma y misma mezcla que `Indice.buscar`, para que el motor no
        tenga que saber cual de los dos tiene delante.
        """
        from .indice import BONO_PREFERENCIA, _preferencias_que_casan

        vector = literal_vector(self.embebedor.embeber([consulta])[0])
        sql, parametros = sql_busqueda(filtros, self.tabla, self.lexico)
        # Se piden mas filas de las que se devuelven: el bono por equipo y la
        # regla de aceptacion se aplican aqui y pueden mover el orden.
        pedidas = max(limite * 4, 20) if (preferencias or acepta) else limite
        conexion = self.conectar()
        try:
            with conexion.cursor() as cur:
                if self.lexico:
                    cur.execute(sql, [vector, consulta, *parametros, pedidas])
                else:
                    cur.execute(sql, [vector, *parametros, vector, pedidas])
                filas = cur.fetchall()
        except Exception as exc:
            raise ErrorAlmacen(f"la busqueda en PostgreSQL fallo: {exc}") from exc

        coincidencias = []
        for fila in filas:
            id_, texto, fuente, tipo, metadatos, similitud, lexico = fila
            if isinstance(metadatos, str):
                metadatos = json.loads(metadatos)
            fragmento = Fragmento(id=str(id_), texto=texto or "", fuente=fuente or "",
                                  tipo=tipo or "documento", metadatos=metadatos or {})
            if acepta is not None and not acepta(fragmento):
                continue
            similitud, lexico = float(similitud), float(lexico or 0.0)
            puntaje = PESO_VECTOR * max(similitud, 0.0) + PESO_LEXICO * lexico
            puntaje = min(1.0, puntaje + BONO_PREFERENCIA * _preferencias_que_casan(
                fragmento, preferencias))
            if puntaje < umbral:
                continue
            coincidencias.append(Coincidencia(fragmento, round(similitud, 4),
                                              round(lexico, 4), round(puntaje, 4)))
        coincidencias.sort(key=lambda c: (-c.puntaje, c.fragmento.id))
        return coincidencias[:limite]

    @property
    def fragmentos(self) -> list[Fragmento]:
        """Los fragmentos sin sus vectores, para lo que no se hace en SQL.

        El clasificador de causas y la prediccion recorren el corpus entero:
        el primero cuenta palabras por causa y la segunda ordena fechas. Eso
        no se expresa en una consulta por vecino mas cercano, asi que se trae
        el texto —sin los vectores, que son el 76% del peso— una sola vez y
        se guarda mientras viva el proceso.
        """
        if self._fragmentos is None:
            self._fragmentos = self.cargar_fragmentos()
        return self._fragmentos

    def cargar_fragmentos(self, limite: int | None = None) -> list[Fragmento]:
        conexion = self.conectar()
        sql = f"SELECT {COLUMNAS} FROM {self.tabla} ORDER BY id"
        if limite:
            sql += f" LIMIT {int(limite)}"
        try:
            with conexion.cursor() as cur:
                cur.execute(sql)
                filas = cur.fetchall()
        except Exception as exc:
            raise ErrorAlmacen(f"no se pudo leer la tabla {self.tabla}: {exc}") from exc

        salida = []
        for id_, texto, fuente, tipo, metadatos in filas:
            if isinstance(metadatos, str):
                metadatos = json.loads(metadatos)
            salida.append(Fragmento(id=str(id_), texto=texto or "",
                                    fuente=fuente or "", tipo=tipo or "documento",
                                    metadatos=metadatos or {}))
        return salida

    def __len__(self) -> int:
        conexion = self.conectar()
        try:
            with conexion.cursor() as cur:
                cur.execute(f"SELECT count(*) FROM {self.tabla}")
                return int(cur.fetchone()[0])
        except Exception as exc:
            raise ErrorAlmacen(f"no se pudo contar {self.tabla}: {exc}") from exc

    def crear_esquema(self) -> None:
        """Crea la tabla y sus indices si no estan. Idempotente."""
        conexion = self.conectar()
        try:
            with conexion:                       # una transaccion, explicita
                with conexion.cursor() as cur:
                    cur.execute(DDL)
        except Exception as exc:
            raise ErrorAlmacen(
                f"no se pudo crear el esquema: {exc}\n"
                "Si es por la extension, instalela primero: "
                "CREATE EXTENSION vector; necesita permiso de superusuario."
            ) from exc

    def agregar(self, fragmentos) -> int:
        """Alias de `guardar_fragmentos`, para la firma de `Indice`."""
        nuevos = self.guardar_fragmentos(fragmentos)
        self._fragmentos = None      # lo cargado se quedo viejo
        return nuevos

    def guardar_fragmentos(self, fragmentos) -> int:
        """Inserta o actualiza fragmentos ya vectorizados."""
        # Se materializa: un generador se agota en el primer recorrido y los
        # dos siguientes no insertarian nada, devolviendo 0 sin error.
        fragmentos = list(fragmentos)
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
            with conexion:                       # o entran todos, o ninguno
                with conexion.cursor() as cur:
                    for f in fragmentos:
                        cur.execute(sql, (f.id, f.texto, f.fuente, f.tipo,
                                          json.dumps(f.metadatos, ensure_ascii=False),
                                          literal_vector(f.vector)))
        except Exception as exc:
            raise ErrorAlmacen(f"no se pudieron guardar los fragmentos: {exc}") from exc
        self._fragmentos = None
        return len(fragmentos)


    def cerrar(self) -> None:
        """Suelta la conexion. La siguiente operacion abre otra."""
        if self._conexion is not None:
            try:
                self._conexion.close()
            finally:
                self._conexion = None


def desde_indice(indice, almacen: "AlmacenPgvector") -> int:
    """Sube a PostgreSQL lo que ya esta en un indice de archivo.

    Es el camino normal: se indexa en la oficina con `nefer fixmate indexar`,
    que es lo que sabe leer Excel, Word y PDF, y lo indexado se sube. La base
    no lee documentos; guarda lo que ya se leyo.
    """
    almacen.crear_esquema()
    if almacen.embebedor.nombre != getattr(indice.embebedor, "nombre", ""):
        raise ErrorAlmacen(
            f"el indice se armo con '{indice.embebedor.nombre}' y el almacen usa "
            f"'{almacen.embebedor.nombre}'. Mezclar embebedores no da error: da "
            "resultados sin sentido.")
    return almacen.guardar_fragmentos(indice.fragmentos)
