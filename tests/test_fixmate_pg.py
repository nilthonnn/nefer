"""FixMate sobre PostgreSQL con pgvector, contra una base de verdad.

Es el camino para cuando el historial deja de caber en un archivo: varios
talleres escribiendo a la vez, una flota entera. La interfaz es la misma que
la del índice en archivo —el motor no distingue cuál tiene delante— y eso es
justamente lo que hay que comprobar, porque es lo que se rompe en silencio.

Sin base delante las pruebas se saltan. En CI hay una, y ahí `FIXMATE_PG_EXIGIR`
convierte el salto en fallo: una suite que se salta sola pasa igual, y es la
peor forma de fallar.

Para correrlas en local:

    docker run --rm -e POSTGRES_PASSWORD=x -p 5433:5432 pgvector/pgvector:pg16
    FIXMATE_PG_DSN="host=localhost port=5433 user=postgres password=x" \\
        python -m pytest tests/test_fixmate_pg.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
EJEMPLOS = RAIZ / "ejemplos" / "fixmate"

DSN = os.getenv("FIXMATE_PG_DSN", "")
EXIGIR = os.getenv("FIXMATE_PG_EXIGIR", "") not in ("", "0", "no")


def _saltar(motivo: str):
    # En CI la base tiene que estar: ahí, no poder conectar es un fallo.
    if EXIGIR:
        pytest.fail(f"FIXMATE_PG_EXIGIR está puesto y {motivo}")
    pytest.skip(motivo)


@pytest.fixture(scope="module")
def almacen():
    if not DSN:
        _saltar("no hay FIXMATE_PG_DSN")
    try:
        import psycopg2                                        # noqa: F401
    except ImportError:
        _saltar("no está psycopg2")

    from nefer.fixmate.almacen_pg import AlmacenPgvector, ErrorAlmacen

    # Tabla propia de esta corrida: dos suites a la vez no se pisan.
    tabla = f"fixmate_pruebas_{os.getpid()}"
    tienda = AlmacenPgvector(dsn=DSN, tabla=tabla)
    try:
        tienda.crear_esquema()
    except ErrorAlmacen as exc:
        _saltar(f"no se pudo preparar la base: {exc}")

    # `crear_esquema` crea la tabla del nombre por defecto; para la de la
    # prueba se copia su forma.
    conexion = tienda.conectar()
    with conexion.cursor() as cur:
        cur.execute(f"CREATE TABLE IF NOT EXISTS {tabla} "
                    f"(LIKE fixmate_fragmentos INCLUDING ALL)")
    conexion.commit()
    try:
        yield tienda
    finally:
        # Si alguna conexión quedara abierta con la tabla tomada, esto se
        # quedaría esperando para siempre: el almacén no deja transacciones
        # abiertas, y el tiempo de espera lo confirma en vez de colgar la suite.
        with conexion.cursor() as cur:
            cur.execute("SET lock_timeout = '10s'")
            cur.execute(f"DROP TABLE IF EXISTS {tabla}")
        tienda.cerrar()


@pytest.fixture(scope="module")
def indice_local():
    from nefer.fixmate import Indice, Motor, actualizar

    indice = Indice()
    actualizar(indice, [EJEMPLOS])
    indice.medicion = Motor(indice).medicion()
    return indice


@pytest.fixture(scope="module")
def cargado(almacen, indice_local):
    from nefer.fixmate.almacen_pg import desde_indice

    desde_indice(indice_local, almacen)
    return almacen


CONSULTAS = [
    "gotea aceite por el cilindro del brazo toda la noche",
    "sale humo negro y pierde fuerza en la subida",
    "no arranca en la mañana y el arranque gira lento",
    "el mastil de la torre no sube",
]


def test_lo_indexado_en_la_oficina_sube_entero(cargado, indice_local):
    assert len(cargado) == len(indice_local)


def test_subir_dos_veces_no_duplica(cargado, indice_local):
    from nefer.fixmate.almacen_pg import desde_indice

    antes = len(cargado)
    desde_indice(indice_local, cargado)
    assert len(cargado) == antes


def test_no_se_pueden_mezclar_embebedores(cargado, indice_local):
    # Mezclarlos no da error al buscar: da resultados sin sentido.
    from nefer.fixmate import embeddings
    from nefer.fixmate.almacen_pg import AlmacenPgvector, ErrorAlmacen, desde_indice

    otro = AlmacenPgvector(embebedor=embeddings.EmbebedorLocal(dimension=64),
                           dsn=DSN, tabla=cargado.tabla)
    try:
        with pytest.raises(ErrorAlmacen, match="Mezclar embebedores"):
            desde_indice(indice_local, otro)
    finally:
        otro.cerrar()


@pytest.mark.parametrize("consulta", CONSULTAS)
def test_la_base_y_el_archivo_contestan_lo_mismo(cargado, indice_local, consulta):
    """El primer antecedente tiene que ser el mismo por los dos caminos.

    Los puntajes no: la mitad léxica es BM25 en el archivo y la búsqueda de
    texto de PostgreSQL en la base, dos implementaciones distintas de la
    misma idea. Lo que tiene que coincidir es a quién señalan.
    """
    del_archivo = indice_local.buscar(consulta, limite=3, umbral=0.20)
    de_la_base = cargado.buscar(consulta, limite=3, umbral=0.20)

    assert de_la_base, "la base no devolvió nada"
    assert de_la_base[0].fragmento.id == del_archivo[0].fragmento.id


def test_lo_que_no_tiene_antecedente_tampoco_lo_tiene_en_la_base(cargado):
    assert cargado.buscar("tramites de aduana del contenedor", umbral=0.20) == []


def test_el_filtro_por_codigo_de_falla_se_aplica_en_sql(cargado):
    resultados = cargado.buscar("problema en el equipo", limite=10,
                                filtros={"codigos_dtc": "P0300"})
    assert resultados
    for c in resultados:
        assert "P0300" in c.fragmento.metadatos.get("codigos_dtc", [])


def test_un_codigo_dictado_con_cualquier_cosa_dentro_no_toca_la_base(cargado):
    # El filtro viaja como parámetro: esto tiene que devolver vacío, no
    # borrar la tabla.
    assert cargado.buscar("humo negro", filtros={
        "codigos_dtc": "P0300'; DROP TABLE fixmate_pruebas; --"}) == []
    assert len(cargado) > 0


def test_las_preferencias_suben_lo_del_equipo_sin_esconder_lo_demas(cargado):
    """Preferir no es filtrar: sube lo de esa máquina y no quita nada.

    Tampoco le gana a un antecedente que encaje mucho mejor —el bono es de
    0,08—, y eso es lo correcto: si la respuesta está en otro equipo de la
    flota, taparla por no ser de este sería peor que no ordenar.
    """
    def posicion(resultados, equipo):
        for n, c in enumerate(resultados):
            if c.fragmento.metadatos.get("codigo_equipo") == equipo:
                return n
        return len(resultados)

    sin = cargado.buscar("fuga de aceite hidraulica", limite=5)
    con = cargado.buscar("fuga de aceite hidraulica", limite=5,
                         preferencias={"codigo_equipo": "EX336-01"})

    assert {c.fragmento.id for c in sin} == {c.fragmento.id for c in con}
    assert posicion(con, "EX336-01") < posicion(sin, "EX336-01")


def test_la_regla_en_python_tambien_filtra_lo_que_trae_la_base(cargado):
    solo_manual = cargado.buscar("apriete del prisionero", limite=5,
                                 acepta=lambda f: f.tipo == "manual")
    assert solo_manual
    assert all(c.fragmento.tipo == "manual" for c in solo_manual)


def test_el_motor_entero_funciona_contra_la_base(cargado):
    """Diagnóstico, clasificador y evidencia, sin que el motor sepa dónde está."""
    from nefer.fixmate import Motor
    from nefer.fixmate.motor import Consulta

    diagnostico = Motor(cargado).consultar(
        Consulta("gotea aceite por el cilindro del brazo"))

    assert "Sello del vástago" in diagnostico.causa_raiz_mas_probable
    assert diagnostico.pasos_recomendados
    assert diagnostico.evidencia_historica[0].codigo_ot == "OT-2026-0501"
    # El clasificador se entrena con lo que hay en la tabla.
    assert diagnostico.causas_probables
    assert diagnostico.precision_medida["casos"] == 14


def test_la_prediccion_lee_las_fechas_de_la_base(cargado):
    import datetime as dt

    from nefer.fixmate import prediccion

    parte = prediccion.pronostico(cargado, "GE074-01", dt.date(2026, 9, 15))
    assert parte.eventos > 0
    assert any("Filtro de aire" in r.causa for r in parte.reincidencias)


def test_sin_la_mitad_lexica_sigue_contestando(cargado):
    """Una base sin diccionario español no deja a nadie sin diagnóstico."""
    from nefer.fixmate.almacen_pg import AlmacenPgvector

    solo_vector = AlmacenPgvector(dsn=DSN, tabla=cargado.tabla, lexico=False)
    try:
        resultados = solo_vector.buscar("gotea aceite por el cilindro del brazo",
                                        limite=3)
        assert resultados
        assert all(c.lexico == 0.0 for c in resultados)
    finally:
        solo_vector.cerrar()


def test_el_esquema_se_crea_en_la_tabla_que_se_pidio(almacen):
    """`--tabla taller_norte` creaba `fixmate_fragmentos` y fallaba al insertar."""
    from nefer.fixmate.almacen_pg import AlmacenPgvector, ErrorAlmacen

    tabla = f"fixmate_otra_{os.getpid()}"
    otra = AlmacenPgvector(dsn=DSN, tabla=tabla)
    try:
        otra.crear_esquema()          # sin CREATE TABLE a mano de por medio
        assert len(otra) == 0
        conexion = otra.conectar()
        with conexion.cursor() as cur:
            cur.execute("SELECT to_regclass(%s)", (tabla,))
            assert cur.fetchone()[0] is not None, "no creó la tabla pedida"
    finally:
        with otra.conectar().cursor() as cur:
            cur.execute("SET lock_timeout = '10s'")
            cur.execute(f"DROP TABLE IF EXISTS {tabla}")
        otra.cerrar()


def test_un_nombre_de_tabla_con_cualquier_cosa_dentro_no_llega_al_sql():
    """El nombre se interpola —PostgreSQL no lo admite como parámetro—, así
    que se valida antes de pegarlo."""
    from nefer.fixmate.almacen_pg import AlmacenPgvector, ErrorAlmacen

    for veneno in ("x; DROP TABLE fixmate_fragmentos; --", "a b", '"x"', ""):
        with pytest.raises(ErrorAlmacen, match="nombre de tabla"):
            AlmacenPgvector(dsn="", tabla=veneno)


def test_cerrar_el_circulo_contra_la_base_no_revienta(cargado, tmp_path):
    """Registrar desde el patio con el almacén en PostgreSQL.

    `registrar()` anota la firma del historial y la API guarda el índice.
    Sin esos dos métodos reventaba con AttributeError *después* de haber
    escrito el historial: el técnico veía un 500, reintentaba, y el reintento
    se rechazaba por duplicado. El informe quedaba escrito y sin indexar.
    """
    from nefer.fixmate import cierre

    historial = tmp_path / "historial.json"
    guardado = cierre.registrar(
        {"resumen_falla": "gotea aceite por el cilindro del brazo",
         "causa_raiz": "Sello del vástago vencido",
         "solucion_aplicada": "Cambio de sello"},
        historial, indice=cargado)

    assert guardado["codigo_ot"]
    cargado.guardar(historial)        # existe y no hace nada: ya está escrito
    assert cargado.fuentes[str(historial)]
    # Y lo registrado se encuentra en el acto, que es para lo que se registra.
    assert any(guardado["codigo_ot"] in c.fragmento.id
               for c in cargado.buscar("gotea aceite por el cilindro", limite=5))
