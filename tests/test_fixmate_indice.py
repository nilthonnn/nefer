"""El indice: que encuentre, que descarte y que sobreviva al viaje a disco.

La busqueda es hibrida a proposito, y las dos mitades se prueban por separado:
el BM25 tiene que encontrar un numero de parte exacto y el vector tiene que
encontrar una falla descrita con otras palabras. Si una de las dos deja de
aportar, estas pruebas lo dicen antes que el tecnico.
"""

import json

import pytest

from nefer.fixmate import embeddings
from nefer.fixmate.almacen_pg import literal_vector, sql_busqueda
from nefer.fixmate.indice import ErrorIndice, Fragmento, Indice


def _indice() -> Indice:
    indice = Indice()
    indice.agregar([
        Fragmento(id="a", texto="Filtro de aire colmatado por polvo de mina; humo "
                                "negro al tomar carga. Repuesto P533781.",
                  tipo="informe", fuente="historial.json",
                  metadatos={"codigo_ot": "OT-1", "codigos_dtc": ["P0300"],
                             "codigo_equipo": "GE074-01"}),
        Fragmento(id="b", texto="Fuga de aceite hidraulico en el cilindro del brazo "
                                "por sello de vastago cortado.",
                  tipo="informe", fuente="historial.json",
                  metadatos={"codigo_ot": "OT-2", "codigos_dtc": [],
                             "codigo_equipo": "EX336-03"}),
        Fragmento(id="c", texto="Electrolito de baterias por debajo de 1.220 de "
                                "densidad; bornes sulfatados.",
                  tipo="manual", fuente="manual.md",
                  metadatos={"seccion": "Sistema electrico"}),
    ])
    return indice


def test_encuentra_el_antecedente_por_la_descripcion_de_la_falla():
    resultados = _indice().buscar("humo negro al tomar carga", limite=1)
    assert resultados[0].fragmento.id == "a"


def test_el_numero_de_parte_exacto_lo_encuentra_el_lexico():
    resultados = _indice().buscar("P533781", limite=1)
    assert resultados[0].fragmento.id == "a"
    assert resultados[0].lexico > 0, "un numero de parte se encuentra por texto exacto"


def test_el_vector_empareja_lo_que_se_dice_distinto():
    # 'fugas hidraulicas' no comparte ninguna palabra exacta con el fragmento
    # ('fuga', 'hidraulico'), asi que aqui el que trabaja es el vector.
    resultados = _indice().buscar("fugas hidraulicas en cilindros", limite=1)
    assert resultados[0].fragmento.id == "b"
    assert resultados[0].similitud > 0


def test_el_filtro_por_codigo_de_falla_descarta_lo_demas():
    resultados = _indice().buscar("problema en el equipo", limite=5,
                                  filtros={"codigos_dtc": "P0300"})
    assert [r.fragmento.id for r in resultados] == ["a"]


def test_un_filtro_sin_coincidencias_no_devuelve_nada():
    assert _indice().buscar("humo negro", filtros={"codigos_dtc": "U1234"}) == []


def test_las_preferencias_empujan_pero_no_descartan():
    indice = _indice()
    sin = indice.buscar("revision general del equipo", limite=3)
    con = indice.buscar("revision general del equipo", limite=3,
                        preferencias={"codigo_equipo": "EX336-03"})
    assert {r.fragmento.id for r in sin} == {r.fragmento.id for r in con}
    assert con[0].fragmento.id == "b", "el equipo preferido tiene que subir"
    # El manual no declara equipo y aun asi sigue estando: descartarlo dejaria
    # al tecnico sin el procedimiento.
    assert "c" in {r.fragmento.id for r in con}


def test_el_umbral_deja_fuera_lo_que_no_se_parece():
    assert _indice().buscar("kilometraje del camion de rampa", umbral=0.9) == []


def test_mismo_indice_mismo_orden():
    uno = [r.fragmento.id for r in _indice().buscar("aceite", limite=3)]
    otro = [r.fragmento.id for r in _indice().buscar("aceite", limite=3)]
    assert uno == otro


def test_indexar_dos_veces_lo_mismo_no_duplica_el_antecedente():
    indice = _indice()
    repetido = Fragmento(id="a", texto="Filtro de aire colmatado, version corregida.",
                         tipo="informe", metadatos={"codigo_ot": "OT-1"})
    agregados = indice.agregar([repetido])

    assert agregados == 0 and len(indice) == 3
    assert indice.buscar("filtro de aire", limite=2)[0].fragmento.texto.endswith(
        "version corregida.")


def test_ida_y_vuelta_a_disco(tmp_path):
    original = _indice()
    ruta = original.guardar(tmp_path / "indice.json")
    recuperado = Indice.cargar(ruta)

    assert len(recuperado) == len(original)
    esperado = [r.fragmento.id for r in original.buscar("humo negro", limite=3)]
    assert [r.fragmento.id for r in recuperado.buscar("humo negro", limite=3)] == esperado


def test_buscar_con_otro_embebedor_es_un_error_y_no_un_resultado_raro(tmp_path):
    ruta = _indice().guardar(tmp_path / "indice.json")
    otro = embeddings.EmbebedorLocal(dimension=64)
    with pytest.raises(ErrorIndice, match="se indexo con"):
        Indice.cargar(ruta, embebedor=otro)


def test_un_indice_de_otra_version_no_se_lee_a_medias(tmp_path):
    ruta = tmp_path / "viejo.json"
    ruta.write_text(json.dumps({"version": 0, "fragmentos": []}), encoding="utf-8")
    with pytest.raises(ErrorIndice, match="formato"):
        Indice.cargar(ruta)


def test_indice_inexistente_dice_como_construirlo(tmp_path):
    with pytest.raises(ErrorIndice, match="nefer fixmate indexar"):
        Indice.cargar(tmp_path / "no-esta.json")


# --------------------------------------------------------------- pgvector

def test_el_vector_va_a_postgres_con_la_sintaxis_de_pgvector():
    assert literal_vector([0.5, -0.25]) == "[0.500000,-0.250000]"


def test_los_filtros_viajan_como_parametros_y_no_pegados_al_sql():
    sql, parametros = sql_busqueda({"codigos_dtc": "P0300'; DROP TABLE x;--"})
    assert "DROP TABLE" not in sql
    assert "P0300'; DROP TABLE x;--" in parametros
    assert sql.count("%s") == len(parametros) + 3   # vector, vector y limite


def test_sin_filtros_no_hay_clausula_where():
    sql, parametros = sql_busqueda(None)
    assert "WHERE" not in sql and parametros == []
